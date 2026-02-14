"""Shared test fixtures for the backend test suite."""

import asyncio
from pathlib import Path

import aiosqlite
import pytest

from src.db.schema import SCHEMA_SQL


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db(tmp_path: Path):
    """Create a fresh in-memory SQLite database with schema applied."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.executescript(SCHEMA_SQL)
    await conn.commit()
    yield conn
    await conn.close()
