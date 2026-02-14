"""CRUD endpoints for the standard unit taxonomy."""

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db.database import get_db

router = APIRouter()


class StandardUnitCreate(BaseModel):
    id: str
    label: str
    description: str
    category: str
    expected_sub_items: list[str] = []
    expected_units: list[str] = []


class TaxonomySeedRequest(BaseModel):
    units: list[StandardUnitCreate]


@router.get("/taxonomy")
async def list_taxonomy() -> list[dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT id, label, description, category, expected_sub_items, expected_units FROM standard_units"
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": row["id"],
            "label": row["label"],
            "description": row["description"],
            "category": row["category"],
            "expected_sub_items": json.loads(row["expected_sub_items"]),
            "expected_units": json.loads(row["expected_units"]),
        }
        for row in rows
    ]


@router.post("/taxonomy/seed")
async def seed_taxonomy(body: TaxonomySeedRequest) -> dict[str, int]:
    db = await get_db()
    count = 0
    for unit in body.units:
        await db.execute(
            "INSERT OR REPLACE INTO standard_units (id, label, description, category, expected_sub_items, expected_units) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                unit.id,
                unit.label,
                unit.description,
                unit.category,
                json.dumps(unit.expected_sub_items, ensure_ascii=False),
                json.dumps(unit.expected_units, ensure_ascii=False),
            ),
        )
        count += 1
    await db.commit()
    return {"seeded_count": count}
