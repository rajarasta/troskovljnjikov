"""Item extraction from worksheets and project name detection."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional

from openpyxl.worksheet.worksheet import Worksheet

from app.services.boq_hierarchy import build_hierarchy, classify_item_type, group_into_units

from .column_detection import (
    detect_column_offset,
    find_best_header_row,
    infer_columns_from_data,
)


def sheet_to_array(ws: Worksheet) -> list[list[Any]]:
    """Convert an openpyxl worksheet to a 2D list of cell values.

    Reads up to column U (index 21) to match the JS cap of ``Math.min(range.e.c, 20)``.
    """
    rows: list[list[Any]] = []
    for row_tuple in ws.iter_rows(min_row=1, max_col=21, values_only=True):
        rows.append([cell if cell is not None else "" for cell in row_tuple])
    return rows


def extract_project_name(file_name: str, rows: list[list[Any]]) -> str:
    """Extract a project name from the filename or the first few rows."""
    name = re.sub(r"\.(xlsx?|csv|json)$", "", file_name, flags=re.IGNORECASE)
    name = re.sub(r"[-_]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    if re.match(r"^\d+$", name) or len(name) < 5:
        if rows and rows[0] and rows[0][0]:
            first_cell = str(rows[0][0])
            if len(first_cell) > 5:
                return first_cell[:100]

    return name


def extract_items_from_sheet(
    ws: Worksheet,
    file_name: str,
    file_path: str,
    sheet_name: str,
    file_date: Optional[datetime] = None,
    external_mapping: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Extract BoQ items from a worksheet.

    Returns ``{"items": [...], "units": [...], "columnMap": ..., "dataStartRow": ...}``
    """
    rows = sheet_to_array(ws)
    if len(rows) < 2:
        return {"items": [], "units": []}

    column_map: dict[str, int]
    data_start_row: int
    skip_patterns: list[str] = []

    if external_mapping:
        column_map = external_mapping["columns"]
        data_start_row = external_mapping.get("dataStartRow", 0)
        skip_patterns = external_mapping.get("skipPatterns", [])
    else:
        header_row_index, detected_map, match_count = find_best_header_row(rows)

        if match_count >= 3:
            column_map = detected_map
            data_start_row = header_row_index + 1

            # If partial header, try to fill missing columns from data patterns
            if column_map.get("unit") is None or column_map.get("quantity") is None:
                inferred = infer_columns_from_data(rows)
                if inferred:
                    inferred_map = inferred["columnMap"]
                    if column_map.get("unit") is None and inferred_map.get("unit") is not None:
                        column_map["unit"] = inferred_map["unit"]
                    if column_map.get("quantity") is None and inferred_map.get("quantity") is not None:
                        column_map["quantity"] = inferred_map["quantity"]
                    if column_map.get("unitPrice") is None and inferred_map.get("unitPrice") is not None:
                        column_map["unitPrice"] = inferred_map["unitPrice"]
                    if column_map.get("total") is None and inferred_map.get("total") is not None:
                        column_map["total"] = inferred_map["total"]
        else:
            inferred = infer_columns_from_data(rows)
            if inferred:
                column_map = inferred["columnMap"]
                data_start_row = inferred["dataStartRow"]
            else:
                offset = detect_column_offset(rows, 0)
                if offset > 0:
                    shifted_rows = [r[offset:] if r else r for r in rows]
                    shifted_row_idx, shifted_map, shifted_count = find_best_header_row(shifted_rows)

                    if shifted_count >= 3:
                        column_map = {
                            key: val + offset
                            for key, val in shifted_map.items()
                        }
                        data_start_row = shifted_row_idx + 1
                    else:
                        column_map = {
                            "itemNumber": 0 + offset,
                            "description": 1 + offset,
                            "unit": 2 + offset,
                            "quantity": 3 + offset,
                            "unitPrice": 4 + offset,
                            "total": 5 + offset,
                        }
                        data_start_row = 1
                else:
                    column_map = {
                        "itemNumber": 0,
                        "description": 1,
                        "unit": 2,
                        "quantity": 3,
                        "unitPrice": 4,
                        "total": 5,
                    }
                    data_start_row = 1

    # Handle dual-description columns: merge descriptionLong into description
    has_long_desc = "descriptionLong" in column_map

    if has_long_desc:
        desc_col = column_map["description"]
        long_col = column_map["descriptionLong"]
        for row in rows:
            if not row:
                continue
            short_desc = str(row[desc_col] if desc_col < len(row) else "").strip()
            long_desc = str(row[long_col] if long_col < len(row) else "").strip()
            if long_desc and short_desc:
                row[desc_col] = short_desc + " \u2014 " + long_desc
            elif long_desc and not short_desc:
                row[desc_col] = long_desc
        del column_map["descriptionLong"]

    project_name = extract_project_name(file_name, rows)

    # Use hierarchy-aware extraction
    hierarchy_items = build_hierarchy(rows, column_map, data_start_row, skip_patterns)

    # Group items into BoQ units
    boq_units = group_into_units(hierarchy_items, rows, column_map, file_path, sheet_name)

    # Build unit parent numbers set for item type classification
    unit_parent_numbers = {u.get("parentItemNumber", "") for u in boq_units}

    # Build row -> unit_id lookup
    row_to_unit_id: dict[int, str] = {}
    for unit in boq_units:
        for item_id in unit.get("itemIds", []):
            parts = item_id.rsplit(":", 1)
            if len(parts) == 2:
                try:
                    row_num = int(parts[-1])
                    row_to_unit_id[row_num] = unit["id"]
                except ValueError:
                    pass

    date_str: str | None = None
    if file_date:
        date_str = file_date.strftime("%Y-%m-%d")

    items: list[dict[str, Any]] = []
    for hi in hierarchy_items:
        # Skip pure parent headers with no data
        if hi.get("isParent") and not hi.get("quantity") and not hi.get("unitPrice") and not hi.get("total"):
            continue

        item: dict[str, Any] = {
            "id": f"{file_path}:{sheet_name}:{hi['row']}",
            "fileId": file_path,
            "fileName": file_name,
            "filePath": file_path,
            "sheetName": sheet_name,
            "row": hi["row"],
            "itemNumber": hi.get("itemNumber"),
            "description": hi.get("description", ""),
            "fullDescription": hi.get("fullDescription"),
            "parentItemNumber": hi.get("parentItemNumber"),
            "unit": hi.get("unit"),
            "quantity": hi.get("quantity"),
            "unitPrice": hi.get("unitPrice"),
            "total": hi.get("total"),
            "_missingPrice": "unitPrice" in column_map and not hi.get("unitPrice"),
            "_missingQuantity": "quantity" in column_map and not hi.get("quantity"),
            "_missingUnit": "unit" in column_map and not hi.get("unit"),
            "unitId": row_to_unit_id.get(hi["row"]),
            "projectName": project_name,
            "date": date_str,
            "itemType": classify_item_type(hi, unit_parent_numbers),
        }

        description = item.get("description", "") or ""
        full_description = item.get("fullDescription", "") or ""
        if len(description) >= 3 or len(full_description) >= 3:
            items.append(item)

    return {
        "items": items,
        "units": boq_units,
        "columnMap": column_map,
        "dataStartRow": data_start_row,
    }
