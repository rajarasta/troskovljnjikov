"""
BoQ Matcher - Text matching for BoQ descriptions.

Delegates to the multi-stage matching pipeline (BM25 + structural re-ranking).
Retains utility functions for grouping, statistics, and quantity comparison.
"""
from __future__ import annotations

import re
from typing import Any

from app.services.matching_pipeline import MatchingPipeline


def normalize_text(text: str) -> str:
    """Normalize text for comparison.

    Keeps Croatian diacritics (U+0100-U+017F) and Cyrillic (U+0400-U+04FF).

    Args:
        text: Input text.

    Returns:
        Normalized lowercase text with collapsed whitespace.
    """
    if not text:
        return ""

    result = text.lower()
    # Remove special characters but keep letters, numbers, spaces,
    # Croatian diacritics (U+0100-U+017F), and Cyrillic (U+0400-U+04FF)
    result = re.sub(r"[^a-z0-9\s\u0100-\u017F\u0400-\u04FF]", " ", result)
    # Normalize whitespace
    result = re.sub(r"\s+", " ", result)
    return result.strip()


def find_similar_descriptions(
    query: str,
    items: list[dict[str, Any]],
    threshold: float = 0.3,
    max_results: int = 20,
    include_exact: bool = True,
    pipeline: MatchingPipeline | None = None,
    query_unit: str | None = None,
    query_code: str | None = None,
) -> list[dict[str, Any]]:
    """Find similar descriptions using the multi-stage matching pipeline.

    If a pre-built pipeline is provided, uses it (fast path for batch).
    Otherwise, builds a temporary index from items (backward compat).

    Args:
        query: The description to search for.
        items: Array of indexed BoQ items (dicts).
        threshold: Minimum similarity score to include (0-1).
        max_results: Maximum number of results to return.
        include_exact: Whether to prioritize exact matches.
        pipeline: Optional pre-built MatchingPipeline (avoids rebuilding index).
        query_unit: Optional unit of the query item for boosting.
        query_code: Optional hierarchical code for boosting.

    Returns:
        Matched items with ``similarity`` and ``matchedQuery`` keys added.
    """
    if not query or not items:
        return []

    p = pipeline or MatchingPipeline()
    if not p.is_indexed:
        p.build_index(items)

    results = p.search(
        query=query,
        max_results=max_results,
        threshold=threshold,
        query_unit=query_unit,
        query_code=query_code,
    )

    if include_exact:
        normalized_query = normalize_text(query)
        exact: list[dict[str, Any]] = []
        other: list[dict[str, Any]] = []
        for r in results:
            if normalize_text(r.get("description", "")) == normalized_query:
                exact.append(r)
            else:
                other.append(r)
        return (exact + other)[:max_results]

    return results


def group_matches_by_file(matches: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Group matched results by file.

    Args:
        matches: Array of matched items.

    Returns:
        Dict keyed by fileName, each value containing fileName, filePath, and items list.
    """
    grouped: dict[str, dict[str, Any]] = {}

    for match in matches:
        file_name = match.get("fileName", "Unknown")
        if file_name not in grouped:
            grouped[file_name] = {
                "fileName": file_name,
                "filePath": match.get("filePath"),
                "items": [],
            }
        grouped[file_name]["items"].append(match)

    return grouped


def calculate_match_stats(matches: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate statistics for matched results.

    Args:
        matches: Array of matched items.

    Returns:
        Statistics dict with count, avgPrice, minPrice, maxPrice, priceRange,
        and statusCounts.
    """
    if not matches:
        return {
            "count": 0,
            "avgPrice": 0,
            "minPrice": 0,
            "maxPrice": 0,
            "priceRange": 0,
            "statusCounts": {},
        }

    prices: list[float] = []
    for m in matches:
        try:
            p = float(m.get("unitPrice", ""))
        except (ValueError, TypeError):
            continue
        if p > 0:
            prices.append(p)

    status_counts: dict[str, int] = {}
    for match in matches:
        status = match.get("status", "pending")
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "count": len(matches),
        "avgPrice": sum(prices) / len(prices) if prices else 0,
        "minPrice": min(prices) if prices else 0,
        "maxPrice": max(prices) if prices else 0,
        "priceRange": (max(prices) - min(prices)) if prices else 0,
        "statusCounts": status_counts,
    }


def calculate_quantity_comparison(
    selected_qty: float | str,
    match_qty: float | str,
) -> dict[str, Any]:
    """Calculate quantity comparison metrics between selected and matched items.

    Args:
        selected_qty: The quantity from the selected item.
        match_qty: The quantity from the matched item.

    Returns:
        Comparison dict with hasData, label, color, and optionally ratio and
        percentDiff.
    """
    try:
        selected = float(selected_qty)
    except (ValueError, TypeError):
        selected = 0.0

    try:
        matched = float(match_qty)
    except (ValueError, TypeError):
        matched = 0.0

    # Handle missing data
    if selected == 0 and matched == 0:
        return {"hasData": False, "label": "N/A", "color": "gray"}
    if selected == 0:
        return {"hasData": True, "label": str(matched), "color": "blue"}
    if matched == 0:
        return {"hasData": True, "label": "No qty", "color": "gray"}

    # Calculate ratio and difference
    ratio = matched / selected
    percent_diff = ((matched - selected) / selected) * 100.0

    # Determine color based on ratio
    if 0.9 <= ratio <= 1.1:
        color = "green"  # Within 10%
        if abs(percent_diff) < 1:
            label = "Same"
        else:
            label = f"{'+' if percent_diff > 0 else ''}{percent_diff:.0f}%"
    elif 0.5 <= ratio <= 2.0:
        color = "amber"  # Within 2x
        label = f"{'+' if percent_diff > 0 else ''}{percent_diff:.0f}%"
    else:
        color = "red"  # Outside 2x
        if ratio < 1:
            label = f"{ratio * 100:.0f}%"
        else:
            label = f"{ratio:.1f}x"

    return {
        "hasData": True,
        "ratio": ratio,
        "percentDiff": percent_diff,
        "label": label,
        "color": color,
    }
