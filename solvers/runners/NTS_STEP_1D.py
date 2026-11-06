"""1D S_N solver with Step (implicit upwind) discretization."""

from .config import Config
from .runner import Runner
from .scheme import Method


class Step:
    """Step Difference: first order, cell average = downstream face."""

    method = Method.STEP

    def prepare(self, config) -> None:
        return None

    def cell_out(self, psi_in, source, sigma_t, dx, mu, theta=None) -> float:
        a = mu / dx
        return (a * psi_in + source) / (a + sigma_t)

    def cell_average(
        self, psi_in, psi_out, sigma_t, dx, mu, theta=None
    ) -> float:
        return psi_out


SCHEME = Step()


def solve(config: Config, **kwargs) -> dict:
    """Run the 1D transport solver with the Step scheme."""
    return Runner(config, scheme=SCHEME, **kwargs)()
