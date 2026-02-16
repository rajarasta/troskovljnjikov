from __future__ import annotations

from datetime import datetime

import pytest

from app.services.indexer import index_file, detect_columns, find_best_header_row


def test_detect_columns_croatian_headers():
    header = ["R.BR", "OPIS", "JED", "KOL", "JED.CIJ", "UKUPNO"]
    col_map, count = detect_columns(header)
    assert count >= 4
    assert "description" in col_map
    assert "unit" in col_map


def test_detect_columns_english_headers():
    header = ["No.", "Description", "Unit", "Quantity", "Price", "Total"]
    col_map, count = detect_columns(header)
    assert count >= 4


def test_find_best_header_row():
    rows = [
        ["", "", "", "", "", ""],  # empty
        ["Projekt:", "Test project", "", "", "", ""],  # metadata
        ["R.BR", "OPIS STAVKE", "JED", "KOLIČINA", "JED.CIJENA", "UKUPNO"],  # header
        ["1.", "Betonski radovi", "m³", "10", "50.00", "500.00"],  # data
    ]
    idx, col_map, count = find_best_header_row(rows)
    assert idx == 2
    assert count >= 4


def test_index_file_real(sample_xlsx_bytes):
    result = index_file("test.xlsx", sample_xlsx_bytes, datetime.now())
    assert result["success"] is True
    assert result["file"]["itemCount"] > 0
    assert len(result["items"]) > 0

    # Check items have expected fields
    item = result["items"][0]
    assert "description" in item
    assert "row" in item
    assert len(item["description"]) >= 3


def test_index_file_extracts_units(sample_xlsx_bytes):
    result = index_file("test.xlsx", sample_xlsx_bytes, datetime.now())
    # Eurospin_SO_Soboslikarski has hierarchical items with units
    if result["units"]:
        unit = result["units"][0]
        assert "parentItemNumber" in unit
        assert "itemIds" in unit
        assert len(unit["itemIds"]) > 0


def test_index_file_extracts_prices(sample_xlsx_bytes):
    result = index_file("test.xlsx", sample_xlsx_bytes, datetime.now())
    priced = [i for i in result["items"] if i.get("unitPrice", 0) > 0]
    assert len(priced) > 0, "Should find items with prices"


def test_index_file_invalid_bytes():
    result = index_file("bad.xlsx", b"not an xlsx file", datetime.now())
    assert result["success"] is False
    assert "error" in result
