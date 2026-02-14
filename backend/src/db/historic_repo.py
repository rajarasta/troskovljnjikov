"""Repository for historic BoQ data."""

from datetime import date

from ..models.boq import ParsedBoQ
from ..models.historic import HistoricLine, HistoricMatch, HistoricUnit
from .database import get_db


async def import_boq_to_historic(boq: ParsedBoQ, filename: str) -> int:
    """Import a parsed BoQ into the historic database."""
    db = await get_db()
    cursor = await db.execute(
        "INSERT INTO projects (name, source_filename, format, import_date) VALUES (?, ?, ?, ?)",
        (boq.chapter_title or filename, filename, boq.format_detected.value, date.today().isoformat()),
    )
    project_id = cursor.lastrowid
    count = 0

    for unit in boq.units:
        cursor = await db.execute(
            "INSERT INTO historic_units (project_id, item_number, title, description, parent_section, parent_chapter) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, unit.item_number, unit.title, unit.description,
             unit.parent_section, unit.parent_chapter),
        )
        unit_id = cursor.lastrowid

        for line in unit.priced_lines:
            await db.execute(
                "INSERT INTO historic_lines (unit_id, item_number, description, unit_of_measure, quantity, unit_price, total) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (unit_id, line.item_number, line.description, line.unit,
                 line.quantity, line.unit_price, line.total),
            )
            count += 1

    await db.commit()
    return count


async def search_historic(query: str, limit: int = 10) -> list[HistoricMatch]:
    """Search historic units by description using FTS5."""
    db = await get_db()
    rows = await db.execute_fetchall(
        """
        SELECT hu.id, hu.item_number, hu.title, hu.description,
               hu.parent_section, hu.parent_chapter, hu.project_id,
               p.name as project_name,
               rank as relevance_score
        FROM historic_units_fts
        JOIN historic_units hu ON hu.id = historic_units_fts.rowid
        JOIN projects p ON p.id = hu.project_id
        WHERE historic_units_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (query, limit),
    )

    matches = []
    for row in rows:
        unit = HistoricUnit(
            id=row["id"],
            project_id=row["project_id"],
            item_number=row["item_number"],
            title=row["title"],
            description=row["description"],
            parent_section=row["parent_section"],
            parent_chapter=row["parent_chapter"],
        )

        line_rows = await db.execute_fetchall(
            "SELECT * FROM historic_lines WHERE unit_id = ?", (row["id"],)
        )
        lines = [
            HistoricLine(
                id=lr["id"],
                unit_id=lr["unit_id"],
                item_number=lr["item_number"],
                description=lr["description"],
                unit_of_measure=lr["unit_of_measure"],
                quantity=lr["quantity"],
                unit_price=lr["unit_price"],
                total=lr["total"],
            )
            for lr in line_rows
        ]

        matches.append(HistoricMatch(
            unit=unit,
            project_name=row["project_name"],
            priced_lines=lines,
            relevance_score=abs(row["relevance_score"]),
        ))

    return matches


async def update_unit_taxonomy(unit_id: int, taxonomy_id: str) -> None:
    """Set the taxonomy_id for a historic unit."""
    db = await get_db()
    await db.execute(
        "UPDATE historic_units SET taxonomy_id = ? WHERE id = ?",
        (taxonomy_id, unit_id),
    )
    await db.commit()
