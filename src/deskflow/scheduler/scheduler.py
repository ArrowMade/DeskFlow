"""Task scheduler — schedule recurring automated tasks."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ScheduledTask:
    id: int
    name: str
    prompt: str
    cron_expr: str
    enabled: bool
    last_run: str | None
    created_at: str


class TaskScheduler:
    def __init__(self, db_path: str = "~/.deskflow/scheduler.db") -> None:
        self.db_path = os.path.expanduser(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                prompt TEXT NOT NULL,
                cron_expr TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                last_run TEXT,
                created_at TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def add_task(self, name: str, prompt: str, cron_expr: str) -> ScheduledTask:
        cursor = self._conn.execute(
            "INSERT INTO scheduled_tasks (name, prompt, cron_expr, created_at) VALUES (?, ?, ?, ?)",
            (name, prompt, cron_expr, datetime.now().isoformat()),
        )
        self._conn.commit()
        return ScheduledTask(
            id=cursor.lastrowid,
            name=name,
            prompt=prompt,
            cron_expr=cron_expr,
            enabled=True,
            last_run=None,
            created_at=datetime.now().isoformat(),
        )

    def list_tasks(self) -> list[ScheduledTask]:
        cursor = self._conn.execute("SELECT * FROM scheduled_tasks WHERE enabled = 1")
        return [
            ScheduledTask(
                id=row[0], name=row[1], prompt=row[2], cron_expr=row[3],
                enabled=bool(row[4]), last_run=row[5], created_at=row[6],
            )
            for row in cursor.fetchall()
        ]

    def remove_task(self, task_id: int) -> bool:
        cursor = self._conn.execute(
            "UPDATE scheduled_tasks SET enabled = 0 WHERE id = ?", (task_id,)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def mark_run(self, task_id: int) -> None:
        self._conn.execute(
            "UPDATE scheduled_tasks SET last_run = ? WHERE id = ?",
            (datetime.now().isoformat(), task_id),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
