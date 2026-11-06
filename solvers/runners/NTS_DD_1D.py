from enum import Enum
import math
import numpy as np
import pandas as pd
import logging
import re
from time import time
from datetime import datetime


from .cuadraturas import DATA

logger = logging.getLogger(__name__)


class Method(Enum):
    """Spatial discretization scheme used in the cell sweep."""

    DD = "DD"
    STEP = "STEP"
    STEP_CHARACTERISTIC = "SC"


def method_from_name(name) -> Method:
    """Parse a scheme name into a Method, rejecting unknown values."""
    if isinstance(name, Method):
        return name
    text = str(name).strip().upper()
    aliases = {
        "DD": Method.DD,
        "STEP": Method.STEP,
        "SC": Method.STEP_CHARACTERISTIC,
        "STEP_CHARACTERISTIC": Method.STEP_CHARACTERISTIC,
        "STEP-CHARACTERISTIC": Method.STEP_CHARACTERISTIC,
    }
    try:
        return aliases[text]
    except KeyError:
        options = sorted(method.value for method in Method)
        raise ValueError(
            f"Invalid SPATIAL_SCHEME: {name!r}. Options: {options}"
        ) from None


def theta_step_characteristic(alpha: float) -> float:
    """Characteristic weighting theta = coth(alpha/2) - 2/alpha.

    ``alpha`` is the cell optical thickness Sigma_t*dx/|mu|.  The series
    expansion avoids catastrophic cancellation as alpha -> 0.
    """
    alpha = float(alpha)
    if alpha < 0.0:
        raise ValueError(f"Optical thickness must be >= 0, got {alpha!r}.")
    if not math.isfinite(alpha):
        if math.isinf(alpha):
            return 1.0
        raise ValueError(f"Optical thickness must be finite, got {alpha!r}.")
    if alpha == 0.0:
        return 0.0
    if alpha < 1.0e-3:
        a2 = alpha * alpha
        return alpha / 6.0 - alpha * a2 / 360.0 + alpha * a2 * a2 / 15120.0
    return 1.0 / math.tanh(0.5 * alpha) - 2.0 / alpha


def _cell_out_dd(psi_in, source, sigma_t, dx, mu, theta=None):
    """Diamond Difference outgoing angular flux."""
    a = mu / dx
    return ((a - 0.5 * sigma_t) * psi_in + source) / (a + 0.5 * sigma_t)


def _cell_out_step(psi_in, source, sigma_t, dx, mu, theta=None):
    """Step (implicit upwind) outgoing angular flux."""
    a = mu / dx
    return (a * psi_in + source) / (a + sigma_t)


def _cell_out_sc(psi_in, source, sigma_t, dx, mu, theta=None):
    """Step Characteristic outgoing angular flux."""
    if theta is None:
        theta = theta_step_characteristic(sigma_t * dx / mu)
    a = mu / dx
    return ((a - 0.5 * sigma_t * (1.0 - theta)) * psi_in + source) / (
        a + 0.5 * sigma_t * (1.0 + theta)
    )


_CELL_KERNELS = {
    Method.DD: _cell_out_dd,
    Method.STEP: _cell_out_step,
    Method.STEP_CHARACTERISTIC: _cell_out_sc,
}


def cell_out(psi_in, source, sigma_t, dx, mu, method, theta=None):
    """Outgoing angular flux of a cell for the selected scheme.

    ``mu`` is the direction cosine magnitude; a negative value is
    normalised to |mu|.  ``source`` is the full isotropic right-hand side
    (it already includes the 1/2 factors of scattering, fission and Q).
    """
    mu = abs(float(mu))
    if mu == 0.0:
        raise ValueError("|mu| must be > 0 to sweep a cell.")
    try:
        kernel = _CELL_KERNELS[method_from_name(method)]
    except KeyError:
        raise ValueError(f"Unknown spatial method: {method!r}") from None
    return kernel(psi_in, source, sigma_t, dx, mu, theta)


def _cell_avg_dd(psi_in, psi_out, sigma_t, dx, mu, theta=None):
    """DD cell average (arithmetic mean of the two interfaces)."""
    return 0.5 * (psi_in + psi_out)


def _cell_avg_step(psi_in, psi_out, sigma_t, dx, mu, theta=None):
    """STEP cell average (downstream face value)."""
    return psi_out


def _cell_avg_sc(psi_in, psi_out, sigma_t, dx, mu, theta=None):
    """SC cell average (characteristic-weighted interfaces)."""
    if theta is None:
        theta = theta_step_characteristic(sigma_t * dx / mu)
    return 0.5 * (1.0 + theta) * psi_out + 0.5 * (1.0 - theta) * psi_in


_CELL_AVERAGES = {
    Method.DD: _cell_avg_dd,
    Method.STEP: _cell_avg_step,
    Method.STEP_CHARACTERISTIC: _cell_avg_sc,
}


def cell_average(psi_in, psi_out, sigma_t, dx, mu, method, theta=None):
    """Cell-averaged angular flux psi_bar for the selected scheme.

    ``psi_in``/``psi_out`` are the incoming/outgoing interface values in
    the direction of travel, so ``psi_out`` is always the downstream face.
    DD and STEP are explicit; SC uses the characteristic weight ``theta``
    (computed from the optical thickness when omitted).
    """
    mu = abs(float(mu))
    if mu == 0.0:
        raise ValueError("|mu| must be > 0 to average a cell.")
    method = method_from_name(method)
    try:
        average = _CELL_AVERAGES[method]
    except KeyError:
        raise ValueError(f"Unknown spatial method: {method!r}") from None
    return average(psi_in, psi_out, sigma_t, dx, mu, theta)


# =================================================================
# Paso A: Configuración
# =================================================================
class Config:
    def __init__(
        self,
        epsilon: float = 1e-5,
        max_iter: int = 2000,
        manual: bool = True,
        allow_placeholders: bool = False,
        **kwargs,
    ):
        # Limpiamos handlers previos para evitar duplicidad en logs
        for handler in logging.root.handlers[:]:
            handler.close()
            logging.root.removeHandler(handler)
        logging.basicConfig(filename="Config.log", level=logging.INFO, filemode="w")
        self.num_regions = 0
        self.num_zones = 0
        self.bound_left = None
        self.bound_right = None
        self.allow_placeholders = allow_placeholders
        self.placeholder_names: set[str] = set()

        # --- Medio multiplicativo (fisión) ---
        self.MODE = None
        self.NU_SIGF = None
        self.SIGMA_F = None
        self.K_EFF = None
        self.TOL_K = 1e-6
        self.MAX_OUTER = 200
        self.K0 = None
        self.POWER_KW = None
        self.E_F_MEV = 200.0
        self.NU = None
        self.AREA_CM2 = 1.0

        # ---- Spatial discretization scheme ----
        self.SPATIAL_SCHEME = Method.DD.value

        if manual:
            if self.num_regions == 0:
                self.regiones_input()

            if self.num_zones == 0:
                self.zones_input()

            self.manual_input()
        else:
            self.auto_input(kwargs)

        self.epsilon = epsilon
        self.max_iter = max_iter

        if not self.has_placeholders:
            self.prelim_calculations()

    @property
    def method(self) -> Method:
        """Spatial scheme as a Method, derived from SPATIAL_SCHEME.

        Keeping a single source of truth means the string written to JSON
        and the enum used by the solver cannot diverge silently.
        """
        return method_from_name(self.SPATIAL_SCHEME)

    def set_spatial_scheme(self, name) -> None:
        """Normalise and store the spatial scheme."""
        self.SPATIAL_SCHEME = method_from_name(name).value

    def regiones_input(self):
        self.num_regions = int(input("\n Enter the number of Regions: "))

    def zones_input(self):
        self.num_zones = int(input("\n Enter the number of Zones: "))

    @property
    def has_placeholders(self) -> bool:
        """True if the user entered names such as kk/mm instead of numbers."""
        return bool(self.placeholder_names)

    @staticmethod
    def _as_int_array(values, name: str, positive: bool = False) -> np.ndarray:
        """Convert a list to ints, rejecting non-integers/unexpanded names."""
        try:
            raw = np.asarray(values, dtype=float)
        except TypeError, ValueError:
            raise ValueError(
                f"{name} must contain integers; if there are placeholders, "
                "expand them with nts-generate --json."
            ) from None
        if np.any(~np.isfinite(raw)):
            raise ValueError(f"{name} contains non-finite values.")
        if np.any(raw != np.floor(raw)):
            raise ValueError(f"{name} must contain integers.")
        ints = raw.astype(int)
        if positive and np.any(ints <= 0):
            raise ValueError(f"{name} must contain integers > 0.")
        return ints

    def _parse_number(
        self,
        text: str,
        integer: bool = False,
        allow_placeholder: bool = True,
    ):
        text = text.strip()
        if not text:
            return None
        if allow_placeholder and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", text):
            self.placeholder_names.add(text)
            return text
        try:
            return int(text) if integer else float(text)
        except ValueError:
            raise ValueError(f"Invalid value: {text!r}") from None

    def _prompt_number(
        self,
        prompt: str,
        default=None,
        integer: bool = False,
        allow_placeholder: bool | None = None,
    ):
        if allow_placeholder is None:
            allow_placeholder = self.allow_placeholders
        text = input(prompt).strip()
        if not text:
            if default is not None:
                return default
            raise ValueError(f"Value required: {prompt.strip()}")
        value = self._parse_number(
            text,
            integer=integer,
            allow_placeholder=allow_placeholder,
        )
        if value is None:
            if default is not None:
                return default
            raise ValueError(f"Value required: {prompt.strip()}")
        return value

    def auto_input(self, kwargs: dict):
        """Carga todos los datos desde un diccionario.

        Estructura esperada del diccionario:
        {
            'num_regions': int,
            'num_zones': int,
            'NC': list or np.array (cells per region),
            'HR': list o np.array (espesores en cm),
            'IZL': list or np.array (zone of each region),
            'SCT': list o np.array (sigma total por zona),
            'SCS': list o np.array (sigma scattering por zona),
            'Q': list or np.array (source per region),
            'N': int (orden cuadratura)
            'reflex_izq': bool (reflective or not)
            'reflex_der': bool (reflective or not)
            'bound_left': list (incoming flux per direction, length N/2)
            'bound_right': list (incoming flux per direction, length N/2)
            'SPATIAL_SCHEME': 'DD' | 'STEP' | 'SC' (default 'DD'),

            # --- opcionales: medio multiplicativo ---
            'NU_SIGF': list (nu * Sigma_f por zona, cm^-1),
            'SIGMA_F': list (Sigma_f por zona, cm^-1),
            'MODE': 'fixed_source' | 'fixed_k' | 'eigenvalue' | 'driven',
            'K_EFF': float | None,
            'TOL_K': float,
            'MAX_OUTER': int,
            'K0': float | None,
            'POWER_KW': float | None,
            'E_F_MEV': float,
            'NU': float | None,
            'AREA_CM2': float,
        }
        """
        print("\n--- LOADING CONFIGURATION FROM DICTIONARY ---")

        # Campos de datos obligatorios
        campos_datos = ["NC", "HR", "IZL", "SCT", "SCS", "Q", "N"]

        # Validar que estén presentes
        for campo in campos_datos:
            if campo not in kwargs:
                raise ValueError(f"Missing required field: '{campo}'")

        # Actualizar num_regions y num_zones si vienen en kwargs
        if "num_regions" in kwargs:
            self.num_regions = int(kwargs["num_regions"])
        if "num_zones" in kwargs:
            self.num_zones = int(kwargs["num_zones"])

        # Validación básica
        if self.num_regions <= 0:
            raise ValueError("num_regions must be >= 1.")
        if self.num_zones <= 0:
            raise ValueError("num_zones must be >= 1.")
        if self.num_zones > self.num_regions:
            raise ValueError("Number of zones cannot exceed the number of regions.")

        # Convertir a numpy arrays
        self.NC = self._as_int_array(kwargs["NC"], "NC", positive=True)
        try:
            self.HR = np.array(kwargs["HR"], dtype=float)
        except TypeError, ValueError:
            raise ValueError(
                "HR must contain numbers; if there are placeholders, expand them "
                "con nts-generate --json."
            ) from None
        if np.any(~np.isfinite(self.HR)) or np.any(self.HR <= 0):
            raise ValueError("HR must contain finite values > 0.")
        self.IZL = self._as_int_array(kwargs["IZL"], "IZL", positive=True)
        self.SCT = np.array(kwargs["SCT"], dtype=float)
        self.SCS = np.array(kwargs["SCS"], dtype=float)
        self.Q = np.array(kwargs["Q"], dtype=float)

        self.reflex_izq = bool(kwargs.get("reflex_izq", False))
        self.reflex_der = bool(kwargs.get("reflex_der", False))

        # Configurar cuadratura (N_HALF se necesita para los defaults de frontera)
        self.N = int(kwargs["N"])
        if self.N % 2 != 0:
            raise ValueError("Quadrature order must be an even number.")
        self.N_HALF: int = self.N // 2

        # Cargar direcciones y pesos
        self.weights_directions()

        # Fronteras: por defecto, flujo entrante nulo (vacío)
        default_bound = np.zeros(self.N_HALF)
        self.bound_left = np.array(kwargs.get("bound_left", default_bound), dtype=float)
        self.bound_right = np.array(
            kwargs.get("bound_right", default_bound), dtype=float
        )

        # --- Medio multiplicativo ---
        self.NU_SIGF = np.array(
            kwargs.get("NU_SIGF", np.zeros(self.num_zones)), dtype=float
        )
        sigma_f = kwargs.get("SIGMA_F")
        self.SIGMA_F = None if sigma_f is None else np.array(sigma_f, dtype=float)
        self.MODE = kwargs.get("MODE")
        self.K_EFF = kwargs.get("K_EFF")
        self.TOL_K = float(kwargs.get("TOL_K", 1e-6))
        self.MAX_OUTER = int(kwargs.get("MAX_OUTER", 200))
        self.K0 = kwargs.get("K0")
        self.POWER_KW = kwargs.get("POWER_KW")
        self.E_F_MEV = float(kwargs.get("E_F_MEV", 200.0))
        self.NU = kwargs.get("NU")
        self.AREA_CM2 = float(kwargs.get("AREA_CM2", 1.0))

        # --- Esquema de discretización espacial ---
        self.set_spatial_scheme(kwargs.get("SPATIAL_SCHEME", Method.DD.value))

        # Validaciones de dimensiones
        if len(self.NC) != self.num_regions:
            raise ValueError(f"NC must have {self.num_regions} elements")
        if len(self.HR) != self.num_regions:
            raise ValueError(f"HR must have {self.num_regions} elements")
        if len(self.IZL) != self.num_regions:
            raise ValueError(f"IZL must have {self.num_regions} elements")
        if len(self.SCT) != self.num_zones:
            raise ValueError(f"SCT must have {self.num_zones} elements")
        if len(self.SCS) != self.num_zones:
            raise ValueError(f"SCS must have {self.num_zones} elements")
        if len(self.Q) != self.num_regions:
            raise ValueError(f"Q must have {self.num_regions} elements")

        if not self.reflex_izq:
            if len(self.bound_left) != self.N_HALF:
                raise ValueError(f"bound_left must have {self.N_HALF} elements")
        if not self.reflex_der:
            if len(self.bound_right) != self.N_HALF:
                raise ValueError(f"bound_right must have {self.N_HALF} elements")

        # Validar que IZL hace referencia a zonas válidas (1-based)
        if np.any(self.IZL < 1) or np.any(self.IZL > self.num_zones):
            raise ValueError(f"IZL must contain values between 1 and {self.num_zones}")

        # Validaciones de fisión / modo
        self._validate_fission_config()

        # Cálculos preliminares
        self.prelim_calculations()

        print("✓ Configuration loaded successfully from dictionary")
        logger.info(f"Configuration loaded from dictionary.\n{self}")

    def _validate_fission_config(self):
        """Validate and normalize multiplicative-medium parameters."""
        if self.NU_SIGF is None:
            self.NU_SIGF = np.zeros(self.num_zones)
        if len(self.NU_SIGF) != self.num_zones:
            raise ValueError(f"NU_SIGF must have {self.num_zones} elements")
        if np.any(self.NU_SIGF < 0.0):
            raise ValueError("NU_SIGF must be >= 0 in all zones.")

        if self.SIGMA_F is not None:
            if len(self.SIGMA_F) != self.num_zones:
                raise ValueError(f"SIGMA_F must have {self.num_zones} elements")
            if np.any(self.SIGMA_F < 0.0):
                raise ValueError("SIGMA_F must be >= 0 in all zones.")
            if np.any(self.SIGMA_F > self.SCT):
                raise ValueError("SIGMA_F cannot exceed SCT.")

        if self.K_EFF is not None:
            self.K_EFF = float(self.K_EFF)
            if self.K_EFF <= 0.0:
                raise ValueError("K_EFF must be > 0.")
        if self.K0 is not None:
            self.K0 = float(self.K0)
            if self.K0 <= 0.0:
                raise ValueError("K0 must be > 0.")
        if self.TOL_K <= 0.0:
            raise ValueError("TOL_K must be > 0.")
        if self.MAX_OUTER <= 0:
            raise ValueError("MAX_OUTER must be >= 1.")

        has_fission = bool(np.any(self.NU_SIGF > 0.0))

        if self.POWER_KW is not None:
            self.POWER_KW = float(self.POWER_KW)
            if self.POWER_KW <= 0.0:
                raise ValueError("POWER_KW must be > 0.")
            if not has_fission:
                raise ValueError("POWER_KW requires NU_SIGF > 0.")
            if self.E_F_MEV <= 0.0:
                raise ValueError("E_F_MEV must be > 0.")
            if self.AREA_CM2 <= 0.0:
                raise ValueError("AREA_CM2 must be > 0.")
            if self.NU is not None:
                self.NU = float(self.NU)
                if self.NU <= 0.0:
                    raise ValueError("NU must be > 0.")
            if self.SIGMA_F is None and self.NU is None:
                raise ValueError(
                    "POWER_KW requires SIGMA_F per zone or NU (nu_bar) "
                    "para convertir NU_SIGF en Sigma_f."
                )

        # Inferencia del modo si no se indica explícitamente
        if self.MODE is None:
            if not has_fission:
                self.MODE = "fixed_source"
            elif self.K_EFF is None:
                self.MODE = "eigenvalue"
            else:
                self.MODE = "fixed_k"
        else:
            self.MODE = str(self.MODE).strip().lower()

        allowed = {"fixed_source", "fixed_k", "eigenvalue", "driven"}
        if self.MODE not in allowed:
            raise ValueError(f"Invalid MODE: {self.MODE!r}. Options: {sorted(allowed)}")

        left_external = bool(
            not self.reflex_izq
            and self.bound_left is not None
            and np.any(self.bound_left != 0.0)
        )
        right_external = bool(
            not self.reflex_der
            and self.bound_right is not None
            and np.any(self.bound_right != 0.0)
        )
        external_source = bool(np.any(self.Q != 0.0) or left_external or right_external)

        if self.MODE == "fixed_source":
            if has_fission:
                raise ValueError(
                    "MODE='fixed_source' exige NU_SIGF = 0. "
                    "Usa MODE='eigenvalue' o MODE='fixed_k'."
                )
            if self.K_EFF is not None:
                raise ValueError("MODE='fixed_source' does not use K_EFF.")

        elif self.MODE == "eigenvalue":
            if not has_fission:
                raise ValueError("MODE='eigenvalue' requires NU_SIGF > 0.")
            if self.K_EFF is not None:
                raise ValueError(
                    "MODE='eigenvalue' calcula k_eff; no impongas K_EFF. "
                    "Usa MODE='fixed_k' si quieres fijarlo."
                )
            if external_source:
                raise ValueError(
                    "MODE='eigenvalue' solves the homogeneous problem "
                    "(Q=0 and zero incoming flux). With a source use "
                    "MODE='fixed_k' o MODE='driven'."
                )

        elif self.MODE == "fixed_k":
            if not has_fission:
                raise ValueError("MODE='fixed_k' requires NU_SIGF > 0.")
            if self.K_EFF is None:
                raise ValueError("MODE='fixed_k' requires K_EFF > 0.")

        elif self.MODE == "driven":
            if not has_fission:
                raise ValueError("MODE='driven' requires NU_SIGF > 0.")
            if self.K_EFF is None:
                self.K_EFF = 1.0
            elif abs(self.K_EFF - 1.0) > 1e-12:
                raise ValueError(
                    "MODE='driven' uses the physical k = 1. "
                    "To scale fission use MODE='fixed_k'."
                )
            # En modo manual las fronteras aún pueden ser None (el Runner
            # preguntará el flujo entrante); en ese caso la comprobación
            # definitiva se hace en Runner._fixed_k_iteration.
            bounds_known = self.bound_left is not None and self.bound_right is not None
            if not external_source and bounds_known:
                raise ValueError(
                    "MODE='driven' requires Q != 0 or non-zero incoming flux."
                )

    def manual_input(self):
        """Carga interactiva paso a paso (incluye medios multiplicativos)."""
        print("\n--- SPATIAL CONFIGURATION ---")
        self.NC = np.array(
            [
                self._prompt_number(
                    f"Cells in Region {i + 1} (integer or placeholder, e.g. cc): ",
                    integer=True,
                    allow_placeholder=True,
                )
                for i in range(self.num_regions)
            ],
            dtype=object,
        )
        self.HR = np.array(
            [
                self._prompt_number(
                    f"Total thickness [cm] Region {i + 1} "
                    f"(number or placeholder, e.g. hh): "
                )
                for i in range(self.num_regions)
            ],
            dtype=object,
        )
        self.IZL = np.array(
            [
                self._prompt_number(
                    f"Material Zone ID Region {i + 1} (integer, 1-based): ",
                    integer=True,
                    allow_placeholder=False,
                )
                for i in range(self.num_regions)
            ],
            dtype=object,
        )

        print("\n--- MATERIAL CONFIGURATION ---")
        self.SCT = np.array(
            [
                self._prompt_number(f"Sigma_Total Zone {i + 1}: ")
                for i in range(self.num_zones)
            ],
            dtype=object,
        )
        self.SCS = np.array(
            [
                self._prompt_number(
                    f"Sigma_Scattering Zone {i + 1} (number or placeholder, e.g. kk): "
                )
                for i in range(self.num_zones)
            ],
            dtype=object,
        )

        print("\n--- QUADRATURE CONFIGURATION ---")
        self.N = self._prompt_number(
            "Quadrature order (2, 4, 6, 8) [8]: ",
            default=8,
            integer=True,
            allow_placeholder=False,
        )
        if self.N % 2 != 0:
            raise ValueError("Quadrature order must be even.")
        self.N_HALF = self.N // 2
        self.weights_directions()

        scheme_text = input("Spatial scheme (DD / STEP / SC) [DD]: ").strip()
        self.set_spatial_scheme(scheme_text or Method.DD.value)

        # Medio multiplicativo (opcional)
        self._fission_input()

        # Fuente externa: se pregunta después de conocer el modo
        if self.MODE == "eigenvalue":
            self.Q = np.zeros(self.num_regions)
            print("\nEigenvalue mode: Q = 0 (homogeneous problem).")
        else:
            print("\n--- FUENTE EXTERNA ---")
            self.Q = np.array(
                [
                    self._prompt_number(
                        f"Source (Q) Region {i + 1} [0]: ",
                        default=0.0,
                    )
                    for i in range(self.num_regions)
                ],
                dtype=object,
            )

        # Fronteras
        print("\n--- Boundary Conditions---")
        self.reflex_izq = input("Reflective left? (y/n) [n]: ").strip().lower() in {
            "y",
            "s",
        }
        self.reflex_der = input("Reflective right? (y/n) [n]: ").strip().lower() in {
            "y",
            "s",
        }
        self.bound_left = self._manual_boundary_values("izquierda", self.reflex_izq)
        self.bound_right = self._manual_boundary_values("derecha", self.reflex_der)

        if self.has_placeholders:
            print(
                "\nPlaceholders detectados: "
                + ", ".join(sorted(self.placeholder_names))
                + ". Numeric validation will run on expansion."
            )
        else:
            # Validar la combinación de modo/fuente también en modo manual
            self._validate_fission_config()

            # Cálculos preliminares
            self.prelim_calculations()

        logger.info(f"Configuration complete.\n{self}")

    def _manual_boundary_values(self, side: str, reflective: bool):
        """Prompt for the incoming flux at a boundary (N/2 values)."""
        if reflective:
            print(f"Boundary {side}: reflective; incoming flux = 0.")
            return np.zeros(self.N_HALF)
        if self.MODE == "eigenvalue":
            print(f"Boundary {side}: eigenvalue; incoming flux = 0.")
            return np.zeros(self.N_HALF)

        default = " ".join(["0"] * self.N_HALF)
        text = input(
            f"Incoming flux {side} ({self.N_HALF} values) [{default}]: "
        ).strip()
        if not text:
            return np.zeros(self.N_HALF)

        tokens = text.replace(",", " ").split()
        if len(tokens) != self.N_HALF:
            raise ValueError(f"Expected {self.N_HALF} values for boundary {side}.")
        values = [self._parse_number(token, allow_placeholder=True) for token in tokens]
        if any(isinstance(value, str) for value in values):
            return np.array(values, dtype=object)
        return np.array(values, dtype=float)

    def _fission_input(self):
        """Prompts for multiplicative media in manual mode."""
        self.NU_SIGF = np.array([0.0] * self.num_zones, dtype=object)
        self.SIGMA_F = None
        self.MODE = "fixed_source"
        self.K_EFF = None
        self.TOL_K = 1e-6
        self.MAX_OUTER = 200
        self.K0 = None
        self.POWER_KW = None
        self.E_F_MEV = 200.0
        self.NU = None
        self.AREA_CM2 = 1.0

        resp = input("Multiplicative medium (fission)? (y/n) [n]: ").strip().lower()
        if resp not in {"y", "s"}:
            print("fixed_source mode (no fission).")
            return

        for i in range(self.num_zones):
            self.NU_SIGF[i] = self._prompt_number(
                f"nu*Sigma_f Zone {i + 1} [cm^-1] (number or placeholder, e.g. mm): "
            )

        mode = (
            input("Mode (eigenvalue / fixed_k / driven) [eigenvalue]: ").strip().lower()
            or "eigenvalue"
        )
        if mode not in {"eigenvalue", "fixed_k", "driven"}:
            raise ValueError(f"Invalid mode: {mode}")
        self.MODE = mode

        if mode == "fixed_k":
            self.K_EFF = self._prompt_number("k_eff impuesto: ")
        elif mode == "driven":
            self.K_EFF = 1.0
            print(
                "driven mode: k = 1 (physical fission); source/flux will be requested."
            )
        else:
            self.K_EFF = None

        self.TOL_K = self._prompt_number("TOL_K [1e-6]: ", default=1e-6)
        self.MAX_OUTER = self._prompt_number(
            "MAX_OUTER [200]: ",
            default=200,
            integer=True,
            allow_placeholder=False,
        )
        k0_text = input("K0 (empty = automatic): ").strip()
        self.K0 = self._parse_number(k0_text) if k0_text else None

        if input("Normalize to a power? (y/n) [n]: ").strip().lower() in {"y", "s"}:
            self.POWER_KW = self._prompt_number("Power [kW]: ")
            self.E_F_MEV = self._prompt_number(
                "E_f [MeV/fission] [200]: ", default=200.0
            )
            self.AREA_CM2 = self._prompt_number(
                "Cross-sectional area [cm^2] [1]: ", default=1.0
            )

            conv = (
                input("Fission conversion: nu or sigma_f [nu]: ").strip().lower()
                or "nu"
            )
            if conv not in {"nu", "sigma_f"}:
                raise ValueError("Conversion must be 'nu' or 'sigma_f'.")
            if conv == "nu":
                self.NU = self._prompt_number("nu (neutrons/fission, e.g. 2.4): ")
            else:
                self.SIGMA_F = np.array(
                    [
                        self._prompt_number(
                            f"Sigma_f Zone {i + 1} [cm^-1] (number or placeholder): "
                        )
                        for i in range(self.num_zones)
                    ],
                    dtype=object,
                )

    def weights_directions(self):
        df = pd.DataFrame(DATA)
        # Filtramos por N. Asumimos que DATA tiene simetría y solo tomamos valores positivos o únicos
        subset = df[df["N"] == self.N]
        if subset.empty:
            # Fallback simple si no hay datos
            print(f"Advertencia: No hay datos para S{self.N}, usando S2.")
            self.miu_m = np.array([0.57735])
            self.omega_m = np.array([1.0])
            self.N_HALF = 1
        else:
            # Tomamos solo la mitad positiva si el archivo tiene todas, o todo si tiene solo la mitad
            n_rows = len(subset)
            if n_rows == self.N:
                self.miu_m = subset["mu_m"].values[
                    self.N_HALF :
                ]  # Asumiendo ordenado negativo a positivo
                self.omega_m = subset["omega_m"].values[self.N_HALF :]
            else:
                self.miu_m = subset["mu_m"].values
                self.omega_m = subset["omega_m"].values

    def prelim_calculations(self):
        self.NTC = np.sum(self.NC)  # Total celdas
        self.NTP = self.NTC + 1  # Total nodos (bordes)

        # --- VECTORIZACIÓN DE PROPIEDADES ---
        # Expandimos las propiedades de regiones a celdas individuales
        # Esto elimina la necesidad de bucles anidados complejos en el Runner
        self.sigma_t_vec = np.zeros(self.NTC)
        self.sigma_s_vec = np.zeros(self.NTC)
        self.nu_sigma_f_vec = np.zeros(self.NTC)
        self.sigma_f_vec = np.zeros(self.NTC)
        self.q_ext_vec = np.zeros(self.NTC)
        self.dx_vec = np.zeros(self.NTC)

        if self.NU_SIGF is None:
            self.NU_SIGF = np.zeros(self.num_zones)
        if self.SIGMA_F is not None and len(self.SIGMA_F) != self.num_zones:
            raise ValueError(f"SIGMA_F must have {self.num_zones} elements")

        idx = 0
        for r in range(self.num_regions):
            n_cells = self.NC[r]
            zone_idx = self.IZL[r] - 1  # Ajuste a base-0
            dx = self.HR[r] / n_cells

            self.sigma_t_vec[idx : idx + n_cells] = self.SCT[zone_idx]
            self.sigma_s_vec[idx : idx + n_cells] = self.SCS[zone_idx]
            self.nu_sigma_f_vec[idx : idx + n_cells] = self.NU_SIGF[zone_idx]
            if self.SIGMA_F is not None:
                self.sigma_f_vec[idx : idx + n_cells] = self.SIGMA_F[zone_idx]
            self.q_ext_vec[idx : idx + n_cells] = self.Q[r]
            self.dx_vec[idx : idx + n_cells] = dx

            idx += n_cells

        # --- Peso característico del esquema SC ---
        # theta = coth(alpha/2) - 2/alpha con alpha = Sigma_t*dx/|mu|.
        # Es constante durante toda la corrida: dimensiones (NTC, N_HALF) y
        # las mismas direcciones (miu_m) que usan los dos barridos.
        self.theta_sc = np.array(
            [
                [theta_step_characteristic(st * dx / mu) for mu in self.miu_m]
                for st, dx in zip(self.sigma_t_vec, self.dx_vec)
            ],
            dtype=float,
        ).reshape(self.NTC, self.N_HALF)

    def __str__(self) -> str:
        return (
            f"\nProgram configuration: {self.num_regions} regions, "
            f"{self.num_zones} zones."
            f"\nSpatial discretization: {self.NC}"
            f"\nThicknesses: {self.HR}"
            f"\nZone distribution: {self.IZL}"
            f"\nMaterial properties:"
            f"\nSigma_T: {self.SCT}"
            f"\nSigma_S: {self.SCS}"
            f"\nnu*Sigma_f: {self.NU_SIGF}"
            f"\nSources: {self.Q}"
            f"\nQuadrature order: S{self.N} with {self.N_HALF} directions."
            f"\nSpatial scheme: {self.SPATIAL_SCHEME}"
            f"\nWeights: {self.omega_m}"
            f"\nDirections: {self.miu_m}"
            f"\nMode: {self.MODE} | K_EFF: {self.K_EFF}"
            f"\nPower: {self.POWER_KW} kW "
            f"(E_f={self.E_F_MEV} MeV, area={self.AREA_CM2} cm2)"
        )

    def as_dict(self) -> dict:
        """Serializable effective configuration (JSON, datos.json)."""

        def _as_list(value):
            if value is None:
                return None
            if isinstance(value, np.ndarray):
                return value.tolist()
            return list(value)

        return {
            "num_regions": self.num_regions,
            "num_zones": self.num_zones,
            "NC": _as_list(self.NC),
            "HR": _as_list(self.HR),
            "IZL": _as_list(self.IZL),
            "SCT": _as_list(self.SCT),
            "SCS": _as_list(self.SCS),
            "NU_SIGF": _as_list(self.NU_SIGF),
            "SIGMA_F": _as_list(self.SIGMA_F),
            "Q": _as_list(self.Q),
            "N": self.N,
            "SPATIAL_SCHEME": self.SPATIAL_SCHEME,
            "reflex_izq": self.reflex_izq,
            "reflex_der": self.reflex_der,
            "bound_left": _as_list(self.bound_left),
            "bound_right": _as_list(self.bound_right),
            "MODE": self.MODE,
            "K_EFF": self.K_EFF,
            "TOL_K": self.TOL_K,
            "MAX_OUTER": self.MAX_OUTER,
            "K0": self.K0,
            "POWER_KW": self.POWER_KW,
            "E_F_MEV": self.E_F_MEV,
            "NU": self.NU,
            "AREA_CM2": self.AREA_CM2,
        }


# =================================================================
# Paso B: Runner (Motor de Cálculo)
# =================================================================
class Runner:
    """Motor de barrido S_N con Diamond Difference.

    Modos:
      * fixed_source: sin fisión (comportamiento histórico).
      * fixed_k:      fisión con k_eff impuesto.
      * driven:       fisión física (k=1) con fuente externa.
      * eigenvalue:   problema homogéneo; calcula k_eff por power iteration.

    Keyword arguments:
    argument -- No necesita argumentos, solo usa la config dada al constructor.
    Return: diccionario con flujos, iteraciones, convergencia y k_eff.
    """

    def __init__(self, config: Config, source=None, run_name: str | None = None):
        self.config = config
        # Origen de la configuración (archivo JSON, inputs.py o wizard) para
        # poder mostrarlo en el banner de inicio. Opcional: el Runner también
        # se usa directamente desde Python y desde los tests.
        self.source = source
        self.run_name = run_name
        self.converged = False
        self.reflex_izq = config.reflex_izq
        self.reflex_der = config.reflex_der

        self.iteration = 0
        self.total_inner_iterations = 0
        self.outer_iterations = 0

        # Flujos Angulares [Nodos x Direcciones]
        # PSI_RIGHT: neutrones viajando hacia x+ (mu > 0)
        # PSI_LEFT:  neutrones viajando hacia x- (mu < 0)
        self.PSI_RIGHT = np.zeros((config.NTP, config.N_HALF))
        self.PSI_LEFT = np.zeros((config.NTP, config.N_HALF))
        self.angular_flux = np.zeros((config.NTP, config.N_HALF))  # Suma de ambos
        # Flujo Escalar [Celdas]
        self.scalar_flux = np.zeros(config.NTC)

        # Fuente Total [Celdas] (Scattering + Externa + Fisión)
        self.total_source = np.zeros(config.NTC)
        self.fission_source = np.zeros(config.NTC)

        # --- Estado del modo multiplicativo ---
        self.mode = config.MODE
        self.k_eff = config.K_EFF if config.MODE in ("fixed_k", "driven") else None
        self.k_history = []
        self.k_converged = None
        self.k_balance = None
        self.power_w = None
        self.power_scale = 1.0

        # Un problema homogéneo (autovalor o fixed_k sin fuente) necesita
        # un flujo inicial no nulo; si no, la fuente de fisión es cero.
        needs_guess = config.MODE == "eigenvalue" or (
            config.MODE in ("fixed_k", "driven") and not self._has_external_source()
        )
        if needs_guess:
            self.scalar_flux[:] = 1.0

        # Fronteras no reflexivas: flujo entrante desde configuración
        # (o prompt en modo manual). Las reflexivas se actualizan en el loop.
        if not self.reflex_der:
            self.boundary_conditions_right()
        if not self.reflex_izq:
            self.boundary_conditions_left()

    def boundary_conditions_left(self):
        print("\n--- CONDICIONES DE FRONTERA ---")
        # Frontera Izquierda (x=0) incidiendo hacia la derecha

        if self.config.bound_left is not None:
            print("Using left boundary conditions from configuration.")
            vals_izq = self.config.bound_left
            logger.info(
                f"Using left boundary conditions from configuration: {vals_izq}"
            )
            self.PSI_RIGHT[0, :] = vals_izq
        else:
            print("Enter incident flux on the LEFT (mu > 0):")
            vals_izq = [
                float(input(f"  Direction {i + 1}: "))
                for i in range(self.config.N_HALF)
            ]
            self.PSI_RIGHT[0, :] = vals_izq

    def boundary_conditions_right(self):
        print("\n--- CONDICIONES DE FRONTERA ---")
        # Frontera Derecha (x=L) incidiendo hacia la izquierda

        if self.config.bound_right is not None:
            print("Using right boundary conditions from configuration.")
            vals_der = self.config.bound_right
            logger.info(
                f"Using right boundary conditions from configuration: {vals_der}"
            )
            self.PSI_LEFT[-1, :] = vals_der
        else:
            print("Enter incident flux on the RIGHT (mu < 0):")
            vals_der = [
                float(input(f"  Direction {i + 1}: "))
                for i in range(self.config.N_HALF)
            ]
            self.PSI_LEFT[-1, :] = vals_der

    def update_reflective_boundaries_left(self):
        """Mirror: what leaves one side enters the same side in the opposite direction"""
        # Izquierda (x=0): Lo que venía de la izquierda (PSI_LEFT) rebota hacia la derecha
        self.PSI_RIGHT[0, :] = self.PSI_LEFT[0, :]
        # Derecha (x=L): Lo que venía de la derecha (PSI_RIGHT) rebota hacia la izquierda
        # self.PSI_LEFT[-1, :] = self.PSI_RIGHT[-1, :]

    def update_reflective_boundaries_right(self):
        """Mirror: what leaves one side enters the same side in the opposite direction"""
        # Izquierda (x=0): Lo que venía de la izquierda (PSI_LEFT) rebota hacia la derecha
        # self.PSI_RIGHT[0, :] = self.PSI_LEFT[0, :]
        # Derecha (x=L): Lo que venía de la derecha (PSI_RIGHT) rebota hacia la izquierda
        self.PSI_LEFT[-1, :] = self.PSI_RIGHT[-1, :]

    def sweep(self):
        """Realiza el barrido de transporte"""
        # Fuente total isotrópica:
        # S = 1/2 * (Q_ext + Sigma_S * Phi) + fission_source
        # fission_source ya incluye el factor 1/2.
        self.total_source = (
            0.5 * (self.config.q_ext_vec + self.config.sigma_s_vec * self.scalar_flux)
            + self.fission_source
        )

        # Esquema espacial resuelto una sola vez (no por celda).
        kernel = _CELL_KERNELS[self.config.method]
        theta_sc = self.config.theta_sc

        # --- BARRIDO HACIA LA DERECHA (mu > 0) ---
        for k in range(self.config.NTC):
            dx = self.config.dx_vec[k]
            st = self.config.sigma_t_vec[k]
            source = self.total_source[k]

            for m in range(self.config.N_HALF):
                mu = self.config.miu_m[m]
                psi_in = self.PSI_RIGHT[k, m]  # Nodo k (entrada)

                self.PSI_RIGHT[k + 1, m] = kernel(
                    psi_in, source, st, dx, mu, theta_sc[k, m]
                )

        # --- BARRIDO HACIA LA IZQUIERDA (mu < 0) ---
        # Iteramos k desde NTC-1 hasta 0
        for k in range(self.config.NTC - 1, -1, -1):
            dx = self.config.dx_vec[k]
            st = self.config.sigma_t_vec[k]
            source = self.total_source[k]

            for m in range(self.config.N_HALF):
                mu = abs(self.config.miu_m[m])  # |mu| para la formula simétrica
                psi_in = self.PSI_LEFT[k + 1, m]  # Nodo k+1 (entrada desde la derecha)

                self.PSI_LEFT[k, m] = kernel(
                    psi_in, source, st, dx, mu, theta_sc[k, m]
                )

    def calculo_flujo(self):
        """Compute the scalar flux from the cell averages of the scheme."""
        old_flux = self.scalar_flux.copy()

        # Reiniciar flujo escalar
        self.scalar_flux[:] = 0.0
        self.angular_flux[:] = 0.0

        cfg = self.config
        average = _CELL_AVERAGES[cfg.method]
        theta_sc = cfg.theta_sc
        omega = cfg.omega_m
        miu = cfg.miu_m
        right = self.PSI_RIGHT
        left = self.PSI_LEFT
        angular = self.angular_flux
        scalar = self.scalar_flux
        dx_vec = cfg.dx_vec
        st_vec = cfg.sigma_t_vec

        for k in range(cfg.NTC):
            suma = 0.0
            dx = dx_vec[k]
            st = st_vec[k]

            for m in range(cfg.N_HALF):
                mu = abs(miu[m])
                theta = theta_sc[k, m]

                # Promedio en la celda para la dirección positiva (izq -> der)
                psi_avg_der = average(right[k, m], right[k + 1, m], st, dx, mu, theta)

                # Promedio en la celda para la dirección negativa (der -> izq)
                psi_avg_izq = average(left[k + 1, m], left[k, m], st, dx, mu, theta)

                angular_contribution = omega[m] * (psi_avg_der + psi_avg_izq)
                suma += angular_contribution
                angular[k, m] = angular_contribution

            scalar[k] = suma

        return old_flux

    def calculo_fugas(self, frontera: int):
        """Compute boundary leakage.\n
        -> boundary=0 #left boundary\n
        -> boundary=1 #right boundary\n
        -> boundary=2 #both boundaries\n

        -> Any other value disables the checks.

        """
        fuga_izquierda = 0.0
        fuga_derecha = 0.0

        # Fuga en la frontera izquierda (x=0)
        if frontera == 0 or frontera == 2:
            for m in range(self.config.N_HALF):
                mu = self.config.miu_m[m]
                w = self.config.omega_m[m]
                fuga_izquierda += w * self.PSI_LEFT[0, m] * abs(mu)

        # Fuga en la frontera derecha (x=L)
        if frontera == 1 or frontera == 2:
            for m in range(self.config.N_HALF):
                mu = self.config.miu_m[m]
                w = self.config.omega_m[m]
                fuga_derecha += w * self.PSI_RIGHT[-1, m] * abs(mu)

        return fuga_izquierda, fuga_derecha

    def check_convergence(
        self, old_flux, verbose: bool = True, tol: float | None = None
    ):
        # Manejo seguro de división por cero
        denom = np.where(self.scalar_flux > 1e-13, self.scalar_flux, 1.0)
        diff = np.abs(self.scalar_flux - old_flux)
        rel_error = np.max(diff / denom)
        threshold = self.config.epsilon if tol is None else tol

        if verbose and self.iteration % 100 == 0:
            print(f"Iter {self.iteration}: Error Max = {rel_error:.2e}")
            logger.info(f"Iter {self.iteration}: Error Max = {rel_error:.2e}")

        return rel_error < threshold

    # -----------------------------------------------------------------
    # Utilidades del modo multiplicativo
    # -----------------------------------------------------------------
    def _has_external_source(self) -> bool:
        cfg = self.config

        # Las fronteras pueden ser None en modo manual hasta que el Runner
        # pregunta el flujo entrante; en ese caso se usa el valor ya cargado.
        left_external = False
        if not cfg.reflex_izq:
            if cfg.bound_left is not None and np.any(cfg.bound_left != 0.0):
                left_external = True
            elif np.any(self.PSI_RIGHT[0, :] != 0.0):
                left_external = True

        right_external = False
        if not cfg.reflex_der:
            if cfg.bound_right is not None and np.any(cfg.bound_right != 0.0):
                right_external = True
            elif np.any(self.PSI_LEFT[-1, :] != 0.0):
                right_external = True

        return bool(np.any(cfg.q_ext_vec != 0.0) or left_external or right_external)

    def _estimate_k0(self) -> float:
        cfg = self.config
        production = float(np.sum(cfg.nu_sigma_f_vec * cfg.dx_vec))
        absorption = float(np.sum((cfg.sigma_t_vec - cfg.sigma_s_vec) * cfg.dx_vec))
        if production > 0.0 and absorption > 0.0:
            return production / absorption
        return 1.0

    def _scale_state(self, factor: float):
        """Scale scalar and angular flux consistently."""
        self.scalar_flux *= factor
        self.PSI_RIGHT *= factor
        self.PSI_LEFT *= factor
        self.angular_flux *= factor

    def _net_leakage(self) -> float:
        """Fuga neta (saliente - entrante) en ambas fronteras."""
        cfg = self.config
        w = cfg.omega_m
        mu = cfg.miu_m
        left_out = float(np.sum(w * np.abs(mu) * self.PSI_LEFT[0, :]))
        left_in = float(np.sum(w * mu * self.PSI_RIGHT[0, :]))
        right_out = float(np.sum(w * mu * self.PSI_RIGHT[-1, :]))
        right_in = float(np.sum(w * np.abs(mu) * self.PSI_LEFT[-1, :]))
        return (left_out - left_in) + (right_out - right_in)

    def balance_k(self):
        """k efectivo estimado con el balance global P/(A+L)."""
        cfg = self.config
        if not np.any(cfg.nu_sigma_f_vec > 0.0):
            return None
        production = float(np.sum(cfg.nu_sigma_f_vec * self.scalar_flux * cfg.dx_vec))
        absorption = float(
            np.sum((cfg.sigma_t_vec - cfg.sigma_s_vec) * self.scalar_flux * cfg.dx_vec)
        )
        leakage = self._net_leakage()
        denominator = absorption + leakage
        if denominator <= 0.0 or production <= 0.0:
            return None
        return production / denominator

    def _inner_solve(self) -> bool:
        """Source iteration (scattering) with frozen fission_source.

        La tolerancia interna se ata a TOL_K para que el error de la
        iteración de scattering no sesgue k_eff.
        """
        self.converged = False
        self.iteration = 0
        inner_tol = min(self.config.epsilon, self.config.TOL_K)
        while self.iteration < self.config.max_iter:
            self.iteration += 1
            self.total_inner_iterations += 1
            if self.reflex_der:
                self.update_reflective_boundaries_right()
            if self.reflex_izq:
                self.update_reflective_boundaries_left()
            self.sweep()
            old_flux = self.calculo_flujo()
            if self.check_convergence(old_flux, verbose=False, tol=inner_tol):
                self.converged = True
                break
        return self.converged

    def _fixed_source_iteration(self):
        logger.info("Starting source iteration (no fission)...")
        self.converged = False
        while self.iteration < self.config.max_iter:
            self.iteration += 1
            if self.reflex_der:
                self.update_reflective_boundaries_right()
            if self.reflex_izq:
                self.update_reflective_boundaries_left()
            self.sweep()
            old_flux = self.calculo_flujo()
            if self.check_convergence(old_flux):
                print(f"\nCONVERGENCE REACHED at iteration {self.iteration}.")
                self.converged = True
                break

        if not self.converged:
            print("\nWARNING: Maximum iterations reached without convergence.")

    def _fixed_k_iteration(self):
        cfg = self.config
        self.k_eff = cfg.K_EFF
        has_source = self._has_external_source()
        self.converged = False
        print(f"\n--- fixed_k MODE (k_eff = {self.k_eff:.6f}) ---")
        if self.mode == "driven" and not has_source:
            raise ValueError("MODE='driven' requires Q != 0 or non-zero incoming flux.")
        if not has_source:
            print(
                "WARNING: no external source or incoming flux. "
                "The problem is homogeneous: the amplitude is arbitrary and only "
                "k = k* would have a stationary solution. The flux will be normalized."
            )

        while self.iteration < cfg.max_iter:
            self.iteration += 1
            if self.reflex_der:
                self.update_reflective_boundaries_right()
            if self.reflex_izq:
                self.update_reflective_boundaries_left()
            self.fission_source = (
                0.5 * cfg.nu_sigma_f_vec * self.scalar_flux / self.k_eff
            )
            self.sweep()
            old_flux = self.calculo_flujo()
            if not has_source:
                scale = float(np.max(np.abs(self.scalar_flux)))
                if scale > 0.0:
                    self._scale_state(1.0 / scale)
            if self.check_convergence(old_flux):
                print(f"\nCONVERGENCE REACHED at iteration {self.iteration}.")
                self.converged = True
                break

        if not self.converged:
            print("\nWARNING: Maximum iterations reached without convergence.")

        self.k_converged = self.converged
        self.k_balance = self.balance_k()
        if self.k_balance is not None:
            print(
                f"k_balance (P/(A+L)) = {self.k_balance:.8f} "
                f"(k impuesto = {self.k_eff:.8f})"
            )

    def _eigenvalue_iteration(self):
        cfg = self.config
        self.k_eff = cfg.K0 if cfg.K0 is not None else self._estimate_k0()
        if self.k_eff <= 0.0:
            raise ValueError("K0 must be > 0 to start power iteration.")

        self.scalar_flux[:] = 1.0
        production_old = float(
            np.sum(cfg.nu_sigma_f_vec * self.scalar_flux * cfg.dx_vec)
        )
        if production_old <= 0.0:
            raise ValueError(
                "NU_SIGF must be positive in at least one zone for the eigenvalue."
            )

        self.k_history = []
        self.k_converged = False
        print(f"\n--- k_eff EIGENVALUE (initial guess = {self.k_eff:.6f}) ---")

        for outer in range(1, cfg.MAX_OUTER + 1):
            self.outer_iterations = outer
            self.fission_source = (
                0.5 * cfg.nu_sigma_f_vec * self.scalar_flux / self.k_eff
            )
            inner_ok = self._inner_solve()

            production_new = float(
                np.sum(cfg.nu_sigma_f_vec * self.scalar_flux * cfg.dx_vec)
            )
            if production_new <= 0.0:
                raise ValueError("Zero fission production during power iteration.")

            k_new = self.k_eff * production_new / production_old
            scale = float(np.max(np.abs(self.scalar_flux)))
            if scale > 0.0:
                self._scale_state(1.0 / scale)
            production_old = float(
                np.sum(cfg.nu_sigma_f_vec * self.scalar_flux * cfg.dx_vec)
            )

            self.k_history.append(k_new)
            dk = abs(k_new - self.k_eff) / abs(k_new)
            self.k_eff = k_new

            if outer % max(1, cfg.MAX_OUTER // 20) == 0 or dk < cfg.TOL_K:
                print(f"Outer {outer:4d}: k_eff={self.k_eff:.10f}  dk={dk:.2e}")

            if not inner_ok:
                print(
                    "WARNING: inner iteration did not converge; "
                    "stopping power iteration."
                )
                break
            if dk < cfg.TOL_K:
                self.k_converged = True
                break

        self.iteration = self.total_inner_iterations
        self.converged = self.k_converged
        self.k_balance = self.balance_k()

        if self.k_converged:
            print(
                f"\nEIGENVALUE CONVERGED: k_eff = {self.k_eff:.10f} "
                f"({self.outer_iterations} outer iterations, "
                f"{self.total_inner_iterations} inner)"
            )
        else:
            print(f"\nWARNING: k_eff did not converge. Last value = {self.k_eff:.10f}")
        if self.k_balance is not None:
            print(f"k_balance (P/(A+L)) = {self.k_balance:.10f}")

    def _apply_power_normalization(self):
        """Scale the flux so that integrated power is POWER_KW."""
        cfg = self.config
        if cfg.POWER_KW is None:
            return

        if np.any(cfg.sigma_f_vec > 0.0):
            sigma_f = cfg.sigma_f_vec
        elif cfg.NU is not None and cfg.NU > 0.0:
            sigma_f = cfg.nu_sigma_f_vec / cfg.NU
        else:
            raise ValueError("POWER_KW requires SIGMA_F per zone or NU (nu_bar).")

        fission_integral = float(np.sum(sigma_f * self.scalar_flux * cfg.dx_vec))
        if fission_integral <= 0.0:
            raise ValueError("Cannot normalize power: fission integral is zero.")

        # E_f [MeV/fisión] * 1.602176634e-13 [W/(MeV/s)]
        power_w = cfg.AREA_CM2 * cfg.E_F_MEV * 1.602176634e-13 * fission_integral
        if power_w <= 0.0:
            raise ValueError("Computed power is not positive.")

        target_w = cfg.POWER_KW * 1e3
        self.power_scale = target_w / power_w
        self._scale_state(self.power_scale)
        self.power_w = target_w

        print(
            f"✓ Power normalized to {cfg.POWER_KW:.6g} kW "
            f"(scale factor = {self.power_scale:.6e})"
        )

    def _build_result(self):
        # Suma Flujos angulares
        self.PSI_TOTAL = self.PSI_RIGHT + self.PSI_LEFT

        # Crear DataFrame con los resultados
        df_output = self._crear_dataframe_salida()

        return {
            "scalar_flux": self.scalar_flux,
            "angular_flux": self.angular_flux,
            "iteration": self.iteration,
            "PSI_RIGHT": self.PSI_RIGHT,
            "PSI_LEFT": self.PSI_LEFT,
            "converged": self.converged,
            "dataframe": df_output,
            "mode": self.mode,
            "spatial_scheme": self.config.SPATIAL_SCHEME,
            "k_eff": self.k_eff,
            "k_balance": self.k_balance,
            "k_history": self.k_history,
            "k_converged": self.k_converged,
            "outer_iterations": self.outer_iterations,
            "power_w": self.power_w,
            "power_scale": self.power_scale,
        }

    def _source_line(self) -> str | None:
        """Human-readable origin of the configuration, or None."""
        parts = []
        if self.source is not None:
            parts.append(str(self.source))
        if self.run_name:
            parts.append(f"run {self.run_name}")
        return " | ".join(parts) if parts else None

    def __call__(self):
        print("\n--- STARTING CALCULATION ---")
        source_line = self._source_line()
        if source_line is not None:
            print(f"Source: {source_line}")
        start = time()

        if self.mode == "eigenvalue":
            self._eigenvalue_iteration()
        elif self.mode in ("fixed_k", "driven"):
            self._fixed_k_iteration()
        else:
            self._fixed_source_iteration()

        self._apply_power_normalization()
        logger.info(f"Elapsed calculation time: {time() - start}")
        return self._build_result()

    def _crear_dataframe_salida(self):
        """Create a DataFrame with the results."""
        # Crear índices de celdas
        cell_indices = np.arange(self.config.NTC)

        # Crear diccionario con datos
        data = {"cell_idx": cell_indices, "scalar_flux": self.scalar_flux.copy()}

        # Crear DataFrame
        df = pd.DataFrame(data)

        return df

    def _guardar_excel(
        self,
        df,
        filename=f"results_runner_{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}.xlsx",
    ):
        """Save the DataFrame to an Excel file with additional information."""
        try:
            with pd.ExcelWriter(filename, engine="openpyxl") as writer:
                # Sheet 1: main results
                df.to_excel(writer, sheet_name="Scalar_Flux", index=False)

                # Sheet 2: convergence information
                info_convergencia = pd.DataFrame(
                    {
                        "Parameter": [
                            "Iterations",
                            "Converged",
                            "Epsilon",
                            "Max Iter",
                            "Total Cells",
                            "Total Nodes",
                            "Quadrature",
                            "Mode",
                            "k_eff",
                            "k_balance",
                        ],
                        "Value": [
                            self.iteration,
                            "converged" if self.converged else "not converged",
                            self.config.epsilon,
                            self.config.max_iter,
                            self.config.NTC,
                            self.config.NTP,
                            f"S{self.config.N}",
                            self.mode,
                            self.k_eff,
                            self.k_balance,
                        ],
                    }
                )
                info_convergencia.to_excel(
                    writer, sheet_name="Convergence_Info", index=False
                )

                # Sheet 3: material properties
                propiedades = pd.DataFrame(
                    {
                        "Zone": np.arange(1, self.config.num_zones + 1),
                        "Sigma_Total": self.config.SCT,
                        "Sigma_Scattering": self.config.SCS,
                        "nu_Sigma_f": self.config.NU_SIGF,
                    }
                )
                propiedades.to_excel(
                    writer, sheet_name="Material_Properties", index=False
                )

                regiones_df = pd.DataFrame(
                    {
                        "Region": np.arange(1, self.config.num_regions + 1),
                        "NC (cells per region)": list(self.config.NC),
                        "HR (thickness [cm])": list(self.config.HR),
                        "IZL (zone, 1-based)": list(self.config.IZL),
                        "Q (source per region)": list(self.config.Q),
                    }
                )
                regiones_df.to_excel(
                    writer, sheet_name="Region_Distribution", index=False
                )

                resumen = pd.DataFrame(
                    {
                        "Parameter": [
                            "Number_of_Regions",
                            "Number_of_Zones",
                            "Total_Cells",
                            "Total_Nodes",
                            "Quadrature_Order",
                        ],
                        "Value": [
                            self.config.num_regions,
                            self.config.num_zones,
                            self.config.NTC,
                            self.config.NTP,
                            f"S{self.config.N}",
                        ],
                    }
                )
                resumen.to_excel(writer, sheet_name="Summary", index=False)

            print(f"✓ Results saved to: {filename}")
            logger.info(f"Results saved to: {filename}")

        except Exception as e:
            print(f"✗ Error saving Excel: {e}")
            logger.error(f"Error saving Excel: {e}")
