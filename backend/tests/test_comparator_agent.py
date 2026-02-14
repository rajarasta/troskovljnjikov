"""Tests for the Comparator agent."""

import pytest
import pytest_asyncio
import aiosqlite

from src.db.schema import SCHEMA_SQL
from src.agent.comparator_agent import create_comparator_agent, ComparatorDeps
from src.agent.schemas import ClassResult


@pytest_asyncio.fixture
async def db():
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.executescript(SCHEMA_SQL)
    yield conn
    await conn.close()


def test_comparator_agent_has_tools():
    agent = create_comparator_agent()
    tool_names = [t.name for t in agent._function_toolset.tools.values()]
    assert "search_historic" in tool_names
    assert "fetch_similar" in tool_names


def test_comparator_deps_holds_classification(db):
    classification = ClassResult(
        taxonomy_id="test", taxonomy_label="Test", confidence=0.9
    )
    deps = ComparatorDeps(db=db, classification=classification)
    assert deps.classification.taxonomy_id == "test"
