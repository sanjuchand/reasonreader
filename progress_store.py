"""Persist per-user, per-copy unit mastery in Postgres."""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def save_progress(user_id: str | None, copy_id: str | None, mastery: dict[str, Any] | None) -> None:
    if not user_id or not copy_id or not mastery:
        return
    url = os.environ.get("DATABASE_URL")
    if not url:
        return
    try:
        import psycopg
    except ImportError:
        return
    rows = []
    for unit_id, entry in mastery.items():
        if not isinstance(entry, dict):
            continue
        rows.append(
            (
                user_id,
                copy_id,
                unit_id,
                entry.get("status") or ("in_progress" if entry.get("unlocked") else "locked"),
                float(entry.get("score") or 0),
                bool(entry.get("unlocked")),
                json.dumps(entry.get("concepts") or []),
            )
        )
    if not rows:
        return
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO unit_progress
                  (user_id, copy_id, unit_id, status, score, unlocked, concepts, updated_at)
                VALUES (%s, %s::uuid, %s, %s, %s, %s, %s::jsonb, now())
                ON CONFLICT (user_id, copy_id, unit_id) DO UPDATE SET
                  status = EXCLUDED.status,
                  score = EXCLUDED.score,
                  unlocked = EXCLUDED.unlocked,
                  concepts = EXCLUDED.concepts,
                  updated_at = now()
                """,
                rows,
            )
        conn.commit()
