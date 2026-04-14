"""Aggregation nach Zuordnung."""
from __future__ import annotations

from household_aggregate import aggregate_owner_totals


def test_aggregate_splits_person_and_unassigned() -> None:
    rows = [
        {
            "category": "other",
            "nav_folder": "rechnungen",
            "document_kind": "invoice",
            "primary_amount_eur": 100.0,
            "owner_kind": "person",
            "owner_person_id": 1,
            "owner_household_id": None,
        },
        {
            "category": "other",
            "nav_folder": "rechnungen",
            "document_kind": "invoice",
            "primary_amount_eur": 50.0,
            "owner_kind": None,
            "owner_person_id": None,
            "owner_household_id": None,
        },
    ]
    agg = aggregate_owner_totals(rows)
    assert agg["totals_by_key"]["person:1"] == 100.0
    assert agg["totals_by_key"]["unassigned"] == 50.0
    assert agg["grand_expense_eur"] == 150.0
