"""Run the 1D CLI in a subprocess and stream its output."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

from core.placeholders import detect_placeholders
from utils.paths import PROJECT_ROOT

ROOT = PROJECT_ROOT

LineCallback = Callable[[str], None]


class RunProcess:
    """One cancellable 1D run."""

    def __init__(self) -> None:
        self.process: subprocess.Popen[str] | None = None
        self.cancelled = False

    @property
    def is_running(self) -> bool:
        """True while the child process is alive."""
        return self.process is not None and self.process.poll() is None

    def cancel(self, timeout: float = 5.0) -> None:
        """Terminate the child process, escalating to kill if it ignores us."""
        self.cancelled = True
        process = self.process
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        except OSError:  # already gone
            self.cancelled = True

    def run(
        self,
        config_paths: list[Path] | Path,
        output_path: Path,
        *,
        excel: bool | str = False,
        scheme: str | None = None,
        on_line: LineCallback | None = None,
    ) -> dict:
        """Execute ``python -m cli.run_1d`` and return a result summary."""
        paths = (
            [Path(config_paths)]
            if isinstance(config_paths, (str, Path))
            else [Path(path) for path in config_paths]
        )
        if not paths:
            raise ValueError("Select at least one configuration.")

        configs = self._load_configs(paths)
        for config in configs:
            placeholders = detect_placeholders(config)
            if placeholders:
                names = ", ".join(sorted(placeholders))
                raise ValueError(
                    f"Configuration has placeholders ({names}); "
                    "expand it with the Sweep tab first."
                )
            if scheme:
                config["SPATIAL_SCHEME"] = scheme

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix="nts-tui-"))
        temp_json = temp_dir / "configs.json"
        temp_json.write_text(json.dumps(configs, indent=2) + "\n")

        command = [
            sys.executable,
            "-m",
            "cli.run_1d",
            "--json",
            str(temp_json),
            "-o",
            str(output_path),
        ]
        if excel:
            command.append("--excel")
            if isinstance(excel, str):
                command.append(excel)

        env = os.environ.copy()
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{ROOT}{os.pathsep}{existing}" if existing else str(ROOT)

        lines: list[str] = []

        def emit(line: str) -> None:
            lines.append(line)
            if on_line is not None:
                on_line(line)

        try:
            self.process = subprocess.Popen(
                command,
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert self.process.stdout is not None
            for line in self.process.stdout:
                emit(line.rstrip("\n"))
            returncode = self.process.wait()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            self.process = None

        return {
            "returncode": returncode,
            "output_path": output_path,
            "log": "\n".join(lines),
            "cancelled": self.cancelled,
        }

    @staticmethod
    def _load_configs(paths: list[Path]) -> list[dict]:
        configs: list[dict] = []
        for path in paths:
            with path.open("r") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                configs.append(data)
            elif isinstance(data, list) and all(
                isinstance(item, dict) for item in data
            ):
                configs.extend(data)
            else:
                raise ValueError(f"{path} must contain an object or a list of objects.")
        return configs
