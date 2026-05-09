import sqlite3
from datetime import datetime
from pathlib import Path

from app.config import DATABASE_PATH
from app.models import Listing


def get_connection():
    db_path = Path(DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                price INTEGER,
                rooms REAL,
                size REAL,
                neighborhood TEXT,
                url TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                notified_at TEXT
            )
            """
        )
        conn.commit()


def listing_exists(external_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT 1 FROM listings WHERE external_id = ? LIMIT 1",
            (external_id,),
        )
        return cursor.fetchone() is not None


def save_listing(listing: Listing):
    now = datetime.utcnow().isoformat()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO listings (
                external_id,
                source,
                title,
                price,
                rooms,
                size,
                neighborhood,
                url,
                first_seen_at,
                notified_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                listing.external_id,
                listing.source,
                listing.title,
                listing.price,
                listing.rooms,
                listing.size,
                listing.neighborhood,
                listing.url,
                now,
            ),
        )
        conn.commit()


def mark_as_notified(external_id: str):
    now = datetime.utcnow().isoformat()

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE listings
            SET notified_at = ?
            WHERE external_id = ?
            """,
            (now, external_id),
        )
        conn.commit()