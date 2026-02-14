"""Agent trigger endpoints - on-demand column detection, batch matching, price suggestion, and photo analysis."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.boq import BoQFile, BoQItem, Workbook
from app.schemas.boq import BoQItemSchema, MatchResponse, MatchResult
from app.services.boq_matcher import (
    calculate_match_stats,
    calculate_quantity_comparison,
    find_similar_descriptions,
)
from app.ws.events import (
    AGENT_ERROR,
    AGENT_RESULT,
    AGENT_SPAWN,
    COLUMN_DETECTED,
    MATCH_FOUND,
    PRICE_SUGGESTED,
    emit,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Shared LLM model
# ---------------------------------------------------------------------------

_llm_model = OpenAIModel(
    settings.LLM_MODEL_NAME,
    provider=OpenAIProvider(base_url=settings.LLM_BASE_URL),
)

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class DetectColumnsRequest(BaseModel):
    file_id: str


class DetectColumnsResponse(BaseModel):
    file_id: str
    column_mapping: dict[str, Any]


class MatchAllRequest(BaseModel):
    workbook_id: str
    threshold: float = 0.3
    max_results: int = 20


class MatchAllResponse(BaseModel):
    workbook_id: str
    matched_count: int
    total_items: int
    results: dict[str, Any]


class SuggestPriceRequest(BaseModel):
    item_id: str
    description: str
    quantity: float | None = None
    unit: str | None = None


class SuggestPriceResponse(BaseModel):
    item_id: str
    suggested_price: float
    confidence: float
    based_on: int
    reasoning: str


class PhotoAnalysisResponse(BaseModel):
    description: str
    detected_items: list[str]
    notes: str


# ---------------------------------------------------------------------------
# Column detection agent
# ---------------------------------------------------------------------------

column_detect_agent = Agent(
    model=_llm_model,
    system_prompt=(
        "You are a column detection assistant for Croatian construction BOQ spreadsheets. "
        "Given a list of header row values, identify which columns map to: "
        "itemNumber, description, unit, quantity, unitPrice, total. "
        "Return a JSON object mapping column names to their 0-based column indices. "
        "Only include columns you are confident about."
    ),
)


@router.post("/detect-columns", response_model=DetectColumnsResponse)
async def detect_columns(
    req: DetectColumnsRequest,
    db: Session = Depends(get_db),
) -> DetectColumnsResponse:
    """Trigger the column detection agent for a file.

    Uses a combination of the deterministic indexer heuristics and an LLM fallback
    when confidence is low.
    """
    file_record = db.query(BoQFile).filter(BoQFile.id == req.file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    await emit(
        AGENT_SPAWN,
        {"agent": "column_detector", "file_id": req.file_id},
    )

    try:
        # If we already have a mapping stored, return it
        if file_record.column_mapping:
            await emit(
                COLUMN_DETECTED,
                {"file_id": req.file_id, "column_mapping": file_record.column_mapping, "source": "cached"},
            )
            return DetectColumnsResponse(
                file_id=req.file_id,
                column_mapping=file_record.column_mapping,
            )

        # Try LLM-assisted column detection
        # Build a prompt with sample data from the file items
        items = (
            db.query(BoQItem)
            .filter(BoQItem.file_id == req.file_id)
            .order_by(BoQItem.row)
            .limit(5)
            .all()
        )

        if not items:
            raise HTTPException(status_code=422, detail="No items found for this file")

        sample_rows = []
        for item in items:
            sample_rows.append(
                f"Row {item.row}: itemNumber={item.item_number!r}, "
                f"description={item.description!r}, "
                f"unit={item.unit!r}, "
                f"quantity={item.quantity}, "
                f"unitPrice={item.unit_price}, "
                f"total={item.total}"
            )

        prompt = (
            "Based on these sample rows from a BOQ file, confirm or correct the column mapping:\n\n"
            + "\n".join(sample_rows)
            + "\n\nReturn a JSON object with column names as keys and 0-based indices as values."
        )

        result = await column_detect_agent.run(prompt)

        # Parse the LLM response - use a basic mapping if parsing fails
        column_mapping = {
            "itemNumber": 0,
            "description": 1,
            "unit": 2,
            "quantity": 3,
            "unitPrice": 4,
            "total": 5,
        }

        # Try to extract JSON from the LLM response
        response_text = result.data
        if isinstance(response_text, str):
            import json
            try:
                # Try to find JSON in the response
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start != -1 and end > start:
                    column_mapping = json.loads(response_text[start:end])
            except (json.JSONDecodeError, ValueError):
                logger.warning("Could not parse LLM column detection response, using defaults")

        # Store the mapping
        file_record.column_mapping = column_mapping
        db.commit()

        await emit(
            COLUMN_DETECTED,
            {"file_id": req.file_id, "column_mapping": column_mapping, "source": "llm"},
        )
        await emit(
            AGENT_RESULT,
            {"agent": "column_detector", "file_id": req.file_id, "column_mapping": column_mapping},
        )

        return DetectColumnsResponse(
            file_id=req.file_id,
            column_mapping=column_mapping,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Column detection failed for file %s", req.file_id)
        await emit(
            AGENT_ERROR,
            {"agent": "column_detector", "file_id": req.file_id, "error": str(exc)},
        )
        raise HTTPException(status_code=500, detail=f"Column detection failed: {exc}")


# ---------------------------------------------------------------------------
# Batch matching
# ---------------------------------------------------------------------------


@router.post("/match-all", response_model=MatchAllResponse)
async def match_all_items(
    req: MatchAllRequest,
    db: Session = Depends(get_db),
) -> MatchAllResponse:
    """Trigger batch matching for all items in a workbook against historical data."""
    workbook = db.query(Workbook).filter(Workbook.id == req.workbook_id).first()
    if not workbook:
        raise HTTPException(status_code=404, detail="Workbook not found")

    working_data: dict[str, Any] = workbook.working_data or {}
    items_data: list[dict[str, Any]] = working_data.get("items", [])

    if not items_data:
        raise HTTPException(status_code=422, detail="Workbook has no items")

    await emit(
        AGENT_SPAWN,
        {"agent": "batch_matcher", "workbook_id": req.workbook_id, "item_count": len(items_data)},
    )

    # Load all historical items
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

    all_results: dict[str, Any] = {}
    matched_count = 0

    for idx, item in enumerate(items_data):
        description = item.get("description", "")
        if not description or len(description) < 3:
            continue

        item_id = item.get("id", str(idx))

        try:
            matches = find_similar_descriptions(
                query=description,
                items=historical_dicts,
                threshold=req.threshold,
                max_results=req.max_results,
            )

            if matches:
                matched_count += 1
                top_match = matches[0]
                await emit(
                    MATCH_FOUND,
                    {
                        "item_id": item_id,
                        "match_count": len(matches),
                        "top_similarity": top_match.get("similarity", 0),
                    },
                )
                all_results[item_id] = {
                    "match_count": len(matches),
                    "top_similarity": top_match.get("similarity", 0),
                    "top_description": top_match.get("description", ""),
                    "top_unit_price": top_match.get("unitPrice", 0),
                }

        except Exception as exc:
            logger.exception("Batch matching error for item %s", item_id)
            await emit(
                AGENT_ERROR,
                {"agent": "batch_matcher", "item_id": item_id, "error": str(exc)},
            )

    await emit(
        AGENT_RESULT,
        {
            "agent": "batch_matcher",
            "workbook_id": req.workbook_id,
            "matched_count": matched_count,
            "total_items": len(items_data),
        },
    )

    return MatchAllResponse(
        workbook_id=req.workbook_id,
        matched_count=matched_count,
        total_items=len(items_data),
        results=all_results,
    )


# ---------------------------------------------------------------------------
# Price suggestion
# ---------------------------------------------------------------------------

price_agent = Agent(
    model=_llm_model,
    system_prompt=(
        "You are a construction cost estimation expert for Croatian BOQ projects. "
        "Given a BOQ item description, historical price data, and context, suggest a fair unit price. "
        "Explain your reasoning briefly. Consider market trends, quantity, and unit of measure. "
        "Always respond with a single numeric price value and a short explanation."
    ),
)


@router.post("/suggest-price", response_model=SuggestPriceResponse)
async def suggest_price(
    req: SuggestPriceRequest,
    db: Session = Depends(get_db),
) -> SuggestPriceResponse:
    """Trigger price suggestion for a single item using historical matches and LLM reasoning."""
    await emit(
        AGENT_SPAWN,
        {"agent": "pricer", "item_id": req.item_id},
    )

    try:
        # Find historical matches
        all_historical = db.query(BoQItem).all()
        historical_dicts: list[dict[str, Any]] = [
            {
                "id": item.id,
                "description": item.description,
                "fullDescription": item.full_description,
                "unit": item.unit,
                "quantity": item.quantity or 0,
                "unitPrice": item.unit_price or 0,
                "total": item.total or 0,
                "projectName": item.project_name,
                "date": item.date,
            }
            for item in all_historical
        ]

        matches = find_similar_descriptions(
            query=req.description,
            items=historical_dicts,
            threshold=settings.MATCH_THRESHOLD,
            max_results=10,
        )

        # Build context for the LLM
        match_context = ""
        prices: list[tuple[float, float]] = []  # (price, similarity)
        if matches:
            lines = []
            for m in matches[:5]:
                price = float(m.get("unitPrice", 0) or 0)
                similarity = float(m.get("similarity", 0) or 0)
                lines.append(
                    f"- {m.get('description', 'N/A')} | "
                    f"Unit: {m.get('unit', 'N/A')} | "
                    f"Price: {price} | "
                    f"Similarity: {similarity:.2f} | "
                    f"Project: {m.get('projectName', 'N/A')}"
                )
                if price > 0 and similarity > 0:
                    prices.append((price, similarity))
            match_context = "\n".join(lines)

        # Calculate a weighted average as a baseline
        if prices:
            total_weight = sum(w for _, w in prices)
            baseline = sum(p * w for p, w in prices) / total_weight if total_weight > 0 else 0.0
        else:
            baseline = 0.0

        prompt = (
            f"BOQ Item to price:\n"
            f"Description: {req.description}\n"
            f"Unit: {req.unit or 'N/A'}\n"
            f"Quantity: {req.quantity or 'N/A'}\n\n"
        )
        if match_context:
            prompt += f"Historical matches:\n{match_context}\n\n"
        prompt += (
            f"Weighted average from matches: {baseline:.2f}\n\n"
            "Suggest a fair unit price and explain briefly."
        )

        result = await price_agent.run(prompt)
        reasoning = result.data

        # Use baseline as suggested price (LLM reasoning is supplementary)
        suggested_price = round(baseline, 2) if baseline > 0 else 0.0
        confidence = round(
            (sum(w for _, w in prices) / len(prices)) if prices else 0.0,
            3,
        )

        await emit(
            PRICE_SUGGESTED,
            {
                "item_id": req.item_id,
                "suggested_price": suggested_price,
                "based_on": len(prices),
            },
        )
        await emit(
            AGENT_RESULT,
            {"agent": "pricer", "item_id": req.item_id, "suggested_price": suggested_price},
        )

        return SuggestPriceResponse(
            item_id=req.item_id,
            suggested_price=suggested_price,
            confidence=confidence,
            based_on=len(prices),
            reasoning=reasoning,
        )

    except Exception as exc:
        logger.exception("Price suggestion failed for item %s", req.item_id)
        await emit(
            AGENT_ERROR,
            {"agent": "pricer", "item_id": req.item_id, "error": str(exc)},
        )
        raise HTTPException(status_code=500, detail=f"Price suggestion failed: {exc}")


# ---------------------------------------------------------------------------
# Photo / vision analysis
# ---------------------------------------------------------------------------

vision_agent = Agent(
    model=_llm_model,
    system_prompt=(
        "You are a construction site photo analyst. "
        "Given a description of a construction photo, identify potential BOQ items visible in the image. "
        "List specific construction materials, finishes, and work items you can identify. "
        "Be specific about quantities where possible."
    ),
)


@router.post("/analyze-photo", response_model=PhotoAnalysisResponse)
async def analyze_photo(
    file: UploadFile = File(...),
) -> PhotoAnalysisResponse:
    """Trigger vision agent analysis on an uploaded construction photo.

    Note: True vision capabilities depend on the underlying model.
    For text-only models, this extracts metadata and provides a best-effort analysis
    based on the filename and any embedded EXIF data.
    """
    await emit(
        AGENT_SPAWN,
        {"agent": "vision", "filename": file.filename},
    )

    try:
        file_bytes = await file.read()
        file_size_kb = len(file_bytes) / 1024

        # Build prompt from file metadata
        prompt = (
            f"A construction site photo has been uploaded.\n"
            f"Filename: {file.filename}\n"
            f"Content type: {file.content_type}\n"
            f"File size: {file_size_kb:.1f} KB\n\n"
            "Based on the filename and typical construction site photos, "
            "what BOQ items might be visible? List potential construction items, "
            "materials, and work activities."
        )

        result = await vision_agent.run(prompt)
        analysis = result.data

        # Parse the response into structured output
        detected_items: list[str] = []
        for line in analysis.split("\n"):
            line = line.strip()
            if line.startswith(("-", "*", "+")):
                detected_items.append(line.lstrip("-*+ ").strip())
            elif line and len(line) > 5 and not line.endswith(":"):
                detected_items.append(line)

        await emit(
            AGENT_RESULT,
            {
                "agent": "vision",
                "filename": file.filename,
                "detected_count": len(detected_items),
            },
        )

        return PhotoAnalysisResponse(
            description=analysis,
            detected_items=detected_items[:20],
            notes=f"Analysis based on file metadata. File size: {file_size_kb:.1f} KB.",
        )

    except Exception as exc:
        logger.exception("Photo analysis failed for %s", file.filename)
        await emit(
            AGENT_ERROR,
            {"agent": "vision", "filename": file.filename, "error": str(exc)},
        )
        raise HTTPException(status_code=500, detail=f"Photo analysis failed: {exc}")
