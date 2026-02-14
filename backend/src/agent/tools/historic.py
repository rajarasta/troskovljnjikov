"""Historic tools: search_historic_by_taxonomy and fetch_similar.

Deterministic tools called by the Comparator agent.
"""

from __future__ import annotations

from typing import Any, Optional

import aiosqlite


async def search_historic_by_taxonomy(
    db: aiosqlite.Connection,
    taxonomy_id: str,
    keywords: str = "",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Search historic units filtered by taxonomy_id, optionally with FTS keywords."""
    if keywords:
        cursor = await db.execute(
            """
            SELECT hu.id, hu.item_number, hu.title, hu.description,
                   hu.parent_section, hu.parent_chapter,
                   p.name AS project_name, p.source_filename
            FROM historic_units hu
            JOIN projects p ON p.id = hu.project_id
            JOIN historic_units_fts ON historic_units_fts.rowid = hu.id
            WHERE hu.taxonomy_id = ? AND historic_units_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (taxonomy_id, keywords, limit),
        )
    else:
        cursor = await db.execute(
            """
            SELECT hu.id, hu.item_number, hu.title, hu.description,
                   hu.parent_section, hu.parent_chapter,
                   p.name AS project_name, p.source_filename
            FROM historic_units hu
            JOIN projects p ON p.id = hu.project_id
            WHERE hu.taxonomy_id = ?
            LIMIT ?
            """,
            (taxonomy_id, limit),
        )

    rows = await cursor.fetchall()
    results = []
    for row in rows:
        line_cursor = await db.execute(
            "SELECT item_number, description, unit_of_measure, quantity, unit_price, total "
            "FROM historic_lines WHERE unit_id = ?",
            (row["id"],),
        )
        lines = await line_cursor.fetchall()
        results.append({
            "historic_unit_id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "project_name": row["project_name"],
            "item_number": row["item_number"],
            "price_lines": [
                {
                    "item_number": l["item_number"],
                    "description": l["description"],
                    "unit_of_measure": l["unit_of_measure"],
                    "quantity": l["quantity"],
                    "unit_price": l["unit_price"],
                    "total": l["total"],
                }
                for l in lines
            ],
        })

    return results


async def fetch_similar(db: aiosqlite.Connection, unit_id: int) -> Optional[dict[str, Any]]:
    """Fetch full details for a single historic unit."""
    cursor = await db.execute(
        """
        SELECT hu.id, hu.item_number, hu.title, hu.description,
               hu.parent_section, hu.parent_chapter, hu.taxonomy_id,
               p.name AS project_name
        FROM historic_units hu
        JOIN projects p ON p.id = hu.project_id
        WHERE hu.id = ?
        """,
        (unit_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    line_cursor = await db.execute(
        "SELECT item_number, description, unit_of_measure, quantity, unit_price, total "
        "FROM historic_lines WHERE unit_id = ?",
        (unit_id,),
    )
    lines = await line_cursor.fetchall()

    return {
        "historic_unit_id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "project_name": row["project_name"],
        "item_number": row["item_number"],
        "taxonomy_id": row["taxonomy_id"],
        "price_lines": [
            {
                "item_number": l["item_number"],
                "description": l["description"],
                "unit_of_measure": l["unit_of_measure"],
                "quantity": l["quantity"],
                "unit_price": l["unit_price"],
                "total": l["total"],
            }
            for l in lines
        ],
    }
