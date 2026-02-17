"""Price Normalizer - deterministic currency, VAT, unit normalization and total computation.

All math is done here, not by the LLM. The agent decides *which* data to use;
this module computes the numbers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.price_extractor import PriceField


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class PricingRules:
    """Configuration for price computation."""
    vat_rate: float = 0.25  # Croatian PDV = 25%
    price_preference: str = "cheapest_delivered"  # "cheapest_delivered" | "cheapest_unit"
    include_shipping: bool = True
    include_vat: bool = True
    target_currency: str = "EUR"


@dataclass
class NormalizedQuote:
    """A price normalized to standard form."""
    unit_price: float
    currency: str = "EUR"
    unit: str = "kom"  # piece
    pack_size: float | None = None
    pack_unit: str | None = None
    vat_included: bool = True
    vat_amount: float = 0.0
    availability: str = "unknown"
    product_name: str = ""
    product_url: str = ""
    vendor: str = ""
    confidence: float = 0.5
    evidence_snippet: str = ""
    source_method: str = "unknown"
    image_url: str = ""


@dataclass
class ComputedTotal:
    """Deterministic total computation result."""
    quantity: float
    unit_price_ex_vat: float
    subtotal_ex_vat: float
    vat: float
    shipping_estimate: float
    total: float
    currency: str = "EUR"
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Croatian decimal / currency parsing
# ---------------------------------------------------------------------------

# Croatian format: 1.234,56 € or 1234,56 EUR or 18,40 €
_HR_PRICE_RE = re.compile(
    r"(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?)\s*(?:€|EUR|HRK|kn)?",
    re.IGNORECASE,
)


def parse_croatian_price(text: str) -> float | None:
    """Parse a Croatian-formatted price string to float.

    Examples: "1.234,56" -> 1234.56, "18,40" -> 18.40, "1234.56" -> 1234.56
    """
    text = text.strip()
    m = _HR_PRICE_RE.search(text)
    if not m:
        return None
    price_str = m.group(1)
    # Croatian: dots are thousands separators, comma is decimal
    price_str = price_str.replace(".", "").replace(",", ".")
    try:
        return float(price_str)
    except ValueError:
        return None


def detect_currency(text: str) -> str:
    """Detect currency from a price string."""
    text_lower = text.lower()
    if "kn" in text_lower or "hrk" in text_lower:
        return "HRK"
    return "EUR"


# ---------------------------------------------------------------------------
# Unit parsing
# ---------------------------------------------------------------------------

_UNIT_MAP: dict[str, str] = {
    "komad": "kom", "kom": "kom", "kom.": "kom", "pcs": "kom", "piece": "kom",
    "m": "m", "m1": "m", "ml": "m",
    "m2": "m²", "m²": "m²", "m\u00b2": "m²",
    "m3": "m³", "m³": "m³", "m\u00b3": "m³",
    "kg": "kg", "t": "t", "ton": "t",
    "l": "l", "lit": "l", "liter": "l",
    "set": "set", "komplet": "set", "kpl": "set",
    "pau": "pau", "pauš": "pau", "paušal": "pau", "pausal": "pau",
    "rola": "rola", "roll": "rola",
    "pak": "pak", "pack": "pak", "pakiranje": "pak",
}

# Pack size pattern: "25m", "10kg", "5l", "50 m"
_PACK_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(m²?|m³?|kg|l|lit|kom|pcs)\b", re.IGNORECASE)


def normalize_unit(raw: str | None) -> str:
    """Normalize a unit string to canonical form."""
    if not raw:
        return "kom"
    key = raw.lower().strip().rstrip(".")
    return _UNIT_MAP.get(key, raw.lower().strip())


def detect_pack_size(text: str) -> tuple[float | None, str | None]:
    """Try to detect pack size from product description."""
    m = _PACK_RE.search(text)
    if m:
        try:
            value = float(m.group(1).replace(",", "."))
            unit = normalize_unit(m.group(2))
            return value, unit
        except ValueError:
            pass
    return None, None


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_price(
    pf: PriceField,
    vendor: str = "",
    domain_vat_included: bool | None = True,
) -> NormalizedQuote:
    """Normalize a PriceField to a standard NormalizedQuote."""
    amount = pf.amount or 0.0
    currency = pf.currency or "EUR"
    vat_included = pf.vat_included if pf.vat_included is not None else domain_vat_included

    # Detect unit and pack size from product name
    unit = normalize_unit(pf.unit)
    pack_size, pack_unit = detect_pack_size(pf.product_name or pf.raw_text)

    # Compute VAT
    if vat_included:
        vat_amount = round(amount - amount / 1.25, 2)  # 25% PDV
    else:
        vat_amount = 0.0

    # Confidence based on extraction method
    confidence_map = {"jsonld": 0.9, "meta": 0.8, "css": 0.6, "llm": 0.5}
    confidence = confidence_map.get(pf.source_method, 0.4)

    return NormalizedQuote(
        unit_price=amount,
        currency=currency,
        unit=unit,
        pack_size=pack_size,
        pack_unit=pack_unit,
        vat_included=vat_included or False,
        vat_amount=vat_amount,
        availability=pf.availability,
        product_name=pf.product_name,
        product_url=pf.product_url,
        vendor=vendor,
        confidence=confidence,
        evidence_snippet=pf.raw_text[:200],
        source_method=pf.source_method,
        image_url=pf.image_url,
    )


# ---------------------------------------------------------------------------
# Total computation (deterministic)
# ---------------------------------------------------------------------------

def compute_total(
    quote: NormalizedQuote,
    quantity: float,
    rules: PricingRules | None = None,
) -> ComputedTotal:
    """Compute the total cost for a given quantity and quote."""
    rules = rules or PricingRules()
    notes: list[str] = []

    unit_price = quote.unit_price

    # If price includes VAT and we want ex-VAT base
    if quote.vat_included:
        unit_price_ex_vat = round(unit_price / (1 + rules.vat_rate), 2)
        notes.append(f"Source price includes PDV ({int(rules.vat_rate * 100)}%)")
    else:
        unit_price_ex_vat = unit_price

    # Pack size adjustment
    if quote.pack_size and quote.pack_size > 0:
        notes.append(f"Pack: {quote.pack_size} {quote.pack_unit or ''}")

    subtotal_ex_vat = round(unit_price_ex_vat * quantity, 2)
    vat = round(subtotal_ex_vat * rules.vat_rate, 2) if rules.include_vat else 0.0

    # Shipping estimate (placeholder — domain-specific overrides later)
    shipping = 0.0
    if rules.include_shipping:
        notes.append("Shipping not estimated (domain-specific)")

    total = round(subtotal_ex_vat + vat + shipping, 2)

    return ComputedTotal(
        quantity=quantity,
        unit_price_ex_vat=unit_price_ex_vat,
        subtotal_ex_vat=subtotal_ex_vat,
        vat=vat,
        shipping_estimate=shipping,
        total=total,
        currency=rules.target_currency,
        notes=notes,
    )
