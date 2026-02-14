"""Tests for historic_repo (update_unit_taxonomy)."""

from unittest.mock import patch

import aiosqlite
import pytest
import pytest_asyncio

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
async def test_update_unit_taxonomy_sets_taxonomy_id(db):
    """update_unit_taxonomy should set taxonomy_id on the given historic unit."""
    # Seed a project and a historic unit with no taxonomy_id
    cursor = await db.execute(
        "INSERT INTO projects (name, source_filename, format, import_date) VALUES (?, ?, ?, ?)",
        ("Test Project", "test.xlsx", "eurospin", "2026-01-01"),
    )
    project_id = cursor.lastrowid

    await db.execute(
        "INSERT INTO standard_units (id, label, description, category, expected_sub_items, expected_units) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("betonski-radovi", "Betonski radovi", "Betonski radovi opis", "Konstruktorski", "[]", "[]"),
    )

    cursor = await db.execute(
        "INSERT INTO historic_units (project_id, item_number, title, description) "
        "VALUES (?, ?, ?, ?)",
        (project_id, "3.1.", "Test Unit", "Some description"),
    )
    unit_id = cursor.lastrowid
    await db.commit()

    # Verify taxonomy_id is NULL initially
    row = await db.execute_fetchall(
        "SELECT taxonomy_id FROM historic_units WHERE id = ?", (unit_id,)
    )
    assert row[0]["taxonomy_id"] is None

    # Call the function under test
    async def _get_db():
        return db

    with patch("src.db.historic_repo.get_db", _get_db):
        from src.db.historic_repo import update_unit_taxonomy
        await update_unit_taxonomy(unit_id, "betonski-radovi")

    # Verify taxonomy_id is now set
    row = await db.execute_fetchall(
        "SELECT taxonomy_id FROM historic_units WHERE id = ?", (unit_id,)
    )
    assert row[0]["taxonomy_id"] == "betonski-radovi"


@pytest.mark.asyncio
async def test_update_unit_taxonomy_nonexistent_unit(db):
    """update_unit_taxonomy should not fail when unit_id doesn't exist (updates 0 rows)."""
    async def _get_db():
        return db

    with patch("src.db.historic_repo.get_db", _get_db):
        from src.db.historic_repo import update_unit_taxonomy
        # Should not raise any exception
        await update_unit_taxonomy(99999, "some-taxonomy-id")

    # Verify no rows were affected (table should be empty or unchanged)
    rows = await db.execute_fetchall("SELECT * FROM historic_units")
    assert len(rows) == 0
