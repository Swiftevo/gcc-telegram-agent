"""Run every test file through one cross-platform, isolated entry point."""

from pathlib import Path
import os
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = ROOT / "tests"
LEGACY_EXECUTABLE_SUITES = {
    Path("tests/access/test_guard.py"),
    Path("tests/applications/test_application.py"),
    Path("tests/persistence/test_database.py"),
    Path("tests/qa/test_qa.py"),
}
REQUIRED_TEST_SUITES = LEGACY_EXECUTABLE_SUITES | {
    Path("tests/access/test_identity.py"),
    Path("tests/access/test_email_shelved.py"),
    Path("tests/access/test_private_group_member.py"),
    Path("tests/knowledge/test_cases.py"),
    Path("tests/knowledge/test_case_validation.py"),
    Path("tests/knowledge/test_onboarding.py"),
    Path("tests/ops/test_sqlite_backup.py"),
    Path("tests/ops/test_runtime.py"),
    Path("tests/persistence/test_migrations.py"),
    Path("tests/persistence/test_session_scopes.py"),
    Path("tests/telegram_bot/test_group_mentions.py"),
    Path("tests/telegram_bot/test_privacy_notice.py"),
    Path("tests/test_logging.py"),
    Path("tests/test_webhook_security.py"),
}


def _configure_utf8_console() -> None:
    """Keep Traditional Chinese and status symbols printable on Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def _environment() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    existing_path = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(ROOT) if not existing_path else os.pathsep.join((str(ROOT), existing_path))
    )
    return env


def _test_files() -> list[Path]:
    files = []
    for path in TESTS_ROOT.rglob("test_*.py"):
        relative = path.relative_to(ROOT)
        files.append(relative)
    return sorted(files, key=lambda path: path.as_posix())


def _command(relative: Path) -> list[str]:
    if relative in LEGACY_EXECUTABLE_SUITES:
        return [sys.executable, "-B", str(relative)]
    module = ".".join(relative.with_suffix("").parts)
    return [sys.executable, "-B", "-m", "unittest", "-v", module]


def main() -> int:
    _configure_utf8_console()
    test_files = _test_files()
    missing_required_suites = REQUIRED_TEST_SUITES.difference(test_files)
    if missing_required_suites:
        missing = ", ".join(sorted(path.as_posix() for path in missing_required_suites))
        print(f"Test runner configuration error; missing required suites: {missing}")
        return 2

    failures = []
    print(f"Running {len(test_files)} test files in isolated processes")
    for index, relative in enumerate(test_files, start=1):
        label = relative.as_posix()
        print(f"\n[{index}/{len(test_files)}] {label}", flush=True)
        result = subprocess.run(
            _command(relative),
            cwd=ROOT,
            env=_environment(),
            check=False,
        )
        if result.returncode:
            failures.append((label, result.returncode))

    print("\n" + "=" * 72)
    if failures:
        print(f"FAILED: {len(failures)} of {len(test_files)} test files failed")
        for label, returncode in failures:
            print(f"  - {label} (exit {returncode})")
        return 1

    print(f"OK: all {len(test_files)} test files passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
