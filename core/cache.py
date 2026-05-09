import sqlite3
import os
from datetime import datetime
from pathlib import Path


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS translations (
    source_text TEXT PRIMARY KEY,
    translated_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class TranslationCache:
    def __init__(self, db_path=None, max_entries=10000):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "cache.db"
        self._db_path = str(db_path)
        self._max_entries = max_entries
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(CREATE_TABLES_SQL)
        self._conn.commit()

    def get(self, source_text):
        self._prune_if_needed()
        row = self._conn.execute(
            "SELECT translated_text FROM translations WHERE source_text = ?",
            (source_text,),
        ).fetchone()
        return row[0] if row else None

    def set(self, source_text, translated_text):
        self._conn.execute(
            "INSERT OR REPLACE INTO translations(source_text, translated_text, created_at) "
            "VALUES (?, ?, ?)",
            (source_text, translated_text, datetime.now().isoformat()),
        )
        self._conn.commit()
        self._prune_if_needed()

    def count(self):
        row = self._conn.execute("SELECT COUNT(*) FROM translations").fetchone()
        return row[0]

    def _prune_if_needed(self):
        total = self._conn.execute("SELECT COUNT(*) FROM translations").fetchone()[0]
        if total > self._max_entries:
            excess = total - int(self._max_entries * 0.8)
            self._conn.execute(
                "DELETE FROM translations WHERE source_text IN "
                "(SELECT source_text FROM translations ORDER BY created_at ASC LIMIT ?)",
                (excess,),
            )
            self._conn.commit()

    def save_bookmark(self, source_text, translated_text):
        self._conn.execute(
            "INSERT INTO bookmarks(source_text, translated_text) VALUES (?, ?)",
            (source_text, translated_text),
        )
        self._conn.commit()

    def get_bookmarks(self, limit=500, date=None):
        if date:
            rows = self._conn.execute(
                "SELECT source_text, translated_text, created_at "
                "FROM bookmarks WHERE date(created_at) = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (date, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT source_text, translated_text, created_at "
                "FROM bookmarks ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return rows

    def get_bookmark_dates(self):
        return [
            row[0]
            for row in self._conn.execute(
                "SELECT DISTINCT date(created_at) FROM bookmarks "
                "ORDER BY date(created_at) DESC"
            ).fetchall()
        ]

    def close(self):
        self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self._conn.close()
