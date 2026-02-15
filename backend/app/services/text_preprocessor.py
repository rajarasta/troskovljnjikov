"""Text preprocessing for BoQ matching pipeline (Stage 1).

Handles three concerns:
  1. Hierarchical code stripping  – remove leading position codes
     (dotted numeric, Kaufland-style, letter-prefixed)
  2. Unit normalization           – expand abbreviations and replace
     Unicode superscripts with ASCII equivalents
  3. Full preprocess + tokenize   – pipeline combining the above with
     whitespace collapse, lowering, and BM25-ready tokenization
"""
from __future__ import annotations

import re

# ── Part 1: Hierarchical Code Stripping ──────────────────────────────

# Kaufland-style: 201.010.00100
_KAUFLAND_CODE_RE = re.compile(r"^\d{3}\.\d{3}(?:\.\d{5})?\s+")
# Dotted hierarchical: 1., 1.2., 1.2.3., A.1.2, 3.3.4.a
# Must contain at least one dot to be recognized as a code.
_HIER_CODE_RE = re.compile(
    r"^[A-Za-z0-9]{1,4}(?:\.[A-Za-z0-9]{1,5})+\.?\s*"
    r"|"
    r"^[A-Za-z0-9]{1,4}\.\s*"
)


def strip_hierarchical_code(text: str) -> str:
    """Remove leading hierarchical position codes from text."""
    if not text:
        return ""
    result = text.strip()
    result = _KAUFLAND_CODE_RE.sub("", result)
    result = _HIER_CODE_RE.sub("", result)
    return result.strip()


# ── Part 2: Unit Normalization ───────────────────────────────────────

_UNIT_MAP: dict[str, str] = {
    "m³": "m3",
    "m²": "m2",
    "m¹": "m1",
    "kom": "komad",
    "kpl": "komplet",
    "pauš": "paušal",
    "pau": "paušal",
    "čel.": "čelični",
    "čel": "čelični",
    "arm.": "armiranobetonski",
    "bet.": "betonski",
    "lit": "l",
}

_UNIT_NORMALIZE: dict[str, str] = {
    "m³": "m3",
    "m²": "m2",
    "m¹": "m1",
    "kom": "komad",
    "komada": "komad",
    "pauš": "paušal",
    "pau": "paušal",
    "paušalno": "paušal",
    "kpl": "komplet",
    "lit": "l",
}


# Build a single regex from the unit map, matching longest keys first
# to avoid partial-match issues (e.g. "čel" matching inside "čelični").
# Pure-word keys get \b boundaries; keys with punctuation/superscripts don't.
_UNIT_RE = re.compile(
    "|".join(
        r"\b" + re.escape(k) + r"\b"
        if re.fullmatch(r"\w+", k, re.UNICODE)
        else re.escape(k)
        for k in sorted(_UNIT_MAP, key=len, reverse=True)
    )
)


def normalize_units(text: str) -> str:
    """Replace unit abbreviations and superscripts with normalized forms."""
    if not text:
        return ""
    return _UNIT_RE.sub(lambda m: _UNIT_MAP[m.group()], text)


def extract_unit(unit: str | None) -> str:
    """Normalize a standalone unit string for comparison."""
    if not unit:
        return ""
    u = unit.strip().lower()
    return _UNIT_NORMALIZE.get(u, u)


# ── Part 3: Full Preprocess + Tokenize ───────────────────────────────


def preprocess(text: str | None) -> str:
    """Full preprocessing pipeline for a BoQ description."""
    if not text:
        return ""
    result = strip_hierarchical_code(text)
    result = normalize_units(result)
    result = re.sub(r"\s+", " ", result).strip()
    result = result.lower()
    return result


def tokenize(text: str | None) -> list[str]:
    """Tokenize preprocessed text for BM25 indexing."""
    if not text:
        return []
    return [t for t in text.split() if len(t) >= 2]
