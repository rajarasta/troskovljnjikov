"""Tests for agent SSE endpoint with mocked pipeline."""

from unittest.mock import patch, AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.models.boq import ParsedBoQ, LogicalUnit, PricedLine, ExcelFormat


def _make_boq():
    unit = LogicalUnit(
        id="unit-1",
        item_number="3.1.1.",
        title="Hidroizolacija",
        description="Test unit",
        priced_lines=[
            PricedLine(item_number="3.1.1.a.", description="Parna brana", unit="m²", quantity=200.0),
        ],
    )
    return ParsedBoQ(
        filename="test.xlsx",
        format_detected=ExcelFormat.FORMAT_A,
        sheet_name="Sheet1",
        units=[unit],
    )


async def _mock_pipeline(unit):
    yield ("reasoning", {"agent_name": "classifier", "message": "test"})
    yield ("suggestion", {"item_number": "3.1.1.a.", "suggested_price": 12.5})
    yield ("complete", {})


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_suggest_no_boq(client):
    with patch("src.api.agent.get_current_boq", return_value=None):
        resp = await client.post("/api/agent/suggest", json={"unit_id": "unit-1"})
    assert resp.status_code == 404
    assert "No BoQ uploaded" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_suggest_unit_not_found(client):
    boq = _make_boq()
    with patch("src.api.agent.get_current_boq", return_value=boq):
        resp = await client.post("/api/agent/suggest", json={"unit_id": "nonexistent"})
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_suggest_streams_events(client):
    boq = _make_boq()
    with patch("src.api.agent.get_current_boq", return_value=boq), \
         patch("src.api.agent.run_pipeline", side_effect=_mock_pipeline):
        resp = await client.post("/api/agent/suggest", json={"unit_id": "unit-1"})

    assert resp.status_code == 200
    # SSE response should contain the event data
    body = resp.text
    assert "suggestion" in body
    assert "complete" in body
    assert "12.5" in body
