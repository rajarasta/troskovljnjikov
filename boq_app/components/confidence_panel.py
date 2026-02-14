"""Right lower: match confidence breakdown bars."""

from __future__ import annotations

import streamlit as st

from ..models import HistoricMatchUI
from ..state import get_matches_for_selected


def render_confidence_panel() -> None:
    """Render the confidence breakdown for the top match."""
    matches = get_matches_for_selected()

    st.markdown(
        '<div class="glass-panel">'
        '<div class="glass-panel-header">Confidence Breakdown</div>',
        unsafe_allow_html=True,
    )

    if not matches:
        st.markdown(
            '<div style="color: var(--text-muted); font-size: 0.78rem; '
            'padding: 0.5rem 0; text-align: center;">'
            "Select a matched item</div></div>",
            unsafe_allow_html=True,
        )
        return

    top_match = matches[0]
    breakdown = top_match.confidence_breakdown
    overall = top_match.match_confidence

    # Overall score
    html = f"""
    <div class="confidence-overall">{overall * 100:.0f}%</div>
    <div class="confidence-overall-label">Overall Confidence</div>
    """

    # Factor bars
    factors = [
        ("Text Similarity", breakdown.text_similarity),
        ("Unit Match", breakdown.unit_match),
        ("Hierarchy Match", breakdown.hierarchy_match),
        ("Description Overlap", breakdown.description_overlap),
    ]

    for label, value in factors:
        pct = value * 100
        html += f"""
        <div class="confidence-breakdown-item">
            <div class="confidence-breakdown-label">
                <span>{label}</span>
                <span class="confidence-breakdown-value">{pct:.0f}%</span>
            </div>
            <div class="confidence-breakdown-bar">
                <div class="confidence-breakdown-fill" style="width: {pct}%;
                     opacity: {0.4 + 0.6 * value};"></div>
            </div>
        </div>
        """

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
