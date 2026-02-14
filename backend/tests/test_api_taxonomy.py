"""Tests for taxonomy API endpoints (list_taxonomy, seed_taxonomy)."""

import json
from unittest.mock import patch

import aiosqlite
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.db.schema import SCHEMA_SQL
from src.main import app


@pytest_asyncio.fixture
async def db():
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.executescript(SCHEMA_SQL)
    await conn.commit()
    yield conn
    await conn.close()


@pytest_asyncio.fixture
async def client(db):
    async def _get_db():
        return db

    with patch("src.api.taxonomy.get_db", _get_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.mark.asyncio
async def test_list_taxonomy_empty(client):
    resp = await client.get("/api/taxonomy")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_seed_taxonomy(client):
    body = {
        "units": [
            {
                "id": "hidroizolacija-ravnog-krova",
                "label": "Hidroizolacija ravnog krova",
                "description": "Izvedba hidroizolacije ravnog krova",
                "category": "Krovopokrivački radovi",
                "expected_sub_items": ["parna brana", "toplinska izolacija"],
                "expected_units": ["m²"],
            }
        ]
    }
    resp = await client.post("/api/taxonomy/seed", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["seeded_count"] == 1


@pytest.mark.asyncio
async def test_seed_then_list(client):
    body = {
        "units": [
            {
                "id": "betonski-radovi",
                "label": "Betonski radovi",
                "description": "Izvedba betonskih konstrukcija",
                "category": "Konstruktorski radovi",
                "expected_sub_items": ["beton", "armatura"],
                "expected_units": ["m³", "kg"],
            },
            {
                "id": "zidarski-radovi",
                "label": "Zidarski radovi",
                "description": "Izvedba zidarskih radova",
                "category": "Građevinski radovi",
                "expected_sub_items": [],
                "expected_units": ["m²"],
            },
        ]
    }
    resp = await client.post("/api/taxonomy/seed", json=body)
    assert resp.status_code == 200
    assert resp.json()["seeded_count"] == 2

    resp = await client.get("/api/taxonomy")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    ids = {item["id"] for item in items}
    assert "betonski-radovi" in ids
    assert "zidarski-radovi" in ids

    # Verify deserialized JSON lists
    beton = next(i for i in items if i["id"] == "betonski-radovi")
    assert beton["expected_sub_items"] == ["beton", "armatura"]
    assert beton["expected_units"] == ["m³", "kg"]


@pytest.mark.asyncio
async def test_seed_upsert_replaces_existing(client):
    body1 = {
        "units": [
            {
                "id": "test-unit",
                "label": "Original Label",
                "description": "Original",
                "category": "Cat",
            }
        ]
    }
    await client.post("/api/taxonomy/seed", json=body1)

    body2 = {
        "units": [
            {
                "id": "test-unit",
                "label": "Updated Label",
                "description": "Updated",
                "category": "Cat",
            }
        ]
    }
    resp = await client.post("/api/taxonomy/seed", json=body2)
    assert resp.status_code == 200

    resp = await client.get("/api/taxonomy")
    items = resp.json()
    assert len(items) == 1
    assert items[0]["label"] == "Updated Label"
    assert items[0]["description"] == "Updated"
