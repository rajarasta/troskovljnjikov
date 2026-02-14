"""Bottom: AVG/MIN/MAX price stats footer."""

from __future__ import annotations

import streamlit as st

from ..state import get_stats_for_selected


def render_stats_footer() -> None:
    """Render the price statistics footer bar."""
    stats = get_stats_for_selected()

    if not stats:
        # Show empty glass panel footer
        st.markdown(
            '<div class="glass-panel glass-panel-compact" '
            'style="text-align: center; color: var(--text-muted); font-size: 0.75rem;">'
            "Price statistics will appear when matches are found"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    cols = st.columns(4)
    cols[0].metric("AVG", f"{stats.avg_price:,.2f} {stats.currency}")
    cols[1].metric("MIN", f"{stats.min_price:,.2f} {stats.currency}")
    cols[2].metric("MAX", f"{stats.max_price:,.2f} {stats.currency}")
    cols[3].metric("MATCHES", str(stats.num_matches))
