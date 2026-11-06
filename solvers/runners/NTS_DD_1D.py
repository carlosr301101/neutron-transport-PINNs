"""1D S_N solver with Diamond Difference spatial discretization.

This module is also the compatibility facade: ``Config``, ``Runner`` and the
public helpers are re-exported here because existing scripts and tests import
them from this path.
"""

from .config import Config
from .runner import Runner
from .scheme import (  # noqa: F401  (re-exported for compatibility)
    Method,
    Scheme,
    cell_average,
    cell_out,
    get_scheme,
    method_from_name,
    theta_step_characteristic,
)


class DiamondDifference:
    """Diamond Difference: second order, arithmetic interface mean."""

    method = Method.DD

    def prepare(self, config) -> None:
        return None

    def cell_out(self, psi_in, source, sigma_t, dx, mu, theta=None) -> float:
        a = mu / dx
        return ((a - 0.5 * sigma_t) * psi_in + source) / (
            a + 0.5 * sigma_t
        )

    def cell_average(
        self, psi_in, psi_out, sigma_t, dx, mu, theta=None
    ) -> float:
        return 0.5 * (psi_in + psi_out)


SCHEME = DiamondDifference()


def solve(config: Config, **kwargs) -> dict:
    """Run the 1D transport solver with the Diamond Difference scheme."""
    return Runner(config, scheme=SCHEME, **kwargs)()
