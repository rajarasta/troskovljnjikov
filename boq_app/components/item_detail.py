"""Center upper: selected item detail card."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ..state import get_selected_item


def render_item_detail() -> None:
    """Render the detail card for the currently selected BoQ item."""
    item = get_selected_item()

    if not item:
        st.markdown(
            '<div class="glass-panel" style="text-align: center; '
            'padding: 2rem; color: var(--text-muted); font-size: 0.85rem;">'
            "Select an item from the navigator"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    # Breadcrumb
    breadcrumb = ""
    if item.parent_chapter:
        breadcrumb += f'<span>{item.parent_chapter}</span> &rsaquo; '
    if item.parent_section:
        breadcrumb += f'<span>{item.parent_section}</span> &rsaquo; '
    breadcrumb += f"<span>{item.item_number}</span>"

    # Build card HTML
    html = f"""
    <div class="glass-panel">
        <div class="glass-panel-header">Selected Item &mdash; Row {item.excel_start_row or '—'}</div>
        <div class="item-breadcrumb">{breadcrumb}</div>
        <div style="display: flex; align-items: baseline; gap: 0.5rem; margin-bottom: 0.5rem;">
            <span class="item-number-badge">{item.item_number}</span>
            <span class="item-title">{item.title}</span>
        </div>
    """
    if item.description:
        html += f'<div class="item-description">{item.description}</div>'
    html += "</div>"

    st.markdown(html, unsafe_allow_html=True)

    # Priced lines table
    if item.priced_lines:
        rows = []
        for pl in item.priced_lines:
            price_display = (
                f"{pl.applied_price:.2f}"
                if pl.applied_price is not None
                else (f"{pl.unit_price:.2f}" if pl.unit_price is not None else "???")
            )
            total_display = (
                f"{pl.total:.2f}" if pl.total is not None else "—"
            )
            rows.append(
                {
                    "R.BR": pl.item_number,
                    "OPIS": pl.description[:60] + ("..." if len(pl.description) > 60 else ""),
                    "JED": pl.unit,
                    "KOL": pl.quantity,
                    "JED.CIJ": price_display,
                    "UKUPNO": total_display,
                }
            )

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True, height=min(200, 38 + 35 * len(rows)))
