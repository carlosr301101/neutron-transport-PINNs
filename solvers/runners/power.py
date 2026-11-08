"""Power normalization helpers for the 1D S_N solver."""

from __future__ import annotations

import numpy as np

# 1 MeV = 1.602176634e-13 J, so E_f[MeV] * 1.602e-13 gives J/fission.
MEV_TO_J = 1.602176634e-13

# Default neutrons per fission: U-238 fast fission (~2.49). It is only used
# to convert NU_SIGF into Sigma_f for power normalization; override it for
# U-235 thermal (~2.43) or other fuels.
DEFAULT_NU = 2.49


def fission_integral(scalar_flux, sigma_f, dx) -> float:
    """Physical fission integral: 2 * sum(sigma_f * phi * dx).

    ``phi`` is the angular average, so the physical reaction-rate integral
    carries the factor 2 (the N quadrature weights sum to 2).
    """
    return 2.0 * float(
        np.sum(
            np.asarray(sigma_f, dtype=float)
            * np.asarray(scalar_flux, dtype=float)
            * np.asarray(dx, dtype=float)
        )
    )


def power_watts(scalar_flux, sigma_f, dx, ef_mev, area_cm2) -> float:
    """Unnormalized thermal power [W] for the given flux distribution."""
    return (
        float(area_cm2)
        * float(ef_mev)
        * MEV_TO_J
        * fission_integral(scalar_flux, sigma_f, dx)
    )


def scale_factor(scalar_flux, sigma_f, dx, ef_mev, area_cm2, target_w) -> float:
    """C_N = target / unnormalized power."""
    power = power_watts(scalar_flux, sigma_f, dx, ef_mev, area_cm2)
    if power <= 0.0:
        raise ValueError("Cannot normalize power: fission integral is zero.")
    return float(target_w) / power
