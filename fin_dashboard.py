"""Neues Finanz-Dashboard (fin-* nur); nutzt dashboard_finance für Kennzahlen."""
from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from dashboard_finance import compute_dashboard_metrics, list_tile_rows
from db import get_document
from download_button import render_document_download

FIN_TILE_KEY = "fin_dash_tile"
FIN_MO_KEY = "fin_dash_monthly_only"

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
        return "fin-num-pos"
    if v < -1e-6:
        return "fin-num-neg"
    return "fin-num-zero"


def _card_html(title: str, body_html: str, accent: str, tile_id: str) -> str:
    return (
        f'<a class="fin-metric-link" href="?fin_tile={tile_id}">'
        f'<div class="fin-metric-card" data-fin-accent="{accent}">'
        f'<div class="fin-metric-title">{title}</div>'
        f'<div class="fin-metric-body">{body_html}</div>'
        "</div></a>"
    )


def _row_metric_actions(html: str) -> None:
    st.markdown(html, unsafe_allow_html=True)


def _grid_row3(a: str, b: str, c: str) -> None:
    cols = st.columns(3, gap="medium")
    for col, pack in zip(cols, (a, b, c), strict=True):
        with col:
            _row_metric_actions(pack)


def _close_tile() -> None:
    st.session_state.pop(FIN_TILE_KEY, None)
    st.rerun()


def _ctx_ym() -> tuple[int, int]:
    t = date.today()
    if "fin_ctx_year" not in st.session_state:
        st.session_state.fin_ctx_year = t.year
    if "fin_ctx_month" not in st.session_state:
        st.session_state.fin_ctx_month = t.month
    return int(st.session_state.fin_ctx_year), int(st.session_state.fin_ctx_month)


def render_fin_dashboard(rows: list[dict[str, Any]]) -> None:
    """Übersicht oder Kachel-Detail; Jahr/Monat kommen aus fin_ctx_* (Top-Bar)."""
    y, m = _ctx_ym()
    q_tile = str(st.query_params.get("fin_tile") or "").strip()
    if q_tile:
        st.session_state[FIN_TILE_KEY] = q_tile
        try:
            del st.query_params["fin_tile"]
        except Exception:
            pass
    tile = st.session_state.get(FIN_TILE_KEY)

    if tile:
        _render_detail(rows, tile, y, m)
        return

    mets = compute_dashboard_metrics(rows, y, m)

    st.markdown(
        f'<h2 class="fin-section-title">Finanzübersicht – {mets.month_label}</h2>',
        unsafe_allow_html=True,
    )

    saldo_body = (
        f'<p class="{_money_class(mets.income_eur)}">Ordner Einnahmen: +{_fmt(mets.income_eur)}</p>'
        f'<p class="fin-num-neg">Ausgaben: −{_fmt(mets.expense_all_eur)}</p>'
        f'<p class="{_money_class(mets.saldo_eur)}"><strong>Saldo: {_fmt(mets.saldo_eur)}</strong></p>'
    )
    fix_body = (
        f"<p>Einnahmen: +{_fmt(mets.income_eur)}</p>"
        f"<p>Monatliche Ausgaben: −{_fmt(mets.expense_monthly_eur)}</p>"
        f'<p class="{_money_class(mets.fixkosten_result_eur)}"><strong>Ergebnis: {_fmt(mets.fixkosten_result_eur)}</strong></p>'
    )
    ein_body = (
        f'<p class="fin-num-lg">{_fmt(mets.income_eur)}</p>'
        f"<p>{mets.income_count} Eintrag/Einträge</p>"
    )
    aus_body = (
        f'<p class="fin-num-lg">{_fmt(mets.expense_all_eur)}</p>'
        f"<p>{mets.expense_all_count} Belege (inkl. einmalig)</p>"
    )
    sch_body = (
        f"<p><strong>{_fmt(mets.debt_open_eur)}</strong> offen</p>"
        '<p class="fin-note fin-note-metric">Unabhängig vom Monat oben: alle offenen '
        "Mahnungen/Forderungen. Verschwindet bei „bezahlt“ oder über "
        "verknüpfte Zahlungsbelege.</p>"
        f"<p>{mets.debt_open_docs} Dokument(e) · {mets.debt_open_count} Kennung(en) gruppiert</p>"
    )
    strom_body = (
        f"<p>Bezahlt (Jahr {mets.strom_year}): {_fmt(mets.strom_bezahlt_eur)}</p>"
        f"<p>Gefordert (offen): {_fmt(mets.strom_gefordert_eur)}</p>"
        f'<p class="{_money_class(mets.strom_diff_eur)}"><strong>Differenz: {_fmt(mets.strom_diff_eur)}</strong></p>'
        '<p class="fin-note">Positiv = mehr gezahlt als offen gefordert, negativ = Nachzahlung.</p>'
    )

    _grid_row3(
        _card_html("Saldo (Monat)", saldo_body, "saldo", "saldo"),
        _card_html("Fixkosten-Saldo", fix_body, "fix", "fixkosten"),
        _card_html("Einnahmen (Monat)", ein_body, "in", "einnahmen"),
    )
    _grid_row3(
        _card_html("Ausgaben (Monat)", aus_body, "aus", "ausgaben"),
        _card_html("Schulden", sch_body, "sch", "schulden"),
        _card_html(f"Stromkosten {mets.strom_year}", strom_body, "strom", "strom_jahr"),
    )

    st.markdown(
        '<p class="fin-section-kicker">Kategorien (Monat)</p>',
        unsafe_allow_html=True,
    )
    cat_a = f"<p><strong>{_fmt(mets.cat_haus_eur)}</strong></p><p>Haustelefon / Internet</p>"
    cat_b = f"<p><strong>{_fmt(mets.cat_handy_eur)}</strong></p><p>Handy</p>"
    cat_c = f"<p><strong>{_fmt(mets.cat_vers_eur)}</strong></p><p>Versicherungen</p>"
    cat_d = (
        f"<p><strong>{_fmt(mets.cat_oepnv_eur)}</strong></p>"
        "<p>ÖPNV (Schriftverkehr + Stichworte)</p>"
    )
    c4 = st.columns(4, gap="small")
    cat_packs = (
        _card_html("Haus & Internet", cat_a, "haus", "haus"),
        _card_html("Handy", cat_b, "handy", "handy"),
        _card_html("Versicherungen", cat_c, "vers", "versicherungen"),
        _card_html("ÖPNV", cat_d, "oep", "oepnv"),
    )
    for col, pack in zip(c4, cat_packs, strict=True):
        with col:
            _row_metric_actions(pack)


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
    if not tile:
        return
    st.markdown(
        f'<h2 class="fin-section-title">{titles.get(tile, tile)}</h2>',
        unsafe_allow_html=True,
    )
    if st.button("← Zurück zur Übersicht", key="fin_dash_back"):
        _close_tile()
        return

    fy, fm = _ctx_ym()
    y_opts = list(range(2000, 2101))
    y_idx = min(max(0, fy - 2000), len(y_opts) - 1)
    m_opts = list(range(1, 13))
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        fy = st.selectbox("Jahr", y_opts, index=y_idx, key="fin_det_y")
        st.session_state.fin_ctx_year = int(fy)
    with c2:
        fm = st.selectbox(
            "Monat",
            m_opts,
            index=max(0, min(11, fm - 1)),
            format_func=lambda x: _MONTH_DE[x - 1],
            key="fin_det_m",
        )
        st.session_state.fin_ctx_month = int(fm)
    with c3:
        if FIN_MO_KEY not in st.session_state:
            st.session_state[FIN_MO_KEY] = False
        show_mo = st.checkbox(
            "Nur monatliche Ausgaben (in der Liste)",
            value=bool(st.session_state.get(FIN_MO_KEY, False)),
            key="fin_det_mo",
        )
        st.session_state[FIN_MO_KEY] = show_mo

    lines = list_tile_rows(
        rows,
        tile,
        int(fy),
        int(fm),
        monthly_only=show_mo,
        strom_year=int(fy) if tile == "strom_jahr" else None,
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
    st.markdown('<p class="fin-section-kicker">Downloads (Original-PDF)</p>', unsafe_allow_html=True)
    for z in lines:
        drow = get_document(int(z["id"]))
        if not drow:
            continue
        r1, r2 = st.columns([2.2, 1])
        with r1:
            st.caption(f"#{z['id']} · {z['filename']} · {_fmt(z['amount_eur'])}")
        with r2:
            render_document_download(drow, key_prefix=f"findet_{tile}_{z['id']}")
