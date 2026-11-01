import numpy as np
import pandas as pd
import logging
from time import time
from datetime import datetime


from .cuadraturas import DATA

logger = logging.getLogger(__name__)


# =================================================================
# Paso A: Configuración
# =================================================================
class Config:
    def __init__(
        self, epsilon: float = 1e-5, max_iter: int = 2000, manual: bool = True, **kwargs
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

        self.prelim_calculations()

    def regiones_input(self):
        self.num_regions = int(input("\n Necesita introducir el numero de Regiones: "))

    def zones_input(self):
        self.num_zones = int(input("\n Necesita introducir el numero de Zonas: "))

    def auto_input(self, kwargs: dict):
        """Carga todos los datos desde un diccionario.

        Estructura esperada del diccionario:
        {
            'num_regions': int,
            'num_zones': int,
            'NC': list o np.array (celdas por región),
            'HR': list o np.array (espesores en cm),
            'IZL': list o np.array (zona de cada región),
            'SCT': list o np.array (sigma total por zona),
            'SCS': list o np.array (sigma scattering por zona),
            'Q': list o np.array (fuente por región),
            'N': int (orden cuadratura)
            'reflex_izq': bool (decide si es reflexiva o no)
            'reflex_der': bool (decide si es reflexiva o no)
            'bound_left': list (flujo entrante por dirección, longitud N/2)
            'bound_right': list (flujo entrante por dirección, longitud N/2)

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
        print("\n--- CARGANDO CONFIGURACIÓN DESDE DICCIONARIO ---")

        # Campos de datos obligatorios
        campos_datos = ["NC", "HR", "IZL", "SCT", "SCS", "Q", "N"]

        # Validar que estén presentes
        for campo in campos_datos:
            if campo not in kwargs:
                raise ValueError(f"Campo obligatorio ausente: '{campo}'")

        # Actualizar num_regions y num_zones si vienen en kwargs
        if "num_regions" in kwargs:
            self.num_regions = int(kwargs["num_regions"])
        if "num_zones" in kwargs:
            self.num_zones = int(kwargs["num_zones"])

        # Validación básica
        if self.num_regions <= 0:
            raise ValueError("num_regions debe ser >= 1.")
        if self.num_zones <= 0:
            raise ValueError("num_zones debe ser >= 1.")
        if self.num_zones > self.num_regions:
            raise ValueError(
                "Número de zonas no puede ser mayor que el número de regiones."
            )

        # Convertir a numpy arrays
        self.NC = np.array(kwargs["NC"], dtype=int)
        self.HR = np.array(kwargs["HR"], dtype=float)
        self.IZL = np.array(kwargs["IZL"], dtype=int)
        self.SCT = np.array(kwargs["SCT"], dtype=float)
        self.SCS = np.array(kwargs["SCS"], dtype=float)
        self.Q = np.array(kwargs["Q"], dtype=float)

        self.reflex_izq = bool(kwargs.get("reflex_izq", False))
        self.reflex_der = bool(kwargs.get("reflex_der", False))

        # Configurar cuadratura (N_HALF se necesita para los defaults de frontera)
        self.N = int(kwargs["N"])
        if self.N % 2 != 0:
            raise ValueError("El orden de la cuadratura debe ser un número par.")
        self.N_HALF = self.N // 2

        # Cargar direcciones y pesos
        self.weights_directions()

        # Fronteras: por defecto, flujo entrante nulo (vacío)
        default_bound = np.zeros(self.N_HALF)
        self.bound_left = np.array(
            kwargs.get("bound_left", default_bound), dtype=float
        )
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

        # Validaciones de dimensiones
        if len(self.NC) != self.num_regions:
            raise ValueError(f"NC debe tener {self.num_regions} elementos")
        if len(self.HR) != self.num_regions:
            raise ValueError(f"HR debe tener {self.num_regions} elementos")
        if len(self.IZL) != self.num_regions:
            raise ValueError(f"IZL debe tener {self.num_regions} elementos")
        if len(self.SCT) != self.num_zones:
            raise ValueError(f"SCT debe tener {self.num_zones} elementos")
        if len(self.SCS) != self.num_zones:
            raise ValueError(f"SCS debe tener {self.num_zones} elementos")
        if len(self.Q) != self.num_regions:
            raise ValueError(f"Q debe tener {self.num_regions} elementos")

        if not self.reflex_izq:
            if len(self.bound_left) != self.N_HALF:
                raise ValueError(f"bound_left debe tener {self.N_HALF} elementos")
        if not self.reflex_der:
            if len(self.bound_right) != self.N_HALF:
                raise ValueError(f"bound_right debe tener {self.N_HALF} elementos")

        # Validar que IZL hace referencia a zonas válidas (1-based)
        if np.any(self.IZL < 1) or np.any(self.IZL > self.num_zones):
            raise ValueError(f"IZL debe contener valores entre 1 y {self.num_zones}")

        # Validaciones de fisión / modo
        self._validate_fission_config()

        # Cálculos preliminares
        self.prelim_calculations()

        print("✓ Configuración cargada exitosamente desde diccionario")
        logger.info(f"Configuración cargada desde diccionario.\n{self}")

    def _validate_fission_config(self):
        """Valida y normaliza los parámetros de medio multiplicativo."""
        if self.NU_SIGF is None:
            self.NU_SIGF = np.zeros(self.num_zones)
        if len(self.NU_SIGF) != self.num_zones:
            raise ValueError(f"NU_SIGF debe tener {self.num_zones} elementos")
        if np.any(self.NU_SIGF < 0.0):
            raise ValueError("NU_SIGF debe ser >= 0 en todas las zonas.")

        if self.SIGMA_F is not None:
            if len(self.SIGMA_F) != self.num_zones:
                raise ValueError(f"SIGMA_F debe tener {self.num_zones} elementos")
            if np.any(self.SIGMA_F < 0.0):
                raise ValueError("SIGMA_F debe ser >= 0 en todas las zonas.")
            if np.any(self.SIGMA_F > self.SCT):
                raise ValueError("SIGMA_F no puede ser mayor que SCT.")

        if self.K_EFF is not None:
            self.K_EFF = float(self.K_EFF)
            if self.K_EFF <= 0.0:
                raise ValueError("K_EFF debe ser > 0.")
        if self.K0 is not None:
            self.K0 = float(self.K0)
            if self.K0 <= 0.0:
                raise ValueError("K0 debe ser > 0.")
        if self.TOL_K <= 0.0:
            raise ValueError("TOL_K debe ser > 0.")
        if self.MAX_OUTER <= 0:
            raise ValueError("MAX_OUTER debe ser >= 1.")

        has_fission = bool(np.any(self.NU_SIGF > 0.0))

        if self.POWER_KW is not None:
            self.POWER_KW = float(self.POWER_KW)
            if self.POWER_KW <= 0.0:
                raise ValueError("POWER_KW debe ser > 0.")
            if not has_fission:
                raise ValueError("POWER_KW requiere NU_SIGF > 0.")
            if self.E_F_MEV <= 0.0:
                raise ValueError("E_F_MEV debe ser > 0.")
            if self.AREA_CM2 <= 0.0:
                raise ValueError("AREA_CM2 debe ser > 0.")
            if self.NU is not None:
                self.NU = float(self.NU)
                if self.NU <= 0.0:
                    raise ValueError("NU debe ser > 0.")
            if self.SIGMA_F is None and self.NU is None:
                raise ValueError(
                    "POWER_KW requiere SIGMA_F por zona o NU (nu_bar) "
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
            raise ValueError(
                f"MODE inválido: {self.MODE!r}. Opciones: {sorted(allowed)}"
            )

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
        external_source = bool(
            np.any(self.Q != 0.0) or left_external or right_external
        )

        if self.MODE == "fixed_source":
            if has_fission:
                raise ValueError(
                    "MODE='fixed_source' exige NU_SIGF = 0. "
                    "Usa MODE='eigenvalue' o MODE='fixed_k'."
                )
            if self.K_EFF is not None:
                raise ValueError("MODE='fixed_source' no usa K_EFF.")

        elif self.MODE == "eigenvalue":
            if not has_fission:
                raise ValueError("MODE='eigenvalue' exige NU_SIGF > 0.")
            if self.K_EFF is not None:
                raise ValueError(
                    "MODE='eigenvalue' calcula k_eff; no impongas K_EFF. "
                    "Usa MODE='fixed_k' si quieres fijarlo."
                )
            if external_source:
                raise ValueError(
                    "MODE='eigenvalue' resuelve el problema homogéneo "
                    "(Q=0 y flujo entrante nulo). Con fuente usa "
                    "MODE='fixed_k' o MODE='driven'."
                )

        elif self.MODE == "fixed_k":
            if not has_fission:
                raise ValueError("MODE='fixed_k' exige NU_SIGF > 0.")
            if self.K_EFF is None:
                raise ValueError("MODE='fixed_k' exige K_EFF > 0.")

        elif self.MODE == "driven":
            if not has_fission:
                raise ValueError("MODE='driven' exige NU_SIGF > 0.")
            if self.K_EFF is None:
                self.K_EFF = 1.0
            elif abs(self.K_EFF - 1.0) > 1e-12:
                raise ValueError(
                    "MODE='driven' usa el k físico = 1. "
                    "Para escalar la fisión usa MODE='fixed_k'."
                )
            # En modo manual las fronteras aún pueden ser None (el Runner
            # preguntará el flujo entrante); en ese caso la comprobación
            # definitiva se hace en Runner._fixed_k_iteration.
            bounds_known = (
                self.bound_left is not None and self.bound_right is not None
            )
            if not external_source and bounds_known:
                raise ValueError(
                    "MODE='driven' exige Q != 0 o flujo entrante distinto de cero."
                )

    def manual_input(self):
        """Método separado para inputs para no bloquear la inicialización"""
        print("\n--- CONFIGURACIÓN ESPACIAL ---")
        self.NC = np.array(
            [int(input(f"Celdas en Región {i + 1}: ")) for i in range(self.num_regions)]
        )
        self.HR = np.array(
            [
                float(input(f"Espesor total [cm] Región {i + 1}: "))
                for i in range(self.num_regions)
            ]
        )
        self.IZL = np.array(
            [
                int(input(f"ID Zona Material Región {i + 1} (1-based): "))
                for i in range(self.num_regions)
            ]
        )

        print("\n--- CONFIGURACIÓN MATERIALES ---")
        self.SCT = np.array(
            [float(input(f"Sigma_Total Zona {i + 1}: ")) for i in range(self.num_zones)]
        )
        self.SCS = np.array(
            [
                float(input(f"Sigma_Scattering Zona {i + 1}: "))
                for i in range(self.num_zones)
            ]
        )
        self.Q = np.array(
            [
                float(input(f"Fuente (Q) Región {i + 1}: "))
                for i in range(self.num_regions)
            ]
        )

        print("\n--- CONFIGURACIÓN CUADRATURA ---")
        self.N = int(input("Orden de cuadratura (ej. 2, 4, 8) -> "))
        if self.N % 2 != 0:
            raise ValueError("Debe ser par.")
        self.N_HALF = self.N // 2
        self.weights_directions()

        # Medio multiplicativo (opcional)
        self._fission_input()

        # Preguntar si es reflexiva
        reflex_izq = (
            input("¿Condiciones reflexivas por la Izquierda? (s/n): ").lower() == "s"
        )
        self.reflex_izq = reflex_izq
        reflex_der = (
            input("¿Condiciones reflexivas por la Derecha? (s/n): ").lower() == "s"
        )
        self.reflex_der = reflex_der

        # Validar la combinación de modo/fuente también en modo manual
        self._validate_fission_config()

        # Calculos preliminares
        self.prelim_calculations()
        logger.info(f"Configuración completa.\n{self}")

    def _fission_input(self):
        """Preguntas opcionales para medios multiplicativos en modo manual."""
        self.NU_SIGF = np.zeros(self.num_zones)
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

        resp = input("¿Medio multiplicativo (fisión)? (s/n): ").strip().lower()
        if resp != "s":
            return

        for i in range(self.num_zones):
            self.NU_SIGF[i] = float(
                input(f"nu*Sigma_f Zona {i + 1} [cm^-1]: ")
            )

        mode = (
            input("Modo (eigenvalue / fixed_k / driven) [eigenvalue]: ")
            .strip()
            .lower()
            or "eigenvalue"
        )
        if mode not in {"eigenvalue", "fixed_k", "driven"}:
            raise ValueError(f"Modo inválido: {mode}")
        self.MODE = mode

        if mode == "fixed_k":
            self.K_EFF = float(input("k_eff impuesto: "))
        elif mode == "driven":
            self.K_EFF = 1.0
            print("Modo driven: se usará k = 1 y se pedirá flujo entrante.")
        else:
            # El autovalor exige fronteras homogéneas y Q = 0.
            self.bound_left = np.zeros(self.N_HALF)
            self.bound_right = np.zeros(self.N_HALF)
            self.Q[:] = 0.0

        if input("¿Normalizar a una potencia? (s/n): ").strip().lower() == "s":
            self.POWER_KW = float(input("Potencia [kW]: "))
            ef_text = input("E_f [MeV/fisión] (200): ").strip()
            self.E_F_MEV = float(ef_text) if ef_text else 200.0
            area_text = input("Área transversal [cm^2] (1): ").strip()
            self.AREA_CM2 = float(area_text) if area_text else 1.0
            self.NU = float(input("nu (neutrones/fisión, p.ej. 2.4): "))

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
            raise ValueError(f"SIGMA_F debe tener {self.num_zones} elementos")

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
            f"\nConfiguracion del programa: {self.num_regions} regiones, "
            f"{self.num_zones} zonas."
            f"\nDiscretizacion espacial: {self.NC}"
            f"\nEspesores: {self.HR}"
            f"\nDistribucion de zonas: {self.IZL}"
            f"\nPropiedades materiales:"
            f"\nSigma_T: {self.SCT}"
            f"\nSigma_S: {self.SCS}"
            f"\nnu*Sigma_f: {self.NU_SIGF}"
            f"\nFuentes: {self.Q}"
            f"\nOrden de cuadratura: S{self.N} con {self.N_HALF} direcciones."
            f"\nPesos: {self.omega_m}"
            f"\nDirecciones: {self.miu_m}"
            f"\nModo: {self.MODE} | K_EFF: {self.K_EFF}"
            f"\nPotencia: {self.POWER_KW} kW "
            f"(E_f={self.E_F_MEV} MeV, area={self.AREA_CM2} cm2)"
        )


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

    def __init__(self, config: Config):
        self.config = config
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
        self.k_eff = (
            config.K_EFF if config.MODE in ("fixed_k", "driven") else None
        )
        self.k_history = []
        self.k_converged = None
        self.k_balance = None
        self.power_w = None
        self.power_scale = 1.0

        # Un problema homogéneo (autovalor o fixed_k sin fuente) necesita
        # un flujo inicial no nulo; si no, la fuente de fisión es cero.
        needs_guess = config.MODE == "eigenvalue" or (
            config.MODE in ("fixed_k", "driven")
            and not self._has_external_source()
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
            print("Usando condiciones de frontera izquierda desde configuración.")
            vals_izq = self.config.bound_left
            logger.info(
                f"Usando condiciones de frontera izquierda desde configuración: {vals_izq}"
            )
            self.PSI_RIGHT[0, :] = vals_izq
        else:
            print("Ingrese flujo incidente en IZQUIERDA (mu > 0):")
            vals_izq = [
                float(input(f"  Dirección {i + 1}: "))
                for i in range(self.config.N_HALF)
            ]
            self.PSI_RIGHT[0, :] = vals_izq

    def boundary_conditions_right(self):
        print("\n--- CONDICIONES DE FRONTERA ---")
        # Frontera Derecha (x=L) incidiendo hacia la izquierda

        if self.config.bound_right is not None:
            print("Usando condiciones de frontera Derecha desde configuración.")
            vals_der = self.config.bound_right
            logger.info(
                f"Usando condiciones de frontera Derecha desde configuración: {vals_der}"
            )
            self.PSI_LEFT[-1, :] = vals_der
        else:
            print("Ingrese flujo incidente en DERECHA (mu < 0):")
            vals_der = [
                float(input(f"  Dirección {i + 1}: "))
                for i in range(self.config.N_HALF)
            ]
            self.PSI_LEFT[-1, :] = vals_der

    def update_reflective_boundaries_left(self):
        """Espejo: Lo que sale por un lado entra por el mismo lado en dirección opuesta"""
        # Izquierda (x=0): Lo que venía de la izquierda (PSI_LEFT) rebota hacia la derecha
        self.PSI_RIGHT[0, :] = self.PSI_LEFT[0, :]
        # Derecha (x=L): Lo que venía de la derecha (PSI_RIGHT) rebota hacia la izquierda
        # self.PSI_LEFT[-1, :] = self.PSI_RIGHT[-1, :]

    def update_reflective_boundaries_right(self):
        """Espejo: Lo que sale por un lado entra por el mismo lado en dirección opuesta"""
        # Izquierda (x=0): Lo que venía de la izquierda (PSI_LEFT) rebota hacia la derecha
        # self.PSI_RIGHT[0, :] = self.PSI_LEFT[0, :]
        # Derecha (x=L): Lo que venía de la derecha (PSI_RIGHT) rebota hacia la izquierda
        self.PSI_LEFT[-1, :] = self.PSI_RIGHT[-1, :]

    def sweep(self):
        """Realiza el barrido de transporte usando Diamond Difference"""
        # Fuente total isotrópica:
        # S = 1/2 * (Q_ext + Sigma_S * Phi) + fission_source
        # fission_source ya incluye el factor 1/2.
        self.total_source = (
            0.5 * (self.config.q_ext_vec + self.config.sigma_s_vec * self.scalar_flux)
            + self.fission_source
        )

        # --- BARRIDO HACIA LA DERECHA (mu > 0) ---
        for k in range(self.config.NTC):
            dx = self.config.dx_vec[k]
            st = self.config.sigma_t_vec[k]
            source = self.total_source[k]

            for m in range(self.config.N_HALF):
                mu = self.config.miu_m[m]
                psi_in = self.PSI_RIGHT[k, m]  # Nodo k (entrada)

                # Ecuación Diamond Difference
                # psi_out = [ (mu/dx - st/2)*psi_in + S ] / (mu/dx + st/2)
                alpha = mu / dx
                num = (alpha - 0.5 * st) * psi_in + source
                den = alpha + 0.5 * st

                psi_out = num / den

                self.PSI_RIGHT[k + 1, m] = psi_out  # Nodo k+1 (salida)

        # --- BARRIDO HACIA LA IZQUIERDA (mu < 0) ---
        # Iteramos k desde NTC-1 hasta 0
        for k in range(self.config.NTC - 1, -1, -1):
            dx = self.config.dx_vec[k]
            st = self.config.sigma_t_vec[k]
            source = self.total_source[k]

            for m in range(self.config.N_HALF):
                mu = abs(
                    self.config.miu_m[m]
                )  # Usamos valor positivo para la formula simétrica
                psi_in = self.PSI_LEFT[k + 1, m]  # Nodo k+1 (entrada desde la derecha)

                alpha = mu / dx
                num = (alpha - 0.5 * st) * psi_in + source
                den = alpha + 0.5 * st

                psi_out = num / den

                self.PSI_LEFT[k, m] = psi_out

    def calculo_flujo(self):
        """Calcula el flujo escalar integrando los flujos angulares"""
        old_flux = self.scalar_flux.copy()

        # Reiniciar flujo escalar
        self.scalar_flux[:] = 0.0
        self.angular_flux[:] = 0.0

        for k in range(self.config.NTC):
            suma = 0.0
            for m in range(self.config.N_HALF):
                w = self.config.omega_m[m]

                # Promedio en el centro de la celda (Diamond Difference Average)
                # psi_avg = 0.5 * (psi_in + psi_out)
                psi_avg_der = 0.5 * (self.PSI_RIGHT[k, m] + self.PSI_RIGHT[k + 1, m])
                psi_avg_izq = 0.5 * (self.PSI_LEFT[k, m] + self.PSI_LEFT[k + 1, m])

                # Sumamos ambas direcciones
                suma += w * (psi_avg_der + psi_avg_izq)
                self.angular_flux[k, m] = w * (psi_avg_der + psi_avg_izq)

            self.scalar_flux[k] = suma

        return old_flux

    def calculo_fugas(self, frontera: int):
        """Calcula las fugas en las fronteras del sistema\n
        -> frontera=0 #Calcula fugas en la frontera Izquierda\n
        -> frontera=1 #Calcula fugas en la frontera Derecha\n
        -> frontera=2 #Calcula fugas en la frontera Izquierda y Derecha\n

        -> Otro valor sera tomado como False las condiciones

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
        absorption = float(
            np.sum((cfg.sigma_t_vec - cfg.sigma_s_vec) * cfg.dx_vec)
        )
        if production > 0.0 and absorption > 0.0:
            return production / absorption
        return 1.0

    def _scale_state(self, factor: float):
        """Escala flujo escalar y angular de forma consistente."""
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
        production = float(
            np.sum(cfg.nu_sigma_f_vec * self.scalar_flux * cfg.dx_vec)
        )
        absorption = float(
            np.sum(
                (cfg.sigma_t_vec - cfg.sigma_s_vec)
                * self.scalar_flux
                * cfg.dx_vec
            )
        )
        leakage = self._net_leakage()
        denominator = absorption + leakage
        if denominator <= 0.0 or production <= 0.0:
            return None
        return production / denominator

    def _inner_solve(self) -> bool:
        """Iteración de fuente (scattering) con fission_source congelada.

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
        logger.info("Iniciando iteración de fuente (sin fisión)...")
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
                print(f"\nCONVERGENCIA ALCANZADA en iteración {self.iteration}.")
                self.converged = True
                break

        if not self.converged:
            print("\nADVERTENCIA: Máximo de iteraciones alcanzado sin convergencia.")

    def _fixed_k_iteration(self):
        cfg = self.config
        self.k_eff = cfg.K_EFF
        has_source = self._has_external_source()
        self.converged = False
        print(f"\n--- MODO fixed_k (k_eff = {self.k_eff:.6f}) ---")
        if self.mode == "driven" and not has_source:
            raise ValueError(
                "MODE='driven' requiere Q != 0 o flujo entrante distinto de cero."
            )
        if not has_source:
            print(
                "ADVERTENCIA: sin fuente externa ni flujo entrante. "
                "El problema es homogéneo: la amplitud es arbitraria y solo "
                "k = k* tendría solución estacionaria. Se normalizará el flujo."
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
                print(f"\nCONVERGENCIA ALCANZADA en iteración {self.iteration}.")
                self.converged = True
                break

        if not self.converged:
            print("\nADVERTENCIA: Máximo de iteraciones alcanzado sin convergencia.")

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
            raise ValueError("K0 debe ser > 0 para iniciar el power iteration.")

        self.scalar_flux[:] = 1.0
        production_old = float(
            np.sum(cfg.nu_sigma_f_vec * self.scalar_flux * cfg.dx_vec)
        )
        if production_old <= 0.0:
            raise ValueError(
                "NU_SIGF debe ser positivo en al menos una zona para el autovalor."
            )

        self.k_history = []
        self.k_converged = False
        print(f"\n--- AUTOVALOR k_eff (guess inicial = {self.k_eff:.6f}) ---")

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
                raise ValueError(
                    "Producción de fisión nula durante el power iteration."
                )

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
                print(
                    f"Outer {outer:4d}: k_eff={self.k_eff:.10f}  dk={dk:.2e}"
                )

            if not inner_ok:
                print(
                    "ADVERTENCIA: la iteración interna no convergió; "
                    "se detiene el power iteration."
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
                f"\nAUTOVALOR CONVERGIDO: k_eff = {self.k_eff:.10f} "
                f"({self.outer_iterations} iteraciones exteriores, "
                f"{self.total_inner_iterations} interiores)"
            )
        else:
            print(
                "\nADVERTENCIA: k_eff no convergió. "
                f"Último valor = {self.k_eff:.10f}"
            )
        if self.k_balance is not None:
            print(f"k_balance (P/(A+L)) = {self.k_balance:.10f}")

    def _apply_power_normalization(self):
        """Escala el flujo para que la potencia integrada sea POWER_KW."""
        cfg = self.config
        if cfg.POWER_KW is None:
            return

        if np.any(cfg.sigma_f_vec > 0.0):
            sigma_f = cfg.sigma_f_vec
        elif cfg.NU is not None and cfg.NU > 0.0:
            sigma_f = cfg.nu_sigma_f_vec / cfg.NU
        else:
            raise ValueError(
                "POWER_KW requiere SIGMA_F por zona o NU (nu_bar)."
            )

        fission_integral = float(
            np.sum(sigma_f * self.scalar_flux * cfg.dx_vec)
        )
        if fission_integral <= 0.0:
            raise ValueError(
                "No se puede normalizar la potencia: integral de fisión nula."
            )

        # E_f [MeV/fisión] * 1.602176634e-13 [W/(MeV/s)]
        power_w = (
            cfg.AREA_CM2
            * cfg.E_F_MEV
            * 1.602176634e-13
            * fission_integral
        )
        if power_w <= 0.0:
            raise ValueError("Potencia calculada no positiva.")

        target_w = cfg.POWER_KW * 1e3
        self.power_scale = target_w / power_w
        self._scale_state(self.power_scale)
        self.power_w = target_w

        print(
            f"✓ Potencia normalizada a {cfg.POWER_KW:.6g} kW "
            f"(factor de escala = {self.power_scale:.6e})"
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
            "k_eff": self.k_eff,
            "k_balance": self.k_balance,
            "k_history": self.k_history,
            "k_converged": self.k_converged,
            "outer_iterations": self.outer_iterations,
            "power_w": self.power_w,
            "power_scale": self.power_scale,
        }

    def __call__(self):
        print("\n--- INICIANDO CÁLCULO ---")
        start = time()

        if self.mode == "eigenvalue":
            self._eigenvalue_iteration()
        elif self.mode in ("fixed_k", "driven"):
            self._fixed_k_iteration()
        else:
            self._fixed_source_iteration()

        self._apply_power_normalization()
        logger.info(f"Tiempo demorado de los calculos: {time() - start}")
        return self._build_result()

    def _crear_dataframe_salida(self):
        """Crea un DataFrame con los resultados del cálculo"""
        # Crear índices de celdas
        cell_indices = np.arange(self.config.NTC)

        # Crear diccionario con datos
        data = {"celda_idx": cell_indices, "flujo_escalar": self.scalar_flux.copy()}

        # Crear DataFrame
        df = pd.DataFrame(data)

        return df

    def _guardar_excel(
        self,
        df,
        filename=f"resultados_runner_{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}.xlsx",
    ):
        """Guarda el DataFrame en un archivo Excel con información adicional"""
        try:
            with pd.ExcelWriter(filename, engine="openpyxl") as writer:
                # Hoja 1: Resultados principales
                df.to_excel(writer, sheet_name="Flujo_Escalar", index=False)

                # Hoja 2: Información de convergencia
                info_convergencia = pd.DataFrame(
                    {
                        "Parámetro": [
                            "Iteraciones",
                            "Convergido",
                            "Epsilon",
                            "Max Iter",
                            "Celdas Totales",
                            "Nodos Totales",
                            "Cuadratura",
                            "Modo",
                            "k_eff",
                            "k_balance",
                        ],
                        "Valor": [
                            self.iteration,
                            "converge" if self.converged else "no converge",
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
                    writer, sheet_name="Info_Convergencia", index=False
                )

                # Hoja 3: Propiedades de materiales
                propiedades = pd.DataFrame(
                    {
                        "Zona": np.arange(1, self.config.num_zones + 1),
                        "Sigma_Total": self.config.SCT,
                        "Sigma_Scattering": self.config.SCS,
                        "nu_Sigma_f": self.config.NU_SIGF,
                    }
                )
                propiedades.to_excel(
                    writer, sheet_name="Propiedades_Material", index=False
                )

                regiones_df = pd.DataFrame(
                    {
                        "Region": np.arange(1, self.config.num_regions + 1),
                        "NC (celdas por region)": list(self.config.NC),
                        "HR (espesor [cm])": list(self.config.HR),
                        "IZL (zona, 1-based)": list(self.config.IZL),
                        "Q (fuente por region)": list(self.config.Q),
                    }
                )
                regiones_df.to_excel(
                    writer, sheet_name="Regiones_Distribucion", index=False
                )

                resumen = pd.DataFrame(
                    {
                        "Parámetro": [
                            "Numero_Regiones",
                            "Numero_Zonas",
                            "Total_Celdas",
                            "Total_Nodos",
                            "Orden_Cuadratura",
                        ],
                        "Valor": [
                            self.config.num_regions,
                            self.config.num_zones,
                            self.config.NTC,
                            self.config.NTP,
                            f"S{self.config.N}",
                        ],
                    }
                )
                resumen.to_excel(writer, sheet_name="Resumen", index=False)

            print(f"✓ Resultados guardados en: {filename}")
            logger.info(f"Resultados guardados en: {filename}")

        except Exception as e:
            print(f"✗ Error al guardar Excel: {e}")
            logger.error(f"Error al guardar Excel: {e}")
