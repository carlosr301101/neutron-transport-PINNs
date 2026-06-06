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
            logging.root.removeHandler(handler)
        logging.basicConfig(filename="Config.log", level=logging.INFO, filemode="w")
        self.num_regions = 0
        self.num_zones = 0
        self.bound_left = None
        self.bound_right = None

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
            'reflex_derecha': bool (decide si es reflexiva o no)

        }
        """
        print("\n--- CARGANDO CONFIGURACIÓN DESDE DICCIONARIO ---")

        # Campos de datos obligatorios (num_regions y num_zones ya están en self)
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

        self.bound_left = np.array(kwargs.get("bound_left", [0]), dtype=float)
        self.bound_right = np.array(kwargs.get("bound_right", [0]), dtype=float)

        self.reflex_izq = kwargs.get("reflex_izq", False)
        self.reflex_der = kwargs.get("reflex_der", False)

        # Configurar cuadratura
        self.N = int(kwargs["N"])
        if self.N % 2 != 0:
            raise ValueError("El orden de la cuadratura debe ser un número par.")
        self.N_HALF = self.N // 2

        # Cargar direcciones y pesos
        self.weights_directions()

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

        # Cálculos preliminares
        self.prelim_calculations()

        print("✓ Configuración cargada exitosamente desde diccionario")
        logger.info(f"Configuración cargada desde diccionario.\n{self}")

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

        # Preguntar si es reflexiva
        reflex_izq = (
            input("¿Condiciones reflexivas por la Izquierda? (s/n): ").lower() == "s"
        )
        self.reflex_izq = reflex_izq
        reflex_der = (
            input("¿Condiciones reflexivas por la Derecha? (s/n): ").lower() == "s"
        )
        self.reflex_der = reflex_der

        # Calculos preliminares
        self.prelim_calculations()
        logger.info(f"Configuración completa.\n{self}")

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
            # Ajusta esto según el formato real de tu archivo cuadraturas.py
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
        self.q_ext_vec = np.zeros(self.NTC)
        self.dx_vec = np.zeros(self.NTC)

        idx = 0
        for r in range(self.num_regions):
            n_cells = self.NC[r]
            zone_idx = self.IZL[r] - 1  # Ajuste a base-0
            dx = self.HR[r] / n_cells

            self.sigma_t_vec[idx : idx + n_cells] = self.SCT[zone_idx]
            self.sigma_s_vec[idx : idx + n_cells] = self.SCS[zone_idx]
            self.q_ext_vec[idx : idx + n_cells] = self.Q[r]
            self.dx_vec[idx : idx + n_cells] = dx

            idx += n_cells

    def __str__(self) -> str:
        return f"\nConfiguracion del programa: {self.num_regions} regiones, {self.num_zones} zonas.\
            \nDiscretizacion espacial: {self.NC}\nEspesores: {self.HR}\nDistribucion de zonas: {self.IZL}\
            \nPropiedades materiales:\nSigma_T: {self.SCT}\nSigma_S: {self.SCS}\nFuentes: {self.Q}\
            \nOrden de cuadratura: S{self.N} con {self.N_HALF} direcciones.\
            \nPesos: {self.omega_m}\nDirecciones: {self.miu_m}\n"


# =================================================================
# Paso B: Runner (Motor de Cálculo)
# =================================================================
class Runner:
    """sumary_line

    Keyword arguments:
    argument -- No necesita argumentos, solo usa la config dada al constructor de la clase y ya.
    Return: Devuelve una tupla con los siguientes valores (self.scalar_flux, self.iteration, self.PSI_RIGHT, self.PSI_LEFT)
    """

    def __init__(self, config: Config):
        self.config = config
        self.converged = False
        self.reflex_izq = config.reflex_izq
        self.reflex_der = config.reflex_der

        self.iteration = 0

        # Flujos Angulares [Nodos x Direcciones]
        # PSI_RIGHT: neutrones viajando hacia x+ (mu > 0)
        # PSI_LEFT:  neutrones viajando hacia x- (mu < 0)
        self.PSI_RIGHT = np.zeros((config.NTP, config.N_HALF))
        self.PSI_LEFT = np.zeros((config.NTP, config.N_HALF))

        # Flujo Escalar [Celdas]
        self.scalar_flux = np.zeros(config.NTC)

        # Fuente Total [Celdas] (Scattering + Externa)
        self.total_source = np.zeros(config.NTC)

        if self.reflex_der or self.reflex_izq:
            if not self.reflex_der:
                self.boundary_conditions_right()
                self.PSI_LEFT[-1, :] = 1.0

            if not self.reflex_izq:
                self.boundary_conditions_left()
                self.PSI_RIGHT[0, :] = 1.0
        else:
            # Inicializamos en 1 solo para evitar ceros, se ajustará en el loop
            self.PSI_RIGHT[0, :] = 1.0
            self.PSI_LEFT[-1, :] = 1.0

        if not self.reflex_der and not self.reflex_izq:
            self.boundary_conditions_left()
            self.boundary_conditions_right()

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
        # Pre-calculamos fuente total isotrópica: Q_total = 0.5 * (Q_ext + Sigma_S * Phi)
        # El 0.5 asume simetría/normalización planar standard.
        self.total_source = 0.5 * (
            self.config.q_ext_vec + self.config.sigma_s_vec * self.scalar_flux
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

        for k in range(self.config.NTC):
            suma = 0.0
            for m in range(self.config.N_HALF):
                w = self.config.omega_m[m]

                # Promedio en el centro de la celda (Diamond Difference Average)
                # psi_avg = 0.5 * (psi_in + psi_out)
                psi_avg_der = 0.5 * (self.PSI_RIGHT[k, m] + self.PSI_RIGHT[k + 1, m])
                psi_avg_izq = 0.5 * (self.PSI_LEFT[k, m] + self.PSI_LEFT[k + 1, m])

                # Sumamos ambas direcciones (asumiendo simetría de pesos x2 o sumando explícitamente)
                # Si w es para todo el ángulo sólido, w_izq = w_der
                suma += w * (psi_avg_der + psi_avg_izq)

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

    def check_convergence(self, old_flux):
        # Manejo seguro de división por cero
        denom = np.where(self.scalar_flux > 1e-13, self.scalar_flux, 1.0)
        diff = np.abs(self.scalar_flux - old_flux)
        rel_error = np.max(diff / denom)

        if self.iteration % 100 == 0:
            print(f"Iter {self.iteration}: Error Max = {rel_error:.2e}")
            logger.info(f"Iter {self.iteration}: Error Max = {rel_error:.2e}")

        return rel_error < self.config.epsilon

    def __call__(self):
        logger.info("Iniciando Iteracion de Fuente...")
        print("\n--- INICIANDO CÁLCULO ---")
        start = time()
        while self.iteration < self.config.max_iter:
            self.iteration += 1

            # 1. Actualizar fronteras si es reflexiva
            if self.config.reflex_der:
                self.update_reflective_boundaries_right()
            if self.config.reflex_izq:
                self.update_reflective_boundaries_left()

            # 2. Barrido (Transport Sweep)
            self.sweep()

            # 3. Calcular flujo escalar y obtener el anterior
            old_flux = self.calculo_flujo()

            # 4. Chequear convergencia
            if self.check_convergence(old_flux):
                print(f"\nCONVERGENCIA ALCANZADA en iteración {self.iteration}.")
                self.converged = True
                break

        if not self.converged:
            print("\nADVERTENCIA: Máximo de iteraciones alcanzado sin convergencia.")
        logger.info(f"Tiempo demorado de los calculos: {time() - start}")

        # Crear DataFrame con los resultados
        df_output = self._crear_dataframe_salida()

        # Guardar automáticamente en Excel
        self._guardar_excel(df_output)

        # Retornar diccionario con resultados
        resultado = {
            "scalar_flux": self.scalar_flux,
            "iteration": self.iteration,
            "PSI_RIGHT": self.PSI_RIGHT,
            "PSI_LEFT": self.PSI_LEFT,
            "converged": self.converged,
            "dataframe": df_output,
        }

        return resultado

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
                        ],
                        "Valor": [
                            self.iteration,
                            "converge" if self.converged else "no converge",
                            self.config.epsilon,
                            self.config.max_iter,
                            self.config.NTC,
                            self.config.NTP,
                            f"S{self.config.N}",
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


# # =================================================================
# # BLOQUE MAIN PARA EJECUCIÓN
# # =================================================================
# if __name__ == "__main__":
#     # Ejemplo de uso
#     try:
#         conf = Config(num_regions=1, num_zones=1)
#         # Usamos inputs manuales como en tu código original
#         conf.manual_input()

#         # Preguntar si es reflexiva
#         ref = input("¿Condiciones reflexivas? (s/n): ").lower() == 's'

#         runner = Runner(conf)
#         flux_result = runner()

#         print("\n--- RESULTADO FINAL (FLUJO ESCALAR) ---")
#         print(flux_result)

#     except ValueError as e:
#         print(f"Error de entrada: {e}")
#     except Exception as e:
#         print(f"Error inesperado: {e}")
#         logger.error(e, exc_info=True)
