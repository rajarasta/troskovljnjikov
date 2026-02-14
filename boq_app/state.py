"""Session state initialization and helpers."""

from __future__ import annotations

import streamlit as st

from .models import PipelineStepStatus, PipelineStepUI


def init_state() -> None:
    """Initialize session state on first run. Safe to call every rerun."""
    if "app_state" not in st.session_state:
        st.session_state.app_state = {
            "parsed_file": None,
            "selected_item_id": None,
            "matches": {},
            "price_stats": {},
            "reasoning_log": [],
            "pipeline": [
                PipelineStepUI(name="Upload"),
                PipelineStepUI(name="Parse"),
                PipelineStepUI(name="Index"),
                PipelineStepUI(name="Match"),
                PipelineStepUI(name="Suggest"),
                PipelineStepUI(name="Review"),
            ],
            "applied_prices": {},
            "theme": "minority_report",
            "use_mock_data": True,
        }


def get_state() -> dict:
    """Return the app state dict."""
    return st.session_state.app_state


def get_selected_item():
    """Return the currently selected BoQItemUI, or None."""
    state = get_state()
    parsed = state.get("parsed_file")
    sel_id = state.get("selected_item_id")
    if not parsed or not sel_id:
        return None
    for item in parsed.items:
        if item.id == sel_id:
            return item
    return None


def get_matches_for_selected():
    """Return match list for the selected item."""
    state = get_state()
    sel_id = state.get("selected_item_id")
    if not sel_id:
        return []
    return state.get("matches", {}).get(sel_id, [])


def get_stats_for_selected():
    """Return PriceStatsUI for the selected item, or None."""
    state = get_state()
    sel_id = state.get("selected_item_id")
    if not sel_id:
        return None
    return state.get("price_stats", {}).get(sel_id)


def update_pipeline_step(step_name: str, status: str, detail: str = "") -> None:
    """Update a pipeline step's status."""
    state = get_state()
    for step in state["pipeline"]:
        if step.name == step_name:
            step.status = PipelineStepStatus(status)
            step.detail = detail
            break
