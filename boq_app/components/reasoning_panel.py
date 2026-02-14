"""Right upper: LLM agent reasoning log panel."""

from __future__ import annotations

import streamlit as st

from ..models import ReasoningEntryUI
from ..state import get_state


def render_reasoning_panel() -> None:
    """Render the LLM reasoning log panel."""
    state = get_state()
    log: list[ReasoningEntryUI] = state.get("reasoning_log", [])

    st.markdown(
        '<div class="glass-panel">'
        '<div class="glass-panel-header">Agent Activity</div>',
        unsafe_allow_html=True,
    )

    if not log:
        st.markdown(
            '<div style="color: var(--text-muted); font-size: 0.78rem; '
            'padding: 0.5rem 0; text-align: center;">'
            "Waiting for pipeline&hellip;</div></div>",
            unsafe_allow_html=True,
        )
        return

    entries_html = ""
    for entry in reversed(log[-30:]):
        agent_class = entry.agent_name.lower()
        if agent_class not in ("indexer", "matcher", "pricer", "system"):
            agent_class = "system"

        type_class = ""
        if entry.entry_type == "thinking":
            type_class = "reasoning-thinking"
        elif entry.entry_type == "result":
            type_class = "reasoning-result"
        elif entry.entry_type == "error":
            type_class = "reasoning-error"

        entries_html += (
            f'<div class="reasoning-entry">'
            f'<span class="reasoning-timestamp">{entry.timestamp}</span>'
            f'<span class="agent-badge {agent_class}">{entry.agent_name}</span>'
            f'<span class="{type_class}">{entry.message}</span>'
            f"</div>"
        )

    html = f'<div class="reasoning-container">{entries_html}</div></div>'
    st.markdown(html, unsafe_allow_html=True)
