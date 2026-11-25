"""Platform-specific wheel configuration.

The 2D solvers are native executables, so the wheel must carry a platform tag
and only the binaries of the platform being built:

    NTS_WHEEL_PLATFORM=manylinux_2_28_x86_64 uv build --wheel
    NTS_WHEEL_PLATFORM=win_amd64 uv build --wheel

Without ``NTS_WHEEL_PLATFORM`` the wheel uses the platform of the build
machine (``linux_x86_64``, ``win_amd64``, ...).
"""

from __future__ import annotations

import os
import sys

from setuptools import Distribution, setup

try:  # setuptools >= 70.1
    from setuptools.command.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:  # pragma: no cover - older toolchains
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel

SOLVERS = ("NTS_DD", "NTS_LD", "NTS_STEP", "NTS_RM_CN", "NTS_RM_LLN")


def _solver_binaries() -> list[str]:
    suffix = ".exe" if os.name == "nt" else ""
    return [f"{name}{suffix}" for name in SOLVERS]


def _is_editable_build() -> bool:
    """True for PEP 660 builds (``uv sync``, ``pip install -e``).

    Editable wheels stay ``py3-none-any``: they only add a ``.pth`` pointing at
    the checkout, and a platform tag makes uv look for wheel-variant metadata.
    """
    return "editable_wheel" in sys.argv or "develop" in sys.argv


class BinaryDistribution(Distribution):
    """Mark the distribution as non-pure so the wheel has a platform tag."""

    def has_ext_modules(self) -> bool:
        return True


class bdist_wheel(_bdist_wheel):
    """Force ``py3-none-<platform>`` instead of an ABI-specific tag."""

    def finalize_options(self) -> None:
        super().finalize_options()
        if not _is_editable_build():
            self.root_is_pure = False

    def get_tag(self) -> tuple[str, str, str]:
        if _is_editable_build():
            return "py3", "none", "any"
        platform = os.environ.get("NTS_WHEEL_PLATFORM") or self.plat_name
        return "py3", "none", platform


setup(
    distclass=BinaryDistribution,
    cmdclass={"bdist_wheel": bdist_wheel},
    package_data={
        "tui": ["*.tcss"],
        "tui2d": ["*.tcss"],
        "templates": ["*.json"],
        "solvers.runners": _solver_binaries(),
    },
    include_package_data=False,
)
