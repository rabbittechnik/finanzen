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


def _tile_with_detail(html: str, tile_id: str, btn_key: str) -> None:
    st.markdown(html, unsafe_allow_html=True)
    if st.button("Details", key=btn_key, type="secondary"):
        _open_tile(tile_id)


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
    ov1, ov2 = st.columns([1, 1])
    with ov1:
        fy = st.number_input("Jahr", min_value=2000, max_value=2100, value=fy, key="dash_ov_y")
    with ov2:
        fm = st.selectbox(
            "Monat",
            list(range(1, 13)),
            index=max(0, min(11, fm - 1)),
            format_func=lambda x: str(x),
            key="dash_ov_m",
        )
    st.session_state[_DASH_Y_KEY] = fy
    st.session_state[_DASH_M_KEY] = fm
    y, m = fy, fm

    mets = compute_dashboard_metrics(rows, y, m)

    st.markdown(
        f'<h2 class="dash-main-title">Finanzübersicht – {mets.month_label}</h2>',
        unsafe_allow_html=True,
    )

    saldo_body = (
        f'<p class="{_money_class(mets.income_eur)}">Einnahmen: +{_fmt(mets.income_eur)}</p>'
        f'<p class="dash-money-neg">Ausgaben: −{_fmt(mets.expense_all_eur)}</p>'
        f'<p class="{_money_class(mets.saldo_eur)}"><strong>Saldo: {_fmt(mets.saldo_eur)}</strong></p>'
    )
    fix_body = (
        f"<p>Einnahmen: +{_fmt(mets.income_eur)}</p>"
        f"<p>Monatliche Ausgaben: −{_fmt(mets.expense_monthly_eur)}</p>"
        f'<p class="{_money_class(mets.fixkosten_result_eur)}"><strong>Ergebnis: {_fmt(mets.fixkosten_result_eur)}</strong></p>'
    )
    ein_body = f"<p><strong>{_fmt(mets.income_eur)}</strong></p><p>{mets.income_count} Eintrag/Einträge</p>"
    aus_body = f"<p><strong>{_fmt(mets.expense_all_eur)}</strong></p><p>{mets.expense_all_count} Belege (inkl. einmalig)</p>"
    sch_body = (
        f"<p><strong>{_fmt(mets.debt_open_eur)}</strong> offen</p>"
        f"<p>{mets.debt_open_docs} Dokument(e) · {mets.debt_open_count} Kennung(en) gruppiert</p>"
    )
    strom_body = (
        f"<p>Bezahlt (Jahr {mets.strom_year}): {_fmt(mets.strom_bezahlt_eur)}</p>"
        f"<p>Gefordert (offen): {_fmt(mets.strom_gefordert_eur)}</p>"
        f'<p class="{_money_class(mets.strom_diff_eur)}"><strong>Differenz: {_fmt(mets.strom_diff_eur)}</strong></p>'
        "<p class=\"dash-tile-note\">Positiv ≈ mehr gezahlt als offen gefordert; negativ ≈ Nachzahlung.</p>"
    )

    r1 = st.columns(3)
    with r1[0]:
        _tile_with_detail(_tile_html("Saldo (Monat)", saldo_body, "saldo"), "saldo", "dash_btn_saldo")
    with r1[1]:
        _tile_with_detail(_tile_html("Fixkosten-Saldo", fix_body, "fixkosten"), "fixkosten", "dash_btn_fix")
    with r1[2]:
        _tile_with_detail(_tile_html("Einnahmen (Monat)", ein_body, "income"), "einnahmen", "dash_btn_ein")

    r2 = st.columns(3)
    with r2[0]:
        _tile_with_detail(_tile_html("Ausgaben (Monat)", aus_body, "expense"), "ausgaben", "dash_btn_aus")
    with r2[1]:
        _tile_with_detail(_tile_html("Schulden", sch_body, "debt"), "schulden", "dash_btn_sch")
    with r2[2]:
        _tile_with_detail(
            _tile_html(f"Stromkosten {mets.strom_year}", strom_body, "strom"),
            "strom_jahr",
            "dash_btn_strom",
        )

    st.markdown('<p class="dash-section-label">Kategorien (Monat)</p>', unsafe_allow_html=True)
    cat_a = (
        f"<p><strong>{_fmt(mets.cat_haus_eur)}</strong></p>"
        "<p>Haustelefon / Internet</p>"
    )
    cat_b = f"<p><strong>{_fmt(mets.cat_handy_eur)}</strong></p><p>Handy</p>"
    cat_c = f"<p><strong>{_fmt(mets.cat_vers_eur)}</strong></p><p>Versicherungen</p>"
    r3 = st.columns(3)
    with r3[0]:
        _tile_with_detail(_tile_html("Haus & Internet", cat_a, "haus"), "haus", "dash_btn_haus")
    with r3[1]:
        _tile_with_detail(_tile_html("Handy", cat_b, "handy"), "handy", "dash_btn_handy")
    with r3[2]:
        _tile_with_detail(_tile_html("Versicherungen", cat_c, "vers"), "versicherungen", "dash_btn_vers")

    oep = f"<p><strong>{_fmt(mets.cat_oepnv_eur)}</strong></p><p>ÖPNV (Schriftverkehr + Stichworte)</p>"
    _tile_with_detail(
        f'<div class="dash-grid-1"><div class="dash-tile-outer">{_tile_html("ÖPNV", oep, "oepnv")}</div></div>',
        "oepnv",
        "dash_btn_oepnv",
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
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        fy = st.number_input("Jahr", min_value=2000, max_value=2100, value=fy, key="dash_det_y")
        st.session_state[_DASH_Y_KEY] = fy
    with c2:
        fm = st.selectbox(
            "Monat",
            list(range(1, 13)),
            index=max(0, min(11, fm - 1)),
            format_func=lambda x: str(x),
            key="dash_det_m",
        )
        st.session_state[_DASH_M_KEY] = fm
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
