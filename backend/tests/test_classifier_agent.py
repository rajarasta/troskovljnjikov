"""Tests for the Classifier agent."""

import json
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
import aiosqlite

from src.db.schema import SCHEMA_SQL
from src.agent.classifier_agent import create_classifier_agent, ClassifierDeps
from src.agent.schemas import ClassResult


@pytest_asyncio.fixture
async def db():
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.executescript(SCHEMA_SQL)
    await conn.execute(
        "INSERT INTO standard_units (id, label, description, category, expected_sub_items, expected_units) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            "hidroizolacija-ravnog-krova",
            "Hidroizolacija ravnog krova",
            "Izvedba hidroizolacije ravnog krova s bitumenskim trakama",
            "Krovopokrivački radovi",
            json.dumps(["parna brana", "toplinska izolacija", "hidroizolacijska membrana"]),
            json.dumps(["m²", "m"]),
        ),
    )
    await conn.commit()
    yield conn
    await conn.close()


def test_classifier_agent_has_tools():
    agent = create_classifier_agent()
    tool_names = [t.name for t in agent._function_toolset.tools.values()]
    assert "match_taxonomy" in tool_names
    assert "check_schema" in tool_names


def test_classifier_deps_holds_db(db):
    deps = ClassifierDeps(db=db)
    assert deps.db is db
