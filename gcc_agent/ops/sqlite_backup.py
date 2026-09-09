"""Create and verify consistent backups of the GCC agent SQLite database."""

from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from typing import Any


EXPECTED_TABLES = {
    "agent_credentials",
    "email_verifications",
    "messages",
    "schema_migrations",
    "sessions",
    "users",
}
MINIMUM_MIGRATION_VERSION = 4


class BackupValidationError(RuntimeError):
    """Raised when a database cannot be trusted as a restore source."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _table_names(db: sqlite3.Connection) -> list[str]:
    rows = db.execute(
        "SELECT name FROM sqlite_schema "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [row[0] for row in rows]


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def verify_database(path: str | Path) -> dict[str, Any]:
    """Verify SQLite structure and return non-sensitive restore evidence."""
    database_path = Path(path).resolve()
    if not database_path.is_file():
        raise BackupValidationError(f"database file does not exist: {database_path}")

    try:
        with closing(sqlite3.connect(database_path)) as db:
            db.execute("PRAGMA query_only = ON")
            integrity_rows = [row[0] for row in db.execute("PRAGMA integrity_check")]
            if integrity_rows != ["ok"]:
                raise BackupValidationError(
                    "SQLite integrity_check failed: " + "; ".join(integrity_rows)
                )

            foreign_key_rows = db.execute("PRAGMA foreign_key_check").fetchall()
            if foreign_key_rows:
                raise BackupValidationError(
                    f"SQLite foreign_key_check found {len(foreign_key_rows)} violation(s)"
                )

            tables = _table_names(db)
            missing_tables = sorted(EXPECTED_TABLES - set(tables))
            if missing_tables:
                raise BackupValidationError(
                    "required table(s) missing: " + ", ".join(missing_tables)
                )

            migration_versions = [
                row[0]
                for row in db.execute(
                    "SELECT version FROM schema_migrations ORDER BY version"
                ).fetchall()
            ]
            if not migration_versions or migration_versions[-1] < MINIMUM_MIGRATION_VERSION:
                raise BackupValidationError(
                    "database schema is older than required migration version "
                    f"{MINIMUM_MIGRATION_VERSION}"
                )

            row_counts = {
                table: db.execute(
                    f"SELECT COUNT(*) FROM {_quote_identifier(table)}"
                ).fetchone()[0]
                for table in tables
            }
    except sqlite3.DatabaseError as exc:
        raise BackupValidationError(f"SQLite validation failed: {exc}") from exc

    return {
        "path": str(database_path),
        "size_bytes": database_path.stat().st_size,
        "sha256": _sha256(database_path),
        "integrity_check": "ok",
        "foreign_key_violations": 0,
        "migration_versions": migration_versions,
        "row_counts": row_counts,
    }


def verify_manifest(
    evidence: dict[str, Any], manifest: str | Path
) -> dict[str, Any]:
    """Confirm that a verified database still matches its backup manifest."""
    manifest_path = Path(manifest).resolve()
    if not manifest_path.is_file():
        raise BackupValidationError(f"manifest file does not exist: {manifest_path}")
    try:
        expected = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupValidationError(f"cannot read backup manifest: {exc}") from exc

    mismatches = [
        key
        for key in ("sha256", "size_bytes", "migration_versions", "row_counts")
        if expected.get(key) != evidence.get(key)
    ]
    if mismatches:
        raise BackupValidationError(
            "restored database does not match manifest field(s): "
            + ", ".join(mismatches)
        )

    result = dict(evidence)
    result["manifest"] = str(manifest_path)
    result["manifest_match"] = True
    return result


def create_backup(
    source: str | Path,
    output_directory: str | Path,
    *,
    timestamp: datetime | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    """Create an atomic, validated SQLite backup and a JSON manifest."""
    source_path = Path(source).resolve()
    output_path = Path(output_directory).resolve()
    if not source_path.is_file():
        raise BackupValidationError(f"source database does not exist: {source_path}")

    output_path.mkdir(parents=True, exist_ok=True)
    if source_path.parent == output_path and source_path.name.startswith("gcc_agent-"):
        raise BackupValidationError("refusing to back up a backup as the source database")

    created_at = (timestamp or datetime.now(timezone.utc)).astimezone(timezone.utc)
    filename = f"gcc_agent-{created_at.strftime('%Y%m%dT%H%M%SZ')}.sqlite3"
    final_path = output_path / filename
    manifest_path = output_path / f"{filename}.manifest.json"
    if final_path.exists() or manifest_path.exists():
        raise BackupValidationError(f"backup already exists: {final_path}")

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{filename}.", suffix=".tmp", dir=output_path
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)

    try:
        try:
            with closing(sqlite3.connect(source_path)) as source_db:
                source_db.execute("PRAGMA query_only = ON")
                quick_check = source_db.execute("PRAGMA quick_check").fetchone()[0]
                if quick_check != "ok":
                    raise BackupValidationError(
                        f"source SQLite quick_check failed: {quick_check}"
                    )
                with closing(sqlite3.connect(temporary_path)) as destination_db:
                    source_db.backup(destination_db)
        except sqlite3.DatabaseError as exc:
            raise BackupValidationError(f"SQLite backup failed: {exc}") from exc

        evidence = verify_database(temporary_path)
        os.chmod(temporary_path, 0o600)
        temporary_path.replace(final_path)
        evidence["path"] = str(final_path)
        evidence["created_at"] = created_at.isoformat().replace("+00:00", "Z")
        evidence["source"] = str(source_path)

        manifest_path.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.chmod(manifest_path, 0o600)
        return final_path, manifest_path, evidence
    finally:
        temporary_path.unlink(missing_ok=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or verify a GCC agent SQLite backup."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="create a validated backup")
    create.add_argument("--source", required=True, help="source SQLite database")
    create.add_argument(
        "--output-dir", required=True, help="directory for backup and manifest"
    )

    verify = subparsers.add_parser("verify", help="verify a restored database")
    verify.add_argument("--database", required=True, help="SQLite database to verify")
    verify.add_argument(
        "--manifest", help="optional manifest used to detect transfer or file mismatch"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "create":
            _, _, evidence = create_backup(args.source, args.output_dir)
        else:
            evidence = verify_database(args.database)
            if args.manifest:
                evidence = verify_manifest(evidence, args.manifest)
    except BackupValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
