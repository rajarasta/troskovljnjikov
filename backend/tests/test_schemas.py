"""Tests for agent pipeline schemas.

Field names aligned with Streamlit frontend models in boq_app/models.py:
  ReasoningEntry.agent_name  (not .agent)
  HistoricComparison.match_id  (not .historic_unit_id)
  HistoricComparison.source_file  (not .source_filename)
  HistoricComparison.year  (not .project_year)
  HistoricComparison.match_confidence  (float, overall score)
  HistoricComparison.confidence_breakdown  (ConfidenceBreakdown object)
  HistoricComparison.matched_lines  (not .price_lines)
  PipelineStats.num_matches  (not .match_count)
"""

from src.agent.schemas import (
    ClassResult,
    CompResult,
    ConfidenceBreakdown,
    Deviation,
    HistoricComparison,
    HistoricPriceLine,
    LinePriceSuggestion,
    PriceRange,
    PriceResult,
    ReasoningEntry,
)


def test_class_result_minimal():
    result = ClassResult(
        taxonomy_id="hidroizolacija-ravnog-krova",
        taxonomy_label="Hidroizolacija ravnog krova",
        confidence=0.85,
    )
    assert result.taxonomy_id == "hidroizolacija-ravnog-krova"
    assert result.deviations == []
    assert result.unmatched_rows == []


def test_class_result_with_deviations():
    result = ClassResult(
        taxonomy_id="toplinska-izolacija",
        taxonomy_label="Toplinska izolacija",
        confidence=0.72,
        deviations=[
            Deviation(
                field="thickness",
                standard_value="0.3cm",
                actual_value="0.4cm",
                description="Debljina veća od standardne",
            )
        ],
        unmatched_rows=[5, 8],
    )
    assert len(result.deviations) == 1
    assert result.deviations[0].field == "thickness"
    assert result.unmatched_rows == [5, 8]


def test_confidence_breakdown():
    breakdown = ConfidenceBreakdown(
        text_similarity=0.85,
        unit_match=1.0,
        hierarchy_match=0.7,
        description_overlap=0.6,
    )
    assert breakdown.overall == 0.82  # weighted average: text 40%, unit 25%, hierarchy 20%, description 15%
    assert breakdown.text_similarity == 0.85


def test_historic_comparison_with_breakdown():
    comp = HistoricComparison(
        match_id=42,
        project_name="Kaufland Osijek",
        source_file="KAUFLAND OSIJEK - ugovorni troškovnik.xlsx",
        year=2025,
        match_confidence=0.8425,
        confidence_breakdown=ConfidenceBreakdown(
            text_similarity=0.88,
            unit_match=1.0,
            hierarchy_match=0.7,
            description_overlap=0.65,
        ),
        matching_sub_items=["beton C40/50"],
        missing_sub_items=[],
        extra_sub_items=["armatura"],
        qty_delta_pct=-8.0,
        matched_lines=[
            HistoricPriceLine(
                item_number="3.2.1.a.",
                description="Beton",
                unit_of_measure="m³",
                quantity=120.0,
                unit_price=95.0,
                total=11400.0,
            )
        ],
    )
    assert comp.year == 2025
    assert comp.qty_delta_pct == -8.0
    assert comp.confidence_breakdown.overall > 0.7
    assert comp.match_confidence == 0.8425


def test_comp_result():
    classification = ClassResult(
        taxonomy_id="betonski-radovi",
        taxonomy_label="Betonski radovi",
        confidence=0.9,
    )
    result = CompResult(
        classification=classification,
        matches=[
            HistoricComparison(
                match_id=42,
                project_name="Kaufland Osijek",
                source_file="k.xlsx",
                year=2025,
                match_confidence=0.84,
                confidence_breakdown=ConfidenceBreakdown(
                    text_similarity=0.88,
                    unit_match=1.0,
                    hierarchy_match=0.7,
                    description_overlap=0.65,
                ),
                matched_lines=[
                    HistoricPriceLine(
                        description="Beton",
                        unit_of_measure="m³",
                        quantity=120.0,
                        unit_price=95.0,
                    )
                ],
            )
        ],
        summary="1 slična stavka pronađena",
    )
    assert len(result.matches) == 1
    assert result.matches[0].project_name == "Kaufland Osijek"


def test_price_result():
    result = PriceResult(
        line_prices=[
            LinePriceSuggestion(
                item_number="3.1.1.1.a.",
                suggested_price=45.0,
                confidence=0.8,
                price_range=PriceRange(low=38.0, high=52.0, median=44.5),
                reasoning="Prosjek 4 historijske cijene",
            )
        ],
        overall_reasoning="Cijena u skladu s historijskim podacima",
    )
    assert result.line_prices[0].suggested_price == 45.0
    assert result.line_prices[0].price_range.median == 44.5


def test_reasoning_entry():
    entry = ReasoningEntry(
        agent_name="classifier",
        message="Pronađen tip: Hidroizolacija ravnog krova (confidence: 0.85)",
        entry_type="result",
    )
    assert entry.agent_name == "classifier"
    assert entry.entry_type == "result"
    assert entry.timestamp  # auto-generated
