"""Pipeline Orchestrator - runs the parse/match/suggest/review pipeline as a background task."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, get_db
from app.models.boq import BoQItem, Workbook
from app.services.boq_matcher import (
    calculate_match_stats,
    find_similar_descriptions,
)
from app.services.matching_pipeline import MatchingPipeline
from app.ws.events import (
    AGENT_ERROR,
    AGENT_PROGRESS,
    AGENT_RESULT,
    AGENT_SPAWN,
    MATCH_FOUND,
    PIPELINE_STAGE_CHANGED,
    PRICE_SUGGESTED,
    emit,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory pipeline state (no DB needed)
# ---------------------------------------------------------------------------


class PipelineStage(str, Enum):
    IDLE = "idle"
    PARSE = "parse"
    MATCH = "match"
    SUGGEST = "suggest"
    REVIEW = "review"
    DONE = "done"
    ERROR = "error"


class PipelineState(BaseModel):
    pipeline_id: str
    workbook_id: str
    stages: list[str]
    current_stage: str = PipelineStage.IDLE
    progress: int = 0
    started_at: str = ""
    finished_at: str | None = None
    error: str | None = None
    results: dict[str, Any] = {}


# Module-level dict holding all pipeline states
_pipelines: dict[str, PipelineState] = {}

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class PipelineStartRequest(BaseModel):
    workbook_id: str
    stages: list[str] = ["parse", "match", "suggest", "review"]


class PipelineStartResponse(BaseModel):
    pipeline_id: str
    status: str


class PipelineStatusResponse(BaseModel):
    pipeline_id: str
    workbook_id: str
    current_stage: str
    progress: int
    started_at: str
    finished_at: str | None
    error: str | None
    results: dict[str, Any]


# ---------------------------------------------------------------------------
# Background pipeline task
# ---------------------------------------------------------------------------


async def _run_pipeline(pipeline_id: str) -> None:
    """Execute the pipeline stages sequentially in the background."""
    state = _pipelines[pipeline_id]

    # Open a dedicated DB session for the background task
    db: Session = SessionLocal()
    try:
        # Load the workbook working data
        workbook = db.query(Workbook).filter(Workbook.id == state.workbook_id).first()
        if not workbook:
            state.current_stage = PipelineStage.ERROR
            state.error = f"Workbook {state.workbook_id} not found"
            await emit(PIPELINE_STAGE_CHANGED, {"stage": "error", "error": state.error}, pipeline_id)
            return

        working_data: dict[str, Any] = workbook.working_data or {}
        items_data: list[dict[str, Any]] = working_data.get("items", [])

        # Load all historical items for matching
        all_historical = db.query(BoQItem).all()
        historical_dicts: list[dict[str, Any]] = [
            {
                "id": item.id,
                "fileId": item.file_id,
                "sheetName": item.sheet_name,
                "row": item.row,
                "itemNumber": item.item_number,
                "description": item.description,
                "fullDescription": item.full_description,
                "parentItemNumber": item.parent_item_number,
                "unit": item.unit,
                "quantity": item.quantity or 0,
                "unitPrice": item.unit_price or 0,
                "total": item.total or 0,
                "projectName": item.project_name,
                "date": item.date,
            }
            for item in all_historical
        ]

        match_results: dict[str, Any] = {}
        matched_items: list[dict[str, Any]] = []

        # ---- Stage: PARSE ----
        if "parse" in state.stages:
            state.current_stage = PipelineStage.PARSE
            state.progress = 0
            await emit(
                PIPELINE_STAGE_CHANGED,
                {"stage": "parse", "progress": 0, "total": len(items_data)},
                pipeline_id,
            )

            for idx, item in enumerate(items_data):
                # Parsing is already done during upload; here we validate/enrich
                progress = int(((idx + 1) / max(len(items_data), 1)) * 100)
                state.progress = progress
                if (idx + 1) % 10 == 0 or idx == len(items_data) - 1:
                    await emit(
                        AGENT_PROGRESS,
                        {"stage": "parse", "current": idx + 1, "total": len(items_data), "progress": progress},
                        pipeline_id,
                    )
                # Yield control so other tasks can run
                await asyncio.sleep(0)

            state.results["parse"] = {"item_count": len(items_data)}

        # ---- Stage: MATCH ----
        if "match" in state.stages:
            state.current_stage = PipelineStage.MATCH
            state.progress = 0
            await emit(
                PIPELINE_STAGE_CHANGED,
                {"stage": "match", "progress": 0, "total": len(items_data)},
                pipeline_id,
            )

            # Build BM25 index once for all historical items
            match_pipeline = MatchingPipeline()
            match_pipeline.build_index(historical_dicts)

            for idx, item in enumerate(items_data):
                description = item.get("description", "")
                if not description or len(description) < 3:
                    continue

                item_id = item.get("id", str(idx))

                await emit(
                    AGENT_SPAWN,
                    {"agent": "matcher", "item_id": item_id, "description": description},
                    pipeline_id,
                )

                try:
                    matches = find_similar_descriptions(
                        query=description,
                        items=historical_dicts,
                        threshold=settings.MATCH_THRESHOLD,
                        max_results=settings.MAX_MATCH_RESULTS,
                        pipeline=match_pipeline,
                        query_unit=item.get("unit"),
                        query_code=item.get("itemNumber"),
                    )

                    if matches:
                        top_match = matches[0]
                        await emit(
                            MATCH_FOUND,
                            {
                                "item_id": item_id,
                                "match_count": len(matches),
                                "top_similarity": top_match.get("similarity", 0),
                                "top_description": top_match.get("description", ""),
                            },
                            pipeline_id,
                        )
                        match_results[item_id] = {
                            "matches": matches[:5],
                            "stats": calculate_match_stats(matches),
                        }
                        matched_items.append({**item, "_matches": matches[:5]})

                    await emit(
                        AGENT_RESULT,
                        {
                            "agent": "matcher",
                            "item_id": item_id,
                            "match_count": len(matches),
                        },
                        pipeline_id,
                    )

                except Exception as exc:
                    logger.exception("Matcher error for item %s", item_id)
                    await emit(
                        AGENT_ERROR,
                        {"agent": "matcher", "item_id": item_id, "error": str(exc)},
                        pipeline_id,
                    )

                progress = int(((idx + 1) / max(len(items_data), 1)) * 100)
                state.progress = progress
                await asyncio.sleep(0)

            state.results["match"] = {
                "matched_count": len(match_results),
                "total_items": len(items_data),
            }

        # ---- Stage: SUGGEST ----
        if "suggest" in state.stages:
            state.current_stage = PipelineStage.SUGGEST
            state.progress = 0
            items_to_price = matched_items if matched_items else []
            await emit(
                PIPELINE_STAGE_CHANGED,
                {"stage": "suggest", "progress": 0, "total": len(items_to_price)},
                pipeline_id,
            )

            suggested_prices: dict[str, Any] = {}
            for idx, item in enumerate(items_to_price):
                item_id = item.get("id", str(idx))
                matches_for_item = item.get("_matches", [])

                await emit(
                    AGENT_SPAWN,
                    {"agent": "pricer", "item_id": item_id},
                    pipeline_id,
                )

                try:
                    # Simple price suggestion: weighted average from top matches
                    prices = []
                    for m in matches_for_item:
                        price = float(m.get("unitPrice", 0) or 0)
                        similarity = float(m.get("similarity", 0) or 0)
                        if price > 0 and similarity > 0:
                            prices.append((price, similarity))

                    if prices:
                        total_weight = sum(w for _, w in prices)
                        suggested = sum(p * w for p, w in prices) / total_weight if total_weight > 0 else 0
                        suggested_prices[item_id] = {
                            "suggested_price": round(suggested, 2),
                            "based_on": len(prices),
                            "confidence": round(total_weight / len(prices), 3),
                        }

                        await emit(
                            PRICE_SUGGESTED,
                            {
                                "item_id": item_id,
                                "suggested_price": round(suggested, 2),
                                "based_on": len(prices),
                            },
                            pipeline_id,
                        )

                    await emit(
                        AGENT_RESULT,
                        {"agent": "pricer", "item_id": item_id, "has_suggestion": bool(prices)},
                        pipeline_id,
                    )

                except Exception as exc:
                    logger.exception("Pricer error for item %s", item_id)
                    await emit(
                        AGENT_ERROR,
                        {"agent": "pricer", "item_id": item_id, "error": str(exc)},
                        pipeline_id,
                    )

                progress = int(((idx + 1) / max(len(items_to_price), 1)) * 100)
                state.progress = progress
                await asyncio.sleep(0)

            state.results["suggest"] = {
                "suggested_count": len(suggested_prices),
                "prices": suggested_prices,
            }

        # ---- Stage: REVIEW ----
        if "review" in state.stages:
            state.current_stage = PipelineStage.REVIEW
            state.progress = 100
            await emit(
                PIPELINE_STAGE_CHANGED,
                {"stage": "review", "progress": 100},
                pipeline_id,
            )

        # ---- Done ----
        state.current_stage = PipelineStage.DONE
        state.progress = 100
        state.finished_at = datetime.utcnow().isoformat()
        await emit(
            PIPELINE_STAGE_CHANGED,
            {"stage": "done", "progress": 100, "results": state.results},
            pipeline_id,
        )

    except Exception as exc:
        logger.exception("Pipeline %s failed", pipeline_id)
        state.current_stage = PipelineStage.ERROR
        state.error = str(exc)
        state.finished_at = datetime.utcnow().isoformat()
        await emit(
            PIPELINE_STAGE_CHANGED,
            {"stage": "error", "error": str(exc)},
            pipeline_id,
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/pipeline/start", response_model=PipelineStartResponse)
async def start_pipeline(req: PipelineStartRequest) -> PipelineStartResponse:
    """Start a new pipeline run as a background task."""
    pipeline_id = str(uuid.uuid4())

    state = PipelineState(
        pipeline_id=pipeline_id,
        workbook_id=req.workbook_id,
        stages=req.stages,
        current_stage=PipelineStage.IDLE,
        progress=0,
        started_at=datetime.utcnow().isoformat(),
    )
    _pipelines[pipeline_id] = state

    asyncio.create_task(_run_pipeline(pipeline_id))

    return PipelineStartResponse(pipeline_id=pipeline_id, status="started")


@router.get("/pipeline/{pipeline_id}/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(pipeline_id: str) -> PipelineStatusResponse:
    """Return the current state and progress of a pipeline run."""
    state = _pipelines.get(pipeline_id)
    if not state:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    return PipelineStatusResponse(
        pipeline_id=state.pipeline_id,
        workbook_id=state.workbook_id,
        current_stage=state.current_stage,
        progress=state.progress,
        started_at=state.started_at,
        finished_at=state.finished_at,
        error=state.error,
        results=state.results,
    )
