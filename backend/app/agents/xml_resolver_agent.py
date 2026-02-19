"""XML Material Resolver Agent — normalizes pre-parsed XML BOM items
into clean MaterialRequirements.

The deterministic XML parser has already extracted structured items
(code, description, qty, unit, price, section). This agent:
- Deduplicates similar items (same code/description) by summing quantities
- Normalizes units and descriptions
- Filters non-material items (fees, overhead, etc.)
- Assigns confidence scores

Two modes:
- LLM mode: Uses Claude to reason about items (better quality, costs API)
- Deterministic mode: Pure Python normalization (free, fast, no LLM)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.models.pricing_pipeline import MaterialRequirement
from app.services.llm_settings import get_model_for_agent, run_with_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------


class MaterialResolution(BaseModel):
    """Complete result of XML material resolution."""

    requirements: list[MaterialRequirement] = Field(default_factory=list)
    unresolved_sections: list[str] = Field(default_factory=list)
    reasoning: str = ""


# ---------------------------------------------------------------------------
# Agent (no tools — all data is passed in the prompt)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a construction materials analyst specializing in window/door manufacturing \
(LogiKal, Pantheon ERP). You receive a pre-parsed list of BOM (Bill of Materials) \
items from an XML project export. Your job is to normalize them into clean \
MaterialRequirements.

Rules:
- Each unique material gets one MaterialRequirement with combined quantity
- Deduplicate: items with the same article code should be merged (sum quantities)
- Normalize units: kom (pieces), m (meters), m2, m3, kg, l, set, pau (lump sum)
- Keep the original Croatian/German article names — do NOT translate
- Filter OUT non-material items (administrative fees, overhead, labor)
- Assign confidence: 1.0 for items with clear codes, 0.7 for generic descriptions
- Use req_id format: "REQ-001", "REQ-002", etc.
- derived_from: the section the item came from (Profiles, Accessories, Glass, Position)
- If an item already has a price from the XML, include it in the notes field

Output a MaterialResolution with all requirements.\
"""


def _build_xml_resolver_agent() -> Agent:
    """Create the agent with the current dynamically selected model."""
    current_model = get_model_for_agent("xml_resolver")
    logger.debug("Building xml_resolver_agent with model: %s", current_model)
    return Agent(
        current_model,
        output_type=MaterialResolution,
        system_prompt=SYSTEM_PROMPT,
        retries=2,
        model_settings={"temperature": 0.1},
    )


# ---------------------------------------------------------------------------
# Deterministic fallback
# ---------------------------------------------------------------------------


def _resolve_deterministic(raw_items: list[dict]) -> MaterialResolution:
    """Pure Python BOM normalization — no LLM needed."""
    merged: dict[str, dict] = {}

    for item in raw_items:
        code = (item.get("code") or "").strip()
        desc = (item.get("description") or "").strip()
        key = code or desc
        if not key:
            continue

        if key in merged:
            merged[key]["qty"] += float(item.get("qty", 0) or 0)
        else:
            price = item.get("price") or item.get("unit_price") or 0
            notes = ""
            if price and float(price) > 0:
                notes = f"XML price: {price} EUR"

            merged[key] = {
                "code": code,
                "description": desc or code,
                "qty": float(item.get("qty", 0) or 0),
                "unit": (item.get("unit") or "kom").strip(),
                "section": item.get("section", ""),
                "notes": notes,
                "confidence": 1.0 if code else 0.7,
            }

    requirements = []
    for i, (key, data) in enumerate(merged.items(), 1):
        requirements.append(MaterialRequirement(
            req_id=f"REQ-{i:03d}",
            description=data["description"],
            qty=data["qty"],
            unit=data["unit"],
            derived_from=data["section"],
            confidence=data["confidence"],
            notes=data["notes"],
        ))

    return MaterialResolution(
        requirements=requirements,
        reasoning=f"Deterministic normalization: {len(raw_items)} items → {len(requirements)} unique materials",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def resolve_materials(
    file_bytes: bytes,
    raw_items: list[dict],
    user_hint: str = "",
) -> MaterialResolution:
    """Normalize pre-parsed BOM items into MaterialRequirements.

    Uses deterministic normalization since the XML parser already produces
    well-structured items. LLM is not needed for this stage — the article_context
    and pricing_synthesizer agents handle the reasoning.
    """
    logger.info("Starting XML material resolution (%d pre-parsed items)", len(raw_items))

    output = _resolve_deterministic(raw_items)
    logger.info(
        "XML resolver (deterministic) returned %d requirements",
        len(output.requirements),
    )
    return output
