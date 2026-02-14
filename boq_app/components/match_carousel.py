"""Left panel: match carousel with stacked layered cards."""

from __future__ import annotations

import streamlit as st

from ..models import HistoricMatchUI, MatchStatus
from ..state import get_matches_for_selected, get_state


def render_match_carousel() -> None:
    """Render the match carousel with stacked cards and sub-layering."""
    state = get_state()
    matches = get_matches_for_selected()

    # Header with match count
    n = len(matches)
    st.markdown(
        '<div class="glass-panel">'
        '<div class="glass-panel-header">'
        f'Historical Matches &middot; <span style="color: var(--accent-primary);">{n}</span>'
        "</div>",
        unsafe_allow_html=True,
    )

    if not matches:
        st.markdown(
            '<div style="color: var(--text-muted); font-size: 0.78rem; '
            'text-align: center; padding: 2rem 0;">'
            "Select an item to find matches</div></div>",
            unsafe_allow_html=True,
        )
        return

    st.markdown("</div>", unsafe_allow_html=True)

    # Render each match as a carousel card with stacked depth effect
    for i, match in enumerate(matches):
        is_first = i == 0
        _render_carousel_card(i, match, is_first, len(matches) - i)


def _render_carousel_card(
    idx: int, match: HistoricMatchUI, is_first: bool, remaining: int
) -> None:
    """Render a single carousel card with optional stack effect."""
    pct = match.match_confidence * 100
    bar_class = "high" if pct >= 70 else ("medium" if pct >= 50 else "low")

    # Delta badge
    delta = match.qty_delta_pct
    if abs(delta) <= 10:
        delta_class = "neutral"
    elif delta > 0:
        delta_class = "positive"
    else:
        delta_class = "negative"
    delta_sign = "+" if delta > 0 else ""

    # Price
    price_str = f"{match.avg_unit_price:,.2f}" if match.avg_unit_price else "\u2014"
    total_str = f"{match.total:,.2f}" if match.total else "\u2014"

    # Stack wrapper on first card only (shows cards behind)
    stack_open = '<div class="carousel-stack">' if is_first and remaining > 1 else ""
    stack_close = "</div>" if is_first and remaining > 1 else ""

    active_class = " active" if is_first else ""

    html = f"""{stack_open}
    <div class="carousel-card{active_class}">
        <div class="carousel-header">
            <span class="carousel-source">{match.source_file}</span>
            <span class="carousel-year">{match.year or '\u2014'}</span>
            <span class="carousel-confidence">{pct:.0f}%</span>
        </div>
        <div class="confidence-bar">
            <div class="confidence-bar-fill {bar_class}" style="width: {pct}%"></div>
        </div>
        <div class="carousel-meta">
            <span class="delta-badge {delta_class}">QTY: {delta_sign}{delta:.0f}%</span>
            <span class="carousel-price">{price_str} <span class="cur">EUR</span></span>
            <span class="carousel-price" style="margin-left: auto;">{total_str} <span class="cur">EUR</span></span>
        </div>
    </div>
    {stack_close}"""

    st.markdown(html, unsafe_allow_html=True)

    # Action buttons
    b_left, b_right = st.columns(2)
    with b_left:
        expand_key = f"carousel_exp_{idx}"
        if st.button("DETAILS", key=f"car_more_{idx}", use_container_width=True):
            st.session_state[expand_key] = not st.session_state.get(expand_key, False)
            st.rerun()
    with b_right:
        if st.button("APPLY", key=f"car_apply_{idx}", type="primary", use_container_width=True):
            _apply_match(match)
            st.rerun()

    # Expanded sub-layer detail
    if st.session_state.get(f"carousel_exp_{idx}", False):
        _render_sublayer(match)


def _render_sublayer(match: HistoricMatchUI) -> None:
    """Render the expanded sub-layer with matched line details."""
    if not match.matched_lines:
        return

    rows = ""
    for line in match.matched_lines:
        price = f"{line.unit_price:,.2f}" if line.unit_price is not None else "\u2014"
        total = f"{line.total:,.2f}" if line.total is not None else "\u2014"
        desc = line.description[:70] + ("..." if len(line.description) > 70 else "")
        rows += f"""
        <tr>
            <td class="mono">{line.item_number}</td>
            <td>{desc}</td>
            <td class="mono" style="text-align:center;">{line.unit_of_measure}</td>
            <td class="mono" style="text-align:right;">{line.quantity}</td>
            <td class="price">{price}</td>
            <td class="price">{total}</td>
        </tr>"""

    html = f"""
    <div class="carousel-detail">
        <table class="carousel-detail-table">
            <thead><tr>
                <th>R.BR</th><th>OPIS</th><th>JED</th>
                <th style="text-align:right;">KOL</th>
                <th style="text-align:right;">JED.CIJ</th>
                <th style="text-align:right;">UKUPNO</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>"""
    st.markdown(html, unsafe_allow_html=True)


def _apply_match(match: HistoricMatchUI) -> None:
    """Apply match prices to the selected item."""
    state = get_state()
    sel_id = state.get("selected_item_id")
    if not sel_id or not state.get("parsed_file"):
        return

    applied = state.setdefault("applied_prices", {})
    item_applied = applied.setdefault(sel_id, {})

    for hist_line in match.matched_lines:
        if hist_line.unit_price is not None:
            item_applied[hist_line.item_number] = hist_line.unit_price

    for item in state["parsed_file"].items:
        if item.id == sel_id:
            for pl in item.priced_lines:
                if pl.item_number in item_applied:
                    pl.applied_price = item_applied[pl.item_number]
                    pl.unit_price = item_applied[pl.item_number]
                    pl.total = pl.quantity * pl.unit_price
            item.match_status = MatchStatus.APPLIED
            break
