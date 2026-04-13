"""SQLite persistence: documents, extractions, matters, reference keys."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import DB_PATH


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_filename TEXT NOT NULL,
                stored_path TEXT NOT NULL UNIQUE,
                sha256 TEXT NOT NULL UNIQUE,
                extracted_text TEXT,
                text_char_count INTEGER DEFAULT 0,
                needs_ocr INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS extractions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                category TEXT,
                sender_name TEXT,
                sender_role TEXT,
                subject TEXT,
                document_date TEXT,
                amounts_json TEXT,
                reference_ids_json TEXT,
                summary_de TEXT,
                raw_json TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(document_id)
            );

            CREATE TABLE IF NOT EXISTS matters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS document_matters (
                document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                matter_id INTEGER NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
                PRIMARY KEY (document_id, matter_id)
            );

            CREATE TABLE IF NOT EXISTS reference_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                id_type TEXT NOT NULL,
                key_value TEXT NOT NULL,
                UNIQUE(document_id, id_type, key_value)
            );

            CREATE INDEX IF NOT EXISTS idx_ref_keys_value ON reference_keys(key_value);
            CREATE INDEX IF NOT EXISTS idx_ref_keys_doc ON reference_keys(document_id);
            """
        )
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def document_by_sha256(sha256: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE sha256 = ?", (sha256,)
        ).fetchone()
        return dict(row) if row else None


def insert_document(
    *,
    original_filename: str,
    stored_path: str,
    sha256: str,
    extracted_text: str,
    needs_ocr: bool,
) -> int:
    created = _utc_now()
    char_count = len(extracted_text or "")
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO documents (original_filename, stored_path, sha256, extracted_text,
                text_char_count, needs_ocr, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                original_filename,
                stored_path,
                sha256,
                extracted_text,
                char_count,
                1 if needs_ocr else 0,
                created,
            ),
        )
        return int(cur.lastrowid)


def list_documents() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT d.*, e.category, e.sender_role, e.summary_de, e.document_date
            FROM documents d
            LEFT JOIN extractions e ON e.document_id = d.id
            ORDER BY d.id DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


def get_document(doc_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        return dict(row) if row else None


def get_extraction(doc_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM extractions WHERE document_id = ?", (doc_id,)
        ).fetchone()
        return dict(row) if row else None


def upsert_extraction(
    document_id: int,
    *,
    category: str | None,
    sender_name: str | None,
    sender_role: str | None,
    subject: str | None,
    document_date: str | None,
    amounts: list[dict],
    reference_ids: list[dict],
    summary_de: str | None,
    raw_json: str,
) -> None:
    created = _utc_now()
    amounts_json = json.dumps(amounts, ensure_ascii=False)
    ref_json = json.dumps(reference_ids, ensure_ascii=False)
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO extractions (document_id, category, sender_name, sender_role, subject,
                document_date, amounts_json, reference_ids_json, summary_de, raw_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(document_id) DO UPDATE SET
                category = excluded.category,
                sender_name = excluded.sender_name,
                sender_role = excluded.sender_role,
                subject = excluded.subject,
                document_date = excluded.document_date,
                amounts_json = excluded.amounts_json,
                reference_ids_json = excluded.reference_ids_json,
                summary_de = excluded.summary_de,
                raw_json = excluded.raw_json,
                created_at = excluded.created_at
            """,
            (
                document_id,
                category,
                sender_name,
                sender_role,
                subject,
                document_date,
                amounts_json,
                ref_json,
                summary_de,
                raw_json,
                created,
            ),
        )


def replace_reference_keys(document_id: int, reference_ids: list[dict]) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM reference_keys WHERE document_id = ?", (document_id,))
        for ref in reference_ids:
            id_type = str(ref.get("id_type") or "other")
            value = str(ref.get("value") or "").strip()
            if not value:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO reference_keys (document_id, id_type, key_value)
                VALUES (?, ?, ?)
                """,
                (document_id, id_type, value),
            )


def list_matters() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT m.*, COUNT(dm.document_id) AS doc_count
            FROM matters m
            LEFT JOIN document_matters dm ON dm.matter_id = m.id
            GROUP BY m.id
            ORDER BY m.id DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


def create_matter(title: str) -> int:
    created = _utc_now()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO matters (title, created_at) VALUES (?, ?)", (title, created)
        )
        return int(cur.lastrowid)


def link_document_to_matter(document_id: int, matter_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO document_matters (document_id, matter_id)
            VALUES (?, ?)
            """,
            (document_id, matter_id),
        )


def unlink_document_from_matter(document_id: int, matter_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM document_matters WHERE document_id = ? AND matter_id = ?",
            (document_id, matter_id),
        )


def documents_for_matter(matter_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT d.*, e.category, e.sender_name, e.sender_role, e.summary_de
            FROM documents d
            JOIN document_matters dm ON dm.document_id = d.id AND dm.matter_id = ?
            LEFT JOIN extractions e ON e.document_id = d.id
            ORDER BY d.id
            """,
            (matter_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def find_documents_sharing_keys(document_id: int) -> list[dict[str, Any]]:
    """Other documents that share at least one reference key value (same string)."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT d.id, d.original_filename, rk.key_value, rk.id_type,
                   e.category, e.sender_role, e.summary_de
            FROM reference_keys rk_self
            JOIN reference_keys rk ON rk.key_value = rk_self.key_value
                AND rk.document_id != rk_self.document_id
            JOIN documents d ON d.id = rk.document_id
            LEFT JOIN extractions e ON e.document_id = d.id
            WHERE rk_self.document_id = ?
            ORDER BY d.id DESC
            """,
            (document_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def matter_ids_for_document(document_id: int) -> list[int]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT matter_id FROM document_matters WHERE document_id = ?",
            (document_id,),
        ).fetchall()
        return [int(r["matter_id"]) for r in rows]


def document_ids_for_reference_key(id_type: str, key_value: str) -> list[int]:
    """Alle Dokumente mit derselben Kennung (Typ + Wert)."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT document_id FROM reference_keys
            WHERE id_type = ? AND key_value = ?
            ORDER BY document_id
            """,
            (id_type, key_value),
        ).fetchall()
        return [int(r["document_id"]) for r in rows]


def find_matter_for_reference_key(id_type: str, key_value: str) -> int | None:
    """Ein bereits existierender Vorgang, der ein Dokument mit dieser Kennung enthält."""
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT dm.matter_id
            FROM reference_keys rk
            INNER JOIN document_matters dm ON dm.document_id = rk.document_id
            WHERE rk.id_type = ? AND rk.key_value = ?
            LIMIT 1
            """,
            (id_type, key_value),
        ).fetchone()
        return int(row["matter_id"]) if row else None
