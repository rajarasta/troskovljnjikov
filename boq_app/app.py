"""BoQ Matcher — Futuristic Streamlit UI.

Two-column layout:
  Left:  match carousel with stacked cards + navigator
  Right: unified unit panel (detail + lines + stats + confidence + reasoning)

Run with: uv run streamlit run boq_ui.py
"""

from __future__ import annotations

import streamlit as st

from .backend import parse_uploaded_file_sync
from .mock_data import (
    generate_mock_matches,
    generate_mock_parsed_file,
    generate_mock_pipeline,
    generate_mock_price_stats,
    generate_mock_reasoning_log,
)
from .state import get_state, init_state
from .styles import get_all_css
from .themes import get_theme_css_vars

# --- Page config (must be first Streamlit call) ---
st.set_page_config(
    page_title="BoQ Matcher",
    page_icon="\U0001f3d7",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- State init ---
init_state()
state = get_state()

# --- Load mock data on first run ---
if state["use_mock_data"] and state["parsed_file"] is None:
    state["parsed_file"] = generate_mock_parsed_file()
    for item in state["parsed_file"].items:
        if item.level >= 2 and item.priced_lines:
            state["selected_item_id"] = item.id
            break
    if state["selected_item_id"]:
        state["matches"][state["selected_item_id"]] = generate_mock_matches()
        state["price_stats"][state["selected_item_id"]] = generate_mock_price_stats()
    state["reasoning_log"] = generate_mock_reasoning_log()
    state["pipeline"] = generate_mock_pipeline()

# --- Handle uploaded file (overrides mock data) ---
uploaded = state.get("uploaded_file")
if uploaded is not None and state.get("_last_uploaded") != uploaded.name:
    content = uploaded.read()
    state["parsed_file"] = parse_uploaded_file_sync(content, uploaded.name)
    state["_last_uploaded"] = uploaded.name
    state["selected_item_id"] = None
    state["matches"] = {}
    state["price_stats"] = {}
    # Select first work item with priced lines, or first item with level >= 2
    for item in state["parsed_file"].items:
        if item.level >= 2 and item.priced_lines:
            state["selected_item_id"] = item.id
            break
    # If no priced item found, select first non-chapter item
    if state["selected_item_id"] is None:
        for item in state["parsed_file"].items:
            if item.level >= 1:
                state["selected_item_id"] = item.id
                break
    # If still nothing, select the very first item
    if state["selected_item_id"] is None and state["parsed_file"].items:
        state["selected_item_id"] = state["parsed_file"].items[0].id

# --- Inject theme CSS ---
theme_vars = get_theme_css_vars(state["theme"])
st.markdown(get_all_css(theme_vars), unsafe_allow_html=True)

# --- Render ---
from .components.header import render_header
from .components.navigator import render_navigator
from .components.match_carousel import render_match_carousel
from .components.unit_panel import render_unit_panel

# Header + Pipeline bar
render_header()

# Main 2-column layout: left (carousel + nav), right (unified unit panel)
col_left, col_right = st.columns([2, 5])

with col_left:
    render_navigator()
    render_match_carousel()

with col_right:
    render_unit_panel()
