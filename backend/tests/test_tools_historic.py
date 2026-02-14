"""Tests for historic tools (search_historic_by_taxonomy, fetch_similar)."""

import json

import pytest
import pytest_asyncio
import aiosqlite

from src.db.schema import SCHEMA_SQL
from src.agent.tools.historic import search_historic_by_taxonomy, fetch_similar


@pytest_asyncio.fixture
async def db():
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.executescript(SCHEMA_SQL)

    # Seed taxonomy
    await conn.execute(
        "INSERT INTO standard_units (id, label, description, category, expected_sub_items, expected_units) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("hidroizolacija-ravnog-krova", "Hidroizolacija ravnog krova",
         "Hidroizolacija", "Krovopokrivački", "[]", "[]"),
    )

    # Seed project + 2 historic units
    await conn.execute(
        "INSERT INTO projects (id, name, source_filename, format, import_date) VALUES (1, 'Kaufland OS', 'k.xlsx', 'kaufland', '2025-01-01')"
    )
    await conn.execute(
        "INSERT INTO historic_units (id, project_id, item_number, title, description, taxonomy_id) "
        "VALUES (10, 1, '3.1.', 'Hidroizolacija ravnog krova', 'Bitumenske trake', 'hidroizolacija-ravnog-krova')"
    )
    await conn.execute(
        "INSERT INTO historic_units (id, project_id, item_number, title, description, taxonomy_id) "
        "VALUES (11, 1, '3.2.', 'Toplinska izolacija', 'XPS ploče', NULL)"
    )
    # Priced lines for unit 10
    await conn.execute(
        "INSERT INTO historic_lines (id, unit_id, item_number, description, unit_of_measure, quantity, unit_price, total) "
        "VALUES (100, 10, '3.1.a.', 'Parna brana', 'm²', 250.0, 12.50, 3125.0)"
    )
    await conn.execute(
        "INSERT INTO historic_lines (id, unit_id, item_number, description, unit_of_measure, quantity, unit_price, total) "
        "VALUES (101, 10, '3.1.b.', 'Membrana', 'm²', 250.0, 35.00, 8750.0)"
    )
    await conn.commit()
    yield conn
    await conn.close()


@pytest.mark.asyncio
async def test_search_by_taxonomy_finds_matching_units(db):
    results = await search_historic_by_taxonomy(db, "hidroizolacija-ravnog-krova")
    assert len(results) == 1
    assert results[0]["title"] == "Hidroizolacija ravnog krova"
    assert results[0]["project_name"] == "Kaufland OS"
    assert len(results[0]["price_lines"]) == 2


@pytest.mark.asyncio
async def test_search_by_taxonomy_with_keywords(db):
    results = await search_historic_by_taxonomy(
        db, "hidroizolacija-ravnog-krova", keywords="bitumenske"
    )
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_search_by_taxonomy_no_results(db):
    results = await search_historic_by_taxonomy(db, "nonexistent-type")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_fetch_similar_returns_full_unit(db):
    result = await fetch_similar(db, 10)
    assert result is not None
    assert result["title"] == "Hidroizolacija ravnog krova"
    assert result["description"] == "Bitumenske trake"
    assert len(result["price_lines"]) == 2
    assert result["price_lines"][0]["unit_price"] == 12.50


@pytest.mark.asyncio
async def test_fetch_similar_not_found(db):
    result = await fetch_similar(db, 9999)
    assert result is None
