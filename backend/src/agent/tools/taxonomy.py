"""Taxonomy tools: match_taxonomy and check_schema.

These are deterministic tools called by the Classifier agent.
They query the standard_units table in SQLite.
"""

from __future__ import annotations

import json
from typing import Any

import aiosqlite


async def match_taxonomy(db: aiosqlite.Connection, description: str, limit: int = 3) -> list[dict[str, Any]]:
    """FTS5 search against standard_units. Returns top matches with scores.

    Args:
        db: SQLite connection.
        description: Free-text description to search for.
        limit: Maximum results to return.

    Returns:
        List of dicts with keys: id, label, description, category, score.
    """
    try:
        cursor = await db.execute(
            """
            SELECT su.id, su.label, su.description, su.category,
                   rank AS score
            FROM standard_units_fts
            JOIN standard_units su ON su.rowid = standard_units_fts.rowid
            WHERE standard_units_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (description, limit),
        )
        rows = await cursor.fetchall()
    except Exception:
        return []

    return [
        {
            "id": row["id"],
            "label": row["label"],
            "description": row["description"],
            "category": row["category"],
            "score": abs(row["score"]),
        }
        for row in rows
    ]


async def check_schema(
    db: aiosqlite.Connection,
    taxonomy_id: str,
    rows: list[dict[str, str]],
) -> dict[str, Any]:
    """Compare extracted rows against a standard unit's expected sub-items.

    Args:
        db: SQLite connection.
        taxonomy_id: The standard unit type ID.
        rows: List of dicts with at least a "description" key.

    Returns:
        Dict with: matched_sub_items, missing_sub_items, extra_sub_items,
        unexpected_units, or error if taxonomy_id not found.
    """
    cursor = await db.execute(
        "SELECT expected_sub_items, expected_units FROM standard_units WHERE id = ?",
        (taxonomy_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return {"error": "taxonomy_not_found"}

    expected_subs: list[str] = json.loads(row["expected_sub_items"])
    expected_units: list[str] = json.loads(row["expected_units"])

    row_descriptions = [r.get("description", "").lower() for r in rows]
    row_units = [r.get("unit", "") for r in rows]

    # Match expected sub-items against row descriptions
    matched = []
    missing = []
    for sub in expected_subs:
        sub_lower = sub.lower()
        if any(sub_lower in desc for desc in row_descriptions):
            matched.append(sub)
        else:
            missing.append(sub)

    # Find extra rows that don't match any expected sub-item
    extra = []
    for desc in row_descriptions:
        if desc and not any(sub.lower() in desc for sub in expected_subs):
            extra.append(desc)

    # Check for unexpected units of measure
    unexpected_units = [u for u in row_units if u and u not in expected_units]

    return {
        "matched_sub_items": matched,
        "missing_sub_items": missing,
        "extra_sub_items": extra,
        "unexpected_units": unexpected_units,
    }
