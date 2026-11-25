"""Failure details must reach the parallel execution summary."""

from __future__ import annotations

import unittest

from execution.parallel import ParallelExecutionResult
from execution.runner import SolverResult


class TestParallelSummaryErrors(unittest.TestCase):
    def test_failed_result_shows_stderr_detail(self):
        result = ParallelExecutionResult()
        result.add_result(
            ("NTS_DD", "input.txt", "output.json"),
            SolverResult(
                success=False,
                exit_code=1,
                duration=0.01,
                stderr="version `GLIBC_2.38' not found",
                error_message="version `GLIBC_2.38' not found",
            ),
        )

        summary = result.get_summary()

        self.assertIn("Failed: 1", summary)
        self.assertIn("GLIBC_2.38", summary)


if __name__ == "__main__":
    unittest.main()
