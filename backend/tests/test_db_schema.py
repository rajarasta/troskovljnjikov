"""Tests for database schema including standard_units."""

import pytest
import pytest_asyncio
import aiosqlite

from src.db.schema import SCHEMA_SQL


@pytest_asyncio.fixture
async def db():
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.executescript(SCHEMA_SQL)
    await conn.commit()
    yield conn
    await conn.close()


@pytest.mark.asyncio
async def test_standard_units_table_exists(db):
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='standard_units'"
    )
    row = await cursor.fetchone()
    assert row is not None


@pytest.mark.asyncio
async def test_standard_units_fts_exists(db):
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='standard_units_fts'"
    )
    row = await cursor.fetchone()
    assert row is not None


@pytest.mark.asyncio
async def test_insert_and_search_standard_unit(db):
    await db.execute(
        "INSERT INTO standard_units (id, label, description, category, expected_sub_items, expected_units) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            "hidroizolacija-ravnog-krova",
            "Hidroizolacija ravnog krova",
            "Izvedba hidroizolacije ravnog krova s bitumenskim trakama",
            "Krovopokrivački radovi",
            '["parna brana", "toplinska izolacija", "hidroizolacijska membrana"]',
            '["m²", "m"]',
        ),
    )
    await db.commit()

    cursor = await db.execute(
        "SELECT * FROM standard_units_fts WHERE standard_units_fts MATCH ?",
        ("hidroizolacija",),
    )
    rows = await cursor.fetchall()
    assert len(rows) >= 1


@pytest.mark.asyncio
async def test_historic_units_has_taxonomy_id(db):
    cursor = await db.execute(
        "INSERT INTO projects (name, source_filename, format, import_date) VALUES (?, ?, ?, ?)",
        ("Test Project", "test.xlsx", "eurospin", "2026-01-01"),
    )
    project_id = cursor.lastrowid

    await db.execute(
        "INSERT INTO standard_units (id, label, description, category, expected_sub_items, expected_units) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("test-type", "Test", "Test desc", "Test cat", "[]", "[]"),
    )

    await db.execute(
        "INSERT INTO historic_units (project_id, item_number, title, description, taxonomy_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (project_id, "3.1.", "Test Unit", "A test", "test-type"),
    )
    await db.commit()

    cursor = await db.execute("SELECT taxonomy_id FROM historic_units WHERE item_number = '3.1.'")
    row = await cursor.fetchone()
    assert row["taxonomy_id"] == "test-type"
