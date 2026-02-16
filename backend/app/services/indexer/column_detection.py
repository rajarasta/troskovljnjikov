"""Column detection logic for BoQ spreadsheet headers."""

from __future__ import annotations

from typing import Any

from .constants import (
    COLUMN_PATTERNS,
    KAUFLAND_CODE_RE,
    KNOWN_UNITS,
    MAX_HEADER_SEARCH_ROWS,
)


def detect_columns(header_row: list[Any]) -> tuple[dict[str, int], int]:
    """Detect column indices from a header row.

    Returns a tuple of (column_map, match_count).
    """
    column_map: dict[str, int] = {}
    match_count = 0
    used_columns: set[int] = set()

    normalized_headers = [
        {"index": i, "value": str(h or "").lower().strip()}
        for i, h in enumerate(header_row)
    ]

    for column_type, patterns in COLUMN_PATTERNS.items():
        if column_type in column_map:
            continue
        for header in normalized_headers:
            if column_type in column_map:
                break
            if not header["value"]:
                continue
            if header["index"] in used_columns:
                continue
            for pattern in patterns:
                if pattern in header["value"]:
                    column_map[column_type] = header["index"]
                    used_columns.add(header["index"])
                    match_count += 1
                    break

    return column_map, match_count


def find_best_header_row(rows: list[list[Any]]) -> tuple[int, dict[str, int], int]:
    """Search multiple rows for the best header row (most column pattern matches).

    Returns (header_row_index, column_map, match_count).
    """
    best_row = -1
    best_map: dict[str, int] = {}
    best_count = 0

    max_row = min(len(rows), MAX_HEADER_SEARCH_ROWS)
    for r in range(max_row):
        row = rows[r]
        if not row:
            continue
        col_map, match_count = detect_columns(row)
        if match_count > best_count:
            best_count = match_count
            best_map = col_map
            best_row = r

    return best_row, best_map, best_count


def detect_column_offset(rows: list[list[Any]], start_row: int) -> int:
    """Detect if column 0 is consistently empty (columns shifted right).

    Returns column offset (0 = no shift, 1 = shifted by 1).
    """
    empty_col0 = 0
    non_empty_col0 = 0
    check_count = min(20, len(rows) - start_row)

    for r in range(start_row, min(start_row + check_count, len(rows))):
        row = rows[r]
        if not row:
            continue
        val = str(row[0] if row[0] is not None else "").strip()
        if val == "":
            empty_col0 += 1
        else:
            non_empty_col0 += 1

    total = empty_col0 + non_empty_col0
    if total == 0:
        return 0

    if (empty_col0 > 0 and non_empty_col0 == 0) or (empty_col0 / total > 0.8):
        return 1
    return 0


def infer_columns_from_data(rows: list[list[Any]]) -> dict[str, Any] | None:
    """Try to infer column layout from data patterns when no header is found.

    Returns {"columnMap": dict, "dataStartRow": int} or None.
    """
    code_count = 0
    check_rows = min(15, len(rows))
    for r in range(check_rows):
        row = rows[r] if r < len(rows) else None
        val = str((row[0] if row and len(row) > 0 else None) or "").strip()
        if KAUFLAND_CODE_RE.match(val):
            code_count += 1

    if code_count < 3:
        return None

    # Kaufland format detected. Find the unit column by scanning data.
    col_count = max(
        (len(r) if r else 0) for r in rows[:check_rows]
    ) if check_rows > 0 else 0

    unit_scores = [0] * col_count

    for r in range(check_rows):
        row = rows[r] if r < len(rows) else None
        if not row:
            continue
        for c in range(3, min(len(row), col_count)):
            val = str(row[c] if row[c] is not None else "").lower().strip()
            if val in KNOWN_UNITS:
                unit_scores[c] += 1

    if not unit_scores:
        return None

    max_score = max(unit_scores)
    unit_col = unit_scores.index(max_score)

    if unit_col < 3 or unit_scores[unit_col] == 0:
        # Can't find unit column, use Kaufland default layout
        return {
            "columnMap": {
                "itemNumber": 0,
                "description": 2,
                "descriptionLong": 3,
                "unit": 5,
                "quantity": 4,
                "unitPrice": 6,
                "total": 7,
            },
            "dataStartRow": 0,
        }

    # Unit column found. Infer surrounding columns.
    column_map: dict[str, int | None] = {
        "itemNumber": 0,
        "description": 2,
        "descriptionLong": 3,
        "quantity": unit_col - 1,
        "unit": unit_col,
        "unitPrice": unit_col + 1,
        "total": unit_col + 2 if unit_col + 2 < col_count else None,
    }

    # Remove None values to match JS behavior (undefined keys not present)
    column_map_clean: dict[str, int] = {
        k: v for k, v in column_map.items() if v is not None
    }

    return {
        "columnMap": column_map_clean,
        "dataStartRow": 0,
    }
