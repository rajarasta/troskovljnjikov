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
    threshold: float = 0.7,
) -> dict[str, Any]:
    """Align current sub-items with historic by description similarity + unit match."""
    used_historic: set[int] = set()
    matched_pairs: list[dict[str, Any]] = []

    for curr in current_lines:
        curr_desc = curr.get("description", "")
        curr_unit = curr.get("unit", "")
        best_match: int | None = None
        best_score = threshold

        for i, hist in enumerate(historic_lines):
            if i in used_historic:
                continue
            hist_desc = hist.get("description", "")
            hist_unit = hist.get("unit_of_measure", "")

            score = _similarity(curr_desc, hist_desc)
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
        curr for curr in current_lines
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
