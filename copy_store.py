"""Postgres rows for copies. Mirrors the Next.js `copies` table."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from ingest.constants import DEMO_COPY_ID, ROOT

load_dotenv(ROOT / ".env")


def _connect():
    url = os.environ.get("DATABASE_URL")
    if not url:
        return None
    try:
        import psycopg
    except ImportError:
        return None
    return psycopg.connect(url)


def get_copy(copy_id: str) -> dict[str, Any] | None:
    conn = _connect()
    if conn is None:
        if copy_id == DEMO_COPY_ID:
            return {
                "id": DEMO_COPY_ID,
                "kind": "demo",
                "owner_id": None,
                "title": "An Inquiry into the Nature and Causes of the Wealth of Nations",
                "author": "Adam Smith",
                "status": "ready",
                "flavor": "smith",
            }
        return None
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, kind, owner_id::text, title, author, status, flavor,
                       source_content_type, source_filename, error
                FROM copies WHERE id = %s::uuid
                """,
                (copy_id,),
            )
            row = cur.fetchone()
    if not row:
        return None
    keys = (
        "id",
        "kind",
        "owner_id",
        "title",
        "author",
        "status",
        "flavor",
        "source_content_type",
        "source_filename",
        "error",
    )
    return dict(zip(keys, row))


def upsert_demo_copy() -> None:
    conn = _connect()
    if conn is None:
        return
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO copies (id, kind, owner_id, title, author, status, flavor, source_content_type)
                VALUES (
                  %s::uuid, 'demo', NULL,
                  'An Inquiry into the Nature and Causes of the Wealth of Nations',
                  'Adam Smith', 'ingesting', 'smith', 'text/html'
                )
                ON CONFLICT (id) DO UPDATE SET
                  title = EXCLUDED.title,
                  author = EXCLUDED.author,
                  flavor = EXCLUDED.flavor,
                  status = 'ingesting',
                  error = NULL,
                  updated_at = now()
                """,
                (DEMO_COPY_ID,),
            )


def set_copy_status(
    copy_id: str,
    status: str,
    *,
    title: str | None = None,
    author: str | None = None,
    error: str | None = None,
) -> None:
    conn = _connect()
    if conn is None:
        return
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE copies SET
                  status = %s,
                  title = COALESCE(%s, title),
                  author = COALESCE(%s, author),
                  error = %s,
                  updated_at = now()
                WHERE id = %s::uuid
                """,
                (status, title, author, error, copy_id),
            )
