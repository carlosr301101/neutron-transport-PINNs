"""Run the 2D C solvers from the TUI."""

from __future__ import annotations

import json
import subprocess
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from core.config import SimulationConfig
from core.input_builder import InputBuilder
from utils.paths import INPUTS_DIR, RESULTS_DIR, get_solver_path

EventCallback = Callable[[str], None]


@dataclass
class RunOutcome:
    """Result of one solver invocation."""

    config: Path
    input: Path | None = None
    output: Path | None = None
    status: int | None = None
    iterations: int | None = None
    cpu: float | None = None
    error: str = ""
    cancelled: bool = False
    lines: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == 0 and not self.error and not self.cancelled


class SolverRunner:
    """Build ``input.txt`` files and execute the C binaries.

    ``inputs_dir`` and ``results_dir`` default to the user's work directory and
    can be overridden by tests.
    """

    def __init__(
        self,
        inputs_dir: Path | str | None = None,
        results_dir: Path | str | None = None,
        timeout: int = 3600,
    ) -> None:
        self.inputs_dir = Path(inputs_dir or INPUTS_DIR)
        self.results_dir = Path(results_dir or RESULTS_DIR)
        self.timeout = timeout
        self.cancelled = False
        self._processes: dict[Path, subprocess.Popen[str]] = {}
        self._lock = threading.Lock()

    # -- paths ---------------------------------------------------------
    def _next_index(self) -> int:
        highest = 0
        for path in self.inputs_dir.glob("input_*.txt"):
            parts = path.stem.split("_")
            if len(parts) == 2:
                try:
                    highest = max(highest, int(parts[1]))
                except ValueError:
                    continue
        return highest + 1

    def prepare(self, config_path: Path, index: int) -> tuple[Path, Path]:
        """Build ``input_NNN.txt`` for *config_path* and return both paths."""
        config = SimulationConfig.from_json_file(str(config_path))
        self.inputs_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        input_path = self.inputs_dir / f"input_{index:03d}.txt"
        output_path = self.results_dir / f"output_{index:03d}.json"
        InputBuilder(config).save(str(input_path))
        return input_path, output_path

    # -- execution -----------------------------------------------------
    def run(
        self,
        config_paths: list[Path] | list[str],
        solver: str,
        workers: int = 1,
        on_event: EventCallback | None = None,
    ) -> list[RunOutcome]:
        """Run every configuration, up to *workers* in parallel."""
        paths = [Path(path) for path in config_paths]
        if not paths:
            raise ValueError("Select at least one configuration.")

        binary = get_solver_path(solver)
        self.cancelled = False

        def emit(message: str) -> None:
            if on_event is not None:
                on_event(message)

        jobs: list[tuple[int, Path, Path, Path]] = []
        failures: dict[int, RunOutcome] = {}
        next_index = self._next_index()
        emit(f"Running {len(paths)} configuration(s) with {solver}")

        for offset, config_path in enumerate(paths):
            index = next_index + offset
            try:
                input_path, output_path = self.prepare(config_path, index)
            except Exception as exc:  # noqa: BLE001 - report and continue
                failures[index] = RunOutcome(
                    config=config_path, error=f"{config_path.name}: {exc}"
                )
                emit(f"ERROR {config_path.name}: {exc}")
                continue
            jobs.append((index, config_path, input_path, output_path))

        outcomes: dict[int, RunOutcome] = dict(failures)
        if jobs:
            with ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
                futures = {
                    pool.submit(
                        self._run_job,
                        index,
                        config_path,
                        input_path,
                        output_path,
                        binary,
                        emit,
                    ): index
                    for index, config_path, input_path, output_path in jobs
                }
                for future in as_completed(futures):
                    index = futures[future]
                    outcomes[index] = future.result()

        return [outcomes[index] for index in sorted(outcomes)]

    def _run_job(
        self,
        index: int,
        config_path: Path,
        input_path: Path,
        output_path: Path,
        binary: Path,
        emit: EventCallback,
    ) -> RunOutcome:
        outcome = RunOutcome(config=config_path, input=input_path, output=output_path)
        emit(f"[{config_path.name}] started {input_path.name} -> {output_path}")
        try:
            process = subprocess.Popen(
                [str(binary), str(input_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as exc:
            outcome.error = f"{config_path.name}: {exc}"
            emit(f"ERROR {outcome.error}")
            return outcome

        with self._lock:
            self._processes[input_path] = process
        try:
            stdout, stderr = process.communicate(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            outcome.error = f"{config_path.name}: timed out after {self.timeout}s"
        finally:
            with self._lock:
                self._processes.pop(input_path, None)

        if self.cancelled:
            outcome.cancelled = True
            outcome.error = "cancelled"
        if process.returncode not in (0, None) and not outcome.error:
            outcome.error = (
                f"{config_path.name}: process exited with {process.returncode}"
            )

        try:
            output_path.write_text(stdout, encoding="utf-8")
        except OSError as exc:
            outcome.error = outcome.error or (
                f"{config_path.name}: cannot write output: {exc}"
            )

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            data = {}
            if not outcome.error:
                outcome.error = f"{config_path.name}: solver did not return JSON"

        outcome.status = data.get("STATUS")
        outcome.iterations = data.get("ITER")
        outcome.cpu = data.get("CPU")
        if stderr.strip():
            outcome.lines = [line for line in stderr.splitlines() if line.strip()]

        if outcome.error:
            emit(f"ERROR {outcome.error}")
        else:
            emit(
                f"[{config_path.name}] STATUS={outcome.status} "
                f"ITER={outcome.iterations} CPU={outcome.cpu}"
            )
        return outcome

    # -- control -------------------------------------------------------
    def cancel(self) -> None:
        """Terminate every solver started by this runner."""
        self.cancelled = True
        with self._lock:
            processes = list(self._processes.values())
        for process in processes:
            try:
                process.terminate()
            except OSError:
                continue
