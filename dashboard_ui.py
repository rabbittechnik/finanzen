"""Finanz-Dashboard: große Kacheln + Detailansicht (mittlere Spalte)."""
from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from dashboard_finance import compute_dashboard_metrics, list_tile_rows
from db import get_document
from download_button import render_document_download

_DASH_TILE_KEY = "dash_fin_tile"
_DASH_Y_KEY = "dash_fin_y"
_DASH_M_KEY = "dash_fin_m"
_DASH_MO_KEY = "dash_fin_monthly_only"

_MONTH_DE = (
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
)


def _fmt(v: float) -> str:
    return f"{v:.2f} €".replace(".", ",")


def _money_class(v: float) -> str:
    if v > 1e-6:
        return "dash-money-pos"
    if v < -1e-6:
        return "dash-money-neg"
    return "dash-money-zero"


def _tile_html(title: str, body_html: str, variant: str) -> str:
    """variant: saldo | fixkosten | income | expense | debt | strom | haus | handy | vers | oepnv"""
    return (
        f'<div class="dash-tile-inner dash-tile--{variant}">'
        f'<div class="dash-tile-title">{title}</div>'
        f'<div class="dash-tile-body">{body_html}</div></div>'
    )


def _dash_three_tiles(
    a: tuple[str, str, str],
    b: tuple[str, str, str],
    c: tuple[str, str, str],
) -> None:
    """Drei Kacheln in einer Zeile; je Kachel Markdown + Details unten rechts."""
    cols = st.columns(3, gap="medium")
    for col, pack in zip(cols, (a, b, c), strict=True):
        html_s, tile_id, btn_key = pack
        with col:
            st.markdown(html_s, unsafe_allow_html=True)
            r1, r2 = st.columns([2.0, 1.05])
            with r1:
                st.empty()
            with r2:
                if st.button("Details", key=btn_key, type="secondary", use_container_width=True):
                    _open_tile(tile_id)


def _dash_tile_wide_plus_strom(
    left_html: str,
    left_tile: str,
    left_key: str,
    right_html: str,
    right_tile: str,
    right_key: str,
) -> None:
    """Untere Zeile: breitere linke Kachel + Strom rechts."""
    c1, c2 = st.columns([1.55, 1.0], gap="medium")
    with c1:
        st.markdown(left_html, unsafe_allow_html=True)
        r1, r2 = st.columns([2.0, 1.05])
        with r1:
            st.empty()
        with r2:
            if st.button("Details", key=left_key, type="secondary", use_container_width=True):
                _open_tile(left_tile)
    with c2:
        st.markdown(right_html, unsafe_allow_html=True)
        r1, r2 = st.columns([2.0, 1.05])
        with r1:
            st.empty()
        with r2:
            if st.button("Details", key=right_key, type="secondary", use_container_width=True):
                _open_tile(right_tile)


def _open_tile(tile_id: str) -> None:
    st.session_state[_DASH_TILE_KEY] = tile_id
    st.rerun()


def _close_tile() -> None:
    st.session_state.pop(_DASH_TILE_KEY, None)
    st.rerun()


def _ensure_filter_defaults() -> tuple[int, int]:
    t = date.today()
    if _DASH_Y_KEY not in st.session_state:
        st.session_state[_DASH_Y_KEY] = t.year
    if _DASH_M_KEY not in st.session_state:
        st.session_state[_DASH_M_KEY] = t.month
    if _DASH_MO_KEY not in st.session_state:
        st.session_state[_DASH_MO_KEY] = False
    return int(st.session_state[_DASH_Y_KEY]), int(st.session_state[_DASH_M_KEY])


def render_finance_dashboard(rows: list[dict[str, Any]]) -> None:
    """Home: Kachel-Übersicht oder Detail (Session-State)."""
    y, m = _ensure_filter_defaults()
    tile = st.session_state.get(_DASH_TILE_KEY)

    if tile:
        _render_detail(rows, tile, y, m)
        return

    fy = int(st.session_state[_DASH_Y_KEY])
    fm = int(st.session_state[_DASH_M_KEY])
    y_opts = list(range(2000, 2101))
    y_idx = min(max(0, fy - 2000), len(y_opts) - 1)
    m_opts = list(range(1, 13))

    f1, f2 = st.columns([1, 1])
    with f1:
        fy = st.selectbox("Jahr", y_opts, index=y_idx, key="dash_ov_y")
    with f2:
        fm = st.selectbox(
            "Monat",
            m_opts,
            index=max(0, min(11, fm - 1)),
            format_func=lambda x: _MONTH_DE[x - 1],
            key="dash_ov_m",
        )
    st.session_state[_DASH_Y_KEY] = int(fy)
    st.session_state[_DASH_M_KEY] = int(fm)
    y, m = int(fy), int(fm)

    if st.button("Update", key="dash_fin_update", type="primary", use_container_width=True):
        st.rerun()

    mets = compute_dashboard_metrics(rows, y, m)

    st.markdown(
        f'<h2 class="dash-main-title">Finanzübersicht – {mets.month_label}</h2>',
        unsafe_allow_html=True,
    )

    saldo_body = (
        f'<p class="{_money_class(mets.income_eur)}">Ordner Einnahmen: +{_fmt(mets.income_eur)}</p>'
        f'<p class="dash-money-neg">Ausgaben: −{_fmt(mets.expense_all_eur)}</p>'
        f'<p class="{_money_class(mets.saldo_eur)}"><strong>Saldo: {_fmt(mets.saldo_eur)}</strong></p>'
    )
    fix_body = (
        f"<p>Einnahmen: +{_fmt(mets.income_eur)}</p>"
        f"<p>Monatliche Ausgaben: −{_fmt(mets.expense_monthly_eur)}</p>"
        f'<p class="{_money_class(mets.fixkosten_result_eur)}"><strong>Ergebnis: {_fmt(mets.fixkosten_result_eur)}</strong></p>'
    )
    ein_body = (
        f'<p class="dash-tile-hero-amt">{_fmt(mets.income_eur)}</p>'
        f"<p>{mets.income_count} Eintrag/Einträge</p>"
    )
    aus_body = (
        f'<p class="dash-tile-hero-amt">{_fmt(mets.expense_all_eur)}</p>'
        f"<p>{mets.expense_all_count} Belege (inkl. einmalig)</p>"
    )
    sch_body = (
        f"<p><strong>{_fmt(mets.debt_open_eur)}</strong> offen</p>"
        f"<p>{mets.debt_open_docs} Dokument(e) · {mets.debt_open_count} Kennung(en) gruppiert</p>"
    )
    strom_body = (
        f"<p>Bezahlt (Jahr {mets.strom_year}): {_fmt(mets.strom_bezahlt_eur)}</p>"
        f"<p>Gefordert (offen): {_fmt(mets.strom_gefordert_eur)}</p>"
        f'<p class="{_money_class(mets.strom_diff_eur)}"><strong>Differenz: {_fmt(mets.strom_diff_eur)}</strong></p>'
        '<p class="dash-tile-note">Positiv = mehr gezahlt als offen gefordert, negativ = Nachzahlung.</p>'
    )

    _dash_three_tiles(
        (
            _tile_html("Saldo (Monat)", saldo_body, "saldo"),
            "saldo",
            "dash_btn_saldo",
        ),
        (
            _tile_html("Fixkosten-Saldo", fix_body, "fixkosten"),
            "fixkosten",
            "dash_btn_fix",
        ),
        (
            _tile_html("Einnahmen (Monat)", ein_body, "income"),
            "einnahmen",
            "dash_btn_ein",
        ),
    )

    st.markdown(
        '<p class="dash-section-label dash-section-label--cats">KATEGORIEN (MONAT)</p>',
        unsafe_allow_html=True,
    )
    cat_a = f"<p><strong>{_fmt(mets.cat_haus_eur)}</strong></p><p>Haustelefon / Internet</p>"
    cat_b = f"<p><strong>{_fmt(mets.cat_handy_eur)}</strong></p><p>Handy</p>"

    _dash_three_tiles(
        (
            _tile_html("Haus & Internet", cat_a, "haus"),
            "haus",
            "dash_btn_haus",
        ),
        (
            _tile_html("Handy", cat_b, "handy"),
            "handy",
            "dash_btn_handy",
        ),
        (
            _tile_html("Schulden", sch_body, "debt"),
            "schulden",
            "dash_btn_sch",
        ),
    )

    wide_haus = _tile_html(
        "Kategorien (Monat) – Haus & Internet",
        cat_a,
        "haus",
    )
    _dash_tile_wide_plus_strom(
        wide_haus,
        "haus",
        "dash_btn_haus_wide",
        _tile_html(f"Stromkosten {mets.strom_year}", strom_body, "strom"),
        "strom_jahr",
        "dash_btn_strom",
    )

    with st.expander("Weitere Kennzahlen (Ausgaben, Versicherungen, ÖPNV)", expanded=False):
        cat_vers = f"<p><strong>{_fmt(mets.cat_vers_eur)}</strong></p><p>Versicherungen</p>"
        oep = (
            f"<p><strong>{_fmt(mets.cat_oepnv_eur)}</strong></p>"
            "<p>ÖPNV (Schriftverkehr + Stichworte)</p>"
        )
        _dash_three_tiles(
            (
                _tile_html("Ausgaben (Monat)", aus_body, "expense"),
                "ausgaben",
                "dash_btn_aus",
            ),
            (
                _tile_html("Versicherungen", cat_vers, "vers"),
                "versicherungen",
                "dash_btn_vers",
            ),
            (
                _tile_html("ÖPNV", oep, "oepnv"),
                "oepnv",
                "dash_btn_oepnv",
            ),
        )


def _render_detail(rows: list[dict[str, Any]], tile: str, y: int, m: int) -> None:
    titles = {
        "saldo": "Saldo (Monat)",
        "fixkosten": "Fixkosten-Saldo",
        "einnahmen": "Einnahmen",
        "ausgaben": "Ausgaben",
        "schulden": "Schulden",
        "strom_jahr": "Stromkosten (Jahr)",
        "haus": "Haus & Internet",
        "handy": "Handy",
        "versicherungen": "Versicherungen",
        "oepnv": "ÖPNV",
    }
    st.markdown(
        f'<h2 class="dash-main-title">{titles.get(tile, tile)}</h2>',
        unsafe_allow_html=True,
    )
    if st.button("← Zurück zur Übersicht", key="dash_back"):
        _close_tile()
        return

    fy = int(st.session_state.get(_DASH_Y_KEY, y))
    fm = int(st.session_state.get(_DASH_M_KEY, m))
    y_opts = list(range(2000, 2101))
    y_idx = min(max(0, fy - 2000), len(y_opts) - 1)
    m_opts = list(range(1, 13))
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        fy = st.selectbox("Jahr", y_opts, index=y_idx, key="dash_det_y")
        st.session_state[_DASH_Y_KEY] = int(fy)
    with c2:
        fm = st.selectbox(
            "Monat",
            m_opts,
            index=max(0, min(11, fm - 1)),
            format_func=lambda x: _MONTH_DE[x - 1],
            key="dash_det_m",
        )
        st.session_state[_DASH_M_KEY] = int(fm)
    with c3:
        show_mo = st.checkbox(
            "Nur monatliche Ausgaben (in der Liste)",
            value=bool(st.session_state.get(_DASH_MO_KEY, False)),
            key="dash_det_mo",
        )
        st.session_state[_DASH_MO_KEY] = show_mo

    lines = list_tile_rows(
        rows,
        tile,
        fy,
        fm,
        monthly_only=show_mo,
        strom_year=fy if tile == "strom_jahr" else None,
    )
    if not lines:
        st.info("Keine passenden Einträge für die Auswahl.")
        return
    st.caption(f"{len(lines)} Zeile(n) — Tab **Dokumente** zum Bearbeiten einzelner PDFs.")
    st.dataframe(
        [
            {
                "ID": z["id"],
                "Datei": z["filename"],
                "Betrag": _fmt(z["amount_eur"]),
                "Datum": z["document_date"],
                "Ablage": z["nav"],
                "Art": z["kind"],
                "Monatlich": z["monthly"],
            }
            for z in lines
        ],
        use_container_width=True,
        hide_index=True,
    )
    st.markdown('<p class="dash-section-label">Downloads (Original-PDF)</p>', unsafe_allow_html=True)
    for z in lines:
        drow = get_document(int(z["id"]))
        if not drow:
            continue
        r1, r2 = st.columns([2.2, 1])
        with r1:
            st.caption(f"#{z['id']} · {z['filename']} · {_fmt(z['amount_eur'])}")
        with r2:
            render_document_download(drow, key_prefix=f"dashdet_{tile}_{z['id']}")
