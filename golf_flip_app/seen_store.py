"""
Simple SQLite-backed deduplication store.

This module stores identifiers of listings that have already been processed
so that the worker does not send duplicate notifications.  Each entry is
keyed by a combination of marketplace and listing_id.  The timestamp
records when the listing was first seen.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


class SeenStore:
    """Persistent store for seen listings backed by SQLite."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        # Ensure the parent directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Create the database table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS seen (
                    marketplace TEXT NOT NULL,
                    listing_id TEXT NOT NULL,
                    seen_at TEXT NOT NULL,
                    PRIMARY KEY (marketplace, listing_id)
                )
                """
            )
            conn.commit()

    def has_seen(self, marketplace: str, listing_id: str) -> bool:
        """Return True if this listing has already been processed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM seen WHERE marketplace=? AND listing_id=?",
                (marketplace, listing_id),
            )
            return cursor.fetchone() is not None

    def mark_seen(self, marketplace: str, listing_id: str) -> None:
        """Mark a listing as seen with the current UTC timestamp."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO seen (marketplace, listing_id, seen_at) VALUES (?, ?, ?)",
                (
                    marketplace,
                    listing_id,
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
