"""Tests for the Pricer agent."""

from src.agent.pricer_agent import create_pricer_agent, PricerDeps
from src.agent.schemas import ClassResult, CompResult


def test_pricer_agent_has_tools():
    agent = create_pricer_agent()
    tool_names = [t.name for t in agent._function_toolset.tools.values()]
    assert "diff_historic" in tool_names
    assert "search_web" in tool_names
    assert "summarize" in tool_names


def test_pricer_deps_holds_comparison():
    classification = ClassResult(
        taxonomy_id="test", taxonomy_label="Test", confidence=0.9
    )
    comparison = CompResult(
        classification=classification,
        matches=[],
        summary="No matches",
    )
    deps = PricerDeps(comparison=comparison)
    assert deps.comparison.summary == "No matches"
