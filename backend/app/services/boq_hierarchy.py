"""
BoQ Hierarchy Detection - Detects parent-child relationships in BoQ spreadsheets.

Handles two common patterns in Croatian construction BoQs:
1. Multi-row descriptions: Parent item description spans several rows
2. Parent + sub-items: e.g., 3.3.4 (parent) -> 3.3.4.a, 3.3.4.b (sub-items)
"""

from __future__ import annotations

import re
from typing import Any


def parse_number(value: Any) -> float:
    """Parse a number from various formats (handles Croatian comma-decimal: '1,52' -> 1.52).

    Mimics JS parseFloat behavior: parses from the start and stops at the first
    character that cannot be part of a float (e.g. a second decimal point).
    JS String.replace(',', '.') only replaces the first comma, so we do the same.
    """
    if isinstance(value, (int, float)):
        return float(value)
    if not value:
        return 0.0
    s = re.sub(r'[^\d.,-]', '', str(value)).replace(',', '.', 1)
    # Emulate JS parseFloat: extract the longest valid float prefix
    m = re.match(r'^[+-]?(\d+\.?\d*|\.\d+)', s)
    if not m:
        return 0.0
    return float(m.group(0))


def is_position_number(text: str | None) -> bool:
    """
    Detect if text looks like a BoQ position/item number.

    Matches: 1., 1.1, 1.1.1, 3.3.4.a, A.1, IV., etc.
    """
    if not text:
        return False
    trimmed = str(text).strip()
    if len(trimmed) == 0 or len(trimmed) > 20:
        return False

    # Common BoQ position patterns:
    # "1." "1.1" "1.1.1" "1.1.1.1" "3.3.4.a" "3.3.4.b"
    # "A.1" "B.2.3"
    # "IV." "III.1"
    if re.match(r'^[A-Za-z0-9]{1,4}(\.[A-Za-z0-9]{1,4}){0,5}\.?$', trimmed):
        return True

    # Kaufland/Tribe code patterns: "201", "201.010", "201.010.00100", "309.020.00115"
    if re.match(r'^\d{3}(\.\d{3}(\.\d{5})?)?$', trimmed):
        return True

    return False


def normalize_position(position: str | None) -> str:
    """Normalize a position number for comparison (strip trailing dot, lowercase)."""
    if not position:
        return ''
    return re.sub(r'\.$', '', str(position).strip()).lower()


def get_parent_position(position: str | None) -> str:
    """
    Get the parent position by stripping the last segment.

    "3.3.4.a" -> "3.3.4", "3.3.4" -> "3.3", "1" -> ""
    """
    normalized = normalize_position(position)
    last_dot = normalized.rfind('.')
    if last_dot == -1:
        return ''
    return normalized[:last_dot]


def is_sub_position(child_pos: str | None, parent_pos: str | None) -> bool:
    """
    Check if child_pos is a direct or indirect sub-position of parent_pos.

    "3.3.4.a" is sub of "3.3.4" -> True
    "3.3.4.a" is sub of "3.3"   -> True
    "3.3.4"   is sub of "3.3.5" -> False
    """
    child = normalize_position(child_pos)
    parent = normalize_position(parent_pos)
    if not child or not parent or child == parent:
        return False
    # Child must start with parent followed by a dot
    return child.startswith(parent + '.')


def is_continuation_row(row: list[Any], column_map: dict[str, int]) -> bool:
    """
    Check if a row is a continuation row (part of a multi-row description).

    A continuation row has description text but NO position number, NO unit,
    NO quantity, NO price.
    """
    # Must have description text
    desc = str(row[column_map['description']] if column_map['description'] < len(row) else '').strip()
    if len(desc) < 3:
        return False

    # Must NOT have a position number
    if 'itemNumber' in column_map:
        pos = str(row[column_map['itemNumber']] if column_map['itemNumber'] < len(row) else '').strip()
        if pos and is_position_number(pos):
            return False
        # Also reject if it has any non-empty value in the position column
        if len(pos) > 0:
            return False

    # Must NOT have unit
    if 'unit' in column_map:
        unit = str(row[column_map['unit']] if column_map['unit'] < len(row) else '').strip()
        if len(unit) > 0:
            return False

    # Must NOT have quantity
    if 'quantity' in column_map:
        qty = parse_number(row[column_map['quantity']] if column_map['quantity'] < len(row) else None)
        if qty != 0:
            return False

    # Must NOT have unit price
    if 'unitPrice' in column_map:
        price = parse_number(row[column_map['unitPrice']] if column_map['unitPrice'] < len(row) else None)
        if price != 0:
            return False

    # Must NOT have total
    if 'total' in column_map:
        total = parse_number(row[column_map['total']] if column_map['total'] < len(row) else None)
        if total != 0:
            return False

    return True


def _is_parent_header_row(row: list[Any], column_map: dict[str, int]) -> bool:
    """
    Check if a row is a section/group header (has position but no data).

    These are parent items that provide context for sub-items below them.
    """
    # Must have a position number
    if 'itemNumber' not in column_map:
        return False
    pos = str(row[column_map['itemNumber']] if column_map['itemNumber'] < len(row) else '').strip()
    if not pos or not is_position_number(pos):
        return False

    # Must have description
    desc = str(row[column_map['description']] if column_map['description'] < len(row) else '').strip()
    if len(desc) < 3:
        return False

    # Must NOT have quantity (or quantity is 0)
    has_quantity = (
        'quantity' in column_map
        and parse_number(row[column_map['quantity']] if column_map['quantity'] < len(row) else None) != 0
    )

    # Must NOT have unit price (or price is 0)
    has_price = (
        'unitPrice' in column_map
        and parse_number(row[column_map['unitPrice']] if column_map['unitPrice'] < len(row) else None) != 0
    )

    # Parent headers have neither quantity nor price
    return not has_quantity and not has_price


def merge_descriptions(descriptions: list[str]) -> str:
    """Merge an array of description strings into one."""
    parts = [str(d).strip() for d in descriptions]
    joined = ' '.join(p for p in parts if len(p) > 0)
    return re.sub(r'\s+', ' ', joined).strip()


def _safe_cell(row: list[Any], idx: int | None) -> Any:
    """Safely get a cell value from a row, returning '' if out of bounds or None."""
    if idx is None or idx >= len(row):
        return ''
    val = row[idx]
    return val if val is not None else ''


def build_hierarchy(
    rows: list[list[Any]],
    column_map: dict[str, int],
    data_start_row: int,
    skip_patterns: list[str] | None = None,
) -> list[dict]:
    """
    Build hierarchy from spreadsheet rows, detecting parent-child relationships
    and merging multi-row descriptions.

    Returns a flat list of items, each enriched with fullDescription (parent context).

    Args:
        rows: 2D list of cell values.
        column_map: Column index mapping
            { "itemNumber", "description", "unit", "quantity", "unitPrice", "total" }.
        data_start_row: First row with data (0-based index into rows list).
        skip_patterns: Patterns to skip (e.g., ["UKUPNO", "TOTAL"]).

    Returns:
        Items with hierarchy info.
    """
    if skip_patterns is None:
        skip_patterns = []

    items: list[dict] = []

    # Track current context: stack of parent items by depth
    # parent_stack[0] = top-level section, parent_stack[1] = sub-section, etc.
    parent_stack: list[dict] = []

    # Track accumulated continuation descriptions for the current item
    current_item_row: int | None = None
    continuation_descs: list[str] = []

    def flush_current_item() -> None:
        nonlocal current_item_row, continuation_descs

        if current_item_row is None:
            return

        row = rows[current_item_row]
        pos = (
            normalize_position(str(_safe_cell(row, column_map.get('itemNumber'))))
            if 'itemNumber' in column_map
            else ''
        )
        desc = str(_safe_cell(row, column_map.get('description'))).strip()

        # Build the full description with continuations
        own_full_desc = merge_descriptions([desc, *continuation_descs])

        # Find parent context from the stack
        parent_context = ''
        parent_item_number = ''
        if pos and len(parent_stack) > 0:
            # Walk the stack to find the nearest ancestor
            for k in range(len(parent_stack) - 1, -1, -1):
                if is_sub_position(pos, parent_stack[k]['position']):
                    parent_context = parent_stack[k]['fullDescription']
                    parent_item_number = parent_stack[k]['position']
                    break

        full_description = (
            merge_descriptions([parent_context, own_full_desc])
            if parent_context
            else own_full_desc
        )

        item: dict = {
            'row': current_item_row,
            'itemNumber': pos,
            'description': desc,
            'ownFullDescription': own_full_desc,
            'fullDescription': full_description,
            'parentItemNumber': parent_item_number if parent_item_number else None,
            'unit': str(_safe_cell(row, column_map.get('unit'))).strip() if 'unit' in column_map else '',
            'quantity': parse_number(_safe_cell(row, column_map.get('quantity'))) if 'quantity' in column_map else 0,
            'unitPrice': parse_number(_safe_cell(row, column_map.get('unitPrice'))) if 'unitPrice' in column_map else 0,
            'total': parse_number(_safe_cell(row, column_map.get('total'))) if 'total' in column_map else 0,
            'isParent': _is_parent_header_row(row, column_map),
        }
        items.append(item)

        # If this was a parent header, push it onto the stack for child context
        if _is_parent_header_row(row, column_map) and pos:
            # Pop any parents at same or deeper level
            while len(parent_stack) > 0 and not is_sub_position(pos, parent_stack[-1]['position']):
                # Check if current position is at same level or shallower
                stack_pos = parent_stack[-1]['position']
                if is_sub_position(pos, stack_pos):
                    break
                parent_stack.pop()
            parent_stack.append({
                'position': pos,
                'description': desc,
                'fullDescription': own_full_desc,
            })

        current_item_row = None
        continuation_descs = []

    for r in range(data_start_row, len(rows)):
        row = rows[r]
        if not row:
            continue

        # Check skip patterns
        if len(skip_patterns) > 0:
            row_text = ' '.join(str(c) if c else '' for c in row).upper()
            if any(p.upper() in row_text for p in skip_patterns):
                flush_current_item()
                continue

        desc = str(_safe_cell(row, column_map.get('description'))).strip()

        # Skip completely empty rows
        if len(desc) == 0 and (
            'itemNumber' not in column_map
            or not str(_safe_cell(row, column_map.get('itemNumber'))).strip()
        ):
            flush_current_item()
            continue

        # Check if this is a continuation row
        if is_continuation_row(row, column_map):
            if current_item_row is not None:
                # Append to current item's description
                continuation_descs.append(desc)
            # If no current item, this is an orphan continuation - skip it
            continue

        # This is a new item (has position or has data)
        flush_current_item()

        # Check if the description is meaningful enough
        if len(desc) < 3:
            # Skip rows with no meaningful description
            # But check if it's just a position number row with description coming as continuations
            pos = (
                str(_safe_cell(row, column_map.get('itemNumber'))).strip()
                if 'itemNumber' in column_map
                else ''
            )
            if pos and is_position_number(pos):
                current_item_row = r
                continue
            continue

        # Check if description is just a number
        if re.match(r'^\d+$', desc):
            continue

        # Check if it looks like a section header (all caps, short text, no numbers)
        if len(desc) < 30 and desc == desc.upper() and not re.search(r'\d', desc):
            continue

        current_item_row = r

    # Flush the last item
    flush_current_item()

    return items


# Keywords that indicate a subtotal row in Croatian construction BoQs
SUBTOTAL_KEYWORDS = ['UKUPNO', 'SVEGA', 'SVEUKUPNO', 'TOTAL']


def is_subtotal_row(row: list[Any], column_map: dict[str, int]) -> dict:
    """
    Check if a row is a subtotal row based on keyword detection.

    Checks description, unit, quantity, unitPrice columns for subtotal keywords.

    Returns:
        dict with keys 'isSubtotal' (bool) and 'total' (float).
    """
    # Check multiple columns for subtotal keywords
    # UKUPNO can appear in various columns depending on the BoQ format
    check_keys = ['description', 'unit', 'quantity', 'unitPrice']
    check_indices = [column_map[k] for k in check_keys if k in column_map]

    for col_idx in check_indices:
        value = str(_safe_cell(row, col_idx)).upper().strip()
        if any(kw in value for kw in SUBTOTAL_KEYWORDS):
            # Extract total value from the total column
            total = parse_number(_safe_cell(row, column_map.get('total'))) if 'total' in column_map else 0.0
            return {'isSubtotal': True, 'total': total}

    return {'isSubtotal': False, 'total': 0.0}


def classify_item_type(
    item: dict[str, Any],
    unit_parent_numbers: set[str],
) -> str:
    """Classify a hierarchy item into one of the BoQ item types.

    Args:
        item: A dict from build_hierarchy() output.
        unit_parent_numbers: Set of parentItemNumber values from group_into_units().

    Returns:
        One of: "section_header", "composite_sub", "ne_nudimo", "simple".
    """
    if item.get("isParent"):
        return "section_header"

    parent_num = item.get("parentItemNumber")
    if parent_num and parent_num in unit_parent_numbers:
        return "composite_sub"

    unit_price = item.get("unitPrice", 0) or 0
    total = item.get("total", 0) or 0
    desc = item.get("description", "")
    if unit_price == 0 and total == 0 and len(desc) >= 3:
        return "ne_nudimo"

    return "simple"


def group_into_units(
    hierarchy_items: list[dict],
    rows: list[list[Any]],
    column_map: dict[str, int],
    file_id: str,
    sheet_name: str,
) -> list[dict]:
    """
    Group hierarchy items into BoQ units (contextual groups).

    A BoQ unit = parent header + continuation rows + sub-items + optional subtotal.

    Args:
        hierarchy_items: Output from build_hierarchy().
        rows: Original 2D spreadsheet rows.
        column_map: Column index mapping.
        file_id: File path for generating unit IDs.
        sheet_name: Sheet name for generating unit IDs.

    Returns:
        List of BoQUnit dicts.
    """
    units: list[dict] = []

    # Build a map from row number to hierarchy item for quick lookup
    item_by_row: dict[int, dict] = {}
    for item in hierarchy_items:
        item_by_row[item['row']] = item

    # Track which items have been assigned to a unit
    assigned_items: set[int] = set()

    # Walk through hierarchy items looking for parent headers
    for i, item in enumerate(hierarchy_items):
        # Skip if already assigned to a unit
        if item['row'] in assigned_items:
            continue

        # Only start a unit from a parent header
        if not item['isParent'] or not item['itemNumber']:
            continue

        parent_pos = item['itemNumber']
        unit_item_ids: list[str] = []
        last_sub_item_row = item['row']

        # Collect sub-items that are direct/indirect children of this parent
        for j in range(i + 1, len(hierarchy_items)):
            candidate = hierarchy_items[j]

            # Stop if we hit another parent at the same or higher level
            if candidate['isParent'] and candidate['itemNumber']:
                # If this parent is NOT a sub-position of our parent, stop
                if not is_sub_position(candidate['itemNumber'], parent_pos):
                    break
                # If it IS a sub-position parent (nested), skip it but continue
                # (its children will still be collected since they're also sub-positions)
                continue

            # Check if this item is a sub-position of our parent
            if candidate['itemNumber'] and is_sub_position(candidate['itemNumber'], parent_pos):
                item_id = f"{file_id}:{sheet_name}:{candidate['row']}"
                unit_item_ids.append(item_id)
                assigned_items.add(candidate['row'])
                last_sub_item_row = candidate['row']
            elif not candidate['itemNumber']:
                # Items without position number right after sub-items might still belong
                # (e.g., continuation rows that build_hierarchy didn't merge)
                continue
            else:
                # Different position hierarchy - stop collecting
                break

        # Only create a unit if there are sub-items with data
        if len(unit_item_ids) == 0:
            continue

        # Scan for subtotal row after the last sub-item (within 3 rows)
        subtotal: float | None = None
        end_row = last_sub_item_row
        for r in range(last_sub_item_row + 1, min(last_sub_item_row + 4, len(rows))):
            row = rows[r]
            if not row:
                continue

            result = is_subtotal_row(row, column_map)
            if result['isSubtotal']:
                subtotal = result['total']
                end_row = r
                break

            # Stop if we hit a row with a position number (next section)
            if 'itemNumber' in column_map:
                pos = str(_safe_cell(row, column_map.get('itemNumber'))).strip()
                if pos and is_position_number(pos):
                    break

            # Stop at empty rows
            desc = str(_safe_cell(row, column_map.get('description'))).strip()
            has_any_data = len(desc) > 0 or (
                'total' in column_map
                and parse_number(_safe_cell(row, column_map.get('total'))) != 0
            )
            if not has_any_data:
                break

        units.append({
            'id': f"{file_id}:{sheet_name}:{parent_pos}",
            'fileId': file_id,
            'filePath': file_id,
            'sheetName': sheet_name,
            'parentItemNumber': parent_pos,
            'parentTitle': item['description'],
            'parentDescription': item.get('ownFullDescription') or item.get('fullDescription') or item['description'],
            'startRow': item['row'],
            'endRow': end_row,
            'itemIds': unit_item_ids,
            'subtotal': subtotal,
            'itemCount': len(unit_item_ids),
        })

    return units
