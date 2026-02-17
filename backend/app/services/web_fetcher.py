"""Web Fetcher - layered HTTP fetching with static (httpx) and rendered (Playwright) modes.

Provides a simple caching layer (15-min TTL) keyed by URL.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from app.services.domain_registry import get_domain_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class FetchResult:
    """Result of fetching a web page."""
    url: str
    final_url: str
    html: str
    text: str
    status_code: int
    fetched_at: str
    from_cache: bool = False
    fetch_mode: str = "static"  # "static" | "render"


# ---------------------------------------------------------------------------
# In-memory cache (URL -> FetchResult, 15 min TTL)
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[float, FetchResult]] = {}
_CACHE_TTL = 900  # 15 minutes


def _cache_get(url: str) -> FetchResult | None:
    entry = _cache.get(url)
    if entry is None:
        return None
    ts, result = entry
    if time.time() - ts > _CACHE_TTL:
        del _cache[url]
        return None
    return FetchResult(
        url=result.url,
        final_url=result.final_url,
        html=result.html,
        text=result.text,
        status_code=result.status_code,
        fetched_at=result.fetched_at,
        from_cache=True,
        fetch_mode=result.fetch_mode,
    )


def _cache_put(url: str, result: FetchResult) -> None:
    _cache[url] = (time.time(), result)


# ---------------------------------------------------------------------------
# Static fetch (httpx)
# ---------------------------------------------------------------------------

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


async def fetch_static(url: str, timeout: float = 15.0) -> FetchResult:
    """Fetch a page using httpx (no JS rendering)."""
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=timeout,
        headers={"User-Agent": _USER_AGENT},
    ) as client:
        resp = await client.get(url)
        html = resp.text
        soup = BeautifulSoup(html, "lxml")
        # Remove script/style noise
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return FetchResult(
            url=url,
            final_url=str(resp.url),
            html=html,
            text=text,
            status_code=resp.status_code,
            fetched_at=datetime.utcnow().isoformat(),
            fetch_mode="static",
        )


# ---------------------------------------------------------------------------
# Rendered fetch (Playwright) - optional
# ---------------------------------------------------------------------------

async def fetch_rendered(url: str, timeout: float = 30.0) -> FetchResult:
    """Fetch a page using Playwright headless browser (JS rendering)."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("Playwright not installed, falling back to static fetch")
        return await fetch_static(url, timeout)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=_USER_AGENT)
        try:
            await page.goto(url, wait_until="networkidle", timeout=int(timeout * 1000))
            html = await page.content()
            final_url = page.url
        finally:
            await browser.close()

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return FetchResult(
        url=url,
        final_url=final_url,
        html=html,
        text=text,
        status_code=200,
        fetched_at=datetime.utcnow().isoformat(),
        fetch_mode="render",
    )


# ---------------------------------------------------------------------------
# Auto-mode fetch (tries static, falls back to render if needed)
# ---------------------------------------------------------------------------

def _looks_like_js_only(html: str) -> bool:
    """Heuristic: page has very little text content, likely needs JS rendering."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(strip=True)
    return len(text) < 200


async def fetch_page(url: str, mode: str = "auto") -> FetchResult:
    """Fetch a page with caching and automatic mode selection.

    Args:
        url: The URL to fetch.
        mode: "static", "render", or "auto" (tries static first, falls back to render).

    Returns:
        FetchResult with HTML, extracted text, and metadata.
    """
    # Check cache first
    cached = _cache_get(url)
    if cached is not None:
        return cached

    # Determine fetch mode
    if mode == "auto":
        config = get_domain_config(url)
        if config and config.fetch_mode == "render":
            mode = "render"
        else:
            mode = "static"

    if mode == "render":
        result = await fetch_rendered(url)
    else:
        result = await fetch_static(url)
        # If static fetch returned JS-only content, try render
        if _looks_like_js_only(result.html):
            logger.info("Static fetch returned JS-only content for %s, trying render", url)
            try:
                result = await fetch_rendered(url)
            except Exception:
                logger.warning("Render fallback failed for %s, using static result", url)

    _cache_put(url, result)
    return result
