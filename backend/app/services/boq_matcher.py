"""
BoQ Matcher - Fuzzy text matching for BoQ descriptions.

Uses string similarity algorithms to find matching historical items.
Direct port of boqMatcher.js.
"""
from __future__ import annotations

import re
from typing import Any


def levenshtein_distance(str1: str, str2: str, max_distance: float = float("inf")) -> int | float:
    """Calculate Levenshtein distance between two strings with early termination.

    Uses a space-optimized single-array approach.

    Args:
        str1: First string.
        str2: Second string.
        max_distance: Optional maximum distance; returns inf if exceeded.

    Returns:
        The edit distance, or float('inf') if it exceeds max_distance.
    """
    m = len(str1)
    n = len(str2)

    # Early termination if length difference exceeds max_distance
    if abs(m - n) > max_distance:
        return float("inf")

    # Optimize for empty strings
    if m == 0:
        return n
    if n == 0:
        return m

    # Use single array instead of full matrix (space optimization)
    prev_row = list(range(n + 1))
    curr_row = [0] * (n + 1)

    for i in range(1, m + 1):
        curr_row[0] = i
        min_in_row = curr_row[0]

        for j in range(1, n + 1):
            cost = 0 if str1[i - 1] == str2[j - 1] else 1
            curr_row[j] = min(
                prev_row[j] + 1,        # deletion
                curr_row[j - 1] + 1,    # insertion
                prev_row[j - 1] + cost,  # substitution
            )
            min_in_row = min(min_in_row, curr_row[j])

        # Early termination if all values in row exceed max_distance
        if min_in_row > max_distance:
            return float("inf")

        # Swap rows
        prev_row, curr_row = curr_row, prev_row

    return prev_row[n]


def calculate_similarity(str1: str, str2: str) -> float:
    """Calculate similarity between two strings (0 to 1).

    Uses a combination of Levenshtein distance and token overlap (Jaccard index).
    Weights: Jaccard 0.6, Levenshtein 0.3, containment bonus 0.2.

    Args:
        str1: First string.
        str2: Second string.

    Returns:
        Similarity score between 0 and 1.
    """
    if not str1 or not str2:
        return 0.0

    s1 = normalize_text(str1)
    s2 = normalize_text(str2)

    if s1 == s2:
        return 1.0
    if len(s1) == 0 or len(s2) == 0:
        return 0.0

    # Token-based similarity (Jaccard index)
    tokens1 = {t for t in s1.split() if len(t) > 2}
    tokens2 = {t for t in s2.split() if len(t) > 2}

    if len(tokens1) == 0 or len(tokens2) == 0:
        # Fall back to character-based similarity
        max_len = max(len(s1), len(s2))
        distance = levenshtein_distance(s1, s2)
        return 1.0 - (distance / max_len)

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    jaccard_similarity = len(intersection) / len(union)

    # Also calculate substring containment bonus
    containment_bonus = 0.0
    if s1 in s2 or s2 in s1:
        containment_bonus = 0.2

    # Calculate Levenshtein-based similarity for shorter strings
    levenshtein_similarity = 0.0
    if len(s1) < 100 and len(s2) < 100:
        max_len = max(len(s1), len(s2))
        distance = levenshtein_distance(s1, s2)
        levenshtein_similarity = 1.0 - (distance / max_len)

    # Combine scores with weights
    combined_score = (jaccard_similarity * 0.6) + (levenshtein_similarity * 0.3) + containment_bonus

    return min(1.0, combined_score)


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
) -> list[dict[str, Any]]:
    """Find similar descriptions in the indexed items.

    Scores against both ``description`` and ``fullDescription`` fields,
    taking the higher score.

    Args:
        query: The description to search for.
        items: Array of indexed BoQ items (dicts).
        threshold: Minimum similarity score to include (0-1).
        max_results: Maximum number of results to return.
        include_exact: Whether to prioritize exact matches.

    Returns:
        Matched items with ``similarity`` and ``matchedQuery`` keys added.
    """
    if not query or not items:
        return []

    normalized_query = normalize_text(query)

    # Score all items - check both description and fullDescription (parent context)
    scored: list[dict[str, Any]] = []
    for item in items:
        description = item.get("description", "")
        desc_similarity = calculate_similarity(normalized_query, description)

        # Also score against fullDescription if available (includes parent context)
        full_desc_similarity = 0.0
        full_description = item.get("fullDescription", "")
        if full_description and full_description != description:
            full_desc_similarity = calculate_similarity(normalized_query, full_description)

        # Use the higher score
        similarity = max(desc_similarity, full_desc_similarity)

        scored.append({
            **item,
            "similarity": similarity,
            "matchedQuery": query,
        })

    # Filter by threshold and sort by similarity (descending)
    filtered = sorted(
        [s for s in scored if s["similarity"] >= threshold],
        key=lambda x: x["similarity"],
        reverse=True,
    )

    # If include_exact, prioritize exact matches
    # Single pass instead of two filter() calls with repeated normalize_text()
    if include_exact:
        exact_matches: list[dict[str, Any]] = []
        other_matches: list[dict[str, Any]] = []

        for item in filtered:
            normalized_desc = normalize_text(item.get("description", ""))
            if normalized_desc == normalized_query:
                exact_matches.append(item)
            else:
                other_matches.append(item)

        return (exact_matches + other_matches)[:max_results]

    return filtered[:max_results]


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
