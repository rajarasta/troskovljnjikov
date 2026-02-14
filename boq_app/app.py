"""BoQ Matcher — Futuristic Streamlit UI.

Two-column layout:
  Left:  match carousel with stacked cards + navigator
  Right: unified unit panel (detail + lines + stats + confidence + reasoning)

Run with: uv run streamlit run boq_ui.py
"""

from __future__ import annotations

import streamlit as st

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
