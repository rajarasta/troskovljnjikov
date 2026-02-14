"""Header bar and pipeline visualization."""

from __future__ import annotations

import streamlit as st

from ..models import PipelineStepUI
from ..state import get_state


def render_header() -> None:
    """Render the app header with title and theme switcher."""
    from ..themes import THEMES

    state = get_state()
    h_left, h_center, h_right = st.columns([2, 4, 2])

    with h_left:
        st.markdown(
            '<div class="app-subtitle">BoQ MATCHER</div>'
            '<div class="app-title">Troškovnik</div>',
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader(
            "Upload BoQ",
            type=["xlsx", "xls"],
            label_visibility="collapsed",
            key="boq_file_uploader",
        )
        if uploaded:
            state["uploaded_file"] = uploaded

    with h_center:
        _render_pipeline(state["pipeline"])

    with h_right:
        theme_names = list(THEMES.keys())
        display_names = [THEMES[k]["name"] for k in theme_names]
        current_idx = theme_names.index(state["theme"]) if state["theme"] in theme_names else 0
        selected = st.selectbox(
            "Theme",
            theme_names,
            index=current_idx,
            format_func=lambda k: THEMES[k]["name"],
            label_visibility="collapsed",
            key="theme_selector",
        )
        if selected != state["theme"]:
            state["theme"] = selected
            st.rerun()


def _render_pipeline(steps: list[PipelineStepUI]) -> None:
    """Render the horizontal pipeline status bar."""
    parts: list[str] = []
    for i, step in enumerate(steps):
        status = step.status.value
        dot_class = f"pipeline-dot {status}"
        label_class = f"pipeline-label {status}"
        parts.append(
            f'<div class="pipeline-step">'
            f'<div class="{dot_class}"></div>'
            f'<span class="{label_class}">{step.name}</span>'
            f"</div>"
        )
        if i < len(steps) - 1:
            line_class = "pipeline-line"
            if step.status.value == "done":
                line_class += " done"
            parts.append(f'<div class="{line_class}"></div>')

    html = f'<div class="pipeline-container glass-panel glass-panel-compact">{"".join(parts)}</div>'
    st.markdown(html, unsafe_allow_html=True)
