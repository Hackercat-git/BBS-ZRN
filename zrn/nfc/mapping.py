"""
UID -> student number mapping — Project ZRN
ByteBell Software

Stores the link between an NFC UID and a student number in a local SQLite
database. Students register themselves through the enrollment flow on the
terminal.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "mapping.db"


class UIDMapping:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS uid_mapping (
                    uid TEXT PRIMARY KEY,
                    leerlingnummer TEXT NOT NULL,
                    naam TEXT,
                    klas TEXT,
                    aangemaakt TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.commit()

    def get_leerlingnummer(self, uid: str) -> Optional[str]:
        """Look up a student number by UID."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT leerlingnummer FROM uid_mapping WHERE uid = ?", (uid,)
            ).fetchone()
            return row[0] if row else None

    def register(self, uid: str, leerlingnummer: str, naam: str = "", klas: str = ""):
        """Link a UID to a student number (enrollment)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO uid_mapping (uid, leerlingnummer, naam, klas)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(uid) DO UPDATE SET
                    leerlingnummer=excluded.leerlingnummer,
                    naam=excluded.naam,
                    klas=excluded.klas
            """, (uid, leerlingnummer, naam, klas))
            conn.commit()
        logger.info(f"Registered: {uid} -> {leerlingnummer} ({naam}, {klas})")

    def delete(self, uid: str):
        """Remove a link."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM uid_mapping WHERE uid = ?", (uid,))
            conn.commit()

    def all_entries(self) -> list[dict]:
        """All registrations (for admin/debug purposes)."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT uid, leerlingnummer, naam, klas, aangemaakt FROM uid_mapping"
            ).fetchall()
            return [
                {"uid": r[0], "leerlingnummer": r[1], "naam": r[2],
                 "klas": r[3], "aangemaakt": r[4]}
                for r in rows
            ]
