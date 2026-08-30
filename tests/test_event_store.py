from event_store import (
    apply_last_judgment,
    clip_answer,
    events_from_judgment,
    events_from_transcript,
    record_events,
)
from tutor_agent import ConceptScore, Judgment


def test_record_events_noops_without_user():
    assert record_events([{"kind": "judged", "copy_id": "x"}]) == 0
    assert record_events([]) == 0


def test_clip_does_not_keep_a_full_paste():
    assert len(clip_answer("A" * 800)) == 280


def test_transcript_keeps_actions_not_chat():
    rows = events_from_transcript(
        [
            {"type": "human", "id": "n1", "content": "[NAV] unit_id=u0005 I am now reading: Book I."},
            {"type": "ai", "content": "Smith distinguishes real and nominal price."},
            {"type": "tool", "name": "search_book", "content": "long quote from the book"},
            {"type": "human", "content": "[[READY_FOR_TEST]]"},
            {
                "type": "human",
                "id": "q1",
                "content": '[[QUIZ_SUBMISSION]]\n{"answers":[{"id":"real-vs-nominal-price","answer":"'
                + ("paste " * 80)
                + '"}]}',
            },
            {"type": "human", "content": "expand on this sentence from the page"},
        ],
        user_id="user",
        copy_id="copy",
        thread_id="thread-1",
    )
    kinds = [row["kind"] for row in rows]
    assert kinds == ["opened_unit", "ready_for_test", "submitted"]
    submitted = rows[-1]
    assert submitted["unit_id"] == "u0005"
    assert submitted["concept"] == "real-vs-nominal-price"
    assert submitted["attempt"] == 1
    assert submitted["answer_chars"] > 280
    assert len(submitted["answer_clip"]) == 280
    assert "long quote from the book" not in json_blob(rows)
    assert "expand on this" not in json_blob(rows)


def test_judgment_events_are_one_row_per_concept():
    judgment = Judgment(
        overall=0.5,
        summary_for_student="You have labour as the real measure.",
        concepts=[
            ConceptScore(concept="Real vs Nominal", score="partial", evidence="internal", reteach_angle="rent"),
        ],
    )
    rows = events_from_judgment(
        user_id="user",
        copy_id="copy",
        unit_id="u0005",
        paired=[{"question": {"id": "q1", "concept": "Real vs Nominal"}, "answer": "labour", "recitation": False}],
        judgment=judgment,
        revise=True,
    )
    assert len(rows) == 1
    assert rows[0]["kind"] == "judged"
    assert rows[0]["score"] == "partial"
    assert rows[0]["payload"]["revise"] is True
    assert "internal" not in json_blob(rows)


def test_last_judgment_attaches_to_latest_submission():
    rows = events_from_transcript(
        [
            {"type": "human", "content": "[NAV] unit_id=u0005 start"},
            {
                "type": "human",
                "id": "old",
                "content": '[[QUIZ_SUBMISSION]]\n{"answers":[{"id":"q1","answer":"first try"}]}',
            },
            {
                "type": "human",
                "id": "new",
                "content": '[[QUIZ_SUBMISSION]]\n{"answers":[{"id":"q1","answer":"second try"}]}',
            },
        ],
        user_id="user",
        copy_id="copy",
    )
    merged = apply_last_judgment(
        rows,
        {
            "overall": 0.5,
            "concepts": [{"concept": "Real vs Nominal", "score": "partial"}],
        },
        unit_id="u0005",
    )
    judged = [row for row in merged if row["kind"] == "judged"]
    assert len(judged) == 1
    assert judged[0]["score"] == "partial"
    assert judged[0]["answer_clip"] == "second try"
    assert judged[0]["concept"] == "Real vs Nominal"


def json_blob(rows: list[dict]) -> str:
    import json

    return json.dumps(rows)
