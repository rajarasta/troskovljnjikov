"""Tests for the pipeline orchestrator.

Tests the event sequence without a running LLM by mocking agent.run().
"""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.agent.pipeline import run_pipeline, PIPELINE_STAGES
from src.agent.schemas import (
    ClassResult,
    CompResult,
    ConfidenceBreakdown,
    HistoricComparison,
    HistoricPriceLine,
    LinePriceSuggestion,
    PriceRange,
    PriceResult,
)
from src.models.boq import LogicalUnit, PricedLine


@pytest.fixture
def sample_unit():
    return LogicalUnit(
        item_number="3.1.1.",
        title="Hidroizolacija ravnog krova",
        description="Izvedba hidroizolacije",
        priced_lines=[
            PricedLine(item_number="3.1.1.a.", description="Parna brana", unit="m²", quantity=200.0),
        ],
    )


def test_pipeline_stages_defined():
    assert len(PIPELINE_STAGES) == 6
    assert PIPELINE_STAGES[0] == "upload"
    assert PIPELINE_STAGES[-1] == "review"


@pytest.mark.asyncio
async def test_pipeline_yields_correct_event_sequence(sample_unit):
    mock_class_result = ClassResult(
        taxonomy_id="hidro", taxonomy_label="Hidro", confidence=0.9
    )
    mock_comp_result = CompResult(
        classification=mock_class_result,
        matches=[
            HistoricComparison(
                match_id=1,
                project_name="Test Project",
                source_file="test.xlsx",
                year=2025,
                match_confidence=0.84,
                confidence_breakdown=ConfidenceBreakdown(
                    text_similarity=0.88,
                    unit_match=1.0,
                    hierarchy_match=0.7,
                    description_overlap=0.65,
                ),
                matched_lines=[HistoricPriceLine(description="Parna brana", unit_of_measure="m²", quantity=250, unit_price=12.5)],
            )
        ],
        summary="Found 1 match",
    )
    mock_price_result = PriceResult(
        line_prices=[
            LinePriceSuggestion(
                item_number="3.1.1.a.",
                suggested_price=12.5,
                confidence=0.8,
                price_range=PriceRange(low=10.0, high=15.0, median=12.5),
                reasoning="Based on 1 match",
            )
        ],
        overall_reasoning="Price OK",
    )

    with patch("src.agent.pipeline.create_classifier_agent") as mock_cls, \
         patch("src.agent.pipeline.create_comparator_agent") as mock_cmp, \
         patch("src.agent.pipeline.create_pricer_agent") as mock_prc, \
         patch("src.agent.pipeline.get_db") as mock_get_db:

        mock_get_db.return_value = AsyncMock()

        for mock_factory, mock_result in [
            (mock_cls, mock_class_result),
            (mock_cmp, mock_comp_result),
            (mock_prc, mock_price_result),
        ]:
            mock_agent = MagicMock()
            mock_run_result = MagicMock()
            mock_run_result.output = mock_result
            mock_agent.run = AsyncMock(return_value=mock_run_result)
            mock_factory.return_value = mock_agent

        events = []
        async for event_type, data in run_pipeline(sample_unit):
            events.append((event_type, data))

        event_types = [e[0] for e in events]

        # Pipeline stage events
        assert "pipeline_stage" in event_types
        # Agent events
        assert "reasoning" in event_types
        assert "classification" in event_types
        assert "historic_match" in event_types
        assert "confidence_breakdown" in event_types
        assert "suggestion" in event_types
        assert "stats" in event_types
        assert "complete" in event_types

        # Correct order
        assert event_types.index("classification") < event_types.index("historic_match")
        assert event_types.index("historic_match") < event_types.index("suggestion")
        assert event_types.index("suggestion") < event_types.index("complete")

        # Reasoning entries have agent_name badge (aligned with frontend)
        reasoning_events = [e for e in events if e[0] == "reasoning"]
        agents_seen = {e[1]["agent_name"] for e in reasoning_events}
        assert "classifier" in agents_seen
