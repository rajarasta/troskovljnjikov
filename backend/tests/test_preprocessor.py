"""Tests for text_preprocessor — Stage 1 of BoQ matching pipeline."""
from __future__ import annotations

from app.services.text_preprocessor import (
    extract_unit,
    normalize_units,
    preprocess,
    strip_hierarchical_code,
    tokenize,
)

# ── Part 1: Hierarchical Code Stripping ─────────────────────────────


def test_strip_dotted_code():
    assert strip_hierarchical_code("1.2.3. Podložni beton") == "Podložni beton"


def test_strip_kaufland_code():
    assert strip_hierarchical_code("201.010.00100 Betonski radovi") == "Betonski radovi"


def test_strip_trailing_dot():
    assert strip_hierarchical_code("3. Armiranobetonski radovi") == "Armiranobetonski radovi"


def test_strip_letter_code():
    assert strip_hierarchical_code("A.1.2 Fasadni radovi") == "Fasadni radovi"


def test_no_code():
    assert strip_hierarchical_code("Podložni beton C12/15") == "Podložni beton C12/15"


def test_code_only():
    assert strip_hierarchical_code("1.2.3.") == ""


def test_empty():
    assert strip_hierarchical_code("") == ""


# ── Part 2: Unit Normalization ───────────────────────────────────────


def test_normalize_m3_superscript():
    assert normalize_units("beton 10 m³") == "beton 10 m3"


def test_normalize_m2_superscript():
    assert normalize_units("podovi 50 m²") == "podovi 50 m2"


def test_normalize_kom():
    assert normalize_units("kom ventila") == "komad ventila"


def test_normalize_celicni():
    assert normalize_units("čel. profil") == "čelični profil"


def test_normalize_celicna_no_false_match():
    """Regression: 'čel' must NOT match inside 'čelična'."""
    assert normalize_units("čelična konstrukcija") == "čelična konstrukcija"


def test_normalize_multiple():
    assert normalize_units("5 m³ betona, 10 m² oplate") == "5 m3 betona, 10 m2 oplate"


def test_extract_unit_superscript():
    assert extract_unit("m³") == "m3"


def test_extract_unit_abbrev():
    assert extract_unit("kom") == "komad"


def test_extract_unit_passthrough():
    assert extract_unit("kg") == "kg"


def test_extract_unit_none():
    assert extract_unit(None) == ""


# ── Part 3: Full Preprocess + Tokenize ───────────────────────────────


def test_preprocess_full():
    text = "1.2.3. Dobava i ugradnja podložnog betona C12/15, debljine  10 cm,  u  m³"
    result = preprocess(text)
    assert not result.startswith("1.2.3")
    assert "  " not in result
    assert "m3" in result
    assert result == result.lower()


def test_preprocess_multirow():
    text = "Dobava i ugradnja\n podložnog betona\n C12/15"
    result = preprocess(text)
    assert "\n" not in result
    assert "  " not in result


def test_preprocess_empty():
    assert preprocess("") == ""
    assert preprocess(None) == ""


def test_tokenize_basic():
    tokens = tokenize("podložni beton c12 15")
    assert "podložni" in tokens
    assert "beton" in tokens
    assert "c12" in tokens
    assert "15" in tokens


def test_tokenize_drops_short():
    tokens = tokenize("a i u beton")
    assert "a" not in tokens
    assert "i" not in tokens
    assert "u" not in tokens
    assert "beton" in tokens


def test_tokenize_empty():
    assert tokenize("") == []
    assert tokenize(None) == []
