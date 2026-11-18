"""Normalize an existing 1D output to a target power (`nts-1d-normalize`)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

from solvers.runners.power import DEFAULT_NU, power_watts


def _as_list(value) -> list:
    return value if isinstance(value, list) else []


def _dx(config: dict) -> np.ndarray:
    nc = _as_list(config.get("NC"))
    hr = _as_list(config.get("HR"))
    if not nc or len(nc) != len(hr):
        raise ValueError("NC and HR are required to build the mesh.")
    dx: list[float] = []
    for n_raw, h_raw in zip(nc, hr):
        n, h = int(n_raw), float(h_raw)
        if n <= 0 or h <= 0:
            raise ValueError("NC and HR must be positive.")
        dx.extend([h / n] * n)
    return np.asarray(dx, dtype=float)


def _per_cell(values: list, config: dict, name: str) -> np.ndarray:
    nc = _as_list(config.get("NC"))
    izl = _as_list(config.get("IZL"))
    if not nc or len(nc) != len(izl):
        raise ValueError("NC and IZL are required to expand zone data.")
    if not values:
        raise ValueError(f"{name} is required.")
    out: list[float] = []
    for n_raw, zone_raw in zip(nc, izl):
        zone = int(zone_raw) - 1
        if zone < 0 or zone >= len(values):
            raise ValueError(f"{name} has no value for zone {zone_raw}.")
        out.extend([float(values[zone])] * int(n_raw))
    return np.asarray(out, dtype=float)


def _sigma_f(config: dict, nu_override: float | None) -> np.ndarray:
    sigma_f = _as_list(config.get("SIGMA_F"))
    if sigma_f:
        return _per_cell(sigma_f, config, "SIGMA_F")
    nu = nu_override if nu_override is not None else config.get("NU")
    if nu is None:
        nu = DEFAULT_NU
        print(f"Using default NU = {DEFAULT_NU} (U-238 fast fission).")
    if float(nu) <= 0.0:
        raise ValueError("NU must be > 0.")
    nu_sigf = _as_list(config.get("NU_SIGF"))
    if not nu_sigf:
        raise ValueError("NU_SIGF is required when SIGMA_F is missing.")
    return _per_cell(nu_sigf, config, "NU_SIGF") / float(nu)


def normalize_run(
    run: dict,
    power_kw: float,
    ef_mev: float | None = None,
    area_cm2: float | None = None,
    nu: float | None = None,
) -> tuple[float, float]:
    """Scale one run in place. Returns (C_N, P_unnormalized)."""
    config = run.get("configuration") or {}
    scalar = np.asarray(run.get("scalar_flux") or [], dtype=float)
    if scalar.size == 0:
        raise ValueError("run has no scalar_flux")
    dx = _dx(config)
    if dx.size != scalar.size:
        raise ValueError(
            f"NC/HR define {dx.size} cells but scalar_flux has {scalar.size}."
        )
    sigma_f = _sigma_f(config, nu)
    if sigma_f.size != scalar.size:
        raise ValueError("SIGMA_F/NU_SIGF do not match the mesh.")

    ef = float(ef_mev if ef_mev is not None else config.get("E_F_MEV", 200.0))
    area = float(
        area_cm2 if area_cm2 is not None else config.get("AREA_CM2", 1.0)
    )
    if ef <= 0.0 or area <= 0.0:
        raise ValueError("E_F_MEV and AREA_CM2 must be positive.")

    power_unnormalized = power_watts(scalar, sigma_f, dx, ef, area)
    if power_unnormalized <= 0.0:
        raise ValueError("fission integral is zero")

    c_n = float(power_kw) * 1e3 / power_unnormalized
    run["scalar_flux"] = (scalar * c_n).tolist()
    angular = run.get("angular_flux")
    if angular is not None:
        run["angular_flux"] = (np.asarray(angular, dtype=float) * c_n).tolist()
    run["power_unnormalized"] = power_unnormalized
    run["power_scale"] = c_n
    run["power_w"] = float(power_kw) * 1e3
    return c_n, power_unnormalized


def _select_runs(runs: list[dict], selectors: list[str] | None) -> list[dict]:
    if not selectors:
        return runs
    chosen: list[dict] = []
    seen: set[int] = set()
    for selector in selectors:
        index = None
        if selector.isdigit():
            candidate = int(selector)
            if 0 <= candidate < len(runs):
                index = candidate
        else:
            for i, run in enumerate(runs):
                if run.get("config_name") == selector:
                    index = i
                    break
        if index is None:
            raise ValueError(f"run not found: {selector!r}")
        if index not in seen:
            chosen.append(runs[index])
            seen.add(index)
    return chosen


def _positive_float(text: str) -> float:
    value = float(text)
    if value <= 0.0:
        raise argparse.ArgumentTypeError("must be > 0")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nts-1d-normalize",
        description="Normalize a consolidated 1D output to a target power",
    )
    parser.add_argument("source", type=Path, help="Path to output_1d_###.json")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output JSON (default: <stem>_normalized.json)",
    )
    parser.add_argument(
        "--power-kw",
        type=_positive_float,
        required=True,
        help="Target power [kW]",
    )
    parser.add_argument(
        "--ef-mev",
        type=_positive_float,
        help="Recoverable energy per fission [MeV] (default: configuration)",
    )
    parser.add_argument(
        "--area-cm2",
        type=_positive_float,
        help="Slab cross-sectional area [cm^2] (default: configuration)",
    )
    parser.add_argument(
        "--nu",
        type=_positive_float,
        help="Neutrons per fission, used when the config has NU_SIGF but no NU",
    )
    parser.add_argument(
        "--run",
        nargs="+",
        metavar="NAME|INDEX",
        help="Only normalize these runs (name or 0-based index)",
    )
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.source.read_text())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not isinstance(payload, dict) or not isinstance(payload.get("runs"), list):
        print("error: expected a consolidated output with runs[]", file=sys.stderr)
        return 1

    try:
        selected = _select_runs(payload["runs"], args.run)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not selected:
        print("error: no runs selected", file=sys.stderr)
        return 2

    normalized = 0
    for i, run in enumerate(selected):
        name = run.get("config_name") or f"run_{i}"
        try:
            c_n, power_unnormalized = normalize_run(
                run,
                args.power_kw,
                ef_mev=args.ef_mev,
                area_cm2=args.area_cm2,
                nu=args.nu,
            )
        except Exception as exc:
            print(f"! {name}: {exc}", file=sys.stderr)
            continue
        normalized += 1
        print(
            f"✓ {name}: P~={power_unnormalized:.6e} W, C_N={c_n:.6e}, "
            f"P={args.power_kw:g} kW"
        )

    if normalized == 0:
        print("error: no run could be normalized", file=sys.stderr)
        return 1

    payload["runs"] = selected
    payload["total"] = len(selected)
    payload["normalized_at"] = datetime.now().isoformat(timespec="seconds")
    output = args.output or args.source.with_name(
        f"{args.source.stem}_normalized.json"
    )
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"✓ Normalized output: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
