"""Kleine Regressionstests für Dashboard-Kennzahlen (ohne Streamlit)."""
from __future__ import annotations

import dashboard_finance as df


def test_compute_dashboard_metrics_empty_month() -> None:
    m = df.compute_dashboard_metrics([], 2024, 6)
    assert m.year == 2024
    assert m.month == 6
    assert "2024" in m.month_label or "Juni" in m.month_label
    assert m.income_eur == 0.0
    assert m.expense_all_eur == 0.0
    assert m.saldo_eur == 0.0


def test_list_tile_rows_saldo_empty() -> None:
    lines = df.list_tile_rows([], "saldo", 2024, 6, monthly_only=False, strom_year=None)
    assert lines == []
