"""Tests für strukturierte Dokumentensuche (ohne echte DB)."""
from __future__ import annotations

from unittest.mock import patch

from document_search import documents_as_assistant_rows, search_documents

_ROWS: list[dict] = [
    {
        "id": 10,
        "original_filename": "r1.pdf",
        "stored_path": "/x/r1.pdf",
        "category": "legal",
        "document_kind": "invoice",
        "sender_name": "Kanzlei Heuberger",
        "sender_role": "lawyer",
        "subject": "Rechnung",
        "summary_de": "Beratung",
        "document_date": "2024-06-15",
        "primary_amount_eur": 250.0,
        "nav_folder": "schriftverkehr",
        "folder_sub": None,
        "zahlstatus": "offen",
    },
    {
        "id": 11,
        "original_filename": "strom.pdf",
        "stored_path": "/x/strom.pdf",
        "category": "energy",
        "document_kind": "invoice",
        "sender_name": "Stadtwerke Nord",
        "sender_role": "utility",
        "subject": "Strom Juni",
        "summary_de": "Abschlag",
        "document_date": "2024-08-01",
        "primary_amount_eur": 89.5,
        "nav_folder": "stromanbieter",
        "folder_sub": "Stadtwerke Nord",
        "zahlstatus": "bezahlt",
    },
    {
        "id": 12,
        "original_filename": "m1.pdf",
        "stored_path": "/x/m1.pdf",
        "category": "other",
        "document_kind": "reminder",
        "sender_name": "Inkasso",
        "sender_role": "collection_agency",
        "subject": "Mahnung",
        "summary_de": "Zahlungserinnerung",
        "document_date": "2024-07-20",
        "primary_amount_eur": 40.0,
        "nav_folder": "mahnungen",
        "folder_sub": None,
        "zahlstatus": "offen",
    },
]


def test_search_vendor_heuberger() -> None:
    with patch("document_search.list_documents", return_value=_ROWS):
        hits = search_documents(vendor="Heuberger", limit=10)
    assert len(hits) == 1
    assert hits[0]["id"] == 10


def test_search_category_strom_synonym() -> None:
    with patch("document_search.list_documents", return_value=_ROWS):
        hits = search_documents(category="strom", type="invoice", limit=10, sort="date_desc")
    assert len(hits) == 1
    assert hits[0]["id"] == 11


def test_search_reminders() -> None:
    with patch("document_search.list_documents", return_value=_ROWS):
        hits = search_documents(type="reminder", limit=10)
    assert len(hits) == 1
    assert hits[0]["id"] == 12


def test_sort_amount_desc() -> None:
    with patch("document_search.list_documents", return_value=_ROWS):
        hits = search_documents(type="invoice", sort="amount_desc", limit=5)
    assert [h["id"] for h in hits] == [10, 11]


def test_documents_as_assistant_rows_shape() -> None:
    slim = documents_as_assistant_rows(_ROWS[:1])
    assert slim[0]["id"] == 10
    assert slim[0]["vendor"] == "Kanzlei Heuberger"
    assert slim[0]["file_path"] == "/x/r1.pdf"
    assert "Rechnung" in slim[0]["tags"]
