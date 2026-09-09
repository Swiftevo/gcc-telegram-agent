import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from gcc_agent.ops.sqlite_backup import (
    BackupValidationError,
    create_backup,
    verify_database,
    verify_manifest,
)


SCHEMA = """
CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY);
CREATE TABLE users (user_id INTEGER PRIMARY KEY, username TEXT);
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id)
);
CREATE TABLE messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    user_id INTEGER NOT NULL REFERENCES users(user_id)
);
CREATE TABLE email_verifications (
    user_id INTEGER PRIMARY KEY REFERENCES users(user_id)
);
CREATE TABLE agent_credentials (
    user_id INTEGER PRIMARY KEY REFERENCES users(user_id)
);
INSERT INTO schema_migrations(version) VALUES (1), (2), (3), (4);
INSERT INTO users(user_id, username) VALUES (1, 'backup-test');
INSERT INTO sessions(session_id, user_id) VALUES ('session-1', 1);
INSERT INTO messages(message_id, session_id, user_id)
VALUES ('message-1', 'session-1', 1);
"""


class SQLiteBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)
        self.source = self.root / "source.db"
        with closing(sqlite3.connect(self.source)) as db:
            db.executescript(SCHEMA)

    def tearDown(self):
        self.temp_directory.cleanup()

    def test_create_backup_is_consistent_and_writes_manifest(self):
        backup, manifest, evidence = create_backup(
            self.source, self.root / "backups"
        )

        with closing(sqlite3.connect(self.source)) as db:
            db.execute("INSERT INTO users(user_id, username) VALUES (2, 'later')")
            db.commit()

        restored = verify_database(backup)
        self.assertEqual(1, restored["row_counts"]["users"])
        self.assertEqual("ok", evidence["integrity_check"])
        self.assertEqual(evidence["sha256"], restored["sha256"])
        self.assertEqual(
            evidence["sha256"],
            json.loads(manifest.read_text(encoding="utf-8"))["sha256"],
        )
        self.assertTrue(verify_manifest(restored, manifest)["manifest_match"])

        with closing(sqlite3.connect(backup)) as db:
            db.execute("INSERT INTO users(user_id, username) VALUES (3, 'changed')")
            db.commit()
        with self.assertRaisesRegex(BackupValidationError, "does not match manifest"):
            verify_manifest(verify_database(backup), manifest)

    def test_verify_rejects_missing_required_table(self):
        with closing(sqlite3.connect(self.source)) as db:
            db.execute("DROP TABLE agent_credentials")
            db.commit()

        with self.assertRaisesRegex(BackupValidationError, "required table"):
            verify_database(self.source)

    def test_verify_rejects_non_database_file(self):
        invalid = self.root / "invalid.db"
        invalid.write_text("not a SQLite database", encoding="utf-8")

        with self.assertRaisesRegex(BackupValidationError, "validation failed"):
            verify_database(invalid)


if __name__ == "__main__":
    unittest.main()
