"""Transport engine for the 1D S_N solver.

The engine is scheme agnostic: the spatial discretization is injected (or
resolved from ``config.method``) and used through the ``Scheme`` protocol.
"""

from __future__ import annotations

import logging
from time import time

import numpy as np
import pandas as pd

from .config import Config
from .power import power_watts
from .scheme import Method, Scheme, get_scheme

logger = logging.getLogger(__name__)


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

    def __init__(
        self,
        config: Config,
        source=None,
        run_name: str | None = None,
        scheme: Scheme | None = None,
    ):
        self.config = config
        self.scheme = scheme if scheme is not None else get_scheme(config.method)
        self.scheme_data = self.scheme.prepare(config)
        # Origen de la configuración (archivo JSON, inputs.py o wizard) para
        # poder mostrarlo en el banner de inicio. Opcional: el Runner también
        # se usa directamente desde Python y desde los tests.
        self.source = source
        self.run_name = run_name
        self.converged = False
        self.reflex_izq = config.reflex_izq
        self.reflex_der = config.reflex_der

        self.iteration = 0
        self.outer_iterations = 0
        self.iteration_eigenvalue = None

        # Flujos Angulares [Nodos x Direcciones]
        # PSI_RIGHT: neutrones viajando hacia x+ (mu > 0)
        # PSI_LEFT:  neutrones viajando hacia x- (mu < 0)
        self.PSI_RIGHT = np.zeros((config.NTP, config.N_HALF))
        self.PSI_LEFT = np.zeros((config.NTP, config.N_HALF))
        # Flujo angular por celda y por direccion: (NTC, N), columnas
        # ordenadas por mu ascendente.  PSI_RIGHT/PSI_LEFT son valores de
        # interfaz; estas son las medias de celda que se reportan.
        self.angular_flux = np.zeros((config.NTC, config.N))
        # mu y omega completos (N direcciones, ordenados por mu ascendente).
        # Los pesos de la mitad positiva suman 1; los N pesos suman 2, por eso
        # el flujo escalar lleva el factor 1/2 (media angular).
        order = np.argsort(np.asarray(config.miu_m, dtype=float))
        self.miu = np.concatenate(
            (
                -np.asarray(config.miu_m, dtype=float)[order][::-1],
                np.asarray(config.miu_m, dtype=float)[order],
            )
        )
        self.omega = np.concatenate(
            (
                np.asarray(config.omega_m, dtype=float)[order][::-1],
                np.asarray(config.omega_m, dtype=float)[order],
            )
        )
        rank = np.argsort(order)
        self._right_col = config.N_HALF + rank
        self._left_col = config.N_HALF - 1 - rank
        # Copias "python-friendly" de los invariantes del barrido: indexar una
        # lista devuelve float nativo y evita el costo de los escalares de
        # NumPy dentro del bucle mas interno.  Se calculan una sola vez.
        self._dx_list = np.asarray(config.dx_vec, dtype=float).tolist()
        self._st_list = np.asarray(config.sigma_t_vec, dtype=float).tolist()
        self._miu_list = np.asarray(config.miu_m, dtype=float).tolist()
        self._abs_miu_list = [abs(mu) for mu in self._miu_list]
        self._omega_list = np.asarray(config.omega_m, dtype=float).tolist()
        self._theta_list = (
            None if self.scheme_data is None else np.asarray(self.scheme_data).tolist()
        )
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
        self.power_unnormalized = None

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
        print("\n--- BOUNDARY CONDITIONS ---")
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
        print("\n--- BOUNDARY CONDITIONS ---")
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
        """Mirror: what leaves one side enters in the opposite direction."""
        # Izquierda (x=0): lo que venía de la izquierda (PSI_LEFT) rebota
        # hacia la derecha.
        self.PSI_RIGHT[0, :] = self.PSI_LEFT[0, :]
        # Derecha (x=L): lo que venía de la derecha (PSI_RIGHT) rebota
        # hacia la izquierda.
        # self.PSI_LEFT[-1, :] = self.PSI_RIGHT[-1, :]

    def update_reflective_boundaries_right(self):
        """Mirror: what leaves one side enters in the opposite direction."""
        # Izquierda (x=0): lo que venía de la izquierda (PSI_LEFT) rebota
        # hacia la derecha.
        # self.PSI_RIGHT[0, :] = self.PSI_LEFT[0, :]
        # Derecha (x=L): lo que venía de la derecha (PSI_RIGHT) rebota
        # hacia la izquierda.
        self.PSI_LEFT[-1, :] = self.PSI_RIGHT[-1, :]

    def sweep(self):
        """Barrido de transporte: calcula flujo escalar y angular en una pasada.

        A diferencia de la version anterior, el promedio de celda se calcula
        aqui mismo (igual que en el solver JavaScript), de modo que no hace
        falta un segundo recorrido en ``calculo_flujo``.  Devuelve el flujo
        escalar previo para que el llamador pueda medir convergencia.
        """
        # Fuente total isotropica.  phi es la media angular:
        # S = Sigma_S * phi + 1/2 * Q_ext + fission_source
        # fission_source = nu*Sigma_f * phi / k (sin el 1/2).
        self.total_source = (
            self.config.sigma_s_vec * self.scalar_flux
            + 0.5 * self.config.q_ext_vec
            + self.fission_source
        )

        old_flux = self.scalar_flux.copy()

        # Locales: evita atributos y escalares de NumPy en el bucle interno.
        ntc = self.config.NTC
        n_half = self.config.N_HALF
        dx_list = self._dx_list
        st_list = self._st_list
        miu_list = self._miu_list
        abs_miu_list = self._abs_miu_list
        omega_list = self._omega_list
        theta_list = self._theta_list
        source_list = self.total_source.tolist()
        right = self.PSI_RIGHT
        left = self.PSI_LEFT
        angular = self.angular_flux
        scalar = self.scalar_flux
        right_col = self._right_col
        left_col = self._left_col
        cell_out = self.scheme.cell_out
        cell_avg = self.scheme.cell_average

        scalar[:] = 0.0
        angular[:] = 0.0

        # --- BARRIDO HACIA LA DERECHA (mu > 0) ---
        for k in range(ntc):
            dx = dx_list[k]
            st = st_list[k]
            src = source_list[k]
            psi_in_row = right[k]
            psi_out_row = right[k + 1]
            theta_row = None if theta_list is None else theta_list[k]
            phi_k = 0.0
            for m in range(n_half):
                theta = None if theta_row is None else theta_row[m]
                psi_in = psi_in_row[m]
                psi_out = cell_out(psi_in, src, st, dx, miu_list[m], theta)
                psi_out_row[m] = psi_out
                psi_avg = cell_avg(psi_in, psi_out, st, dx, miu_list[m], theta)
                angular[k, right_col[m]] = psi_avg
                phi_k += omega_list[m] * psi_avg
            scalar[k] = phi_k

        # --- BARRIDO HACIA LA IZQUIERDA (mu < 0) ---
        # Iteramos k desde NTC-1 hasta 0
        for k in range(ntc - 1, -1, -1):
            dx = dx_list[k]
            st = st_list[k]
            src = source_list[k]
            psi_in_row = left[k + 1]
            psi_out_row = left[k]
            theta_row = None if theta_list is None else theta_list[k]
            phi_k = scalar[k]
            for m in range(n_half):
                theta = None if theta_row is None else theta_row[m]
                psi_in = psi_in_row[m]
                psi_out = cell_out(psi_in, src, st, dx, abs_miu_list[m], theta)
                psi_out_row[m] = psi_out
                psi_avg = cell_avg(psi_in, psi_out, st, dx, abs_miu_list[m], theta)
                angular[k, left_col[m]] = psi_avg
                phi_k += omega_list[m] * psi_avg
            scalar[k] = 0.5 * phi_k

        return old_flux

    def calculo_flujo(self):
        """Recalcula flujo escalar y angular desde los flujos de interfaz.

        Se conserva como API publica (y para diagnostico), pero la iteracion
        usa ``sweep``, que ya promedia en la misma pasada.  Esta version es
        vectorizada: recorre las celdas y direcciones con NumPy en lugar de
        hacerlo con dos bucles Python.
        """
        old_flux = self.scalar_flux.copy()

        cfg = self.config
        method = self.scheme.method
        right = self.PSI_RIGHT
        left = self.PSI_LEFT

        if method is Method.DD:
            avg_right = 0.5 * (right[:-1, :] + right[1:, :])
            avg_left = 0.5 * (left[1:, :] + left[:-1, :])
        elif method is Method.STEP:
            avg_right = right[1:, :]
            avg_left = left[:-1, :]
        else:  # Step Characteristic
            theta = np.asarray(self.scheme_data, dtype=float)
            hi = 0.5 * (1.0 + theta)
            lo = 0.5 * (1.0 - theta)
            avg_right = hi * right[1:, :] + lo * right[:-1, :]
            avg_left = hi * left[:-1, :] + lo * left[1:, :]

        self.angular_flux[:, self._right_col] = avg_right
        self.angular_flux[:, self._left_col] = avg_left
        self.scalar_flux[:] = 0.5 * (
            (avg_right + avg_left) * np.asarray(cfg.omega_m, dtype=float)
        ).sum(axis=1)
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

    @staticmethod
    def _relative_flux_change(old_flux, new_flux) -> float:
        """max_i |1 - phi_new_i / phi_old_i|.

        Algebraically equal to ``max |phi_new - phi_old| / |phi_old|``.
        Cells with ``phi_old = 0`` fall back to an absolute difference
        (the relative change is undefined there).
        """
        old = np.asarray(old_flux, dtype=float)
        new = np.asarray(new_flux, dtype=float)
        denom = np.where(np.abs(old) > 1e-13, np.abs(old), 1.0)
        return float(np.max(np.abs(new - old) / denom))

    def check_convergence(
        self, old_flux, verbose: bool = True, tol: float | None = None
    ):
        """Stop when the relative flux change is below the tolerance.

        ``max_i |1 - phi_new_i / phi_old_i| < epsilon`` (see
        ``_relative_flux_change`` for the zero-flux fallback).  This is the
        only place that increments ``iteration``: one count per completed
        flux update (right + left sweep + scalar-flux recalculation).
        """
        self.iteration += 1
        rel_error = self._relative_flux_change(old_flux, self.scalar_flux)
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
            left_external = (
                cfg.bound_left is not None and np.any(cfg.bound_left != 0.0)
            ) or np.any(self.PSI_RIGHT[0, :] != 0.0)

        right_external = False
        if not cfg.reflex_der:
            right_external = (
                cfg.bound_right is not None and np.any(cfg.bound_right != 0.0)
            ) or np.any(self.PSI_LEFT[-1, :] != 0.0)

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
        # phi es la media angular: las tasas de reaccion usan 2*phi.
        production = 2.0 * float(
            np.sum(cfg.nu_sigma_f_vec * self.scalar_flux * cfg.dx_vec)
        )
        absorption = 2.0 * float(
            np.sum((cfg.sigma_t_vec - cfg.sigma_s_vec) * self.scalar_flux * cfg.dx_vec)
        )
        leakage = self._net_leakage()
        denominator = absorption + leakage
        if denominator <= 0.0 or production <= 0.0:
            return None
        return production / denominator

    def _inner_solve(self) -> bool:
        """Source iteration (scattering) with frozen fission_source.

        La tolerancia interna no se hace más fina que la del flujo: usar
        ``min(epsilon, TOL_K)`` obligaba a ~40 % más barridos sin cambiar
        k_eff de forma apreciable.  ``max`` mantiene el sesgo de scattering
        por debajo de la tolerancia que el usuario pidió.
        """
        self.converged = False
        inner = 0
        inner_tol = max(self.config.epsilon, self.config.TOL_K)
        while inner < self.config.max_iter:
            inner += 1
            if self.reflex_der:
                self.update_reflective_boundaries_right()
            if self.reflex_izq:
                self.update_reflective_boundaries_left()
            old_flux = self.sweep()
            if self.check_convergence(old_flux, verbose=False, tol=inner_tol):
                self.converged = True
                break
        return self.converged

    def _fixed_source_iteration(self):
        logger.info("Starting source iteration (no fission)...")
        self.converged = False
        while self.iteration < self.config.max_iter:
            if self.reflex_der:
                self.update_reflective_boundaries_right()
            if self.reflex_izq:
                self.update_reflective_boundaries_left()
            old_flux = self.sweep()
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
            if self.reflex_der:
                self.update_reflective_boundaries_right()
            if self.reflex_izq:
                self.update_reflective_boundaries_left()
            self.fission_source = (
                cfg.nu_sigma_f_vec * self.scalar_flux / self.k_eff
            )
            old_flux = self.sweep()
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
                cfg.nu_sigma_f_vec * self.scalar_flux / self.k_eff
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

        self.iteration_eigenvalue = self.outer_iterations
        self.converged = self.k_converged
        self.k_balance = self.balance_k()

        if self.k_converged:
            print(
                f"\nEIGENVALUE CONVERGED: k_eff = {self.k_eff:.10f} "
                f"({self.outer_iterations} eigenvalue iterations, "
                f"{self.iteration} flux updates)"
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

        # phi es la media angular: la integral de fision fisica es 2*sum(sf*phi)
        self.power_unnormalized = power_watts(
            self.scalar_flux, sigma_f, cfg.dx_vec, cfg.E_F_MEV, cfg.AREA_CM2
        )
        if self.power_unnormalized <= 0.0:
            raise ValueError("Cannot normalize power: fission integral is zero.")

        target_w = cfg.POWER_KW * 1e3
        self.power_scale = target_w / self.power_unnormalized
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
            "miu": self.miu,
            "omega": self.omega,
            "iteration": self.iteration,
            "iteration_eigenvalue": self.iteration_eigenvalue,
            "PSI_RIGHT": self.PSI_RIGHT,
            "PSI_LEFT": self.PSI_LEFT,
            "converged": self.converged,
            "dataframe": df_output,
            "mode": self.mode,
            "spatial_scheme": self.scheme.method.value,
            "k_eff": self.k_eff,
            "k_balance": self.k_balance,
            "k_history": self.k_history,
            "k_converged": self.k_converged,
            "outer_iterations": self.outer_iterations,
            "power_w": self.power_w,
            "power_scale": self.power_scale,
            "power_unnormalized": self.power_unnormalized,
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
