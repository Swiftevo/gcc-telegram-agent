"""Run the original executable suites during unittest discovery."""

from pathlib import Path
import os
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SUITES = (
    "tests/persistence/test_database.py",
    "tests/access/test_guard.py",
    "tests/qa/test_qa.py",
    "tests/applications/test_application.py",
    "tests/knowledge/test_cases.py",
)


class RegressionSuites(unittest.TestCase):
    def test_executable_suites(self) -> None:
        for suite in SUITES:
            with self.subTest(suite=suite):
                env = os.environ.copy()
                env["PYTHONPATH"] = str(ROOT)
                result = subprocess.run(
                    [sys.executable, "-B", suite],
                    cwd=ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(
                    0,
                    result.returncode,
                    msg=f"{suite}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
                )


if __name__ == "__main__":
    unittest.main()
