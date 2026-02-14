"""Right panel: unified unit view with subdivisions.

One glass panel, internally divided into sections:
  1. Item header (breadcrumb, number badge, title)
  2. Description
  3. Priced lines table
  4. Price stats (AVG / MIN / MAX)
  5. Confidence breakdown
  6. Agent reasoning log
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ..models import ReasoningEntryUI
from ..state import (
    get_matches_for_selected,
    get_selected_item,
    get_state,
    get_stats_for_selected,
)


def render_unit_panel() -> None:
    """Render the unified unit panel with all subdivisions."""
    item = get_selected_item()

    if not item:
        st.markdown(
            '<div class="unit-panel">'
            '<div class="unit-section" style="text-align: center; '
            'padding: 3rem 2rem; color: var(--text-muted); font-size: 0.85rem;">'
            "Select an item from the navigator to view details"
            "</div></div>",
            unsafe_allow_html=True,
        )
        return

    # --- Open the unified panel ---
    st.markdown('<div class="unit-panel">', unsafe_allow_html=True)

    # Section 1: Item header
    breadcrumb = ""
    if item.parent_chapter:
        breadcrumb += f"<span>{item.parent_chapter}</span> &rsaquo; "
    if item.parent_section:
        breadcrumb += f"<span>{item.parent_section}</span> &rsaquo; "
    breadcrumb += f"<span>{item.item_number}</span>"

    row_info = f"Row {item.excel_start_row}" if item.excel_start_row else ""

    st.markdown(
        f"""<div class="unit-section">
        <div style="display: flex; justify-content: space-between; align-items: baseline;">
            <div class="unit-section-header">Selected Item</div>
            <span style="font-family: var(--font-mono); font-size: 0.62rem; color: var(--text-muted);">{row_info}</span>
        </div>
        <div class="item-breadcrumb">{breadcrumb}</div>
        <div style="display: flex; align-items: baseline; gap: 0.4rem; margin-bottom: 0.4rem;">
            <span class="item-number-badge">{item.item_number}</span>
            <span class="item-title">{item.title}</span>
        </div>
        {"<div class='item-description'>" + item.description + "</div>" if item.description else ""}
        </div>""",
        unsafe_allow_html=True,
    )

    # Section 2: Priced lines table
    if item.priced_lines:
        st.markdown(
            '<div class="unit-section">'
            '<div class="unit-section-header">Priced Lines</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        rows = []
        for pl in item.priced_lines:
            price_display = (
                f"{pl.applied_price:.2f}"
                if pl.applied_price is not None
                else (f"{pl.unit_price:.2f}" if pl.unit_price is not None else "???")
            )
            total_display = f"{pl.total:.2f}" if pl.total is not None else "\u2014"
            rows.append(
                {
                    "R.BR": pl.item_number,
                    "OPIS": (
                        pl.description[:55] + "..."
                        if len(pl.description) > 55
                        else pl.description
                    ),
                    "JED": pl.unit,
                    "KOL": pl.quantity,
                    "JED.CIJ": price_display,
                    "UKUPNO": total_display,
                }
            )

        df = pd.DataFrame(rows)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=min(180, 38 + 35 * len(rows)),
        )

    # Section 3: Price stats
    stats = get_stats_for_selected()
    if stats:
        st.markdown(
            f"""<div class="unit-section">
            <div class="unit-section-header">Price Statistics</div>
            <div class="stats-row">
                <div class="stat-item">
                    <div class="stat-value">{stats.avg_price:,.2f}</div>
                    <div class="stat-label">AVG {stats.currency}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{stats.min_price:,.2f}</div>
                    <div class="stat-label">MIN {stats.currency}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{stats.max_price:,.2f}</div>
                    <div class="stat-label">MAX {stats.currency}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{stats.num_matches}</div>
                    <div class="stat-label">MATCHES</div>
                </div>
            </div>
            </div>""",
            unsafe_allow_html=True,
        )

    # Section 4: Confidence breakdown (from top match)
    matches = get_matches_for_selected()
    if matches:
        top = matches[0]
        bd = top.confidence_breakdown
        overall_pct = top.match_confidence * 100

        factors_html = ""
        for label, value in [
            ("Text Similarity", bd.text_similarity),
            ("Unit Match", bd.unit_match),
            ("Hierarchy", bd.hierarchy_match),
            ("Description", bd.description_overlap),
        ]:
            pct = value * 100
            factors_html += f"""
            <div class="confidence-breakdown-item">
                <div class="confidence-breakdown-label">
                    <span>{label}</span>
                    <span class="confidence-breakdown-value">{pct:.0f}%</span>
                </div>
                <div class="confidence-breakdown-bar">
                    <div class="confidence-breakdown-fill" style="width: {pct}%; opacity: {0.4 + 0.6 * value};"></div>
                </div>
            </div>"""

        st.markdown(
            f"""<div class="unit-section">
            <div class="unit-section-header">Confidence Breakdown</div>
            <div class="confidence-overall">{overall_pct:.0f}%</div>
            <div class="confidence-overall-label">Top Match Confidence</div>
            {factors_html}
            </div>""",
            unsafe_allow_html=True,
        )

    # Section 5: Agent reasoning log
    state = get_state()
    log: list[ReasoningEntryUI] = state.get("reasoning_log", [])
    if log:
        entries_html = ""
        for entry in reversed(log[-20:]):
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

        st.markdown(
            f"""<div class="unit-section">
            <div class="unit-section-header">Agent Activity</div>
            <div class="reasoning-container">{entries_html}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    # --- Close the unified panel ---
    st.markdown("</div>", unsafe_allow_html=True)
