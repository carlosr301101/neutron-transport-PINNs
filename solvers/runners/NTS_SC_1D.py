"""1D S_N solver with Step Characteristic spatial discretization."""

import numpy as np

from .config import Config
from .runner import Runner
from .scheme import Method, theta_step_characteristic


class StepCharacteristic:
    """Step Characteristics: second order, characteristic-weighted average."""

    method = Method.STEP_CHARACTERISTIC

    def prepare(self, config) -> np.ndarray:
        """Optical-thickness weights, shape (NTC, N_HALF)."""
        return np.array(
            [
                [theta_step_characteristic(st * dx / mu) for mu in config.miu_m]
                for st, dx in zip(config.sigma_t_vec, config.dx_vec)
            ],
            dtype=float,
        ).reshape(config.NTC, config.N_HALF)

    def cell_out(self, psi_in, source, sigma_t, dx, mu, theta=None) -> float:
        if theta is None:
            theta = theta_step_characteristic(sigma_t * dx / mu)
        a = mu / dx
        return ((a - 0.5 * sigma_t * (1.0 - theta)) * psi_in + source) / (
            a + 0.5 * sigma_t * (1.0 + theta)
        )

    def cell_average(
        self, psi_in, psi_out, sigma_t, dx, mu, theta=None
    ) -> float:
        if theta is None:
            theta = theta_step_characteristic(sigma_t * dx / mu)
        return 0.5 * (1.0 + theta) * psi_out + 0.5 * (1.0 - theta) * psi_in


SCHEME = StepCharacteristic()


def solve(config: Config, **kwargs) -> dict:
    """Run the 1D transport solver with the Step Characteristic scheme."""
    return Runner(config, scheme=SCHEME, **kwargs)()
