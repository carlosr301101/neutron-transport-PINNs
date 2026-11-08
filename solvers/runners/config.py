"""Configuration model for the 1D S_N solver (scheme agnostic)."""

# pyright: reportConstantRedefinition=false
# Config attributes mirror the JSON keys and are intentionally UPPERCASE
# (NU_SIGF, TOL_K, ...), so they are assigned outside __init__ on purpose.

from __future__ import annotations

import logging
import re

import numpy as np
import pandas as pd

from .cuadraturas import DATA
from .power import DEFAULT_NU
from .scheme import Method, method_from_name

logger = logging.getLogger(__name__)


class Config:
    def __init__(
        self,
        epsilon: float = 1e-5,
        max_iter: int = 2000,
        manual: bool = True,
        allow_placeholders: bool = False,
        forced_scheme=None,
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
        self._forced_scheme = forced_scheme

        # --- Medio multiplicativo (fisión) ---
        self.MODE: str | None = None
        self.NU_SIGF = None
        self.SIGMA_F = None
        self.K_EFF: float | None = None
        self.TOL_K: float = 1e-6
        self.MAX_OUTER: int = 200
        self.K0: float | None = None
        self.POWER_KW: float | None = None
        self.E_F_MEV: float = 200.0
        self.NU: float | None = None
        self.AREA_CM2: float = 1.0

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
    ) -> int | float | str | None:
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
        default: int | float | None = None,
        integer: bool = False,
        allow_placeholder: bool | None = None,
    ) -> int | float | str | None:
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

    @staticmethod
    def _as_float(value: int | float | str | None, name: str) -> float:
        """Coerce a numeric prompt result to float, rejecting placeholders."""
        if value is None:
            raise ValueError(f"{name} is required.")
        if isinstance(value, str):
            raise ValueError(f"{name} must be numeric; placeholders are not allowed.")
        return float(value)

    def _prompt_float(
        self, prompt: str, default: float | None = None
    ) -> float:
        """Prompt for a strictly numeric (float) value."""
        value = self._prompt_number(
            prompt, default=default, allow_placeholder=False
        )
        return self._as_float(value, prompt.strip().rstrip(":"))

    def _prompt_int(self, prompt: str, default: int | None = None) -> int:
        """Prompt for a strictly numeric (integer) value."""
        value = self._prompt_number(
            prompt, default=default, integer=True, allow_placeholder=False
        )
        if value is None or isinstance(value, str):
            raise ValueError(f"{prompt.strip()} must be an integer.")
        return int(value)

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
        self.set_spatial_scheme(
            self._forced_scheme or kwargs.get("SPATIAL_SCHEME", Method.DD.value)
        )

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
                self.NU = DEFAULT_NU
                print(
                    f"Using default NU = {DEFAULT_NU} (U-238 fast fission)."
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
        self.N = self._prompt_int("Quadrature order (2, 4, 6, 8) [8]: ", default=8)
        if self.N % 2 != 0:
            raise ValueError("Quadrature order must be even.")
        self.N_HALF = self.N // 2
        self.weights_directions()

        if self._forced_scheme:
            self.set_spatial_scheme(self._forced_scheme)
        else:
            scheme_text = input("Spatial scheme (DD / STEP / SC) [DD]: ").strip()
            self.set_spatial_scheme(scheme_text or Method.DD.value)

        # Medio multiplicativo (opcional)
        self._fission_input()

        # Fuente externa: se pregunta después de conocer el modo
        if self.MODE == "eigenvalue":
            self.Q = np.zeros(self.num_regions)
            print("\nEigenvalue mode: Q = 0 (homogeneous problem).")
        else:
            print("\n--- EXTERNAL SOURCE ---")
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
        print("\n--- BOUNDARY CONDITIONS ---")
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
            self.K_EFF = self._prompt_float("k_eff imposed: ")
        elif mode == "driven":
            self.K_EFF = 1.0
            print(
                "driven mode: k = 1 (physical fission); source/flux will be requested."
            )
        else:
            self.K_EFF = None

        self.TOL_K = self._prompt_float("TOL_K [1e-6]: ", default=1e-6)
        self.MAX_OUTER = self._prompt_int("MAX_OUTER [200]: ", default=200)
        k0_text = input("K0 (empty = automatic): ").strip()
        self.K0 = (
            self._as_float(
                self._parse_number(k0_text, allow_placeholder=False), "K0"
            )
            if k0_text
            else None
        )

        if input("Normalize to a power? (y/n) [n]: ").strip().lower() in {"y", "s"}:
            self.POWER_KW = self._prompt_float("Power [kW]: ")
            self.E_F_MEV = self._prompt_float(
                "E_f [MeV/fission] [200]: ", default=200.0
            )
            self.AREA_CM2 = self._prompt_float(
                "Cross-sectional area [cm^2] [1]: ", default=1.0
            )

            conv = (
                input("Fission conversion: nu or sigma_f [nu]: ").strip().lower()
                or "nu"
            )
            if conv not in {"nu", "sigma_f"}:
                raise ValueError("Conversion must be 'nu' or 'sigma_f'.")
            if conv == "nu":
                self.NU = self._prompt_float(
                    f"nu (neutrons/fission, U-238 default) [{DEFAULT_NU}]: ",
                    default=DEFAULT_NU,
                )
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
            print(f"Warning: no data for S{self.N}, falling back to S2.")
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
