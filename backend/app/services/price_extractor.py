"""Price Extractor - layered extraction pipeline for product prices from HTML.

Extraction order:
1. JSON-LD (application/ld+json) — structured Product/Offer schema
2. Meta tags (OpenGraph, product meta)
3. LLM fallback — send DOM snippet to LLM for extraction
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class PriceField:
    """A single extracted price data point."""
    raw_text: str
    amount: float | None = None
    currency: str = "EUR"
    vat_included: bool | None = None
    unit: str | None = None  # e.g. "kom", "m", "m²"
    pack_size: str | None = None  # e.g. "25m"
    availability: str = "unknown"  # "in_stock", "out_of_stock", "unknown"
    product_name: str = ""
    product_url: str = ""
    source_method: str = "unknown"  # "jsonld", "meta", "css", "llm"
    image_url: str = ""


# ---------------------------------------------------------------------------
# Layer 1: JSON-LD extraction
# ---------------------------------------------------------------------------

def extract_jsonld(html: str) -> list[PriceField]:
    """Extract prices from JSON-LD Product/Offer schemas."""
    soup = BeautifulSoup(html, "lxml")
    results: list[PriceField] = []

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            _extract_jsonld_item(item, results)

    return results


def _extract_jsonld_item(item: dict[str, Any], results: list[PriceField]) -> None:
    """Recursively extract price info from a JSON-LD item."""
    item_type = item.get("@type", "")
    if isinstance(item_type, list):
        item_type = item_type[0] if item_type else ""

    if item_type in ("Product", "IndividualProduct"):
        name = item.get("name", "")
        image = item.get("image", "")
        if isinstance(image, list):
            image = image[0] if image else ""
        if isinstance(image, dict):
            image = image.get("url", "")

        offers = item.get("offers", {})
        if isinstance(offers, list):
            for offer in offers:
                _parse_offer(offer, name, image, results)
        elif isinstance(offers, dict):
            _parse_offer(offers, name, image, results)

    # Check for nested @graph
    if "@graph" in item:
        for sub in item["@graph"]:
            if isinstance(sub, dict):
                _extract_jsonld_item(sub, results)


def _parse_offer(offer: dict[str, Any], name: str, image: str, results: list[PriceField]) -> None:
    """Parse a schema.org Offer into a PriceField."""
    price = offer.get("price") or offer.get("lowPrice")
    if price is None:
        return

    try:
        amount = float(str(price).replace(",", ".").replace(" ", ""))
    except (ValueError, TypeError):
        return

    currency = offer.get("priceCurrency", "EUR")
    availability = offer.get("availability", "")
    if "InStock" in str(availability):
        avail = "in_stock"
    elif "OutOfStock" in str(availability):
        avail = "out_of_stock"
    else:
        avail = "unknown"

    url = offer.get("url", "")

    results.append(PriceField(
        raw_text=f"{amount} {currency}",
        amount=amount,
        currency=currency,
        availability=avail,
        product_name=name,
        product_url=url,
        source_method="jsonld",
        image_url=image,
    ))


# ---------------------------------------------------------------------------
# Layer 2: Meta tag extraction
# ---------------------------------------------------------------------------

def extract_meta_tags(html: str) -> list[PriceField]:
    """Extract prices from OpenGraph and product meta tags."""
    soup = BeautifulSoup(html, "lxml")
    results: list[PriceField] = []

    price_amount = None
    currency = "EUR"
    name = ""

    # OpenGraph product tags
    og_price = soup.find("meta", property="product:price:amount")
    og_currency = soup.find("meta", property="product:price:currency")
    og_title = soup.find("meta", property="og:title")
    og_avail = soup.find("meta", property="product:availability")

    if og_price and og_price.get("content"):
        try:
            price_amount = float(str(og_price["content"]).replace(",", ".").replace(" ", ""))
        except (ValueError, TypeError):
            pass

    if og_currency and og_currency.get("content"):
        currency = str(og_currency["content"])

    if og_title and og_title.get("content"):
        name = str(og_title["content"])

    avail = "unknown"
    if og_avail and og_avail.get("content"):
        avail_str = str(og_avail["content"]).lower()
        if "instock" in avail_str or "in stock" in avail_str:
            avail = "in_stock"
        elif "outofstock" in avail_str:
            avail = "out_of_stock"

    if price_amount is not None:
        results.append(PriceField(
            raw_text=f"{price_amount} {currency}",
            amount=price_amount,
            currency=currency,
            availability=avail,
            product_name=name,
            source_method="meta",
        ))

    return results


# ---------------------------------------------------------------------------
# Layer 3: CSS-based extraction (generic price patterns)
# ---------------------------------------------------------------------------

# Common price CSS class/attribute patterns
_PRICE_SELECTORS = [
    "[data-price]",
    ".product-price",
    ".price",
    ".woocommerce-Price-amount",
    ".price-new",
    ".current-price",
    ".special-price",
    "#product-price",
    "[itemprop='price']",
]

_PRICE_RE = re.compile(
    r"(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)\s*(?:€|EUR|HRK|kn)",
    re.IGNORECASE,
)


def extract_css_prices(html: str) -> list[PriceField]:
    """Extract prices using common CSS selectors and regex patterns."""
    soup = BeautifulSoup(html, "lxml")
    results: list[PriceField] = []
    seen_amounts: set[float] = set()

    for selector in _PRICE_SELECTORS:
        for el in soup.select(selector):
            # Check data-price attribute first
            data_price = el.get("data-price") or el.get("content")
            if data_price:
                try:
                    amount = float(str(data_price).replace(",", ".").replace(" ", ""))
                    if amount > 0 and amount not in seen_amounts:
                        seen_amounts.add(amount)
                        results.append(PriceField(
                            raw_text=el.get_text(strip=True),
                            amount=amount,
                            source_method="css",
                        ))
                except (ValueError, TypeError):
                    pass

            # Try regex on text content
            text = el.get_text(strip=True)
            for m in _PRICE_RE.finditer(text):
                price_str = m.group(1).replace(".", "").replace(",", ".")
                try:
                    amount = float(price_str)
                    if amount > 0 and amount not in seen_amounts:
                        seen_amounts.add(amount)
                        currency = "EUR"
                        if "kn" in m.group(0).lower() or "hrk" in m.group(0).upper():
                            currency = "HRK"
                        results.append(PriceField(
                            raw_text=text,
                            amount=amount,
                            currency=currency,
                            source_method="css",
                        ))
                except (ValueError, TypeError):
                    pass

    return results


# ---------------------------------------------------------------------------
# Combined extraction pipeline
# ---------------------------------------------------------------------------

def extract_prices(html: str, product_hint: str = "") -> list[PriceField]:
    """Run the full extraction pipeline on an HTML page.

    Tries JSON-LD first, then meta tags, then CSS selectors.
    Returns all extracted prices sorted by confidence (jsonld > meta > css).
    """
    all_prices: list[PriceField] = []

    # Layer 1: JSON-LD (highest confidence)
    jsonld_prices = extract_jsonld(html)
    all_prices.extend(jsonld_prices)

    # Layer 2: Meta tags
    meta_prices = extract_meta_tags(html)
    all_prices.extend(meta_prices)

    # Layer 3: CSS selectors
    css_prices = extract_css_prices(html)
    all_prices.extend(css_prices)

    # Deduplicate by amount (keep first occurrence = highest confidence method)
    seen: set[float] = set()
    deduped: list[PriceField] = []
    for p in all_prices:
        if p.amount is not None and p.amount not in seen:
            seen.add(p.amount)
            deduped.append(p)
        elif p.amount is None:
            deduped.append(p)

    return deduped


def extract_product_links(html: str, base_url: str = "") -> list[dict[str, str]]:
    """Extract product links from a search results / listing page.

    Returns list of {url, title} for product pages.
    """
    soup = BeautifulSoup(html, "lxml")
    links: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    # Common product link selectors
    selectors = [
        "a.product-item-link",
        "a.woocommerce-LoopProduct-link",
        ".product a[href]",
        ".product-card a[href]",
        ".products a.product-link",
        "h2.product-title a",
        "h3.product-title a",
        ".product-name a",
        "a[data-product-url]",
        ".search-results .item a",
    ]

    for selector in selectors:
        for a in soup.select(selector):
            href = a.get("href", "")
            if not href or href in seen_urls:
                continue
            # Resolve relative URLs
            if href.startswith("/") and base_url:
                from urllib.parse import urljoin
                href = urljoin(base_url, href)
            if not href.startswith("http"):
                continue
            title = a.get_text(strip=True) or a.get("title", "")
            seen_urls.add(href)
            links.append({"url": href, "title": title})

    # Fallback: look for any links that look like product pages
    if not links:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Heuristic: product URLs often contain "product", "proizvod", "artikl"
            if any(kw in href.lower() for kw in ("product", "proizvod", "artikl", "item", "/p/")):
                if href not in seen_urls:
                    if href.startswith("/") and base_url:
                        from urllib.parse import urljoin
                        href = urljoin(base_url, href)
                    if href.startswith("http"):
                        title = a.get_text(strip=True) or ""
                        seen_urls.add(href)
                        links.append({"url": href, "title": title})

    return links[:20]  # Cap at 20 candidates
