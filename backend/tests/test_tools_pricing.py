"""Tests for pricing tools (diff_historic)."""

from src.agent.tools.pricing import diff_historic


def test_diff_historic_exact_match():
    current = [
        {"item_number": "a.", "description": "Parna brana PE folija", "unit": "m²", "quantity": 200.0},
        {"item_number": "b.", "description": "Hidroizolacijska membrana", "unit": "m²", "quantity": 200.0},
    ]
    historic = [
        {"description": "Parna brana", "unit_of_measure": "m²", "quantity": 250.0, "unit_price": 12.50},
        {"description": "Hidroizolacijska membrana PVC", "unit_of_measure": "m²", "quantity": 250.0, "unit_price": 35.00},
    ]
    result = diff_historic(current, historic)
    assert len(result["matched_pairs"]) == 2
    assert len(result["unmatched_current"]) == 0
    assert len(result["unmatched_historic"]) == 0


def test_diff_historic_missing_and_extra():
    current = [
        {"item_number": "a.", "description": "Parna brana", "unit": "m²", "quantity": 200.0},
        {"item_number": "b.", "description": "Vertikalna izolacija", "unit": "m", "quantity": 50.0},
    ]
    historic = [
        {"description": "Parna brana", "unit_of_measure": "m²", "quantity": 250.0, "unit_price": 12.50},
        {"description": "Toplinska izolacija XPS", "unit_of_measure": "m²", "quantity": 250.0, "unit_price": 28.00},
    ]
    result = diff_historic(current, historic)
    assert len(result["matched_pairs"]) == 1  # parna brana matches
    assert len(result["unmatched_current"]) == 1  # vertikalna izolacija
    assert len(result["unmatched_historic"]) == 1  # toplinska izolacija


def test_diff_historic_price_delta():
    current = [
        {"item_number": "a.", "description": "Beton C40/50", "unit": "m³", "quantity": 100.0},
    ]
    historic = [
        {"description": "Beton C40/50", "unit_of_measure": "m³", "quantity": 120.0, "unit_price": 95.00},
    ]
    result = diff_historic(current, historic)
    pair = result["matched_pairs"][0]
    assert pair["historic_unit_price"] == 95.00
    assert pair["quantity_delta"] == -20.0  # current has 20 less


def test_diff_historic_empty_inputs():
    result = diff_historic([], [])
    assert result["matched_pairs"] == []
    assert result["unmatched_current"] == []
    assert result["unmatched_historic"] == []
