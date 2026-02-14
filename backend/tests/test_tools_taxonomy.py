"""Tests for taxonomy tools (match_taxonomy, check_schema)."""

import json

import pytest
import pytest_asyncio
import aiosqlite

from src.db.schema import SCHEMA_SQL
from src.agent.tools.taxonomy import match_taxonomy, check_schema


@pytest_asyncio.fixture
async def db():
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.executescript(SCHEMA_SQL)
    # Seed two taxonomy entries
    await conn.execute(
        "INSERT INTO standard_units (id, label, description, category, expected_sub_items, expected_units) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            "hidroizolacija-ravnog-krova",
            "Hidroizolacija ravnog krova",
            "Izvedba hidroizolacije ravnog krova s bitumenskim trakama uključujući parnu branu",
            "Krovopokrivački radovi",
            json.dumps(["parna brana", "toplinska izolacija", "hidroizolacijska membrana"]),
            json.dumps(["m²", "m"]),
        ),
    )
    await conn.execute(
        "INSERT INTO standard_units (id, label, description, category, expected_sub_items, expected_units) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            "betonski-radovi",
            "Betonski radovi",
            "Izvedba betonskih konstrukcija i podloga beton C40/50",
            "Konstruktorski radovi",
            json.dumps(["beton C40/50", "armatura", "oplata"]),
            json.dumps(["m³", "m²", "kg"]),
        ),
    )
    await conn.commit()
    yield conn
    await conn.close()


@pytest.mark.asyncio
async def test_match_taxonomy_finds_best_match(db):
    results = await match_taxonomy(db, "Hidroizolacija krova s bitumenskim trakama")
    assert len(results) >= 1
    assert results[0]["id"] == "hidroizolacija-ravnog-krova"


@pytest.mark.asyncio
async def test_match_taxonomy_returns_top_3(db):
    results = await match_taxonomy(db, "radovi izolacija beton")
    assert len(results) <= 3


@pytest.mark.asyncio
async def test_match_taxonomy_no_match(db):
    results = await match_taxonomy(db, "xyznonexistent")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_check_schema_all_present(db):
    rows = [
        {"description": "Parna brana na bazi PE folije", "unit": "m²"},
        {"description": "Toplinska izolacija XPS 5cm", "unit": "m²"},
        {"description": "Hidroizolacijska membrana", "unit": "m²"},
    ]
    result = await check_schema(db, "hidroizolacija-ravnog-krova", rows)
    assert len(result["missing_sub_items"]) == 0
    assert len(result["extra_sub_items"]) == 0


@pytest.mark.asyncio
async def test_check_schema_missing_and_extra(db):
    rows = [
        {"description": "Parna brana PE folija", "unit": "m²"},
        {"description": "Vertikalna hidroizolacija uz zidove", "unit": "m"},
    ]
    result = await check_schema(db, "hidroizolacija-ravnog-krova", rows)
    # "toplinska izolacija" and "hidroizolacijska membrana" are missing
    assert "toplinska izolacija" in result["missing_sub_items"]
    # "Vertikalna hidroizolacija uz zidove" is extra
    assert len(result["extra_sub_items"]) >= 1


@pytest.mark.asyncio
async def test_check_schema_unknown_taxonomy(db):
    result = await check_schema(db, "nonexistent-type", [])
    assert result["error"] == "taxonomy_not_found"
