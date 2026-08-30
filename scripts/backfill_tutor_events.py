"""Load one LangGraph thread into tutor_events. No source text."""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from corpus_store import get_unit
from event_store import apply_last_judgment, events_from_transcript, replace_backfill
from tutor_agent import is_mostly_recitation

THREAD_ID = "01a04b00-cabd-7893-aa10-5292aa3ecf9f"


def main() -> None:
    base = os.environ.get("LANGGRAPH_URL") or "http://127.0.0.1:2024"
    thread_id = os.environ.get("BACKFILL_THREAD_ID") or THREAD_ID
    state = json.load(urllib.request.urlopen(f"{base}/threads/{thread_id}/state"))
    values = state.get("values") or {}
    user_id = values.get("user_id")
    copy_id = values.get("copy_id")
    if not user_id or not copy_id:
        raise SystemExit("thread has no user_id/copy_id")

    def recitation_of(unit_id: str | None, answer: str) -> bool | None:
        if not unit_id:
            return None
        unit = get_unit(copy_id, unit_id) or {}
        sources = [paragraph.get("text") or "" for paragraph in unit.get("paragraphs") or []]
        return is_mostly_recitation(answer, sources)

    rows = events_from_transcript(
        values.get("messages") or [],
        user_id=user_id,
        copy_id=copy_id,
        thread_id=thread_id,
        recitation_of=recitation_of,
    )
    rows = apply_last_judgment(
        rows,
        values.get("last_judgment"),
        unit_id=values.get("current_chapter_id"),
    )
    written = replace_backfill(thread_id, rows)
    kinds: dict[str, int] = {}
    for row in rows:
        kinds[row["kind"]] = kinds.get(row["kind"], 0) + 1
    print(f"wrote {written} events for {thread_id}: {kinds}")


if __name__ == "__main__":
    main()
