"""Backward-compatibility shim — all logic moved to app.services.indexer."""

from app.services.indexer import (  # noqa: F401
    detect_columns,
    find_best_header_row,
    index_file,
    index_folder,
    resolve_file_date,
)
