"""SQLite database layer for the PTG procurement pilot."""

import aiosqlite
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "rfq_data.db")

STATUS_CHOICES = [
    "awaiting_reply",
    "supplier_replied",
    "engineer_review",
    "approved",
    "po_issued",
    "delivery_confirmed",
    "closed",
]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS rfqs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rfq_id TEXT UNIQUE NOT NULL,
    supplier_name TEXT NOT NULL,
    supplier_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'awaiting_reply',
    sent_at TEXT NOT NULL,
    last_reply_at TEXT,
    followup_count INTEGER NOT NULL DEFAULT 0,
    delivery_date TEXT,
    po_number TEXT,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.commit()


def _row_to_dict(row, cursor) -> dict:
    columns = [d[0] for d in cursor.description]
    return dict(zip(columns, row))


async def get_all_open() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM rfqs WHERE status != 'closed' ORDER BY sent_at ASC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_rfq(rfq_id: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM rfqs WHERE rfq_id = ?", (rfq_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_rfq_by_id(id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM rfqs WHERE id = ?", (id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_rfq(
    rfq_id: str,
    supplier_name: str,
    supplier_email: str,
    subject: str,
    sent_at: str,
) -> dict:
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO rfqs (rfq_id, supplier_name, supplier_email, subject,
                              status, sent_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'awaiting_reply', ?, ?, ?)
            """,
            (rfq_id, supplier_name, supplier_email, subject, sent_at, now, now),
        )
        await db.commit()
    return await get_rfq(rfq_id)


async def update_rfq_status(id: int, status: str) -> Optional[dict]:
    if status not in STATUS_CHOICES:
        raise ValueError(f"Invalid status: {status}")
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE rfqs SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, id),
        )
        await db.commit()
    return await get_rfq_by_id(id)


async def add_note(id: int, note: str) -> Optional[dict]:
    now = datetime.utcnow().isoformat()
    rfq = await get_rfq_by_id(id)
    if not rfq:
        return None
    existing = rfq.get("notes", "")
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    new_notes = f"{existing}\n[{timestamp}] {note}".strip()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE rfqs SET notes = ?, updated_at = ? WHERE id = ?",
            (new_notes, now, id),
        )
        await db.commit()
    return await get_rfq_by_id(id)


async def increment_followup(id: int) -> Optional[dict]:
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE rfqs SET followup_count = followup_count + 1, updated_at = ? WHERE id = ?",
            (now, id),
        )
        await db.commit()
    return await get_rfq_by_id(id)


async def get_next_rfq_number() -> str:
    year = datetime.utcnow().year
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM rfqs WHERE rfq_id LIKE ?", (f"RFQ-{year}-%",)
        ) as cursor:
            row = await cursor.fetchone()
            count = row[0] if row else 0
    return f"RFQ-{year}-{count + 1:03d}"
