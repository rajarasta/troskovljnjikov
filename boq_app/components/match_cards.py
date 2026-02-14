"""Center lower: historical match result cards."""

from __future__ import annotations

import streamlit as st

from ..models import HistoricMatchUI
from ..state import get_matches_for_selected, get_state


def render_match_cards() -> None:
    """Render match result cards for the selected item."""
    matches = get_matches_for_selected()

    st.markdown(
        '<div class="glass-panel">'
        '<div class="glass-panel-header">Matching Results from Historical Files</div>',
        unsafe_allow_html=True,
    )

    if not matches:
        st.markdown(
            '<div style="color: var(--text-muted); font-size: 0.8rem; '
            'padding: 0.5rem 0; text-align: center;">'
            "No matches found</div></div>",
            unsafe_allow_html=True,
        )
        return

    st.markdown("</div>", unsafe_allow_html=True)

    for i, match in enumerate(matches):
        _render_single_card(i, match)


def _render_single_card(idx: int, match: HistoricMatchUI) -> None:
    """Render a single match card."""
    pct = match.match_confidence * 100
    bar_width = match.match_confidence * 100

    if pct >= 75:
        bar_class = "high"
    elif pct >= 50:
        bar_class = "medium"
    else:
        bar_class = "low"

    # QTY delta badge
    delta = match.qty_delta_pct
    if abs(delta) <= 10:
        delta_class = "neutral"
    elif delta > 0:
        delta_class = "positive"
    else:
        delta_class = "negative"
    delta_sign = "+" if delta > 0 else ""
    delta_text = f"QTY: {delta_sign}{delta:.0f}%"

    # Price display
    price_str = f"{match.avg_unit_price:,.2f}" if match.avg_unit_price else "—"
    total_str = f"{match.total:,.2f}" if match.total else "—"

    html = f"""
    <div class="match-card">
        <div class="match-card-header">
            <span class="match-source">{match.source_file}</span>
            <span class="match-year-badge">{match.year or '—'}</span>
            <span class="match-confidence">{pct:.0f}%</span>
        </div>
        <div class="confidence-bar">
            <div class="confidence-bar-fill {bar_class}" style="width: {bar_width}%"></div>
        </div>
        <div class="match-meta">
            <span class="delta-badge {delta_class}">{delta_text}</span>
            <span class="match-price">{price_str} <span class="currency">EUR</span></span>
            <span class="match-price" style="margin-left: auto;">{total_str} <span class="currency">EUR</span></span>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    # Action buttons
    btn_left, btn_right = st.columns(2)
    with btn_left:
        expand_key = f"expanded_{idx}"
        if st.button("DETAILS", key=f"more_{idx}", use_container_width=True):
            current = st.session_state.get(expand_key, False)
            st.session_state[expand_key] = not current
            st.rerun()
    with btn_right:
        if st.button("APPLY", key=f"apply_{idx}", type="primary", use_container_width=True):
            _apply_match(match)
            st.rerun()

    # Expanded detail
    if st.session_state.get(f"expanded_{idx}", False):
        _render_expanded_detail(match)


def _render_expanded_detail(match: HistoricMatchUI) -> None:
    """Render expanded match detail with individual line items."""
    if not match.matched_lines:
        return

    lines_html = ""
    for line in match.matched_lines:
        price = f"{line.unit_price:,.2f}" if line.unit_price is not None else "—"
        total = f"{line.total:,.2f}" if line.total is not None else "—"
        desc = line.description[:80] + ("..." if len(line.description) > 80 else "")
        lines_html += f"""
        <tr>
            <td style="padding: 4px 8px; font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-muted);">{line.item_number}</td>
            <td style="padding: 4px 8px; font-size: 0.78rem; color: var(--text-secondary);">{desc}</td>
            <td style="padding: 4px 8px; font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-muted); text-align: center;">{line.unit_of_measure}</td>
            <td style="padding: 4px 8px; font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-primary); text-align: right;">{line.quantity}</td>
            <td style="padding: 4px 8px; font-family: var(--font-mono); font-size: 0.75rem; color: var(--accent-primary); text-align: right;">{price}</td>
            <td style="padding: 4px 8px; font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-primary); text-align: right;">{total}</td>
        </tr>
        """

    html = f"""
    <div style="margin: 0.5rem 0 0.75rem 0; padding: 0.5rem; background: var(--bg-input);
                border-radius: var(--radius-badge); border: 1px solid var(--border-subtle);">
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="border-bottom: 1px solid var(--border-subtle);">
                    <th style="padding: 4px 8px; font-size: 0.68rem; color: var(--text-muted); text-align: left; text-transform: uppercase; letter-spacing: 0.05em;">R.BR</th>
                    <th style="padding: 4px 8px; font-size: 0.68rem; color: var(--text-muted); text-align: left; text-transform: uppercase; letter-spacing: 0.05em;">OPIS</th>
                    <th style="padding: 4px 8px; font-size: 0.68rem; color: var(--text-muted); text-align: center; text-transform: uppercase; letter-spacing: 0.05em;">JED</th>
                    <th style="padding: 4px 8px; font-size: 0.68rem; color: var(--text-muted); text-align: right; text-transform: uppercase; letter-spacing: 0.05em;">KOL</th>
                    <th style="padding: 4px 8px; font-size: 0.68rem; color: var(--text-muted); text-align: right; text-transform: uppercase; letter-spacing: 0.05em;">JED.CIJ</th>
                    <th style="padding: 4px 8px; font-size: 0.68rem; color: var(--text-muted); text-align: right; text-transform: uppercase; letter-spacing: 0.05em;">UKUPNO</th>
                </tr>
            </thead>
            <tbody>{lines_html}</tbody>
        </table>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def _apply_match(match: HistoricMatchUI) -> None:
    """Apply match prices to the selected item's priced lines."""
    state = get_state()
    sel_id = state.get("selected_item_id")
    if not sel_id or not state.get("parsed_file"):
        return

    applied = state.setdefault("applied_prices", {})
    item_applied = applied.setdefault(sel_id, {})

    for hist_line in match.matched_lines:
        if hist_line.unit_price is not None:
            item_applied[hist_line.item_number] = hist_line.unit_price

    # Update the parsed file's priced lines with applied prices
    for item in state["parsed_file"].items:
        if item.id == sel_id:
            for pl in item.priced_lines:
                if pl.item_number in item_applied:
                    pl.applied_price = item_applied[pl.item_number]
                    pl.unit_price = item_applied[pl.item_number]
                    pl.total = pl.quantity * pl.unit_price
            from ..models import MatchStatus
            item.match_status = MatchStatus.APPLIED
            break
