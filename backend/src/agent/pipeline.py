"""Pipeline orchestrator: runs Classifier -> Comparator -> Pricer sequentially.

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


def _reasoning(agent_name: str, message: str, entry_type: str = "info") -> tuple[str, dict[str, Any]]:
    entry = ReasoningEntry(agent_name=agent_name, message=message, entry_type=entry_type)
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
            "match_id": match.match_id,
            "project_name": match.project_name,
            "breakdown": match.confidence_breakdown.model_dump(),
        })
        yield _reasoning("comparator",
            f"  {match.project_name} ({match.year}): "
            f"sličnost {match.confidence_breakdown.overall:.0%}, "
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
        num_matches=len(comparison.matches),
        total_suggestions=len(all_prices),
    )
    yield ("stats", stats.model_dump())

    # --- Complete (pipeline: review) ---
    yield _stage("review")
    yield ("complete", {})
