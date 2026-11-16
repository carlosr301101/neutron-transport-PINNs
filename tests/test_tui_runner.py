"""Tests for the cancellable solver subprocess wrapper."""

from __future__ import annotations

import subprocess
import sys
import unittest

from tui.services.runner import RunProcess


class TestRunProcess(unittest.TestCase):
    def test_idle_process_is_not_running(self):
        process = RunProcess()
        self.assertFalse(process.is_running)
        process.cancel()  # must not raise
        self.assertTrue(process.cancelled)

    def test_cancel_terminates_the_child(self):
        process = RunProcess()
        process.process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            self.assertTrue(process.is_running)
            process.cancel(timeout=5)
            self.assertFalse(process.is_running)
            self.assertTrue(process.cancelled)
        finally:
            if process.process.poll() is None:
                process.process.kill()
                process.process.wait()


if __name__ == "__main__":
    unittest.main()
