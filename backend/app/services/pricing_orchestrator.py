"""Pricing Pipeline Orchestrator — deterministic state machine that spawns
short-lived LLM agents to produce 3-point pricing from XML project exports.

State machine:
  INIT → INGEST → RESOLVE_MATERIALS → ENRICH_CATALOG
       → WEB_QUOTES → HISTORICAL → SYNTHESIZE → FINALIZE → DONE

The orchestrator is NOT an LLM agent. It is deterministic Python code that:
- Manages state transitions
- Spawns agents and collects results
- Passes artifacts between stages
- Enforces concurrency limits
- Persists results to DB
- Emits WebSocket events for frontend progress
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from app.config import settings
from app.database import SessionLocal
from app.models.pricing_pipeline import PricingRun
from app.ws.events import emit

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stage enum
# ---------------------------------------------------------------------------


class PricingStage(str, Enum):
    INIT = "init"
    INGEST = "ingest"
    RESOLVE_MATERIALS = "resolve_materials"
    ENRICH_CATALOG = "enrich_catalog"
    WEB_QUOTES = "web_quotes"
    HISTORICAL = "historical"
    SYNTHESIZE = "synthesize"
    FINALIZE = "finalize"
    DONE = "done"
    ERROR = "error"


# ---------------------------------------------------------------------------
# WebSocket event constants
# ---------------------------------------------------------------------------

PRICING_STAGE_CHANGED = "pricing:stage_changed"
PRICING_ITEM_PROGRESS = "pricing:item_progress"
PRICING_ITEM_RESULT = "pricing:item_result"
PRICING_COMPLETE = "pricing:complete"
PRICING_ERROR = "pricing:error"


# ---------------------------------------------------------------------------
# In-memory state
# ---------------------------------------------------------------------------

_runs: dict[str, dict[str, Any]] = {}

# Concurrency controls
_llm_semaphore = asyncio.Semaphore(3)
_web_semaphore = asyncio.Semaphore(2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def start_pricing_pipeline(file_bytes: bytes, filename: str) -> str:
    """Start a new pricing pipeline run. Returns run_id."""
    run_id = str(uuid.uuid4())

    _runs[run_id] = {
        "run_id": run_id,
        "filename": filename,
        "stage": PricingStage.INIT,
        "progress": 0,
        "started_at": datetime.utcnow().isoformat(),
        "finished_at": None,
        "artifacts": {},
        "error": None,
    }

    # Persist run record
    db = SessionLocal()
    try:
        db.add(PricingRun(id=run_id, source_file=filename, status="init"))
        db.commit()
    finally:
        db.close()

    asyncio.create_task(_run_pricing_pipeline(run_id, file_bytes))
    return run_id


def get_run_status(run_id: str) -> dict[str, Any] | None:
    """Get the current state of a pricing run."""
    return _runs.get(run_id)


def get_run_results(run_id: str) -> dict[str, Any] | None:
    """Get the artifacts of a completed run."""
    state = _runs.get(run_id)
    if not state:
        return None
    return state.get("artifacts")


# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------


async def _run_pricing_pipeline(run_id: str, file_bytes: bytes) -> None:
    """Execute the full pricing pipeline as a background task."""
    state = _runs[run_id]
    db = SessionLocal()
    timing: dict[str, float] = {}

    try:
        # ---- Stage: INGEST (deterministic XML parsing) ----
        t0 = time.monotonic()
        state["stage"] = PricingStage.INGEST
        await emit(PRICING_STAGE_CHANGED, {
            "run_id": run_id, "stage": "ingest",
        })

        from app.services.xml_parser import extract_material_items, parse_pantheon_xml

        parsed = parse_pantheon_xml(file_bytes)
        raw_items = extract_material_items(parsed)

        state["artifacts"]["parsed_metadata"] = parsed.get("metadata", {})
        state["artifacts"]["raw_item_count"] = len(raw_items)
        timing["ingest"] = round(time.monotonic() - t0, 3)

        logger.info(
            "Pipeline %s: INGEST done — %d raw items from '%s'",
            run_id, len(raw_items), parsed.get("project_name", "?"),
        )

        # ---- Stage: RESOLVE_MATERIALS (LLM agent) ----
        t0 = time.monotonic()
        state["stage"] = PricingStage.RESOLVE_MATERIALS
        await emit(PRICING_STAGE_CHANGED, {
            "run_id": run_id, "stage": "resolve_materials",
            "item_count": len(raw_items),
        })

        from app.agents.xml_resolver_agent import resolve_materials

        async with _llm_semaphore:
            resolution = await resolve_materials(file_bytes, raw_items)

        requirements = resolution.requirements
        state["artifacts"]["requirements"] = [r.model_dump() for r in requirements]
        state["artifacts"]["unresolved_sections"] = resolution.unresolved_sections
        timing["resolve_materials"] = round(time.monotonic() - t0, 3)

        logger.info(
            "Pipeline %s: RESOLVE_MATERIALS done — %d requirements",
            run_id, len(requirements),
        )

        if not requirements:
            logger.warning("Pipeline %s: no materials resolved, finishing early", run_id)
            state["stage"] = PricingStage.DONE
            state["artifacts"]["timing"] = timing
            state["finished_at"] = datetime.utcnow().isoformat()
            await emit(PRICING_COMPLETE, {
                "run_id": run_id, "material_count": 0,
                "suggestion_count": 0, "timing": timing,
            })
            _persist_run(db, run_id, "done", 0, timing)
            return

        # ---- Stage: ENRICH_CATALOG (deterministic prefetch + LLM enrichment) ----
        t0 = time.monotonic()
        state["stage"] = PricingStage.ENRICH_CATALOG
        await emit(PRICING_STAGE_CHANGED, {
            "run_id": run_id, "stage": "enrich_catalog",
            "item_count": len(requirements),
        })

        from app.agents.article_context_agent import enrich_with_catalog
        from app.services.catalog_service import catalog_lookup

        # Deterministic prefetch
        catalog_prefetch: dict[str, list[dict]] = {}
        for req in requirements:
            catalog_prefetch[req.req_id] = catalog_lookup(req.description, top_k=5)

        # LLM enrichment
        async with _llm_semaphore:
            enriched = await enrich_with_catalog(requirements, catalog_prefetch)

        state["artifacts"]["catalog_matches"] = [e.model_dump() for e in enriched]
        timing["enrich_catalog"] = round(time.monotonic() - t0, 3)

        logger.info(
            "Pipeline %s: ENRICH_CATALOG done — %d matches",
            run_id, len(enriched),
        )

        # ---- Stage: WEB_QUOTES (parallel web search, reuses existing search_agent) ----
        t0 = time.monotonic()
        state["stage"] = PricingStage.WEB_QUOTES
        await emit(PRICING_STAGE_CHANGED, {
            "run_id": run_id, "stage": "web_quotes",
            "item_count": len(requirements),
        })

        from app.agents.search_agent import run_price_search

        web_results: dict[str, dict] = {}
        web_errors: list[str] = []

        async def _search_one(req) -> None:
            try:
                async with _web_semaphore:
                    async with _llm_semaphore:
                        result = await run_price_search(
                            description=req.description,
                            unit=req.unit,
                            quantity=req.qty,
                        )
                        web_results[req.req_id] = result.model_dump()
                        await emit(PRICING_ITEM_RESULT, {
                            "run_id": run_id,
                            "stage": "web_quotes",
                            "req_id": req.req_id,
                            "quote_count": len(result.quotes),
                        })
            except Exception as exc:
                web_errors.append(f"{req.req_id}: {exc}")
                logger.warning(
                    "Pipeline %s: web search failed for %s: %s",
                    run_id, req.req_id, exc,
                )

        # Run web searches with controlled concurrency
        tasks = [_search_one(req) for req in requirements]
        await asyncio.gather(*tasks, return_exceptions=True)

        state["artifacts"]["web_quotes"] = web_results
        if web_errors:
            state["artifacts"]["web_errors"] = web_errors
        timing["web_quotes"] = round(time.monotonic() - t0, 3)

        logger.info(
            "Pipeline %s: WEB_QUOTES done — %d/%d successful",
            run_id, len(web_results), len(requirements),
        )

        # ---- Stage: HISTORICAL (deterministic RAG search) ----
        t0 = time.monotonic()
        state["stage"] = PricingStage.HISTORICAL
        await emit(PRICING_STAGE_CHANGED, {
            "run_id": run_id, "stage": "historical",
            "item_count": len(requirements),
        })

        from app.services.rag import search as rag_search

        historical_results: dict[str, list[dict]] = {}
        for req in requirements:
            hits = rag_search(query_text=req.description, top_k=10)
            # Filter: drop zero prices, low similarity
            filtered = [
                {
                    "source_boq_id": h["id"],
                    "matched_description": "",
                    "similarity": h["similarity"],
                    "unit_price": h["metadata"].get("unit_price", 0),
                    "unit": h["metadata"].get("unit", ""),
                    "file_date": h["metadata"].get("file_date", ""),
                    "file_id": h["metadata"].get("file_id", ""),
                }
                for h in hits
                if h["similarity"] >= settings.MATCH_THRESHOLD
                and float(h["metadata"].get("unit_price", 0) or 0) > 0
            ]
            historical_results[req.req_id] = filtered
            await asyncio.sleep(0)  # yield to event loop

        state["artifacts"]["historical"] = historical_results
        timing["historical"] = round(time.monotonic() - t0, 3)

        logger.info(
            "Pipeline %s: HISTORICAL done — evidence for %d/%d items",
            run_id,
            sum(1 for v in historical_results.values() if v),
            len(requirements),
        )

        # ---- Stage: SYNTHESIZE (LLM produces 3 price points per item) ----
        t0 = time.monotonic()
        state["stage"] = PricingStage.SYNTHESIZE
        await emit(PRICING_STAGE_CHANGED, {
            "run_id": run_id, "stage": "synthesize",
            "item_count": len(requirements),
        })

        from app.agents.pricing_synthesizer_agent import synthesize_price

        suggestions: list[dict] = []
        synthesis_errors: list[str] = []

        # Build catalog price lookup from enriched results
        catalog_by_req: dict[str, list[dict]] = {}
        for cm in enriched:
            catalog_by_req[cm.req_id] = [
                c.model_dump() for c in cm.article_candidates
            ]

        for idx, req in enumerate(requirements):
            try:
                cat_prices = catalog_by_req.get(req.req_id, [])
                wq = web_results.get(req.req_id, {}).get("quotes", [])
                hp = historical_results.get(req.req_id, [])

                async with _llm_semaphore:
                    suggestion = await synthesize_price(
                        req_id=req.req_id,
                        description=req.description,
                        unit=req.unit,
                        qty=req.qty,
                        catalog_prices=cat_prices,
                        web_quotes=wq,
                        historical_prices=hp,
                    )

                suggestions.append(suggestion.model_dump())
                await emit(PRICING_ITEM_RESULT, {
                    "run_id": run_id,
                    "stage": "synthesize",
                    "req_id": req.req_id,
                    "idx": idx + 1,
                    "total": len(requirements),
                    "low": suggestion.points[0].unit_price_net,
                    "mid": suggestion.points[1].unit_price_net,
                    "high": suggestion.points[2].unit_price_net,
                    "confidence": suggestion.confidence,
                })

            except Exception as exc:
                synthesis_errors.append(f"{req.req_id}: {exc}")
                logger.warning(
                    "Pipeline %s: synthesis failed for %s: %s",
                    run_id, req.req_id, exc,
                )

        state["artifacts"]["suggestions"] = suggestions
        if synthesis_errors:
            state["artifacts"]["synthesis_errors"] = synthesis_errors
        timing["synthesize"] = round(time.monotonic() - t0, 3)

        logger.info(
            "Pipeline %s: SYNTHESIZE done — %d/%d priced",
            run_id, len(suggestions), len(requirements),
        )

        # ---- Stage: FINALIZE ----
        state["stage"] = PricingStage.FINALIZE
        state["artifacts"]["timing"] = timing
        state["finished_at"] = datetime.utcnow().isoformat()

        _persist_run(db, run_id, "done", len(requirements), timing, suggestions)

        state["stage"] = PricingStage.DONE
        state["progress"] = 100
        await emit(PRICING_COMPLETE, {
            "run_id": run_id,
            "material_count": len(requirements),
            "suggestion_count": len(suggestions),
            "timing": timing,
        })

        logger.info("Pipeline %s: DONE", run_id)

    except Exception as exc:
        logger.exception("Pricing pipeline %s failed", run_id)
        state["stage"] = PricingStage.ERROR
        state["error"] = str(exc)
        state["finished_at"] = datetime.utcnow().isoformat()

        _persist_run_error(db, run_id, str(exc))

        await emit(PRICING_ERROR, {"run_id": run_id, "error": str(exc)})
    finally:
        db.close()


# ---------------------------------------------------------------------------
# DB persistence helpers
# ---------------------------------------------------------------------------


def _persist_run(
    db,
    run_id: str,
    status: str,
    item_count: int,
    timing: dict,
    suggestions: list[dict] | None = None,
) -> None:
    """Update the PricingRun record in the database."""
    try:
        run_record = db.query(PricingRun).filter(PricingRun.id == run_id).first()
        if run_record:
            run_record.status = status
            run_record.finished_at = datetime.utcnow()
            run_record.item_count = item_count
            run_record.artifacts = {
                "suggestions": suggestions or [],
                "timing": timing,
                "material_count": item_count,
            }
            db.commit()
    except Exception:
        logger.exception("Failed to persist run %s", run_id)


def _persist_run_error(db, run_id: str, error: str) -> None:
    """Mark a PricingRun as failed in the database."""
    try:
        run_record = db.query(PricingRun).filter(PricingRun.id == run_id).first()
        if run_record:
            run_record.status = "error"
            run_record.error = error
            run_record.finished_at = datetime.utcnow()
            db.commit()
    except Exception:
        logger.exception("Failed to persist error for run %s", run_id)
