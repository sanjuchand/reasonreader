from tutor_agent import (
    READY_RE,
    is_quiz_submission,
    is_ready_for_test,
    last_human_text,
    normalize_citation_tokens,
    parse_quiz_answers,
    route,
    _format_judgment,
    _should_revise,
    Judgment,
    ConceptScore,
)


def test_quiz_submission_detection():
    assert is_quiz_submission("[[QUIZ_SUBMISSION]]\n{}")
    assert not is_quiz_submission("quiz me please")


def test_ready_for_test():
    assert is_ready_for_test("I think I'm ready. Quiz me.")
    assert is_ready_for_test("test me on this chapter")
    assert not is_ready_for_test("[[QUIZ_SUBMISSION]] {}")
    assert not is_ready_for_test("[NAV] unit_id=u0003 hello")
    assert READY_RE.search("give me a quiz")
    assert is_ready_for_test("test")
    assert is_ready_for_test("quiz.")
    assert not is_ready_for_test("the test of this idea is specialization")


def test_parse_quiz_answers():
    payload = '[[QUIZ_SUBMISSION]]\n{"answers": [{"id": "q1", "answer": "pins"}]}'
    assert parse_quiz_answers(payload)[0]["answer"] == "pins"


def test_route_quiz_goes_to_judge():
    state = {"messages": [{"type": "human", "content": "[[QUIZ_SUBMISSION]] {}"}], "mode": "test"}
    assert route(state) == "judge"


def test_route_ready_goes_to_test():
    state = {"messages": [{"type": "human", "content": "quiz me"}], "mode": "teach"}
    assert route(state) == "test"


def test_skip_quiz_returns_to_teach():
    state = {
        "messages": [{"type": "human", "content": "[[SKIP_QUIZ]] already said this"}],
        "mode": "test",
        "open_quiz": {"questions": [{"id": "q1"}]},
        "current_chapter_id": "u0003",
        "mastery": {"u0003": {"unlocked": True}},
    }
    from tutor_agent import prep

    updates = prep(state)
    assert updates["mode"] == "teach"
    assert updates["open_quiz"] is None
    merged = {**state, **updates}
    assert route(merged) == "teach"


def test_route_revise_mode():
    state = {"messages": [{"type": "human", "content": "ok, go on"}], "mode": "revise"}
    assert route(state) == "revise"


def test_should_revise_on_miss():
    judgment = Judgment(
        overall=0.9,
        summary_for_student="no",
        concepts=[
            ConceptScore(concept="pins", score="miss", evidence="x", reteach_angle="y"),
            ConceptScore(concept="market", score="mastered", evidence="x", reteach_angle=""),
        ],
    )
    assert _should_revise(judgment) is True


def test_format_judgment_is_spoken_not_a_rubric():
    judgment = Judgment(
        overall=0.5,
        summary_for_student=(
            "You've got trade as the driver of division of labour [@u0004:p0], "
            "but Smith also says nobody planned it."
        ),
        concepts=[
            ConceptScore(
                concept="principle of division of labor",
                score="partial",
                evidence="internal",
                reteach_angle="unintended",
            ),
            ConceptScore(
                concept="natural specialization",
                score="miss",
                evidence="said don't know",
                reteach_angle="talent",
            ),
        ],
    )
    text = _format_judgment(judgment, advancing=False, next_label=None)
    assert "Concept scores" not in text
    assert "Overall:" not in text
    assert "partial." not in text
    assert "don't know" not in text
    assert "natural specialization" in text
    assert "You've got trade" in text
    assert "[@u0004:p0]" in text


def test_should_advance_when_mastered():
    judgment = Judgment(
        overall=1.0,
        summary_for_student="yes",
        concepts=[
            ConceptScore(concept="pins", score="mastered", evidence="x", reteach_angle=""),
            ConceptScore(concept="market", score="mastered", evidence="x", reteach_angle=""),
        ],
    )
    assert _should_revise(judgment) is False


def test_last_human_skips_summarizer_injection():
    state = {
        "messages": [
            {"type": "human", "content": "knife sharpening"},
            {
                "type": "human",
                "content": "Here is a summary of the conversation to date:\n\n## SESSION INTENT\nquiz",
                "additional_kwargs": {"lc_source": "summarization"},
            },
        ]
    }
    assert last_human_text(state) == "knife sharpening"


def test_normalize_citation_tokens():
    assert normalize_citation_tokens("see [u0000:p0]") == "see [@u0000:p0]"
    assert (
        normalize_citation_tokens("range [@u0000:p1-@u0000:p3]")
        == "range [@u0000:p1] [@u0000:p3]"
    )
    assert normalize_citation_tokens("already [@u0003:p0]") == "already [@u0003:p0]"
