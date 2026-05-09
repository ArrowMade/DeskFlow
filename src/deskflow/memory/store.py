"""SQLite-backed persistent memory store."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path


class MemoryStore:
    def __init__(self, db_path: str = "~/.deskflow/memory.db") -> None:
        self.db_path = os.path.expanduser(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_message TEXT NOT NULL,
                tags TEXT DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT NOT NULL,
                source TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
        """)
        self._conn.commit()

    def save_interaction(self, user_message: str, tags: str = "[]") -> None:
        self._conn.execute(
            "INSERT INTO interactions (timestamp, user_message, tags) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), user_message, tags),
        )
        self._conn.commit()

    def save_fact(self, fact: str, source: str = "") -> None:
        self._conn.execute(
            "INSERT INTO facts (fact, source, created_at) VALUES (?, ?, ?)",
            (fact, source, datetime.now().isoformat()),
        )
        self._conn.commit()

    def get_recent_facts(self, limit: int = 20) -> list[str]:
        cursor = self._conn.execute(
            "SELECT fact FROM facts ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [row[0] for row in cursor.fetchall()]

    def get_recent_interactions(self, limit: int = 10) -> list[dict]:
        cursor = self._conn.execute(
            "SELECT timestamp, user_message FROM interactions ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [
            {"timestamp": row[0], "user_message": row[1]}
            for row in cursor.fetchall()
        ]

    def search_facts(self, query: str) -> list[str]:
        cursor = self._conn.execute(
            "SELECT fact FROM facts WHERE fact LIKE ? ORDER BY created_at DESC",
            (f"%{query}%",),
        )
        return [row[0] for row in cursor.fetchall()]

    def close(self) -> None:
        self._conn.close()
