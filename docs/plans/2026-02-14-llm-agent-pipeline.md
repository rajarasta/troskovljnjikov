# LLM Agent Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace deterministic price averaging with a 3-stage PydanticAI agent pipeline (Classifier → Comparator → Pricer) that uses tool calls against a local Ministral-3B.

**Architecture:** Three PydanticAI agents chained sequentially. Each has 2-3 focused tools (mix of deterministic DB queries and external calls). The pipeline orchestrator runs them per logical unit and yields SSE events. Plugs into existing FastAPI endpoint and React frontend with no frontend changes.

**Tech Stack:** PydanticAI, FastAPI, aiosqlite, SQLite FTS5, sse-starlette, httpx, pytest

**Working directory:** `/media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/.worktrees/boq-editor`

**Run commands from:** `backend/` subdirectory (where `pyproject.toml` lives)

---

## Task 1: Test Infrastructure

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Modify: `backend/pyproject.toml` (add pytest dependency)

**Step 1: Add pytest to dev dependencies**

In `backend/pyproject.toml`, add after the `[tool.uv]` section:

```toml
[dependency-groups]
dev = ["pytest>=8.0", "pytest-asyncio>=0.24"]
```

**Step 2: Install dependencies**

Run: `cd backend && uv sync`
Expected: Dependencies install including pytest and pytest-asyncio

**Step 3: Create test infrastructure**

Create `backend/tests/__init__.py` (empty file).

Create `backend/tests/conftest.py`:

```python
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
```

**Step 4: Verify pytest runs**

Run: `cd backend && uv run pytest tests/ -v --co`
Expected: "no tests ran" (collection only, no errors)

**Step 5: Commit**

```bash
git add backend/pyproject.toml backend/tests/
git commit -m "chore: add pytest infrastructure"
```

---

## Task 2: Pipeline Schemas

**Files:**
- Create: `backend/src/agent/schemas.py`
- Create: `backend/tests/test_schemas.py`

**Step 1: Write the failing test**

Create `backend/tests/test_schemas.py`:

```python
"""Tests for agent pipeline schemas."""

from src.agent.schemas import (
    ClassResult,
    CompResult,
    Deviation,
    HistoricComparison,
    HistoricPriceLine,
    LinePriceSuggestion,
    PriceRange,
    PriceResult,
)


def test_class_result_minimal():
    result = ClassResult(
        taxonomy_id="hidroizolacija-ravnog-krova",
        taxonomy_label="Hidroizolacija ravnog krova",
        confidence=0.85,
    )
    assert result.taxonomy_id == "hidroizolacija-ravnog-krova"
    assert result.deviations == []
    assert result.unmatched_rows == []


def test_class_result_with_deviations():
    result = ClassResult(
        taxonomy_id="toplinska-izolacija",
        taxonomy_label="Toplinska izolacija",
        confidence=0.72,
        deviations=[
            Deviation(
                field="thickness",
                standard_value="0.3cm",
                actual_value="0.4cm",
                description="Debljina veća od standardne",
            )
        ],
        unmatched_rows=[5, 8],
    )
    assert len(result.deviations) == 1
    assert result.deviations[0].field == "thickness"
    assert result.unmatched_rows == [5, 8]


def test_comp_result():
    classification = ClassResult(
        taxonomy_id="betonski-radovi",
        taxonomy_label="Betonski radovi",
        confidence=0.9,
    )
    result = CompResult(
        classification=classification,
        matches=[
            HistoricComparison(
                historic_unit_id=42,
                project_name="Kaufland Osijek",
                similarity_score=0.88,
                matching_sub_items=["beton C40/50"],
                missing_sub_items=[],
                extra_sub_items=["armatura"],
                price_lines=[
                    HistoricPriceLine(
                        description="Beton",
                        unit_of_measure="m³",
                        quantity=120.0,
                        unit_price=95.0,
                    )
                ],
            )
        ],
        summary="1 slična stavka pronađena",
    )
    assert len(result.matches) == 1
    assert result.matches[0].project_name == "Kaufland Osijek"


def test_price_result():
    result = PriceResult(
        line_prices=[
            LinePriceSuggestion(
                item_number="3.1.1.1.a.",
                suggested_price=45.0,
                confidence=0.8,
                price_range=PriceRange(low=38.0, high=52.0, median=44.5),
                reasoning="Prosjek 4 historijske cijene",
            )
        ],
        overall_reasoning="Cijena u skladu s historijskim podacima",
    )
    assert result.line_prices[0].suggested_price == 45.0
    assert result.line_prices[0].price_range.median == 44.5
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.agent.schemas'`

**Step 3: Implement schemas**

Create `backend/src/agent/schemas.py`:

```python
"""Pydantic schemas for the 3-stage agent pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- Agent 1: Classifier output ---

class Deviation(BaseModel):
    field: str
    standard_value: str
    actual_value: str
    description: str


class ClassResult(BaseModel):
    taxonomy_id: str
    taxonomy_label: str
    confidence: float = Field(ge=0, le=1)
    deviations: list[Deviation] = []
    unmatched_rows: list[int] = []


# --- Agent 2: Comparator output ---

class HistoricPriceLine(BaseModel):
    description: str
    unit_of_measure: str
    quantity: float
    unit_price: float


class HistoricComparison(BaseModel):
    historic_unit_id: int
    project_name: str
    similarity_score: float = Field(ge=0, le=1)
    matching_sub_items: list[str] = []
    missing_sub_items: list[str] = []
    extra_sub_items: list[str] = []
    price_lines: list[HistoricPriceLine] = []


class CompResult(BaseModel):
    classification: ClassResult
    matches: list[HistoricComparison] = []
    summary: str = ""


# --- Agent 3: Pricer output ---

class PriceRange(BaseModel):
    low: float
    high: float
    median: float


class LinePriceSuggestion(BaseModel):
    item_number: str
    suggested_price: float
    confidence: float = Field(ge=0, le=1)
    price_range: PriceRange
    reasoning: str = ""


class PriceResult(BaseModel):
    line_prices: list[LinePriceSuggestion] = []
    overall_reasoning: str = ""
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_schemas.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add backend/src/agent/schemas.py backend/tests/test_schemas.py
git commit -m "feat: add pipeline schemas (ClassResult, CompResult, PriceResult)"
```

---

## Task 3: DB Schema — Standard Units Table

**Files:**
- Modify: `backend/src/db/schema.py`
- Create: `backend/tests/test_db_schema.py`

**Step 1: Write the failing test**

Create `backend/tests/test_db_schema.py`:

```python
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
    # Insert a project first
    cursor = await db.execute(
        "INSERT INTO projects (name, source_filename, format, import_date) VALUES (?, ?, ?, ?)",
        ("Test Project", "test.xlsx", "eurospin", "2026-01-01"),
    )
    project_id = cursor.lastrowid

    # Insert standard unit
    await db.execute(
        "INSERT INTO standard_units (id, label, description, category, expected_sub_items, expected_units) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("test-type", "Test", "Test desc", "Test cat", "[]", "[]"),
    )

    # Insert historic unit with taxonomy_id
    await db.execute(
        "INSERT INTO historic_units (project_id, item_number, title, description, taxonomy_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (project_id, "3.1.", "Test Unit", "A test", "test-type"),
    )
    await db.commit()

    cursor = await db.execute("SELECT taxonomy_id FROM historic_units WHERE item_number = '3.1.'")
    row = await cursor.fetchone()
    assert row["taxonomy_id"] == "test-type"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_db_schema.py -v`
Expected: FAIL — `standard_units` table doesn't exist

**Step 3: Update schema**

In `backend/src/db/schema.py`, append before the closing `"""`:

Add after the `historic_units` table definition (after the `CREATE TABLE IF NOT EXISTS historic_lines` block):

```python
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    client TEXT DEFAULT '',
    location TEXT DEFAULT '',
    import_date TEXT NOT NULL,
    source_filename TEXT NOT NULL,
    format TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS standard_units (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    expected_sub_items TEXT NOT NULL DEFAULT '[]',
    expected_units TEXT NOT NULL DEFAULT '[]',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS standard_units_fts USING fts5(
    label,
    description,
    expected_sub_items,
    content=standard_units,
    content_rowid=rowid,
    tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS standard_units_ai AFTER INSERT ON standard_units BEGIN
    INSERT INTO standard_units_fts(rowid, label, description, expected_sub_items)
    VALUES (new.rowid, new.label, new.description, new.expected_sub_items);
END;

CREATE TRIGGER IF NOT EXISTS standard_units_ad AFTER DELETE ON standard_units BEGIN
    INSERT INTO standard_units_fts(standard_units_fts, rowid, label, description, expected_sub_items)
    VALUES ('delete', old.rowid, old.label, old.description, old.expected_sub_items);
END;

CREATE TABLE IF NOT EXISTS historic_units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    item_number TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    parent_section TEXT DEFAULT '',
    parent_chapter TEXT DEFAULT '',
    taxonomy_id TEXT REFERENCES standard_units(id)
);

CREATE TABLE IF NOT EXISTS historic_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id INTEGER NOT NULL REFERENCES historic_units(id),
    item_number TEXT NOT NULL,
    description TEXT DEFAULT '',
    unit_of_measure TEXT NOT NULL DEFAULT '',
    quantity REAL NOT NULL DEFAULT 0,
    unit_price REAL,
    total REAL
);

CREATE VIRTUAL TABLE IF NOT EXISTS historic_units_fts USING fts5(
    title,
    description,
    content=historic_units,
    content_rowid=id,
    tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS historic_units_ai AFTER INSERT ON historic_units BEGIN
    INSERT INTO historic_units_fts(rowid, title, description)
    VALUES (new.id, new.title, new.description);
END;

CREATE TRIGGER IF NOT EXISTS historic_units_ad AFTER DELETE ON historic_units BEGIN
    INSERT INTO historic_units_fts(historic_units_fts, rowid, title, description)
    VALUES ('delete', old.id, old.title, old.description);
END;

CREATE INDEX IF NOT EXISTS idx_historic_lines_unit
    ON historic_lines(unit_of_measure);

CREATE INDEX IF NOT EXISTS idx_historic_units_project
    ON historic_units(project_id);

CREATE INDEX IF NOT EXISTS idx_historic_units_taxonomy
    ON historic_units(taxonomy_id);
"""
```

**Important:** This is a full replacement of `SCHEMA_SQL`. The existing DB file at `backend/data/historic.db` (if it has data) will need to be migrated. For development, deleting and recreating it is fine. For production, run: `ALTER TABLE historic_units ADD COLUMN taxonomy_id TEXT REFERENCES standard_units(id);`

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_db_schema.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add backend/src/db/schema.py backend/tests/test_db_schema.py
git commit -m "feat: add standard_units table and taxonomy_id to historic_units"
```

---

## Task 4: Taxonomy Tools

**Files:**
- Create: `backend/src/agent/tools/__init__.py`
- Create: `backend/src/agent/tools/taxonomy.py`
- Create: `backend/tests/test_tools_taxonomy.py`

**Step 1: Write the failing test**

Create `backend/tests/test_tools_taxonomy.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_tools_taxonomy.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.agent.tools'`

**Step 3: Implement taxonomy tools**

Create `backend/src/agent/tools/__init__.py` (empty file).

Create `backend/src/agent/tools/taxonomy.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_tools_taxonomy.py -v`
Expected: 6 passed

**Step 5: Commit**

```bash
git add backend/src/agent/tools/ backend/tests/test_tools_taxonomy.py
git commit -m "feat: add taxonomy tools (match_taxonomy, check_schema)"
```

---

## Task 5: Historic Tools

**Files:**
- Create: `backend/src/agent/tools/historic.py`
- Create: `backend/tests/test_tools_historic.py`

**Step 1: Write the failing test**

Create `backend/tests/test_tools_historic.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_tools_historic.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement historic tools**

Create `backend/src/agent/tools/historic.py`:

```python
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
    """Search historic units filtered by taxonomy_id, optionally with FTS keywords.

    Args:
        db: SQLite connection.
        taxonomy_id: Standard unit type to filter by.
        keywords: Optional FTS5 search terms for further filtering.
        limit: Max results.

    Returns:
        List of historic units with their price lines and project info.
    """
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
    """Fetch full details for a single historic unit.

    Args:
        db: SQLite connection.
        unit_id: The historic_units.id to look up.

    Returns:
        Full unit dict with price lines, or None if not found.
    """
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
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_tools_historic.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add backend/src/agent/tools/historic.py backend/tests/test_tools_historic.py
git commit -m "feat: add historic tools (search_historic_by_taxonomy, fetch_similar)"
```

---

## Task 6: Pricing Tools

**Files:**
- Create: `backend/src/agent/tools/pricing.py`
- Create: `backend/tests/test_tools_pricing.py`

**Step 1: Write the failing test**

Create `backend/tests/test_tools_pricing.py`:

```python
"""Tests for pricing tools (diff_historic)."""

from src.agent.tools.pricing import diff_historic


def test_diff_historic_exact_match():
    current = [
        {"item_number": "a.", "description": "Parna brana PE folija", "unit": "m²", "quantity": 200.0},
        {"item_number": "b.", "description": "Hidroizolacijska membrana", "unit": "m²", "quantity": 200.0},
    ]
    historic = [
        {"description": "Parna brana", "unit_of_measure": "m²", "quantity": 250.0, "unit_price": 12.50},
        {"description": "Hidroizolacijska membrana PVC", "unit_of_measure": "m²", "quantity": 250.0, "unit_price": 35.00},
    ]
    result = diff_historic(current, historic)
    assert len(result["matched_pairs"]) == 2
    assert len(result["unmatched_current"]) == 0
    assert len(result["unmatched_historic"]) == 0


def test_diff_historic_missing_and_extra():
    current = [
        {"item_number": "a.", "description": "Parna brana", "unit": "m²", "quantity": 200.0},
        {"item_number": "b.", "description": "Vertikalna izolacija", "unit": "m", "quantity": 50.0},
    ]
    historic = [
        {"description": "Parna brana", "unit_of_measure": "m²", "quantity": 250.0, "unit_price": 12.50},
        {"description": "Toplinska izolacija XPS", "unit_of_measure": "m²", "quantity": 250.0, "unit_price": 28.00},
    ]
    result = diff_historic(current, historic)
    assert len(result["matched_pairs"]) == 1  # parna brana matches
    assert len(result["unmatched_current"]) == 1  # vertikalna izolacija
    assert len(result["unmatched_historic"]) == 1  # toplinska izolacija


def test_diff_historic_price_delta():
    current = [
        {"item_number": "a.", "description": "Beton C40/50", "unit": "m³", "quantity": 100.0},
    ]
    historic = [
        {"description": "Beton C40/50", "unit_of_measure": "m³", "quantity": 120.0, "unit_price": 95.00},
    ]
    result = diff_historic(current, historic)
    pair = result["matched_pairs"][0]
    assert pair["historic_unit_price"] == 95.00
    assert pair["quantity_delta"] == -20.0  # current has 20 less


def test_diff_historic_empty_inputs():
    result = diff_historic([], [])
    assert result["matched_pairs"] == []
    assert result["unmatched_current"] == []
    assert result["unmatched_historic"] == []
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_tools_pricing.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement pricing tools**

Create `backend/src/agent/tools/pricing.py`:

```python
"""Pricing tools: diff_historic.

Deterministic tool called by the Pricer agent.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any


def _similarity(a: str, b: str) -> float:
    """Simple string similarity using SequenceMatcher."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def diff_historic(
    current_lines: list[dict[str, Any]],
    historic_lines: list[dict[str, Any]],
    threshold: float = 0.4,
) -> dict[str, Any]:
    """Align current sub-items with historic by description similarity + unit match.

    Args:
        current_lines: List of dicts with description, unit, quantity.
        historic_lines: List of dicts with description, unit_of_measure, quantity, unit_price.
        threshold: Minimum similarity score to consider a match.

    Returns:
        Dict with matched_pairs, unmatched_current, unmatched_historic.
    """
    used_historic = set()
    matched_pairs = []

    for curr in current_lines:
        curr_desc = curr.get("description", "")
        curr_unit = curr.get("unit", "")
        best_match = None
        best_score = threshold

        for i, hist in enumerate(historic_lines):
            if i in used_historic:
                continue
            hist_desc = hist.get("description", "")
            hist_unit = hist.get("unit_of_measure", "")

            # Description similarity
            score = _similarity(curr_desc, hist_desc)
            # Boost if units match
            if curr_unit and hist_unit and curr_unit == hist_unit:
                score += 0.2

            if score > best_score:
                best_score = score
                best_match = i

        if best_match is not None:
            used_historic.add(best_match)
            hist = historic_lines[best_match]
            matched_pairs.append({
                "current_item_number": curr.get("item_number", ""),
                "current_description": curr_desc,
                "historic_description": hist.get("description", ""),
                "current_unit": curr_unit,
                "historic_unit": hist.get("unit_of_measure", ""),
                "current_quantity": curr.get("quantity", 0.0),
                "historic_quantity": hist.get("quantity", 0.0),
                "quantity_delta": curr.get("quantity", 0.0) - hist.get("quantity", 0.0),
                "historic_unit_price": hist.get("unit_price"),
                "similarity_score": round(best_score, 3),
            })

    unmatched_current = [
        curr for j, curr in enumerate(current_lines)
        if not any(p["current_item_number"] == curr.get("item_number", "") for p in matched_pairs)
    ]
    unmatched_historic = [
        hist for k, hist in enumerate(historic_lines) if k not in used_historic
    ]

    return {
        "matched_pairs": matched_pairs,
        "unmatched_current": unmatched_current,
        "unmatched_historic": unmatched_historic,
    }
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_tools_pricing.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add backend/src/agent/tools/pricing.py backend/tests/test_tools_pricing.py
git commit -m "feat: add pricing tools (diff_historic)"
```

---

## Task 7: External Tools

**Files:**
- Create: `backend/src/agent/tools/external.py`
- Create: `backend/tests/test_tools_external.py`

**Step 1: Write the failing test**

Create `backend/tests/test_tools_external.py`:

```python
"""Tests for external tools (search_web, summarize).

These tests use mocks since they depend on external services and the LLM.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.agent.tools.external import search_web, summarize


@pytest.mark.asyncio
async def test_search_web_returns_snippets():
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: {
        "results": [
            {"title": "Cijene betona 2026", "snippet": "Prosječna cijena betona C40/50 je 95 EUR/m³", "url": "https://example.com"}
        ]
    }
    mock_response.raise_for_status = lambda: None

    with patch("src.agent.tools.external.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        results = await search_web("cijena betona C40/50 2026")
        assert isinstance(results, list)


@pytest.mark.asyncio
async def test_summarize_calls_llm():
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content="Sažetak teksta."))]

    with patch("src.agent.tools.external.openai.AsyncOpenAI") as mock_oai_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_oai_cls.return_value = mock_client

        result = await summarize("Dugačak tekst o cijenama građevinskog materijala...")
        assert isinstance(result, str)
        assert len(result) > 0
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_tools_external.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement external tools**

Create `backend/src/agent/tools/external.py`:

```python
"""External tools: search_web and summarize.

Non-deterministic tools called by the Pricer agent.
search_web performs HTTP requests; summarize calls the local LLM.
"""

from __future__ import annotations

import httpx
import openai

from ...config import LLM_BASE_URL, LLM_MODEL_NAME


async def search_web(query: str, max_results: int = 3) -> list[dict[str, str]]:
    """Search the web for current material prices or construction info.

    Uses a simple HTTP search. Returns a list of result snippets.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.

    Returns:
        List of dicts with title, snippet, url keys.
    """
    # Simple DuckDuckGo instant answer API (no API key needed)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        # Abstract text
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", query),
                "snippet": data["AbstractText"],
                "url": data.get("AbstractURL", ""),
            })
        # Related topics
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append({
                    "title": topic.get("Text", "")[:80],
                    "snippet": topic.get("Text", ""),
                    "url": topic.get("FirstURL", ""),
                })

        return results[:max_results]
    except Exception:
        return []


async def summarize(text: str, max_tokens: int = 200) -> str:
    """Summarize text using the local LLM.

    Args:
        text: Text to summarize.
        max_tokens: Maximum tokens in summary.

    Returns:
        Summarized text string.
    """
    client = openai.AsyncOpenAI(base_url=LLM_BASE_URL, api_key="not-needed")
    try:
        response = await client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": "Sažmi sljedeći tekst u 2-3 rečenice. Zadrži ključne brojke i cijene."},
                {"role": "user", "content": text},
            ],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        return f"Greška pri sažimanju: {e}"
```

**Note:** The import path uses relative import `from ...config`. This works because `tools/` is inside `agent/` which is inside `src/`. Verify this matches the actual package structure. If it fails, switch to `from src.config import ...`.

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_tools_external.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add backend/src/agent/tools/external.py backend/tests/test_tools_external.py
git commit -m "feat: add external tools (search_web, summarize)"
```

---

## Task 8: Classifier Agent

**Files:**
- Create: `backend/src/agent/classifier_agent.py`
- Create: `backend/tests/test_classifier_agent.py`

**Step 1: Write the failing test**

Create `backend/tests/test_classifier_agent.py`:

```python
"""Tests for the Classifier agent.

Uses a mock model to avoid needing a running LLM server.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
import aiosqlite

from src.db.schema import SCHEMA_SQL
from src.agent.classifier_agent import create_classifier_agent, ClassifierDeps
from src.agent.schemas import ClassResult


@pytest_asyncio.fixture
async def db():
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.executescript(SCHEMA_SQL)
    await conn.execute(
        "INSERT INTO standard_units (id, label, description, category, expected_sub_items, expected_units) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            "hidroizolacija-ravnog-krova",
            "Hidroizolacija ravnog krova",
            "Izvedba hidroizolacije ravnog krova s bitumenskim trakama",
            "Krovopokrivački radovi",
            json.dumps(["parna brana", "toplinska izolacija", "hidroizolacijska membrana"]),
            json.dumps(["m²", "m"]),
        ),
    )
    await conn.commit()
    yield conn
    await conn.close()


def test_classifier_agent_has_tools():
    agent = create_classifier_agent()
    tool_names = [t.name for t in agent._function_tools.values()]
    assert "match_taxonomy" in tool_names
    assert "check_schema" in tool_names


def test_classifier_deps_holds_db(db):
    deps = ClassifierDeps(db=db)
    assert deps.db is db
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_classifier_agent.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement classifier agent**

Create `backend/src/agent/classifier_agent.py`:

```python
"""Agent 1: Classifier — maps raw Excel rows to standard taxonomy types."""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from ..config import LLM_BASE_URL, LLM_MODEL_NAME
from .schemas import ClassResult
from .tools.taxonomy import match_taxonomy as _match_taxonomy
from .tools.taxonomy import check_schema as _check_schema


@dataclass
class ClassifierDeps:
    db: aiosqlite.Connection


def create_classifier_agent() -> Agent[ClassifierDeps, ClassResult]:
    """Create and configure the Classifier agent."""
    provider = OpenAIProvider(base_url=LLM_BASE_URL)
    model = OpenAIChatModel(model_name=LLM_MODEL_NAME, provider=provider)

    agent = Agent(
        model,
        output_type=ClassResult,
        deps_type=ClassifierDeps,
        system_prompt=(
            "Ti si klasifikator građevinskih stavki iz Excel troškovnika.\n"
            "Dobivat ćeš opis stavke s redovima iz troškovnika.\n"
            "Koristi alat match_taxonomy da pronađeš odgovarajući standardni tip.\n"
            "Zatim koristi check_schema da provjeriš podudaraju li se podstavke.\n"
            "Vrati taxonomy_id, confidence (0-1), i popis odstupanja.\n"
            "Ako nijedan tip ne odgovara, postavi confidence na 0 i taxonomy_id na 'nepoznato'."
        ),
        retries=2,
    )

    @agent.tool
    async def match_taxonomy(ctx: RunContext[ClassifierDeps], description: str) -> str:
        """Search standard unit taxonomy by description. Returns top-3 matches as JSON."""
        results = await _match_taxonomy(ctx.deps.db, description)
        return str(results)

    @agent.tool
    async def check_schema(ctx: RunContext[ClassifierDeps], taxonomy_id: str, rows_json: str) -> str:
        """Check extracted rows against a standard unit's expected sub-items.

        Args:
            taxonomy_id: The standard unit type ID to check against.
            rows_json: JSON string of list of dicts with 'description' and 'unit' keys.
        """
        import json
        try:
            rows = json.loads(rows_json)
        except json.JSONDecodeError:
            return '{"error": "invalid JSON"}'
        result = await _check_schema(ctx.deps.db, taxonomy_id, rows)
        return str(result)

    return agent
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_classifier_agent.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add backend/src/agent/classifier_agent.py backend/tests/test_classifier_agent.py
git commit -m "feat: add Classifier agent with taxonomy tools"
```

---

## Task 9: Comparator Agent

**Files:**
- Create: `backend/src/agent/comparator_agent.py`
- Create: `backend/tests/test_comparator_agent.py`

**Step 1: Write the failing test**

Create `backend/tests/test_comparator_agent.py`:

```python
"""Tests for the Comparator agent."""

import pytest
import pytest_asyncio
import aiosqlite

from src.db.schema import SCHEMA_SQL
from src.agent.comparator_agent import create_comparator_agent, ComparatorDeps
from src.agent.schemas import ClassResult


@pytest_asyncio.fixture
async def db():
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.executescript(SCHEMA_SQL)
    yield conn
    await conn.close()


def test_comparator_agent_has_tools():
    agent = create_comparator_agent()
    tool_names = [t.name for t in agent._function_tools.values()]
    assert "search_historic" in tool_names
    assert "fetch_similar" in tool_names


def test_comparator_deps_holds_classification(db):
    classification = ClassResult(
        taxonomy_id="test", taxonomy_label="Test", confidence=0.9
    )
    deps = ComparatorDeps(db=db, classification=classification)
    assert deps.classification.taxonomy_id == "test"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_comparator_agent.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement comparator agent**

Create `backend/src/agent/comparator_agent.py`:

```python
"""Agent 2: Comparator — finds and compares historic units for a classified type."""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from ..config import LLM_BASE_URL, LLM_MODEL_NAME
from .schemas import ClassResult, CompResult
from .tools.historic import search_historic_by_taxonomy as _search
from .tools.historic import fetch_similar as _fetch


@dataclass
class ComparatorDeps:
    db: aiosqlite.Connection
    classification: ClassResult


def create_comparator_agent() -> Agent[ComparatorDeps, CompResult]:
    """Create and configure the Comparator agent."""
    provider = OpenAIProvider(base_url=LLM_BASE_URL)
    model = OpenAIChatModel(model_name=LLM_MODEL_NAME, provider=provider)

    agent = Agent(
        model,
        output_type=CompResult,
        deps_type=ComparatorDeps,
        system_prompt=(
            "Ti si uspoređivač građevinskih stavki.\n"
            "Dobivaš klasificiranu stavku s taxonomy_id.\n"
            "Koristi search_historic da pronađeš historijske stavke istog tipa.\n"
            "Ako trebaš više detalja o nekoj stavci, koristi fetch_similar.\n"
            "Vrati popis usporedbi sa sličnostima i razlikama.\n"
            "Uključi classification objekt iz ulaza u svoj odgovor."
        ),
        retries=2,
    )

    @agent.tool
    async def search_historic(
        ctx: RunContext[ComparatorDeps], keywords: str = ""
    ) -> str:
        """Search historic units matching the classified taxonomy type.

        Args:
            keywords: Optional additional search terms to narrow results.
        """
        taxonomy_id = ctx.deps.classification.taxonomy_id
        results = await _search(ctx.deps.db, taxonomy_id, keywords=keywords)
        return str(results)

    @agent.tool
    async def fetch_similar(ctx: RunContext[ComparatorDeps], unit_id: int) -> str:
        """Fetch full details for a specific historic unit by ID."""
        result = await _fetch(ctx.deps.db, unit_id)
        return str(result) if result else '{"error": "not found"}'

    return agent
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_comparator_agent.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add backend/src/agent/comparator_agent.py backend/tests/test_comparator_agent.py
git commit -m "feat: add Comparator agent with historic tools"
```

---

## Task 10: Pricer Agent

**Files:**
- Create: `backend/src/agent/pricer_agent.py`
- Create: `backend/tests/test_pricer_agent.py`

**Step 1: Write the failing test**

Create `backend/tests/test_pricer_agent.py`:

```python
"""Tests for the Pricer agent."""

from src.agent.pricer_agent import create_pricer_agent, PricerDeps
from src.agent.schemas import ClassResult, CompResult


def test_pricer_agent_has_tools():
    agent = create_pricer_agent()
    tool_names = [t.name for t in agent._function_tools.values()]
    assert "diff_historic" in tool_names
    assert "search_web" in tool_names
    assert "summarize" in tool_names


def test_pricer_deps_holds_comparison():
    classification = ClassResult(
        taxonomy_id="test", taxonomy_label="Test", confidence=0.9
    )
    comparison = CompResult(
        classification=classification,
        matches=[],
        summary="No matches",
    )
    deps = PricerDeps(comparison=comparison)
    assert deps.comparison.summary == "No matches"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_pricer_agent.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement pricer agent**

Create `backend/src/agent/pricer_agent.py`:

```python
"""Agent 3: Pricer — reasons about pricing using diffs, web search, and summarization."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from ..config import LLM_BASE_URL, LLM_MODEL_NAME
from .schemas import CompResult, PriceResult
from .tools.pricing import diff_historic as _diff
from .tools.external import search_web as _search_web
from .tools.external import summarize as _summarize


@dataclass
class PricerDeps:
    comparison: CompResult


def create_pricer_agent() -> Agent[PricerDeps, PriceResult]:
    """Create and configure the Pricer agent."""
    provider = OpenAIProvider(base_url=LLM_BASE_URL)
    model = OpenAIChatModel(model_name=LLM_MODEL_NAME, provider=provider)

    agent = Agent(
        model,
        output_type=PriceResult,
        deps_type=PricerDeps,
        system_prompt=(
            "Ti si stručnjak za određivanje cijena građevinskih radova.\n"
            "Dobivaš klasificiranu stavku i historijske usporedbe.\n"
            "Koristi diff_historic da usporediš trenutne podstavke s historijskima.\n"
            "Ako nešto izgleda neobično, koristi search_web za provjeru tržišnih cijena.\n"
            "Koristi summarize za sažimanje dugačkih tekstova.\n"
            "Predloži realnu cijenu za svaku podstavku s obrazloženjem.\n"
            "Uključi price_range (low, high, median) iz historijskih podataka."
        ),
        retries=2,
    )

    @agent.tool
    async def diff_historic(
        ctx: RunContext[PricerDeps],
        current_lines_json: str,
        historic_lines_json: str,
    ) -> str:
        """Compare current sub-items with historic ones.

        Args:
            current_lines_json: JSON list of current items (description, unit, quantity).
            historic_lines_json: JSON list of historic items (description, unit_of_measure, quantity, unit_price).
        """
        import json
        try:
            current = json.loads(current_lines_json)
            historic = json.loads(historic_lines_json)
        except json.JSONDecodeError:
            return '{"error": "invalid JSON"}'
        result = _diff(current, historic)
        return str(result)

    @agent.tool
    async def search_web(ctx: RunContext[PricerDeps], query: str) -> str:
        """Search the web for current material prices or construction cost data."""
        results = await _search_web(query)
        return str(results)

    @agent.tool
    async def summarize(ctx: RunContext[PricerDeps], text: str) -> str:
        """Summarize a long text into 2-3 key sentences."""
        return await _summarize(text)

    return agent
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_pricer_agent.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add backend/src/agent/pricer_agent.py backend/tests/test_pricer_agent.py
git commit -m "feat: add Pricer agent with diff, web search, and summarize tools"
```

---

## Task 11: Pipeline Orchestrator

**Files:**
- Create: `backend/src/agent/pipeline.py`
- Create: `backend/tests/test_pipeline.py`

**Step 1: Write the failing test**

Create `backend/tests/test_pipeline.py`:

```python
"""Tests for the pipeline orchestrator.

Tests the event sequence without a running LLM by mocking agent.run().
"""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.agent.pipeline import run_pipeline
from src.agent.schemas import (
    ClassResult,
    CompResult,
    HistoricComparison,
    HistoricPriceLine,
    LinePriceSuggestion,
    PriceRange,
    PriceResult,
)
from src.models.boq import LogicalUnit, PricedLine


@pytest.fixture
def sample_unit():
    return LogicalUnit(
        item_number="3.1.1.",
        title="Hidroizolacija ravnog krova",
        description="Izvedba hidroizolacije",
        priced_lines=[
            PricedLine(item_number="3.1.1.a.", description="Parna brana", unit="m²", quantity=200.0),
        ],
    )


@pytest.mark.asyncio
async def test_pipeline_yields_correct_event_sequence(sample_unit):
    mock_class_result = ClassResult(
        taxonomy_id="hidro", taxonomy_label="Hidro", confidence=0.9
    )
    mock_comp_result = CompResult(
        classification=mock_class_result,
        matches=[
            HistoricComparison(
                historic_unit_id=1,
                project_name="Test Project",
                similarity_score=0.8,
                price_lines=[HistoricPriceLine(description="Parna brana", unit_of_measure="m²", quantity=250, unit_price=12.5)],
            )
        ],
        summary="Found 1 match",
    )
    mock_price_result = PriceResult(
        line_prices=[
            LinePriceSuggestion(
                item_number="3.1.1.a.",
                suggested_price=12.5,
                confidence=0.8,
                price_range=PriceRange(low=10.0, high=15.0, median=12.5),
                reasoning="Based on 1 match",
            )
        ],
        overall_reasoning="Price OK",
    )

    # Mock all three agents
    with patch("src.agent.pipeline.create_classifier_agent") as mock_cls, \
         patch("src.agent.pipeline.create_comparator_agent") as mock_cmp, \
         patch("src.agent.pipeline.create_pricer_agent") as mock_prc, \
         patch("src.agent.pipeline.get_db") as mock_get_db:

        mock_get_db.return_value = AsyncMock()

        for mock_factory, mock_result in [
            (mock_cls, mock_class_result),
            (mock_cmp, mock_comp_result),
            (mock_prc, mock_price_result),
        ]:
            mock_agent = MagicMock()
            mock_run_result = MagicMock()
            mock_run_result.output = mock_result
            mock_agent.run = AsyncMock(return_value=mock_run_result)
            mock_factory.return_value = mock_agent

        events = []
        async for event_type, data in run_pipeline(sample_unit):
            events.append(event_type)

        assert "classification_start" in events
        assert "classification" in events
        assert "comparison_start" in events
        assert "historic_match" in events
        assert "pricing_start" in events
        assert "suggestion" in events
        assert "complete" in events
        # Correct order
        assert events.index("classification_start") < events.index("classification")
        assert events.index("classification") < events.index("comparison_start")
        assert events.index("comparison_start") < events.index("suggestion")
        assert events.index("suggestion") < events.index("complete")
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement pipeline orchestrator**

Create `backend/src/agent/pipeline.py`:

```python
"""Pipeline orchestrator: runs Classifier → Comparator → Pricer sequentially."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

from ..db.database import get_db
from ..models.boq import LogicalUnit
from .classifier_agent import ClassifierDeps, create_classifier_agent
from .comparator_agent import ComparatorDeps, create_comparator_agent
from .pricer_agent import PricerDeps, create_pricer_agent


def _format_unit_for_classifier(unit: LogicalUnit) -> str:
    """Format a logical unit's data as text for the Classifier agent."""
    lines = [f"Stavka: {unit.item_number} — {unit.title}"]
    if unit.description:
        lines.append(f"Opis: {unit.description}")
    if unit.priced_lines:
        lines.append("Podstavke:")
        for pl in unit.priced_lines:
            lines.append(f"  {pl.item_number}: {pl.description} [{pl.unit}] količina={pl.quantity}")
    return "\n".join(lines)


def _format_for_comparator(classification_json: str) -> str:
    """Format classification result as text for the Comparator agent."""
    return f"Klasificirana stavka:\n{classification_json}\n\nPronađi historijske stavke istog tipa i usporedi ih."


def _format_for_pricer(unit: LogicalUnit, comparison_json: str) -> str:
    """Format comparison result + current unit for the Pricer agent."""
    lines = [f"Trenutna stavka: {unit.item_number} — {unit.title}"]
    lines.append("Trenutne podstavke (JSON):")
    current_lines = [
        {"item_number": pl.item_number, "description": pl.description, "unit": pl.unit, "quantity": pl.quantity}
        for pl in unit.priced_lines
    ]
    lines.append(json.dumps(current_lines, ensure_ascii=False))
    lines.append(f"\nHistorijske usporedbe:\n{comparison_json}")
    lines.append("\nPredloži cijenu za svaku podstavku.")
    return "\n".join(lines)


async def run_pipeline(unit: LogicalUnit) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """Run the 3-stage agent pipeline for a logical unit.

    Yields (event_type, data) tuples for SSE streaming.
    """
    db = await get_db()

    # --- Stage 1: Classifier ---
    yield ("classification_start", {"unit_id": unit.id})

    classifier = create_classifier_agent()
    class_result = await classifier.run(
        _format_unit_for_classifier(unit),
        deps=ClassifierDeps(db=db),
    )
    classification = class_result.output

    yield ("classification", classification.model_dump())

    # --- Stage 2: Comparator ---
    yield ("comparison_start", {"taxonomy_id": classification.taxonomy_id})

    comparator = create_comparator_agent()
    classification_json = classification.model_dump_json()
    comp_result = await comparator.run(
        _format_for_comparator(classification_json),
        deps=ComparatorDeps(db=db, classification=classification),
    )
    comparison = comp_result.output

    for match in comparison.matches:
        yield ("historic_match", match.model_dump())

    # --- Stage 3: Pricer ---
    yield ("pricing_start", {"unit_id": unit.id})

    pricer = create_pricer_agent()
    comparison_json = comparison.model_dump_json()
    price_result = await pricer.run(
        _format_for_pricer(unit, comparison_json),
        deps=PricerDeps(comparison=comparison),
    )

    for suggestion in price_result.output.line_prices:
        yield ("suggestion", suggestion.model_dump())

    yield ("complete", {})
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_pipeline.py -v`
Expected: 1 passed

**Step 5: Commit**

```bash
git add backend/src/agent/pipeline.py backend/tests/test_pipeline.py
git commit -m "feat: add pipeline orchestrator (Classifier → Comparator → Pricer)"
```

---

## Task 12: API Integration

**Files:**
- Modify: `backend/src/api/agent.py`
- Create: `backend/src/api/taxonomy.py`
- Modify: `backend/src/api/router.py`
- Delete: `backend/src/agent/price_agent.py`

**Step 1: Update agent endpoint to use pipeline**

Replace `backend/src/api/agent.py` entirely:

```python
"""SSE endpoint for agent price suggestions."""

import json

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from ..models.agent import SuggestRequest
from ..agent.pipeline import run_pipeline
from .upload import get_current_boq

router = APIRouter()


@router.post("/agent/suggest")
async def suggest_prices(body: SuggestRequest):
    boq = get_current_boq()
    if not boq:
        raise HTTPException(404, "No BoQ uploaded yet")

    unit = None
    for u in boq.units:
        if u.id == body.unit_id:
            unit = u
            break
    if not unit:
        raise HTTPException(404, f"Unit {body.unit_id} not found")

    async def event_stream():
        async for event_type, data in run_pipeline(unit):
            yield {"event": event_type, "data": json.dumps(data, ensure_ascii=False)}

    return EventSourceResponse(event_stream())
```

**Step 2: Create taxonomy API**

Create `backend/src/api/taxonomy.py`:

```python
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
```

**Step 3: Update router**

In `backend/src/api/router.py`, add the taxonomy router:

```python
from fastapi import APIRouter

from .upload import router as upload_router
from .units import router as units_router
from .historic import router as historic_router
from .agent import router as agent_router
from .output import router as output_router
from .export import router as export_router
from .taxonomy import router as taxonomy_router

router = APIRouter()
router.include_router(upload_router, tags=["upload"])
router.include_router(units_router, tags=["units"])
router.include_router(historic_router, tags=["historic"])
router.include_router(agent_router, tags=["agent"])
router.include_router(output_router, tags=["output"])
router.include_router(export_router, tags=["export"])
router.include_router(taxonomy_router, tags=["taxonomy"])
```

**Step 4: Delete old price_agent**

Run: `rm backend/src/agent/price_agent.py`

**Step 5: Verify app starts**

Run: `cd backend && uv run python -c "from src.main import app; print('OK')"`
Expected: `OK`

**Step 6: Commit**

```bash
git add backend/src/api/agent.py backend/src/api/taxonomy.py backend/src/api/router.py
git rm backend/src/agent/price_agent.py
git commit -m "feat: wire pipeline into API, add taxonomy endpoints, remove old price_agent"
```

---

## Task 13: Historic Import with Classification

**Files:**
- Modify: `backend/src/db/historic_repo.py`
- Modify: `backend/src/api/historic.py`

**Step 1: Add search_by_taxonomy to historic_repo**

Add this function to the end of `backend/src/db/historic_repo.py`:

```python
async def update_unit_taxonomy(unit_id: int, taxonomy_id: str) -> None:
    """Set the taxonomy_id for a historic unit."""
    db = await get_db()
    await db.execute(
        "UPDATE historic_units SET taxonomy_id = ? WHERE id = ?",
        (taxonomy_id, unit_id),
    )
    await db.commit()
```

**Step 2: Update historic import endpoint**

In `backend/src/api/historic.py`, update the import endpoint to optionally classify units during import. Add after the existing import:

```python
from fastapi import APIRouter, UploadFile, File, Query

from ..models.historic import HistoricMatch
from ..db.historic_repo import search_historic, import_boq_to_historic
from ..parser.excel_parser import parse_excel

router = APIRouter()


@router.get("/historic/search", response_model=list[HistoricMatch])
async def search_historic_units(q: str = Query(..., min_length=2), limit: int = 10):
    return await search_historic(q, limit)


@router.post("/historic/import")
async def import_historic(file: UploadFile = File(...)):
    content = await file.read()
    boq = parse_excel(content, file.filename or "unknown.xlsx")
    count = await import_boq_to_historic(boq, file.filename or "unknown.xlsx")
    return {"imported_count": count, "unit_count": len(boq.units)}
```

**Note:** Classification during import is a separate async operation that will be triggered by the user via the UI (selecting a unit → running the classifier). This keeps the import fast and lets the user review classifications. A batch classification endpoint can be added later.

**Step 3: Commit**

```bash
git add backend/src/db/historic_repo.py backend/src/api/historic.py
git commit -m "feat: add update_unit_taxonomy for historic import classification"
```

---

## Task 14: Run All Tests

**Step 1: Run full test suite**

Run: `cd backend && uv run pytest tests/ -v`
Expected: All tests pass (approximately 22 tests)

**Step 2: Fix any failures**

If any test fails, fix the issue and re-run.

**Step 3: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: address test failures from integration"
```

---

## Task 15: Smoke Test with Live LLM

**Prerequisites:** llama-server running at `http://localhost:8080/v1`

**Step 1: Start the backend**

Run: `cd backend && uv run uvicorn src.main:app --host 127.0.0.1 --port 8081 --reload`
Expected: Server starts on port 8081

**Step 2: Seed a taxonomy entry**

Run:
```bash
curl -X POST http://localhost:8081/api/taxonomy/seed \
  -H "Content-Type: application/json" \
  -d '{
    "units": [
      {
        "id": "hidroizolacija-ravnog-krova",
        "label": "Hidroizolacija ravnog krova",
        "description": "Izvedba hidroizolacije ravnog krova s bitumenskim trakama uključujući parnu branu i toplinsku izolaciju",
        "category": "Krovopokrivački radovi",
        "expected_sub_items": ["parna brana", "toplinska izolacija", "hidroizolacijska membrana"],
        "expected_units": ["m²", "m"]
      }
    ]
  }'
```
Expected: `{"seeded_count": 1}`

**Step 3: Upload an Excel file and trigger the pipeline**

Use the frontend or curl to upload one of the test Excel files and call the suggest endpoint. Verify that SSE events stream back with classification, historic matches, and price suggestions.

**Step 4: Commit smoke test results**

No code changes — just verify the pipeline works end-to-end.
