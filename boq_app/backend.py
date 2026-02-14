"""Backend integration: mock data stubs -> real FastAPI.

Phase 1 (USE_REAL_BACKEND=false): Returns mock data + local xlsx parsing via analyze_xlsx.py.
Phase 2 (USE_REAL_BACKEND=true): Calls FastAPI endpoints via httpx.

Field names match frontend models (agent_name, match_id, source_file, year, etc.)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import AsyncGenerator

import httpx

from .models import ParsedFileUI, BoQItemUI, PricedLineUI, HistoricMatchUI, ReasoningEntryUI
from .mock_data import generate_mock_matches, generate_mock_reasoning_log

USE_REAL_BACKEND = os.getenv("BOQ_REAL_BACKEND", "false").lower() == "true"
BACKEND_URL = os.getenv("BOQ_BACKEND_URL", "http://localhost:8081/api")

# Find repo root by looking for analyze_xlsx.py (works from worktrees too)
_self_path = Path(__file__).resolve()
REPO_ROOT: Path | None = None
for _p in _self_path.parents:
    if (_p / "analyze_xlsx.py").exists():
        REPO_ROOT = _p
        break

if REPO_ROOT is not None and str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def parse_uploaded_file_sync(content: bytes, filename: str) -> ParsedFileUI:
    """Parse an uploaded Excel file using analyze_xlsx.py.

    Uses the repo-root analyze_xlsx.py for real xlsx parsing,
    converting its output to frontend models.
    """
    try:
        from analyze_xlsx import analyze_file  # type: ignore[import-not-found]

        # analyze_file expects a file path, so write to a temp file
        suffix = Path(filename).suffix or ".xlsx"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            result = analyze_file(tmp_path)
        finally:
            os.unlink(tmp_path)

        # Build ParsedFileUI from the analysis result.
        # analyze_xlsx.py returns structural metadata (header_row, bold_rows,
        # sample_rows, format_family, etc.) rather than fully parsed BoQ items.
        # We extract what we can and present it as a minimal parsed structure.
        items: list[BoQItemUI] = []

        # Use bold rows as chapter/section indicators and sample rows as items
        bold_rows = result.get("bold_rows", [])
        for i, (row_num, text) in enumerate(bold_rows):
            items.append(BoQItemUI(
                id=f"bold-{row_num}",
                item_number=str(i + 1) + ".",
                title=str(text),
                description="",
                level=0,
                excel_start_row=row_num,
                excel_end_row=row_num,
            ))

        return ParsedFileUI(
            filename=filename,
            format_detected=result.get("format_family", "unknown"),
            sheet_name=result.get("boq_sheet", ""),
            chapter_title=(
                bold_rows[0][1] if bold_rows else ""
            ),
            items=items,
            total_rows=result.get("total_rows", 0),
            metadata={
                "header_row": result.get("header_row"),
                "header_score": result.get("header_score"),
                "header_content": result.get("header_content", []),
                "col_count": result.get("col_count"),
                "sheet_names": result.get("sheet_names", []),
                "merged_cells_count": len(result.get("merged_cells", [])),
            },
        )
    except Exception as e:
        # Fallback: return empty file with error info
        return ParsedFileUI(
            filename=filename,
            format_detected="error",
            sheet_name="",
            chapter_title=f"Parse error: {e}",
            items=[],
        )


async def parse_uploaded_file(content: bytes, filename: str) -> ParsedFileUI:
    """Parse an uploaded Excel file (async wrapper)."""
    if not USE_REAL_BACKEND:
        return parse_uploaded_file_sync(content, filename)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BACKEND_URL}/upload",
            files={
                "file": (
                    filename,
                    content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        resp.raise_for_status()
        return ParsedFileUI(**resp.json())


async def search_historic_matches(unit_id: str) -> list[HistoricMatchUI]:
    """Search for historic matches for a given unit."""
    if not USE_REAL_BACKEND:
        return generate_mock_matches()

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BACKEND_URL}/historic/search", params={"q": unit_id}
        )
        resp.raise_for_status()
        return [HistoricMatchUI(**m) for m in resp.json()]


async def run_suggestions(
    unit_id: str,
) -> AsyncGenerator[tuple[str, dict], None]:
    """Stream SSE events from the agent pipeline.

    Yields (event_type, data) tuples matching the backend pipeline format.
    Field names use frontend conventions (agent_name, match_id, etc.)
    """
    if not USE_REAL_BACKEND:
        for entry in generate_mock_reasoning_log():
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
                    data = json.loads(line[5:].strip())
                    yield (event_type, data)
