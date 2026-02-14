"""External tools: search_web and summarize.

Non-deterministic tools called by the Pricer agent.
search_web performs HTTP requests; summarize calls the local LLM.
"""

from __future__ import annotations

import httpx
import openai

from src.config import LLM_BASE_URL, LLM_MODEL_NAME


async def search_web(query: str, max_results: int = 3) -> list[dict[str, str]]:
    """Search the web for current material prices or construction info.

    Uses a simple HTTP search. Returns a list of result snippets.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", query),
                "snippet": data["AbstractText"],
                "url": data.get("AbstractURL", ""),
            })
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append({
                    "title": topic.get("Text", "")[:80],
                    "snippet": topic.get("Text", ""),
                    "url": topic.get("FirstURL", ""),
                })

        return results[:max_results]
    except Exception:
        return []


async def summarize(text: str, max_tokens: int = 200) -> str:
    """Summarize text using the local LLM."""
    client = openai.AsyncOpenAI(base_url=LLM_BASE_URL, api_key="not-needed")
    try:
        response = await client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": "Sažmi sljedeći tekst u 2-3 rečenice. Zadrži ključne brojke i cijene."},
                {"role": "user", "content": text},
            ],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        return f"Greška pri sažimanju: {e}"
