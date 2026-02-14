"""SQLite database connection and initialization."""

import aiosqlite

from ..config import DB_PATH
from .schema import SCHEMA_SQL

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(str(DB_PATH))
        _db.row_factory = aiosqlite.Row
    return _db


async def init_db():
    db = await get_db()
    await db.executescript(SCHEMA_SQL)
    await db.commit()


async def close_db():
    global _db
    if _db is not None:
        await _db.close()
        _db = None
