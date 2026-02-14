"""Row classification for Excel BoQ sheets."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from ..models.boq import RowType

# Patterns for item number hierarchy levels
_RE_CHAPTER = re.compile(r"^\d+\.$")                         # "3."
_RE_SECTION = re.compile(r"^\d+\.\d+\.$")                    # "3.1."
_RE_SUBSECTION = re.compile(r"^\d+\.\d+\.\d+\.$")            # "3.1.1."
_RE_WORK_ITEM = re.compile(r"^\d+\.\d+\.\d+\.\d+\.$")       # "3.1.1.1."
_RE_PRICED_LINE = re.compile(r"^\d+(\.\d+)*\.[a-z]\.$")      # "3.1.1.1.a."

# Also handle shallower hierarchies where work items are at level 3
_RE_WORK_ITEM_SHALLOW = re.compile(r"^\d+\.\d+\.$")          # "7.1." when no subsection


@dataclass
class ClassifiedRow:
    excel_row: int
    row_type: RowType
    item_number: str = ""
    text: str = ""
    unit: str = ""
    quantity: float = 0.0
    unit_price: Optional[float] = None
    total: Optional[float] = None


def classify_row(row: tuple, merged_ranges: list) -> ClassifiedRow:
    """Classify a single Excel row by its type."""
    excel_row = row[0].row
    col_a = _cell_str(row, 0)
    col_b = _cell_str(row, 1)
    col_c = _cell_str(row, 2) if len(row) > 2 else ""
    col_d = _cell_val(row, 3) if len(row) > 3 else None
    col_e = _cell_val(row, 4) if len(row) > 4 else None
    col_f = _cell_val(row, 5) if len(row) > 5 else None

    is_bold = _is_bold(row, 1)
    is_merged = _is_merged(row, 1, merged_ranges)

    # Empty row
    if not col_a and not col_b and col_c == "" and col_d is None:
        return ClassifiedRow(excel_row=excel_row, row_type=RowType.EMPTY)

    # Header row (contains "STAVKA", "JEDINICA MJERE", etc.)
    if col_b and any(kw in col_b.upper() for kw in ("STAVKA", "JEDINICA MJERE", "RB")):
        return ClassifiedRow(excel_row=excel_row, row_type=RowType.HEADER, text=col_b)

    # Check for subtotal rows (bold, has formula or "UKUPNO" in col E)
    if is_bold and col_f is not None and (
        (isinstance(col_f, str) and "SUM" in str(col_f).upper())
        or (col_e and "UKUPNO" in str(col_e).upper())
    ):
        return ClassifiedRow(
            excel_row=excel_row,
            row_type=RowType.SUBTOTAL,
            item_number=col_a,
            text=col_b,
        )

    # Chapter: "3.", bold, merged
    if col_a and _RE_CHAPTER.match(col_a) and is_bold:
        return ClassifiedRow(
            excel_row=excel_row, row_type=RowType.CHAPTER,
            item_number=col_a, text=col_b,
        )

    # Priced line: "3.1.1.1.a.", not bold, has unit in col C
    if col_a and _RE_PRICED_LINE.match(col_a) and col_c:
        return ClassifiedRow(
            excel_row=excel_row, row_type=RowType.PRICED_LINE,
            item_number=col_a, text=col_b,
            unit=col_c,
            quantity=_to_float(col_d),
            unit_price=_to_float(col_e) if col_e is not None else None,
            total=_to_float(col_f) if col_f is not None else None,
        )

    # Work item: "3.1.1.1.", bold, NOT merged, no data in C-F
    if col_a and _RE_WORK_ITEM.match(col_a) and is_bold and not col_c:
        return ClassifiedRow(
            excel_row=excel_row, row_type=RowType.WORK_ITEM,
            item_number=col_a, text=col_b,
        )

    # Subsection: "3.1.1.", bold, merged
    if col_a and _RE_SUBSECTION.match(col_a) and is_bold:
        return ClassifiedRow(
            excel_row=excel_row, row_type=RowType.SUBSECTION,
            item_number=col_a, text=col_b,
        )

    # Section: "3.1.", bold, merged
    if col_a and _RE_SECTION.match(col_a) and is_bold and is_merged:
        return ClassifiedRow(
            excel_row=excel_row, row_type=RowType.SECTION,
            item_number=col_a, text=col_b,
        )

    # Shallow work item: "7.1." bold, NOT merged, when it acts as a work item
    # (has priced lines like "7.1.a." following it)
    if col_a and _RE_SECTION.match(col_a) and is_bold and not is_merged and not col_c:
        return ClassifiedRow(
            excel_row=excel_row, row_type=RowType.WORK_ITEM,
            item_number=col_a, text=col_b,
        )

    # Description row: col A empty, col B has text, not bold
    if not col_a and col_b and not is_bold:
        return ClassifiedRow(
            excel_row=excel_row, row_type=RowType.DESCRIPTION, text=col_b,
        )

    # General notes: col A empty, col B bold with text
    if not col_a and col_b and is_bold:
        return ClassifiedRow(
            excel_row=excel_row, row_type=RowType.GENERAL_NOTES, text=col_b,
        )

    # Fallback: if col A has text, treat as description
    if col_b:
        return ClassifiedRow(
            excel_row=excel_row, row_type=RowType.DESCRIPTION, text=col_b,
        )

    return ClassifiedRow(excel_row=excel_row, row_type=RowType.EMPTY)


def _cell_str(row: tuple, idx: int) -> str:
    if idx >= len(row):
        return ""
    val = row[idx].value
    return str(val).strip() if val is not None else ""


def _cell_val(row: tuple, idx: int):
    if idx >= len(row):
        return None
    return row[idx].value


def _is_bold(row: tuple, idx: int) -> bool:
    if idx >= len(row):
        return False
    cell = row[idx]
    return bool(cell.font and cell.font.bold)


def _is_merged(row: tuple, idx: int, merged_ranges: list) -> bool:
    if idx >= len(row):
        return False
    cell = row[idx]
    for mr in merged_ranges:
        if cell.coordinate in mr:
            return True
    return False


def _to_float(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    try:
        cleaned = str(val).replace(",", ".").replace(" ", "")
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0
