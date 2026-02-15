from __future__ import annotations

from app.services.boq_matcher import (
    calculate_match_stats,
    calculate_quantity_comparison,
    find_similar_descriptions,
    normalize_text,
)


def test_normalize_text_croatian():
    result = normalize_text("Betoniranje šljunkom č ć ž đ")
    assert "š" in result
    assert "č" in result
    assert "ć" in result
    assert "ž" in result
    assert "đ" in result
    assert result == "betoniranje šljunkom č ć ž đ"


def test_normalize_text_strips_special():
    result = normalize_text("Price: 100,00 EUR!")
    assert ":" not in result
    assert "!" not in result


def test_find_similar_descriptions():
    items = [
        {"description": "podložni beton C12/15", "unitPrice": 45},
        {"description": "armiranobetonska ploča", "unitPrice": 120},
        {"description": "podložni beton C15/20", "unitPrice": 50},
        {"description": "čelična konstrukcija", "unitPrice": 200},
    ]
    matches = find_similar_descriptions("podložni beton", items, threshold=0.3)
    assert len(matches) >= 2
    assert matches[0]["description"] in ("podložni beton C12/15", "podložni beton C15/20")


def test_calculate_match_stats():
    matches = [
        {"unitPrice": "10.00"},
        {"unitPrice": "20.00"},
        {"unitPrice": "30.00"},
    ]
    stats = calculate_match_stats(matches)
    assert stats["count"] == 3
    assert stats["avgPrice"] == 20.0
    assert stats["minPrice"] == 10.0
    assert stats["maxPrice"] == 30.0


def test_quantity_comparison_same():
    result = calculate_quantity_comparison(100, 105)
    assert result["color"] == "green"
    assert result["hasData"] is True


def test_quantity_comparison_amber():
    result = calculate_quantity_comparison(100, 180)
    assert result["color"] == "amber"


def test_quantity_comparison_red():
    result = calculate_quantity_comparison(10, 100)
    assert result["color"] == "red"


def test_quantity_comparison_missing():
    result = calculate_quantity_comparison(0, 0)
    assert result["hasData"] is False
