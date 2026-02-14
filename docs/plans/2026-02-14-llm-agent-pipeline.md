# LLM Agent Pipeline + Streamlit UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace deterministic price averaging with a 3-stage PydanticAI agent pipeline (Classifier → Comparator → Pricer) and build a futuristic Streamlit UI with glassmorphism theming and full LLM observability.

**Architecture:** Three PydanticAI agents chained sequentially, each with 2-3 focused tools. Pipeline orchestrator yields SSE events with timestamps, agent badges, and confidence breakdowns. Streamlit frontend consumes events via `st.empty()` live updates. Backend stubs start with mock data, hot-swap to real FastAPI.

**Tech Stack:** PydanticAI, FastAPI, aiosqlite, SQLite FTS5, sse-starlette, httpx, Streamlit, pytest

**Working directory:** `/media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/.worktrees/boq-editor`

**Run commands from:** `backend/` for backend tasks, project root for Streamlit tasks

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
    ConfidenceBreakdown,
    Deviation,
    HistoricComparison,
    HistoricPriceLine,
    LinePriceSuggestion,
    PriceRange,
    PriceResult,
    ReasoningEntry,
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


def test_confidence_breakdown():
    breakdown = ConfidenceBreakdown(
        text_similarity=0.85,
        unit_match=1.0,
        hierarchy_match=0.7,
        description_overlap=0.6,
    )
    assert breakdown.overall == 0.7875  # weighted average
    assert breakdown.text_similarity == 0.85


def test_historic_comparison_with_breakdown():
    comp = HistoricComparison(
        historic_unit_id=42,
        project_name="Kaufland Osijek",
        source_filename="KAUFLAND OSIJEK - ugovorni troškovnik.xlsx",
        project_year=2025,
        confidence=ConfidenceBreakdown(
            text_similarity=0.88,
            unit_match=1.0,
            hierarchy_match=0.7,
            description_overlap=0.65,
        ),
        matching_sub_items=["beton C40/50"],
        missing_sub_items=[],
        extra_sub_items=["armatura"],
        qty_delta_pct=-8.0,
        price_lines=[
            HistoricPriceLine(
                description="Beton",
                unit_of_measure="m³",
                quantity=120.0,
                unit_price=95.0,
            )
        ],
    )
    assert comp.project_year == 2025
    assert comp.qty_delta_pct == -8.0
    assert comp.confidence.overall > 0.7


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
                source_filename="k.xlsx",
                project_year=2025,
                confidence=ConfidenceBreakdown(
                    text_similarity=0.88,
                    unit_match=1.0,
                    hierarchy_match=0.7,
                    description_overlap=0.65,
                ),
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


def test_reasoning_entry():
    entry = ReasoningEntry(
        agent="classifier",
        message="Pronađen tip: Hidroizolacija ravnog krova (confidence: 0.85)",
    )
    assert entry.agent == "classifier"
    assert entry.timestamp  # auto-generated
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.agent.schemas'`

**Step 3: Implement schemas**

Create `backend/src/agent/schemas.py`:

```python
"""Pydantic schemas for the 3-stage agent pipeline.

These schemas are shared between:
- Backend pipeline (agent outputs)
- SSE events (serialized to JSON)
- Streamlit frontend (UI models consume these directly)
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field, computed_field


# --- Shared: Confidence Breakdown (used by Comparator + UI confidence bars) ---

class ConfidenceBreakdown(BaseModel):
    """Per-factor confidence scores for the UI confidence panel."""
    text_similarity: float = Field(ge=0, le=1)
    unit_match: float = Field(ge=0, le=1)
    hierarchy_match: float = Field(ge=0, le=1)
    description_overlap: float = Field(ge=0, le=1)

    @computed_field
    @property
    def overall(self) -> float:
        """Weighted average: text 40%, unit 25%, hierarchy 20%, description 15%."""
        return round(
            self.text_similarity * 0.4
            + self.unit_match * 0.25
            + self.hierarchy_match * 0.2
            + self.description_overlap * 0.15,
            4,
        )


# --- Shared: Reasoning log entry (consumed by reasoning panel) ---

class ReasoningEntry(BaseModel):
    """Single entry in the LLM reasoning log."""
    agent: str  # "classifier", "comparator", "pricer"
    message: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


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
    source_filename: str = ""
    project_year: int = 0
    confidence: ConfidenceBreakdown
    matching_sub_items: list[str] = []
    missing_sub_items: list[str] = []
    extra_sub_items: list[str] = []
    qty_delta_pct: float = 0.0  # percentage difference in total quantity
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


# --- Pipeline stats (consumed by stats footer) ---

class PipelineStats(BaseModel):
    """Aggregate stats emitted at pipeline completion."""
    avg_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0
    match_count: int = 0
    total_suggestions: int = 0
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_schemas.py -v`
Expected: 7 passed

**Step 5: Commit**

```bash
git add backend/src/agent/schemas.py backend/tests/test_schemas.py
git commit -m "feat: add pipeline schemas with ConfidenceBreakdown and ReasoningEntry"
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
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_db_schema.py -v`
Expected: FAIL — `standard_units` table doesn't exist

**Step 3: Update schema**

Replace `backend/src/db/schema.py` entirely:

```python
"""SQLite schema for historic BoQ storage."""

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

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_db_schema.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add backend/src/db/schema.py backend/tests/test_db_schema.py
git commit -m "feat: add standard_units table and taxonomy_id to historic_units"
```

---

## Tasks 4-10: Backend Tools & Agents

Tasks 4-10 are unchanged from the original plan. See original plan sections for:

- **Task 4**: Taxonomy Tools (`match_taxonomy`, `check_schema`)
- **Task 5**: Historic Tools (`search_historic_by_taxonomy`, `fetch_similar`)
- **Task 6**: Pricing Tools (`diff_historic`)
- **Task 7**: External Tools (`search_web`, `summarize`)
- **Task 8**: Classifier Agent
- **Task 9**: Comparator Agent
- **Task 10**: Pricer Agent

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

from src.agent.pipeline import run_pipeline, PIPELINE_STAGES
from src.agent.schemas import (
    ClassResult,
    CompResult,
    ConfidenceBreakdown,
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


def test_pipeline_stages_defined():
    assert len(PIPELINE_STAGES) == 6
    assert PIPELINE_STAGES[0] == "upload"
    assert PIPELINE_STAGES[-1] == "review"


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
                source_filename="test.xlsx",
                project_year=2025,
                confidence=ConfidenceBreakdown(
                    text_similarity=0.88,
                    unit_match=1.0,
                    hierarchy_match=0.7,
                    description_overlap=0.65,
                ),
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
            events.append((event_type, data))

        event_types = [e[0] for e in events]

        # Pipeline stage events
        assert "pipeline_stage" in event_types
        # Agent events
        assert "reasoning" in event_types
        assert "classification" in event_types
        assert "historic_match" in event_types
        assert "confidence_breakdown" in event_types
        assert "suggestion" in event_types
        assert "stats" in event_types
        assert "complete" in event_types

        # Correct order
        assert event_types.index("classification") < event_types.index("historic_match")
        assert event_types.index("historic_match") < event_types.index("suggestion")
        assert event_types.index("suggestion") < event_types.index("complete")

        # Reasoning entries have agent badge
        reasoning_events = [e for e in events if e[0] == "reasoning"]
        agents_seen = {e[1]["agent"] for e in reasoning_events}
        assert "classifier" in agents_seen
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement pipeline orchestrator**

Create `backend/src/agent/pipeline.py`:

```python
"""Pipeline orchestrator: runs Classifier → Comparator → Pricer sequentially.

Emits rich SSE events for the Streamlit UI:
- pipeline_stage: current stage for pipeline bar
- reasoning: log entries with agent badge + timestamp
- classification, historic_match, confidence_breakdown, suggestion: data events
- stats: aggregate stats for footer
- complete: pipeline finished
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from ..db.database import get_db
from ..models.boq import LogicalUnit
from .classifier_agent import ClassifierDeps, create_classifier_agent
from .comparator_agent import ComparatorDeps, create_comparator_agent
from .pricer_agent import PricerDeps, create_pricer_agent
from .schemas import PipelineStats, ReasoningEntry

# Pipeline bar stages (matches Streamlit header component)
PIPELINE_STAGES = ["upload", "parse", "index", "match", "suggest", "review"]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reasoning(agent: str, message: str) -> tuple[str, dict[str, Any]]:
    entry = ReasoningEntry(agent=agent, message=message)
    return ("reasoning", entry.model_dump())


def _stage(stage: str) -> tuple[str, dict[str, Any]]:
    return ("pipeline_stage", {"stage": stage, "timestamp": _ts()})


def _format_unit_for_classifier(unit: LogicalUnit) -> str:
    lines = [f"Stavka: {unit.item_number} — {unit.title}"]
    if unit.description:
        lines.append(f"Opis: {unit.description}")
    if unit.priced_lines:
        lines.append("Podstavke:")
        for pl in unit.priced_lines:
            lines.append(f"  {pl.item_number}: {pl.description} [{pl.unit}] količina={pl.quantity}")
    return "\n".join(lines)


def _format_for_comparator(classification_json: str) -> str:
    return f"Klasificirana stavka:\n{classification_json}\n\nPronađi historijske stavke istog tipa i usporedi ih."


def _format_for_pricer(unit: LogicalUnit, comparison_json: str) -> str:
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
    Events include timestamps and agent badges for the Streamlit reasoning panel.
    """
    db = await get_db()

    # --- Stage 1: Classifier (pipeline: index) ---
    yield _stage("index")
    yield _reasoning("classifier", f"Klasificiram stavku: {unit.title}")

    classifier = create_classifier_agent()
    class_result = await classifier.run(
        _format_unit_for_classifier(unit),
        deps=ClassifierDeps(db=db),
    )
    classification = class_result.output

    yield ("classification", classification.model_dump())
    yield _reasoning("classifier",
        f"Pronađen tip: {classification.taxonomy_label} (confidence: {classification.confidence})")

    if classification.deviations:
        devs = ", ".join(d.description for d in classification.deviations)
        yield _reasoning("classifier", f"Odstupanja od standarda: {devs}")

    # --- Stage 2: Comparator (pipeline: match) ---
    yield _stage("match")
    yield _reasoning("comparator", f"Tražim historijske stavke za tip: {classification.taxonomy_id}")

    comparator = create_comparator_agent()
    classification_json = classification.model_dump_json()
    comp_result = await comparator.run(
        _format_for_comparator(classification_json),
        deps=ComparatorDeps(db=db, classification=classification),
    )
    comparison = comp_result.output

    yield _reasoning("comparator",
        f"Pronađeno {len(comparison.matches)} historijskih podudaranja")

    for match in comparison.matches:
        yield ("historic_match", match.model_dump())
        yield ("confidence_breakdown", {
            "historic_unit_id": match.historic_unit_id,
            "project_name": match.project_name,
            "breakdown": match.confidence.model_dump(),
        })
        yield _reasoning("comparator",
            f"  {match.project_name} ({match.project_year}): "
            f"sličnost {match.confidence.overall:.0%}, "
            f"qty Δ {match.qty_delta_pct:+.1f}%")

    # --- Stage 3: Pricer (pipeline: suggest) ---
    yield _stage("suggest")
    yield _reasoning("pricer", "Analiziram cijene na temelju historijskih podataka")

    pricer = create_pricer_agent()
    comparison_json = comparison.model_dump_json()
    price_result = await pricer.run(
        _format_for_pricer(unit, comparison_json),
        deps=PricerDeps(comparison=comparison),
    )

    all_prices = []
    for suggestion in price_result.output.line_prices:
        yield ("suggestion", suggestion.model_dump())
        all_prices.append(suggestion.suggested_price)
        yield _reasoning("pricer",
            f"  {suggestion.item_number}: {suggestion.suggested_price:.2f} EUR "
            f"(confidence: {suggestion.confidence:.0%})")

    if price_result.output.overall_reasoning:
        yield _reasoning("pricer", price_result.output.overall_reasoning)

    # --- Stats for footer ---
    stats = PipelineStats(
        avg_price=sum(all_prices) / len(all_prices) if all_prices else 0,
        min_price=min(all_prices) if all_prices else 0,
        max_price=max(all_prices) if all_prices else 0,
        match_count=len(comparison.matches),
        total_suggestions=len(all_prices),
    )
    yield ("stats", stats.model_dump())

    # --- Complete (pipeline: review) ---
    yield _stage("review")
    yield ("complete", {})
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_pipeline.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add backend/src/agent/pipeline.py backend/tests/test_pipeline.py
git commit -m "feat: add pipeline orchestrator with rich SSE events for Streamlit UI"
```

---

## Task 12: API Integration

Unchanged from original plan. Swap `run_price_suggestion()` for `run_pipeline()` in `api/agent.py`, add `api/taxonomy.py`, update `api/router.py`, delete `price_agent.py`.

---

## Task 13: Historic Import with Classification

Unchanged from original plan. Add `update_unit_taxonomy()` to `historic_repo.py`.

---

## Task 14: Streamlit Skeleton & Theming

**Files:**
- Create: `boq_app/app.py`
- Create: `boq_app/themes.py`
- Create: `boq_app/styles.py`
- Create: `.streamlit/config.toml`

**Step 1: Create .streamlit config**

Create `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#4a9eff"
backgroundColor = "#0a0f1e"
secondaryBackgroundColor = "#141e3c"
textColor = "#e0e6f0"
font = "monospace"

[server]
headless = true
```

**Step 2: Create themes**

Create `boq_app/themes.py`:

```python
"""Theme system: CSS custom properties swapped by changing one dict."""

THEMES = {
    "minority_report": {
        "--bg-primary": "rgba(10, 15, 30, 0.95)",
        "--bg-panel": "rgba(20, 30, 60, 0.45)",
        "--bg-panel-hover": "rgba(30, 45, 80, 0.55)",
        "--border-panel": "rgba(100, 160, 255, 0.15)",
        "--border-glow": "rgba(74, 158, 255, 0.3)",
        "--accent-primary": "#4a9eff",
        "--accent-secondary": "#ff8c42",
        "--accent-success": "#22c55e",
        "--accent-warning": "#f59e0b",
        "--accent-danger": "#ef4444",
        "--text-primary": "#e0e6f0",
        "--text-secondary": "#8899b4",
        "--text-muted": "#4a5568",
        "--glass-blur": "20px",
        "--glass-border": "1px solid rgba(100, 160, 255, 0.15)",
        "--shadow-panel": "0 8px 32px rgba(0, 0, 0, 0.3)",
        "--shadow-glow": "0 0 20px rgba(74, 158, 255, 0.1)",
        "--radius": "12px",
        "--font-mono": "'JetBrains Mono', 'Fira Code', monospace",
        "--agent-classifier": "#4a9eff",
        "--agent-comparator": "#ff8c42",
        "--agent-pricer": "#22c55e",
    },
    "blueprint": {
        "--bg-primary": "rgba(0, 20, 60, 0.95)",
        "--bg-panel": "rgba(10, 40, 90, 0.5)",
        "--bg-panel-hover": "rgba(20, 55, 110, 0.6)",
        "--border-panel": "rgba(200, 220, 255, 0.2)",
        "--border-glow": "rgba(200, 220, 255, 0.4)",
        "--accent-primary": "#b0c4ff",
        "--accent-secondary": "#ffd700",
        "--accent-success": "#66ff66",
        "--accent-warning": "#ffcc00",
        "--accent-danger": "#ff6666",
        "--text-primary": "#d0e0ff",
        "--text-secondary": "#8090b0",
        "--text-muted": "#405070",
        "--glass-blur": "15px",
        "--glass-border": "1px solid rgba(200, 220, 255, 0.2)",
        "--shadow-panel": "0 4px 20px rgba(0, 0, 0, 0.4)",
        "--shadow-glow": "0 0 15px rgba(200, 220, 255, 0.1)",
        "--radius": "8px",
        "--font-mono": "'Courier New', monospace",
        "--agent-classifier": "#b0c4ff",
        "--agent-comparator": "#ffd700",
        "--agent-pricer": "#66ff66",
    },
    "construction_site": {
        "--bg-primary": "rgba(30, 20, 10, 0.95)",
        "--bg-panel": "rgba(60, 40, 20, 0.5)",
        "--bg-panel-hover": "rgba(80, 55, 30, 0.6)",
        "--border-panel": "rgba(255, 160, 60, 0.2)",
        "--border-glow": "rgba(255, 140, 40, 0.3)",
        "--accent-primary": "#ff8c28",
        "--accent-secondary": "#ffd700",
        "--accent-success": "#4ade80",
        "--accent-warning": "#fbbf24",
        "--accent-danger": "#f87171",
        "--text-primary": "#f0e6d0",
        "--text-secondary": "#b4a088",
        "--text-muted": "#6b5a48",
        "--glass-blur": "12px",
        "--glass-border": "1px solid rgba(255, 160, 60, 0.2)",
        "--shadow-panel": "0 6px 24px rgba(0, 0, 0, 0.4)",
        "--shadow-glow": "0 0 15px rgba(255, 140, 40, 0.1)",
        "--radius": "8px",
        "--font-mono": "'JetBrains Mono', monospace",
        "--agent-classifier": "#ff8c28",
        "--agent-comparator": "#ffd700",
        "--agent-pricer": "#4ade80",
    },
}

DEFAULT_THEME = "minority_report"
```

**Step 3: Create styles**

Create `boq_app/styles.py`:

```python
"""All CSS: glassmorphism base, component styles, Streamlit overrides."""


def build_css(theme_vars: dict[str, str]) -> str:
    """Build complete CSS string from theme variables."""
    root_vars = "\n".join(f"    {k}: {v};" for k, v in theme_vars.items())

    return f"""
<style>
:root {{
{root_vars}
}}

/* --- Base: hide Streamlit chrome --- */
#MainMenu, footer, header {{visibility: hidden;}}
.stDeployButton {{display: none;}}

/* --- Glassmorphism panels --- */
[data-testid="stVerticalBlock"] > div > div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: var(--bg-panel) !important;
    backdrop-filter: blur(var(--glass-blur)) !important;
    -webkit-backdrop-filter: blur(var(--glass-blur)) !important;
    border: var(--glass-border) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow-panel) !important;
    border-top: 2px solid var(--border-glow) !important;
}}

/* --- Global background --- */
.stApp {{
    background: var(--bg-primary) !important;
}}

/* --- Pipeline bar dots --- */
.pipeline-dot {{
    width: 12px; height: 12px;
    border-radius: 50%;
    display: inline-block;
    margin: 0 4px;
    background: var(--text-muted);
    transition: all 0.3s ease;
}}
.pipeline-dot.active {{
    background: var(--accent-primary);
    box-shadow: 0 0 10px var(--accent-primary);
    animation: pulse 1.5s infinite;
}}
.pipeline-dot.done {{
    background: var(--accent-success);
}}

@keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.5; }}
}}

/* --- Agent badges --- */
.agent-badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: bold;
    font-family: var(--font-mono);
}}
.agent-badge.classifier {{ background: var(--agent-classifier); color: #000; }}
.agent-badge.comparator {{ background: var(--agent-comparator); color: #000; }}
.agent-badge.pricer {{ background: var(--agent-pricer); color: #000; }}

/* --- Confidence bars --- */
.confidence-bar {{
    height: 8px;
    border-radius: 4px;
    background: var(--text-muted);
    overflow: hidden;
    margin: 4px 0;
}}
.confidence-bar-fill {{
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease;
}}

/* --- Navigation tree --- */
.nav-item {{
    padding: 6px 12px;
    border-left: 3px solid transparent;
    cursor: pointer;
    transition: all 0.2s;
    font-family: var(--font-mono);
    font-size: 0.85rem;
}}
.nav-item:hover {{
    background: var(--bg-panel-hover);
}}
.nav-item.active {{
    border-left-color: var(--accent-primary);
    background: var(--bg-panel-hover);
    box-shadow: var(--shadow-glow);
}}
.nav-item.matched {{ border-left-color: var(--accent-success); }}
.nav-item.pending {{ border-left-color: var(--text-muted); }}

/* --- Streamlit widget overrides --- */
.stButton > button {{
    background: var(--bg-panel) !important;
    border: var(--glass-border) !important;
    color: var(--text-primary) !important;
    border-radius: var(--radius) !important;
}}
.stButton > button:hover {{
    background: var(--bg-panel-hover) !important;
    box-shadow: var(--shadow-glow) !important;
}}

/* --- Match cards --- */
.match-card {{
    background: var(--bg-panel);
    border: var(--glass-border);
    border-radius: var(--radius);
    padding: 12px;
    margin: 8px 0;
    transition: all 0.2s;
}}
.match-card:hover {{
    border-color: var(--accent-primary);
    box-shadow: var(--shadow-glow);
}}
</style>
"""
```

**Step 4: Create app skeleton**

Create `boq_app/app.py`:

```python
"""Main Streamlit entry point: 3-column glassmorphism layout."""

import streamlit as st

from themes import THEMES, DEFAULT_THEME
from styles import build_css

# --- Page config ---
st.set_page_config(
    page_title="Troškovnjik BoQ Matcher",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Session state init ---
if "theme" not in st.session_state:
    st.session_state.theme = DEFAULT_THEME
if "app_state" not in st.session_state:
    st.session_state.app_state = {
        "pipeline_stage": "upload",
        "selected_unit_idx": 0,
        "parsed_boq": None,
        "reasoning_log": [],
        "matches": [],
        "suggestions": {},
        "stats": {},
    }

# --- Inject CSS ---
theme_vars = THEMES[st.session_state.theme]
st.markdown(build_css(theme_vars), unsafe_allow_html=True)

# --- Header ---
header_cols = st.columns([3, 6, 2, 1])
with header_cols[0]:
    st.markdown("### 🏗️ Troškovnjik")
with header_cols[1]:
    # Pipeline bar placeholder
    st.caption("Upload → Parse → Index → Match → Suggest → Review")
with header_cols[2]:
    st.selectbox(
        "Theme",
        list(THEMES.keys()),
        key="theme",
        label_visibility="collapsed",
    )
with header_cols[3]:
    st.file_uploader("📁", type=["xlsx"], key="upload", label_visibility="collapsed")

# --- 3-column layout ---
left, center, right = st.columns([1, 2, 1])

with left:
    with st.container(border=True):
        st.markdown("#### BoQ Navigator")
        st.caption("Upload a file to begin")

with center:
    with st.container(border=True):
        st.markdown("#### Item Detail")
        st.caption("Select an item from the navigator")
    with st.container(border=True):
        st.markdown("#### Match Results")
        st.caption("Matches will appear here")

with right:
    with st.container(border=True):
        st.markdown("#### LLM Reasoning")
        st.caption("Agent activity will appear here")
    with st.container(border=True):
        st.markdown("#### Confidence Breakdown")
        st.caption("Match scoring factors")

# --- Stats footer ---
f1, f2, f3, f4 = st.columns(4)
f1.metric("AVG", "—")
f2.metric("MIN", "—")
f3.metric("MAX", "—")
f4.metric("MATCHES", "—")
```

**Step 5: Verify Streamlit loads**

Run: `uv run streamlit run boq_app/app.py`
Expected: App loads in browser with glassmorphism panels, 3 columns, theme switcher

**Step 6: Commit**

```bash
git add boq_app/ .streamlit/
git commit -m "feat: add Streamlit skeleton with glassmorphism theming (3 themes)"
```

---

## Task 15: Streamlit Data Models & Mock Data

**Files:**
- Create: `boq_app/models.py`
- Create: `boq_app/mock_data.py`
- Create: `boq_app/state.py`

**Step 1: Create UI models**

Create `boq_app/models.py`:

```python
"""UI-side Pydantic models — thin wrappers around backend models.

These map directly to backend models from backend/src/models/ and
backend/src/agent/schemas.py. Import paths are kept separate so the
Streamlit app can run standalone with mock data.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field


# Mirrors backend LogicalUnit
class BoQItemUI(BaseModel):
    id: str
    item_number: str
    title: str
    description: str = ""
    priced_lines: list[PricedLineUI] = []
    parent_section: str = ""
    parent_chapter: str = ""
    level: int = 0  # 0=chapter, 1=section, 2=subsection, 3=work_item
    status: str = "pending"  # "pending", "matched", "applied"


# Mirrors backend PricedLine
class PricedLineUI(BaseModel):
    item_number: str
    description: str = ""
    unit: str = ""
    quantity: float = 0.0
    unit_price: float | None = None
    total: float | None = None
    suggested_price: float | None = None
    suggestion_confidence: float | None = None


# Mirrors backend ParsedBoQ
class ParsedFileUI(BaseModel):
    filename: str
    format_detected: str
    sheet_name: str
    chapter_title: str = ""
    items: list[BoQItemUI] = []


# Mirrors backend ConfidenceBreakdown
class ConfidenceBreakdownUI(BaseModel):
    text_similarity: float = 0.0
    unit_match: float = 0.0
    hierarchy_match: float = 0.0
    description_overlap: float = 0.0

    @computed_field
    @property
    def overall(self) -> float:
        return round(
            self.text_similarity * 0.4
            + self.unit_match * 0.25
            + self.hierarchy_match * 0.2
            + self.description_overlap * 0.15,
            4,
        )


# Mirrors backend HistoricComparison
class HistoricMatchUI(BaseModel):
    historic_unit_id: int
    project_name: str
    source_filename: str = ""
    project_year: int = 0
    confidence: ConfidenceBreakdownUI
    matching_sub_items: list[str] = []
    missing_sub_items: list[str] = []
    extra_sub_items: list[str] = []
    qty_delta_pct: float = 0.0
    price_lines: list[HistoricMatchLineUI] = []


class HistoricMatchLineUI(BaseModel):
    description: str
    unit_of_measure: str
    quantity: float
    unit_price: float


# Mirrors backend ReasoningEntry
class ReasoningEntryUI(BaseModel):
    agent: str  # "classifier", "comparator", "pricer"
    message: str
    timestamp: str = ""


# Fix forward references
BoQItemUI.model_rebuild()
```

**Step 2: Create mock data**

Create `boq_app/mock_data.py`:

```python
"""Realistic Croatian BoQ mock data for development."""

from models import (
    BoQItemUI,
    ConfidenceBreakdownUI,
    HistoricMatchLineUI,
    HistoricMatchUI,
    ParsedFileUI,
    PricedLineUI,
    ReasoningEntryUI,
)

MOCK_PARSED_FILE = ParsedFileUI(
    filename="ES SAVSKA OPATOVINA - Krovopokrivački.xlsx",
    format_detected="eurospin",
    sheet_name="Radovi",
    chapter_title="26. Krovopokrivački - izolacija krova",
    items=[
        BoQItemUI(
            id="unit-1",
            item_number="3.1.1.",
            title="Hidroizolacija ravnog krova",
            description="Izvedba kompletne hidroizolacije ravnog krova uključujući parnu branu, toplinsku izolaciju i završnu hidroizolacijsku membranu.",
            level=3,
            status="matched",
            priced_lines=[
                PricedLineUI(item_number="3.1.1.a.", description="Parna brana PE folija 0.2mm", unit="m²", quantity=250.0, unit_price=4.50, total=1125.0),
                PricedLineUI(item_number="3.1.1.b.", description="Toplinska izolacija XPS 5cm", unit="m²", quantity=250.0, unit_price=18.00, total=4500.0),
                PricedLineUI(item_number="3.1.1.c.", description="Hidroizolacijska membrana PVC 1.5mm", unit="m²", quantity=250.0, unit_price=35.00, total=8750.0),
            ],
        ),
        BoQItemUI(
            id="unit-2",
            item_number="3.1.2.",
            title="Toplinska izolacija fasade",
            description="Izvedba kontaktne fasade s toplinskom izolacijom EPS 10cm.",
            level=3,
            status="pending",
            priced_lines=[
                PricedLineUI(item_number="3.1.2.a.", description="EPS ploče 10cm", unit="m²", quantity=180.0, unit_price=12.00, total=2160.0),
                PricedLineUI(item_number="3.1.2.b.", description="Ljepilo i armirna mrežica", unit="m²", quantity=180.0, unit_price=8.50, total=1530.0),
            ],
        ),
        BoQItemUI(
            id="unit-3",
            item_number="3.2.1.",
            title="Betonski radovi - podloge",
            description="Izvedba betonskih podloga i stopa beton C40/50.",
            level=3,
            status="pending",
            priced_lines=[
                PricedLineUI(item_number="3.2.1.a.", description="Beton C40/50", unit="m³", quantity=45.0, unit_price=95.00, total=4275.0),
                PricedLineUI(item_number="3.2.1.b.", description="Armatura B500B", unit="kg", quantity=3200.0, unit_price=1.20, total=3840.0),
            ],
        ),
    ],
)

MOCK_MATCHES = [
    HistoricMatchUI(
        historic_unit_id=101,
        project_name="Kaufland Osijek (Retfala)",
        source_filename="Kaufland Osijek (RETFALA).xlsx",
        project_year=2025,
        confidence=ConfidenceBreakdownUI(text_similarity=0.88, unit_match=1.0, hierarchy_match=0.75, description_overlap=0.70),
        matching_sub_items=["parna brana", "toplinska izolacija", "hidroizolacijska membrana"],
        missing_sub_items=[],
        extra_sub_items=[],
        qty_delta_pct=-8.0,
        price_lines=[
            HistoricMatchLineUI(description="Parna brana PE folija", unit_of_measure="m²", quantity=230.0, unit_price=4.20),
            HistoricMatchLineUI(description="Toplinska izolacija XPS", unit_of_measure="m²", quantity=230.0, unit_price=16.50),
            HistoricMatchLineUI(description="Hidroizolacijska membrana", unit_of_measure="m²", quantity=230.0, unit_price=32.00),
        ],
    ),
    HistoricMatchUI(
        historic_unit_id=102,
        project_name="Eurospin Savska Opatovina",
        source_filename="Eurospin_SO_Krovopokrivački.xlsx",
        project_year=2025,
        confidence=ConfidenceBreakdownUI(text_similarity=0.92, unit_match=1.0, hierarchy_match=0.80, description_overlap=0.85),
        matching_sub_items=["parna brana", "hidroizolacijska membrana"],
        missing_sub_items=["toplinska izolacija"],
        extra_sub_items=["vertikalna uz parapetne zidove"],
        qty_delta_pct=12.5,
        price_lines=[
            HistoricMatchLineUI(description="Parna brana", unit_of_measure="m²", quantity=280.0, unit_price=5.00),
            HistoricMatchLineUI(description="Hidroizolacijska membrana PVC", unit_of_measure="m²", quantity=280.0, unit_price=38.00),
        ],
    ),
]

MOCK_REASONING = [
    ReasoningEntryUI(agent="classifier", message="Klasificiram stavku: Hidroizolacija ravnog krova", timestamp="2026-02-14T10:00:01Z"),
    ReasoningEntryUI(agent="classifier", message="Pronađen tip: hidroizolacija-ravnog-krova (confidence: 0.85)", timestamp="2026-02-14T10:00:02Z"),
    ReasoningEntryUI(agent="comparator", message="Tražim historijske stavke za tip: hidroizolacija-ravnog-krova", timestamp="2026-02-14T10:00:03Z"),
    ReasoningEntryUI(agent="comparator", message="Pronađeno 2 historijskih podudaranja", timestamp="2026-02-14T10:00:04Z"),
    ReasoningEntryUI(agent="comparator", message="  Kaufland Osijek (2025): sličnost 84%, qty Δ -8.0%", timestamp="2026-02-14T10:00:04Z"),
    ReasoningEntryUI(agent="comparator", message="  Eurospin SO (2025): sličnost 90%, qty Δ +12.5%", timestamp="2026-02-14T10:00:05Z"),
    ReasoningEntryUI(agent="pricer", message="Analiziram cijene na temelju historijskih podataka", timestamp="2026-02-14T10:00:06Z"),
    ReasoningEntryUI(agent="pricer", message="  3.1.1.a.: 4.60 EUR (confidence: 80%)", timestamp="2026-02-14T10:00:07Z"),
    ReasoningEntryUI(agent="pricer", message="  3.1.1.b.: 16.50 EUR (confidence: 70%)", timestamp="2026-02-14T10:00:07Z"),
    ReasoningEntryUI(agent="pricer", message="  3.1.1.c.: 35.00 EUR (confidence: 85%)", timestamp="2026-02-14T10:00:08Z"),
]
```

**Step 3: Create state manager**

Create `boq_app/state.py`:

```python
"""Session state initialization and helpers."""

import streamlit as st
from themes import DEFAULT_THEME


def init_state():
    """Initialize all session state keys if not present."""
    defaults = {
        "theme": DEFAULT_THEME,
        "pipeline_stage": "upload",
        "selected_unit_idx": 0,
        "parsed_file": None,
        "reasoning_log": [],
        "matches": [],
        "suggestions": {},
        "stats": {"avg": 0, "min": 0, "max": 0, "matches": 0},
        "expanded_cards": set(),
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def get_state(key: str):
    return st.session_state.get(key)


def set_state(key: str, value):
    st.session_state[key] = value
```

**Step 4: Verify imports**

Run: `uv run python -c "from boq_app.models import BoQItemUI; print('OK')"`
Expected: `OK`

**Step 5: Commit**

```bash
git add boq_app/models.py boq_app/mock_data.py boq_app/state.py
git commit -m "feat: add Streamlit UI models, mock data, and state management"
```

---

## Task 16: Streamlit Components

**Files:**
- Create: `boq_app/components/__init__.py`
- Create: `boq_app/components/header.py`
- Create: `boq_app/components/navigator.py`
- Create: `boq_app/components/item_detail.py`
- Create: `boq_app/components/match_cards.py`
- Create: `boq_app/components/reasoning_panel.py`
- Create: `boq_app/components/confidence_panel.py`
- Create: `boq_app/components/stats_footer.py`

Each component is a function that renders into its panel. Components use `st.markdown(unsafe_allow_html=True)` for glassmorphism styling and CSS classes defined in `styles.py`.

This is a large task — implement one component at a time, verify it renders, then move to the next. See the Streamlit UI design doc for exact component specifications.

Key patterns:
- `navigator.py`: `st.radio()` with CSS tree transform, indented by level, colored left border by status
- `item_detail.py`: glass card with item# badge, title, `st.dataframe()` for priced lines
- `match_cards.py`: loop over matches, confidence gradient bar, QTY delta badge, APPLY button, expandable details
- `reasoning_panel.py`: reversed log, monospace, agent badge (CSS class per agent), timestamp
- `confidence_panel.py`: horizontal bars per scoring factor with `st.markdown()` div fills
- `header.py`: pipeline dots with active/done CSS classes
- `stats_footer.py`: `st.metric()` in 4 columns

**Step 1: Create components/__init__.py** (empty file)

**Step 2: Implement all 7 components**

Follow the specifications in the Streamlit UI design doc. Each component takes data from `st.session_state` and renders its panel.

**Step 3: Update app.py to use components**

Replace the placeholder panels in `boq_app/app.py` with component function calls.

**Step 4: Verify all panels render with mock data**

Run: `uv run streamlit run boq_app/app.py`
Expected: All 7 panels render with mock data, glassmorphism styling applied

**Step 5: Commit**

```bash
git add boq_app/components/ boq_app/app.py
git commit -m "feat: add all 7 Streamlit UI components with glassmorphism"
```

---

## Task 17: Streamlit Interactivity

**Files:**
- Modify: `boq_app/app.py`
- Modify: `boq_app/components/navigator.py`
- Modify: `boq_app/components/match_cards.py`

**Step 1: Wire navigator selection**

Clicking a navigator item updates `selected_unit_idx` in session state. The detail card and match panels re-render for the selected unit. Use `st.radio()` `on_change` or `st.fragment()` for independent panel reruns.

**Step 2: Wire APPLY button**

Each match card has an APPLY button. Clicking it copies the historic prices to the selected unit's priced lines in session state. The output panel shows the applied prices.

**Step 3: Wire file upload**

`st.file_uploader` on change populates session state with parsed data (mock data initially, real parsing later). Pipeline stage advances from "upload" to "parse".

**Step 4: Wire MORE/DETAILS expansion**

Each match card has a toggle that expands to show the full historic priced lines table. Uses `expanded_cards` set in session state.

**Step 5: Use st.fragment() for independent panels**

Left navigator, center detail, and right reasoning panels re-run independently using `st.fragment()` to avoid full page reruns.

**Step 6: Verify interactivity**

Run: `uv run streamlit run boq_app/app.py`
Expected: Click navigator → detail updates. Click APPLY → prices copy. Upload file → data loads.

**Step 7: Commit**

```bash
git add boq_app/
git commit -m "feat: wire Streamlit interactivity (navigator, APPLY, upload, expand)"
```

---

## Task 18: Backend Integration

**Files:**
- Create: `boq_app/backend.py`
- Modify: `boq_app/app.py`

**Step 1: Create backend integration module**

Create `boq_app/backend.py`:

```python
"""Backend integration: mock data stubs → real FastAPI.

Phase 1: Returns mock data for standalone development.
Phase 2: Calls FastAPI endpoints via httpx.

Toggle via USE_REAL_BACKEND flag or environment variable.
"""

from __future__ import annotations

import asyncio
import os
from typing import AsyncGenerator

import httpx

from models import ParsedFileUI, HistoricMatchUI, ReasoningEntryUI
from mock_data import MOCK_PARSED_FILE, MOCK_MATCHES, MOCK_REASONING

USE_REAL_BACKEND = os.getenv("BOQ_REAL_BACKEND", "false").lower() == "true"
BACKEND_URL = os.getenv("BOQ_BACKEND_URL", "http://localhost:8081/api")


async def parse_uploaded_file(content: bytes, filename: str) -> ParsedFileUI:
    """Parse an uploaded Excel file into structured BoQ data."""
    if not USE_REAL_BACKEND:
        return MOCK_PARSED_FILE

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BACKEND_URL}/upload",
            files={"file": (filename, content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        resp.raise_for_status()
        return ParsedFileUI(**resp.json())


async def search_historic_matches(unit_id: str) -> list[HistoricMatchUI]:
    """Search for historic matches for a given unit."""
    if not USE_REAL_BACKEND:
        return MOCK_MATCHES

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BACKEND_URL}/historic/search", params={"q": unit_id})
        resp.raise_for_status()
        return [HistoricMatchUI(**m) for m in resp.json()]


async def run_suggestions(unit_id: str) -> AsyncGenerator[tuple[str, dict], None]:
    """Stream SSE events from the agent pipeline.

    Yields (event_type, data) tuples matching the backend pipeline format.
    """
    if not USE_REAL_BACKEND:
        # Mock: yield pre-built reasoning entries with delays
        import time
        for entry in MOCK_REASONING:
            yield ("reasoning", entry.model_dump())
            await asyncio.sleep(0.1)
        yield ("complete", {})
        return

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{BACKEND_URL}/agent/suggest",
            json={"unit_id": unit_id},
        ) as resp:
            event_type = ""
            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                elif line.startswith("data:"):
                    import json
                    data = json.loads(line[5:].strip())
                    yield (event_type, data)
```

**Step 2: Wire into app.py**

Update `boq_app/app.py` to call `backend.py` functions:
- File upload → `asyncio.run(parse_uploaded_file(content, filename))`
- Unit selection → `asyncio.run(search_historic_matches(unit_id))`
- "Run Analysis" button → stream `run_suggestions()` via `st.empty()` live updates

**Step 3: Test with mock data**

Run: `uv run streamlit run boq_app/app.py`
Expected: Upload triggers mock parsing, analysis streams mock reasoning entries

**Step 4: Test with real backend**

Run: `BOQ_REAL_BACKEND=true uv run streamlit run boq_app/app.py`
Prerequisites: FastAPI backend running on :8081, llama-server on :8080
Expected: Real Excel parsing, real LLM pipeline, real SSE streaming

**Step 5: Commit**

```bash
git add boq_app/backend.py boq_app/app.py
git commit -m "feat: add backend integration with mock/real toggle"
```

---

## Task 19: Polish — Themes & Testing

**Files:**
- Modify: `boq_app/app.py`
- Modify: `boq_app/themes.py`

**Step 1: Verify all 3 themes work**

Switch themes via the header selectbox. Verify:
- Minority Report: blue/cyan glass on dark navy
- Blueprint: white on deep blue
- Construction Site: warm amber/orange

**Step 2: Test with all 30 xlsx files**

Upload each file from `vanjski-podaci/primjeri-excel-ponuda/` and verify:
- File parses without errors
- Navigator populates with items
- Encoding handles Croatian characters (č, ć, š, ž, đ)

**Step 3: backdrop-filter fallback**

Test in browser. If `backdrop-filter: blur()` doesn't render, add fallback in `styles.py`:

```css
@supports not (backdrop-filter: blur(20px)) {
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(20, 30, 60, 0.85) !important;
    }
}
```

**Step 4: Commit**

```bash
git add boq_app/
git commit -m "polish: verify themes, test with all 30 xlsx files, add blur fallback"
```

---

## Task 20: Run All Backend Tests

**Step 1: Run full test suite**

Run: `cd backend && uv run pytest tests/ -v`
Expected: All tests pass (~24 tests)

**Step 2: Fix any failures and commit**

---

## Task 21: End-to-End Smoke Test

**Prerequisites:** llama-server running at `http://localhost:8080/v1`

**Step 1: Start backend**

Run: `cd backend && uv run uvicorn src.main:app --host 127.0.0.1 --port 8081 --reload`

**Step 2: Seed taxonomy**

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

**Step 3: Start Streamlit with real backend**

Run: `BOQ_REAL_BACKEND=true uv run streamlit run boq_app/app.py`

**Step 4: Verify end-to-end flow**

1. Upload an xlsx from `vanjski-podaci/`
2. Navigator populates
3. Click a unit → detail card shows
4. Click "Run Analysis" → reasoning panel streams live
5. Match cards appear with confidence bars and QTY deltas
6. APPLY button copies prices
7. Stats footer shows AVG/MIN/MAX/MATCHES
8. Theme switcher changes palette
