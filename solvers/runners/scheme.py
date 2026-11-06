"""Spatial scheme abstraction for the 1D S_N solver.

``get_scheme`` is the only dispatch point.  The concrete solver modules
(``NTS_DD_1D``, ``NTS_STEP_1D``, ``NTS_SC_1D``) are imported lazily so they
can import this module at load time without creating a cycle.
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Protocol

import numpy as np


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


class Scheme(Protocol):
    """Cell-level spatial discretization."""

    method: Method

    def prepare(self, config) -> np.ndarray | None:
        """Per-run data (SC optical weights); None when not needed."""

    def cell_out(self, psi_in, source, sigma_t, dx, mu, theta=None) -> float:
        """Outgoing angular flux of one cell."""

    def cell_average(
        self, psi_in, psi_out, sigma_t, dx, mu, theta=None
    ) -> float:
        """Cell-averaged angular flux of one cell."""


_REGISTRY: dict[Method, Scheme] = {}


def get_scheme(method) -> Scheme:
    """Resolve a Method (or scheme name) to its singleton implementation."""
    if not _REGISTRY:
        from . import NTS_DD_1D, NTS_SC_1D, NTS_STEP_1D

        _REGISTRY.update(
            {
                Method.DD: NTS_DD_1D.SCHEME,
                Method.STEP: NTS_STEP_1D.SCHEME,
                Method.STEP_CHARACTERISTIC: NTS_SC_1D.SCHEME,
            }
        )
    return _REGISTRY[method_from_name(method)]


def cell_out(psi_in, source, sigma_t, dx, mu, method, theta=None):
    """Outgoing angular flux for the selected scheme (public helper).

    ``mu`` is the direction cosine magnitude; a negative value is
    normalised to |mu|.
    """
    mu = abs(float(mu))
    if mu == 0.0:
        raise ValueError("|mu| must be > 0 to sweep a cell.")
    return get_scheme(method).cell_out(psi_in, source, sigma_t, dx, mu, theta)


def cell_average(psi_in, psi_out, sigma_t, dx, mu, method, theta=None):
    """Cell-averaged angular flux for the selected scheme (public helper)."""
    mu = abs(float(mu))
    if mu == 0.0:
        raise ValueError("|mu| must be > 0 to average a cell.")
    return get_scheme(method).cell_average(
        psi_in, psi_out, sigma_t, dx, mu, theta
    )
