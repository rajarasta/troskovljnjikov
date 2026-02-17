"""Lookup agent - resolves synthetic cell IDs to virtual BoQ items for price search."""
from __future__ import annotations

import logging
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.models.boq import BoQItem

logger = logging.getLogger(__name__)


def is_synthetic_item_id(item_id: str) -> bool:
    """Check if item_id is a synthetic cell reference like excel-cell-ROW-COL-TIMESTAMP."""
    return item_id.startswith("excel-cell-")


def parse_synthetic_item_id(item_id: str) -> Optional[dict]:
    """Parse synthetic item ID to extract row, col, timestamp.

    Format: excel-cell-ROW-COL-TIMESTAMP
    Example: excel-cell-66-1-1771297459634
    """
    if not is_synthetic_item_id(item_id):
        return None

    match = re.match(r"excel-cell-(\d+)-(\d+)-(\d+)", item_id)
    if not match:
        return None

    return {
        "row": int(match.group(1)),
        "col": int(match.group(2)),
        "timestamp": int(match.group(3)),
    }


def resolve_synthetic_item(
    item_id: str,
    description: str,
    file_id: str,
    db: Session,
) -> BoQItem:
    """Resolve a synthetic cell ID to a virtual BoQ item.

    Creates an in-memory BoQItem from the synthetic cell data.
    This item can be used for price search without hitting the database.

    Args:
        item_id: Synthetic item ID (excel-cell-ROW-COL-TIMESTAMP)
        description: Cell text/description from spreadsheet
        file_id: File ID the cell belongs to
        db: Database session (for context)

    Returns:
        A virtual BoQItem object (not saved to DB)
    """
    parsed = parse_synthetic_item_id(item_id)
    if not parsed:
        raise ValueError(f"Invalid synthetic item ID: {item_id}")

    # Create a virtual BoQ item in memory
    # This item exists only for the price search request
    virtual_item = BoQItem(
        id=item_id,  # Keep the synthetic ID as is
        file_id=file_id,
        sheet_name=None,
        row=parsed["row"],
        item_number=None,
        description=description,
        full_description=None,
        parent_item_number=None,
        unit=None,
        quantity=None,
        unit_price=None,
        total=None,
        project_name=None,
        date=None,
        item_type=None,
        material_price=None,
        labor_price=None,
        material_total=None,
        labor_total=None,
        notes=None,
        drawing_path=None,
        llm_response=None,
    )

    logger.info(
        "Resolved synthetic item: row=%d, col=%d, description=%s",
        parsed["row"],
        parsed["col"],
        description[:50] if description else "N/A",
    )

    return virtual_item
