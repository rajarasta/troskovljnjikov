"""Left panel: hierarchical BoQ item navigator tree."""

from __future__ import annotations

import streamlit as st

from ..state import get_state


def render_navigator() -> None:
    """Render the BoQ item navigator as a tree-like list."""
    state = get_state()
    parsed = state.get("parsed_file")

    st.markdown(
        '<div class="glass-panel">'
        '<div class="glass-panel-header">Navigator</div>',
        unsafe_allow_html=True,
    )

    if not parsed:
        st.markdown(
            '<div style="color: var(--text-muted); font-size: 0.8rem; '
            'padding: 1rem 0; text-align: center;">'
            "Upload a file to begin</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # Build navigation items
    item_ids = []
    item_labels = []
    for item in parsed.items:
        item_ids.append(item.id)
        indent = "\u2003" * item.level  # em-space for indentation
        item_labels.append(f"{indent}{item.item_number} {item.title}")

    current_sel = state.get("selected_item_id")
    current_idx = 0
    if current_sel in item_ids:
        current_idx = item_ids.index(current_sel)

    selected = st.radio(
        "BoQ Items",
        item_ids,
        index=current_idx,
        format_func=lambda id_: item_labels[item_ids.index(id_)],
        label_visibility="collapsed",
        key="nav_radio",
    )

    if selected != state.get("selected_item_id"):
        state["selected_item_id"] = selected
        st.rerun()

    # Render status indicators as HTML overlay
    status_html_parts = []
    for item in parsed.items:
        status = item.match_status.value
        css_class = status.replace("_", "-")
        status_html_parts.append(
            f'<div style="position: relative;">'
            f'<span class="status-dot {css_class}" '
            f'style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%);">'
            f"</span></div>"
        )

    st.markdown("</div>", unsafe_allow_html=True)
