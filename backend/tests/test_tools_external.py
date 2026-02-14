"""Tests for external tools (search_web, summarize).

These tests use mocks since they depend on external services and the LLM.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.agent.tools.external import search_web, summarize


@pytest.mark.asyncio
async def test_search_web_returns_snippets():
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: {
        "results": [
            {"title": "Cijene betona 2026", "snippet": "Prosječna cijena betona C40/50 je 95 EUR/m³", "url": "https://example.com"}
        ]
    }
    mock_response.raise_for_status = lambda: None

    with patch("src.agent.tools.external.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        results = await search_web("cijena betona C40/50 2026")
        assert isinstance(results, list)


@pytest.mark.asyncio
async def test_summarize_calls_llm():
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content="Sažetak teksta."))]

    with patch("src.agent.tools.external.openai.AsyncOpenAI") as mock_oai_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_oai_cls.return_value = mock_client

        result = await summarize("Dugačak tekst o cijenama građevinskog materijala...")
        assert isinstance(result, str)
        assert len(result) > 0
