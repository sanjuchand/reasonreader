"""Append-only tutor events. No source text. Short answer clips only."""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from typing import Any

from dotenv import load_dotenv

load_dotenv()

ANSWER_CLIP = 280
NAV_RE = re.compile(r"^\[NAV\]\s+unit_id=(\S+)")
QUIZ_PREFIX = "[[QUIZ_SUBMISSION]]"
READY_PREFIX = "[[READY_FOR_TEST]]"
SKIP_PREFIX = "[[SKIP_QUIZ]]"


def _message_type(message: Any) -> str:
    if isinstance(message, dict):
        return message.get("type") or message.get("role") or ""
    return getattr(message, "type", "") or ""


def _message_text(message: Any) -> str:
    content = message.get("content") if isinstance(message, dict) else getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(block.get("text") or "")
            else:
                parts.append(getattr(block, "text", "") or "")
        return "".join(parts)
    return str(content or "")


def _message_id(message: Any) -> str | None:
    if isinstance(message, dict):
        return message.get("id")
    return getattr(message, "id", None)


def clip_answer(text: str, *, limit: int = ANSWER_CLIP) -> str:
    return (text or "").strip()[:limit]


def parse_quiz_answers(text: str) -> list[dict]:
    raw = (text or "").lstrip()
    if raw.startswith(QUIZ_PREFIX):
        raw = raw[len(QUIZ_PREFIX) :].strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return [{"id": "answer", "answer": raw}]
    answers = payload.get("answers", payload)
    if isinstance(answers, list):
        return [item for item in answers if isinstance(item, dict)]
    return [{"id": "answer", "answer": raw}]


def events_from_judgment(
    *,
    user_id: str | None,
    copy_id: str | None,
    unit_id: str | None,
    paired: list[dict],
    judgment: Any,
    revise: bool,
    source: str = "live",
    thread_id: str | None = None,
) -> list[dict]:
    if not user_id or not copy_id or not unit_id:
        return []
    concepts = getattr(judgment, "concepts", None)
    if concepts is None and isinstance(judgment, dict):
        concepts = judgment.get("concepts") or []
    overall = getattr(judgment, "overall", None)
    if overall is None and isinstance(judgment, dict):
        overall = judgment.get("overall")
    rows = []
    for index, item in enumerate(paired):
        question = item.get("question") or {}
        answer = item.get("answer") or ""
        scored = concepts[index] if index < len(concepts) else None
        if scored is None:
            score = None
            concept = question.get("concept") or question.get("id")
        elif isinstance(scored, dict):
            score = scored.get("score")
            concept = scored.get("concept") or question.get("concept")
        else:
            score = getattr(scored, "score", None)
            concept = getattr(scored, "concept", None) or question.get("concept")
        rows.append(
            {
                "user_id": user_id,
                "copy_id": copy_id,
                "thread_id": thread_id,
                "unit_id": unit_id,
                "kind": "judged",
                "concept": concept,
                "score": score,
                "recitation": bool(item.get("recitation")),
                "overall": overall,
                "attempt": None,
                "answer_chars": len(answer),
                "answer_clip": clip_answer(answer),
                "payload": {
                    "source": source,
                    "question_id": question.get("id"),
                    "revise": revise,
                },
            }
        )
    return rows


def events_from_transcript(
    messages: list,
    *,
    user_id: str,
    copy_id: str,
    thread_id: str | None = None,
    recitation_of=None,
) -> list[dict]:
    """NAV / ready / quiz submissions only. No tutor prose, no book text."""
    unit_id = None
    rows: list[dict] = []
    attempts: dict[tuple[str | None, str | None], int] = defaultdict(int)
    for message in messages:
        if _message_type(message) not in {"human", "user"}:
            continue
        text = _message_text(message)
        mid = _message_id(message)
        nav = NAV_RE.match(text.lstrip())
        if nav:
            unit_id = nav.group(1)
            rows.append(
                {
                    "user_id": user_id,
                    "copy_id": copy_id,
                    "thread_id": thread_id,
                    "unit_id": unit_id,
                    "kind": "opened_unit",
                    "concept": None,
                    "score": None,
                    "recitation": None,
                    "overall": None,
                    "attempt": None,
                    "answer_chars": None,
                    "answer_clip": None,
                    "payload": {"source": "backfill", "message_id": mid},
                }
            )
            continue
        if text.lstrip().startswith(READY_PREFIX):
            rows.append(
                {
                    "user_id": user_id,
                    "copy_id": copy_id,
                    "thread_id": thread_id,
                    "unit_id": unit_id,
                    "kind": "ready_for_test",
                    "concept": None,
                    "score": None,
                    "recitation": None,
                    "overall": None,
                    "attempt": None,
                    "answer_chars": None,
                    "answer_clip": None,
                    "payload": {"source": "backfill", "message_id": mid},
                }
            )
            continue
        if text.lstrip().startswith(SKIP_PREFIX):
            rows.append(
                {
                    "user_id": user_id,
                    "copy_id": copy_id,
                    "thread_id": thread_id,
                    "unit_id": unit_id,
                    "kind": "keep_teaching",
                    "concept": None,
                    "score": None,
                    "recitation": None,
                    "overall": None,
                    "attempt": None,
                    "answer_chars": None,
                    "answer_clip": None,
                    "payload": {"source": "backfill", "message_id": mid},
                }
            )
            continue
        if not text.lstrip().startswith(QUIZ_PREFIX):
            continue
        for item in parse_quiz_answers(text):
            answer = item.get("answer") or ""
            concept = item.get("id")
            key = (unit_id, concept)
            attempts[key] += 1
            recited = recitation_of(unit_id, answer) if recitation_of else None
            rows.append(
                {
                    "user_id": user_id,
                    "copy_id": copy_id,
                    "thread_id": thread_id,
                    "unit_id": unit_id,
                    "kind": "submitted",
                    "concept": concept,
                    "score": None,
                    "recitation": recited,
                    "overall": None,
                    "attempt": attempts[key],
                    "answer_chars": len(answer),
                    "answer_clip": clip_answer(answer),
                    "payload": {"source": "backfill", "message_id": mid, "question_id": concept},
                }
            )
    return rows


def apply_last_judgment(rows: list[dict], judgment: dict | None, *, unit_id: str | None) -> list[dict]:
    if not judgment or not unit_id:
        return rows
    concepts = list(judgment.get("concepts") or [])
    if not concepts:
        return rows
    submitted = [
        row
        for row in rows
        if row.get("kind") == "submitted" and row.get("unit_id") == unit_id
    ]
    if not submitted:
        return rows
    last_mid = submitted[-1].get("payload", {}).get("message_id")
    latest = [row for row in submitted if row.get("payload", {}).get("message_id") == last_mid]
    extra = []
    for index, scored in enumerate(concepts):
        match = latest[index] if index < len(latest) else (latest[-1] if latest else None)
        extra.append(
            {
                **(match or {"user_id": rows[-1]["user_id"], "copy_id": rows[-1]["copy_id"], "thread_id": rows[-1].get("thread_id"), "unit_id": unit_id}),
                "kind": "judged",
                "concept": scored.get("concept"),
                "score": scored.get("score"),
                "overall": judgment.get("overall"),
                "payload": {
                    **((match or {}).get("payload") or {}),
                    "source": "backfill",
                    "revise": scored.get("score") != "mastered",
                },
            }
        )
    return rows + extra


def record_events(rows: list[dict] | None) -> int:
    if not rows:
        return 0
    url = os.environ.get("DATABASE_URL")
    if not url:
        return 0
    try:
        import psycopg
    except ImportError:
        return 0
    ready = [row for row in rows if row.get("user_id") and row.get("copy_id") and row.get("kind")]
    if not ready:
        return 0
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            for row in ready:
                attempt = row.get("attempt")
                if attempt is None and row["kind"] in {"judged", "submitted"} and row.get("concept"):
                    cur.execute(
                        """
                        SELECT COALESCE(MAX(attempt), 0)
                        FROM tutor_events
                        WHERE user_id = %s::uuid AND copy_id = %s::uuid
                          AND unit_id = %s AND kind = %s AND concept = %s
                        """,
                        (row["user_id"], row["copy_id"], row.get("unit_id"), row["kind"], row["concept"]),
                    )
                    attempt = int(cur.fetchone()[0]) + 1
                cur.execute(
                    """
                    INSERT INTO tutor_events (
                      user_id, copy_id, thread_id, unit_id, kind, concept, score,
                      recitation, overall, attempt, answer_chars, answer_clip, payload
                    ) VALUES (
                      %s::uuid, %s::uuid, %s, %s, %s, %s, %s,
                      %s, %s, %s, %s, %s, %s::jsonb
                    )
                    """,
                    (
                        row["user_id"],
                        row["copy_id"],
                        row.get("thread_id"),
                        row.get("unit_id"),
                        row["kind"],
                        row.get("concept"),
                        row.get("score"),
                        row.get("recitation"),
                        row.get("overall"),
                        attempt,
                        row.get("answer_chars"),
                        row.get("answer_clip"),
                        json.dumps(row.get("payload") or {}),
                    ),
                )
        conn.commit()
    return len(ready)


def replace_backfill(thread_id: str, rows: list[dict]) -> int:
    url = os.environ.get("DATABASE_URL")
    if not url or not thread_id:
        return 0
    import psycopg

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM tutor_events
                WHERE thread_id = %s AND payload->>'source' = 'backfill'
                """,
                (thread_id,),
            )
        conn.commit()
    return record_events(rows)
