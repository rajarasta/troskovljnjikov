"""Autopilot Service - automatic batch matching, price suggestion, and LLM summary on upload.

Triggered after file upload. Runs three stages:
1. LLM streaming summary of the uploaded file
2. Batch ChromaDB matching for all items
3. Price suggestion via weighted average from top matches

Results are cached in-memory and served via REST endpoints + streamed via WebSocket.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import settings
from app.database import SessionLocal
from app.services.llm_settings import run_stream_with_settings
from app.models.boq import ChatMessage
from app.services.rag import search as rag_search
from app.ws.events import (
    AUTOPILOT_COMPLETE,
    AUTOPILOT_ERROR,
    AUTOPILOT_MATCH_PROGRESS,
    AUTOPILOT_MATCH_RESULT,
    AUTOPILOT_PRICE_SUGGESTED,
    AUTOPILOT_SUMMARY_TOKEN,
    emit,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory caches
# ---------------------------------------------------------------------------

# file_id -> { item_id -> [match dicts] }
_match_cache: dict[str, dict[str, list[dict[str, Any]]]] = {}

# file_id -> { item_id -> {suggested_price, confidence, based_on} }
_price_cache: dict[str, dict[str, dict[str, Any]]] = {}

# file_id -> { item_id -> "high" | "medium" | "low" }
_confidence_cache: dict[str, dict[str, str]] = {}

# file_id -> "idle" | "summarizing" | "matching" | "pricing" | "done" | "error"
_status: dict[str, str] = {}

# file_id -> {current, total}
_progress: dict[str, dict[str, int]] = {}

# ---------------------------------------------------------------------------
# Cache API (called by router)
# ---------------------------------------------------------------------------


def get_cached_matches(file_id: str, item_id: str) -> list[dict[str, Any]] | None:
    return _match_cache.get(file_id, {}).get(item_id)


def get_all_cached_matches(file_id: str) -> dict[str, list[dict[str, Any]]]:
    return _match_cache.get(file_id, {})


def get_cached_price(file_id: str, item_id: str) -> dict[str, Any] | None:
    return _price_cache.get(file_id, {}).get(item_id)


def get_all_cached_prices(file_id: str) -> dict[str, dict[str, Any]]:
    return _price_cache.get(file_id, {})


def get_all_confidences(file_id: str) -> dict[str, str]:
    return _confidence_cache.get(file_id, {})


def get_status(file_id: str) -> dict[str, Any]:
    return {
        "status": _status.get(file_id, "idle"),
        "progress": _progress.get(file_id, {"current": 0, "total": 0}),
    }


def invalidate_cache(file_id: str) -> None:
    _match_cache.pop(file_id, None)
    _price_cache.pop(file_id, None)
    _confidence_cache.pop(file_id, None)
    _status.pop(file_id, None)
    _progress.pop(file_id, None)


# ---------------------------------------------------------------------------
# Confidence tier logic
# ---------------------------------------------------------------------------

HIGH_THRESHOLD = 0.7
MEDIUM_THRESHOLD = 0.4


def _confidence_tier(top_similarity: float) -> str:
    if top_similarity >= HIGH_THRESHOLD:
        return "high"
    if top_similarity >= MEDIUM_THRESHOLD:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# LLM agent for file summary
# ---------------------------------------------------------------------------

_summary_model = OpenAIModel(
    settings.LLM_MODEL_NAME,
    provider=OpenAIProvider(base_url=settings.LLM_BASE_URL),
)

_summary_agent = Agent(
    model=_summary_model,
    system_prompt=(
        "You are a construction cost estimation assistant analyzing Croatian BOQ (Bill of Quantities) files. "
        "Provide a concise summary of the uploaded file including: project name/sender, total number of items, "
        "approximate total value, notable patterns (missing prices, unusual quantities), and any quality issues. "
        "Respond in the same language as the content (usually Croatian). Keep it under 200 words."
    ),
)


# ---------------------------------------------------------------------------
# Main autopilot coroutine
# ---------------------------------------------------------------------------


async def run_autopilot(
    file_id: str,
    items: list[dict[str, Any]],
    units: list[dict[str, Any]],
    file_info: dict[str, Any],
) -> None:
    """Run the full autopilot pipeline in the background."""
    try:
        # Initialize caches
        _match_cache[file_id] = {}
        _price_cache[file_id] = {}
        _confidence_cache[file_id] = {}
        _status[file_id] = "summarizing"
        _progress[file_id] = {"current": 0, "total": len(items)}

        # Stage 1: LLM Summary
        await _run_summary(file_id, items, file_info)

        # Stage 2: Batch Match
        _status[file_id] = "matching"
        await _run_batch_match(file_id, items)

        # Stage 3: Price Suggestions
        _status[file_id] = "pricing"
        await _run_price_suggestions(file_id)

        # Done
        _status[file_id] = "done"
        confidences = _confidence_cache.get(file_id, {})
        high_count = sum(1 for v in confidences.values() if v == "high")
        medium_count = sum(1 for v in confidences.values() if v == "medium")
        low_count = sum(1 for v in confidences.values() if v == "low")

        await emit(AUTOPILOT_COMPLETE, {
            "file_id": file_id,
            "total_items": len(items),
            "matched_items": len(_match_cache.get(file_id, {})),
            "priced_items": len(_price_cache.get(file_id, {})),
            "high_confidence": high_count,
            "medium_confidence": medium_count,
            "low_confidence": low_count,
        })

    except Exception as exc:
        logger.exception("Autopilot failed for file %s", file_id)
        _status[file_id] = "error"
        await emit(AUTOPILOT_ERROR, {
            "file_id": file_id,
            "error": str(exc),
        })


# ---------------------------------------------------------------------------
# Stage 1: LLM Summary
# ---------------------------------------------------------------------------


async def _run_summary(
    file_id: str,
    items: list[dict[str, Any]],
    file_info: dict[str, Any],
) -> None:
    """Generate a streaming LLM summary of the file."""
    # Build summary prompt
    total_value = sum(float(i.get("total") or 0) for i in items)
    missing = file_info.get("missingData", {})
    sample_items = items[:5]
    sample_descs = "\n".join(
        f"  - {i.get('itemNumber', '?')}: {i.get('description', '')[:80]}"
        for i in sample_items
    )

    prompt = (
        f"File: {file_info.get('fileName', 'Unknown')}\n"
        f"Sheets: {file_info.get('sheetCount', 0)}\n"
        f"Items: {file_info.get('itemCount', 0)}\n"
        f"Total value: {total_value:,.2f} EUR\n"
        f"Missing prices: {missing.get('prices', 0)}\n"
        f"Missing quantities: {missing.get('quantities', 0)}\n"
        f"Missing units: {missing.get('units', 0)}\n"
        f"\nSample items:\n{sample_descs}\n"
        f"\nPlease summarize this BOQ file."
    )

    try:
        accumulated_text = ""
        async with await run_stream_with_settings("autopilot_summary", _summary_agent, prompt) as stream:
            async for token in stream.stream_text(delta=True):
                accumulated_text += token
                await emit(AUTOPILOT_SUMMARY_TOKEN, {
                    "file_id": file_id,
                    "token": token,
                    "done": False,
                })

        # Signal summary complete
        await emit(AUTOPILOT_SUMMARY_TOKEN, {
            "file_id": file_id,
            "token": "",
            "done": True,
        })

        # Persist the full summary as a ChatMessage
        db = SessionLocal()
        try:
            msg = ChatMessage(
                item_id=f"file:{file_id}",
                role="assistant",
                content=accumulated_text,
            )
            db.add(msg)
            db.commit()
        finally:
            db.close()

    except Exception as exc:
        logger.warning("LLM summary failed for file %s: %s", file_id, exc)
        await emit(AUTOPILOT_SUMMARY_TOKEN, {
            "file_id": file_id,
            "token": f"Summary generation failed: {exc}",
            "done": True,
        })


# ---------------------------------------------------------------------------
# Stage 2: Batch Match
# ---------------------------------------------------------------------------


async def _run_batch_match(file_id: str, items: list[dict[str, Any]]) -> None:
    """Match all items against ChromaDB."""
    matchable = [i for i in items if len(i.get("description", "") or "") >= 3]
    total = len(matchable)
    _progress[file_id] = {"current": 0, "total": total}

    for idx, item in enumerate(matchable):
        item_id = item.get("id") or f"{file_id}:{item.get('sheetName', '')}:{item['row']}"
        description = item.get("fullDescription") or item.get("description", "")

        try:
            hits = rag_search(
                query_text=description,
                top_k=5,
                file_id_exclude=file_id,
            )
            matches = [h for h in hits if h["similarity"] >= settings.MATCH_THRESHOLD]

            _match_cache[file_id][item_id] = matches

            top_sim = matches[0]["similarity"] if matches else 0.0
            tier = _confidence_tier(top_sim)
            _confidence_cache[file_id][item_id] = tier

            await emit(AUTOPILOT_MATCH_RESULT, {
                "file_id": file_id,
                "item_id": item_id,
                "match_count": len(matches),
                "top_similarity": round(top_sim, 4),
                "confidence": tier,
            })

        except Exception as exc:
            logger.warning("Batch match error for %s: %s", item_id, exc)
            _confidence_cache[file_id][item_id] = "low"

        _progress[file_id] = {"current": idx + 1, "total": total}

        if (idx + 1) % 10 == 0 or idx == total - 1:
            await emit(AUTOPILOT_MATCH_PROGRESS, {
                "file_id": file_id,
                "current": idx + 1,
                "total": total,
            })

        # Yield to event loop every item
        await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# Stage 3: Price Suggestions
# ---------------------------------------------------------------------------


async def _run_price_suggestions(file_id: str) -> None:
    """Compute suggested prices from cached match results."""
    matches_by_item = _match_cache.get(file_id, {})

    for item_id, matches in matches_by_item.items():
        if not matches:
            continue

        prices: list[tuple[float, float]] = []
        for m in matches:
            meta = m.get("metadata", {})
            price = float(meta.get("unit_price", 0) or 0)
            similarity = float(m.get("similarity", 0) or 0)
            if price > 0 and similarity > 0:
                prices.append((price, similarity))

        if not prices:
            continue

        total_weight = sum(w for _, w in prices)
        suggested = sum(p * w for p, w in prices) / total_weight if total_weight > 0 else 0
        confidence = round(total_weight / len(prices), 3)

        suggestion = {
            "suggested_price": round(suggested, 2),
            "confidence": confidence,
            "based_on": len(prices),
        }
        _price_cache[file_id][item_id] = suggestion

        await emit(AUTOPILOT_PRICE_SUGGESTED, {
            "file_id": file_id,
            "item_id": item_id,
            **suggestion,
        })

        await asyncio.sleep(0)
