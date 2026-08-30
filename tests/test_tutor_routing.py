from tutor_agent import (
    READY_RE,
    apply_recitation_misses,
    is_mostly_recitation,
    is_quiz_submission,
    is_ready_for_test,
    last_human_text,
    last_quiz_answer_clip,
    normalize_citation_tokens,
    parse_quiz_answers,
    route,
    trim_model_messages,
    _format_judgment,
    _should_revise,
    Judgment,
    ConceptScore,
)


def test_quiz_submission_detection():
    assert is_quiz_submission("[[QUIZ_SUBMISSION]]\n{}")
    assert not is_quiz_submission("quiz me please")


def test_ready_for_test():
    assert is_ready_for_test("[[READY_FOR_TEST]]")
    assert is_ready_for_test("I think I'm ready. Quiz me.")
    assert is_ready_for_test("test me on this chapter")
    assert READY_RE.search("give me a quiz")
    assert not is_ready_for_test("[[QUIZ_SUBMISSION]] {}")
    assert not is_ready_for_test("[NAV] unit_id=u0003 hello")
    assert not is_ready_for_test("move on")
    assert not is_ready_for_test("ok")
    assert not is_ready_for_test("the test of this idea is specialization")


def test_parse_quiz_answers():
    payload = '[[QUIZ_SUBMISSION]]\n{"answers": [{"id": "q1", "answer": "pins"}]}'
    assert parse_quiz_answers(payload)[0]["answer"] == "pins"


def test_route_quiz_goes_to_judge():
    state = {"messages": [{"type": "human", "content": "[[QUIZ_SUBMISSION]] {}"}], "mode": "test"}
    assert route(state) == "judge"


def test_route_ready_goes_to_test():
    state = {"messages": [{"type": "human", "content": "[[READY_FOR_TEST]]"}], "mode": "teach"}
    assert route(state) == "test"


def test_move_on_is_not_a_test_request():
    state = {"messages": [{"type": "human", "content": "move on"}], "mode": "teach"}
    assert route(state) == "teach"


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


def test_after_a_miss_next_reply_is_reteach_not_another_quiz():
    state = {
        "messages": [{"type": "human", "content": "can you try another angle?"}],
        "mode": "revise",
        "open_quiz": None,
        "weak_concepts": ["Labour as National Supply"],
    }
    assert route(state) == "revise"
    assert route({**state, "messages": [{"type": "human", "content": "test me"}]}) == "test"


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


SMITH_OPENING = (
    "The greatest improvement in the productive powers of labour, and the greater part of the skill, "
    "dexterity, and judgment with which it is any where directed, or applied, seem to have been the "
    "effects of the division of labour."
)


def test_recitation_of_source_is_detected():
    assert is_mostly_recitation(SMITH_OPENING, [SMITH_OPENING])
    assert not is_mostly_recitation(
        "Smith says splitting work into trades is what makes people productive.",
        [SMITH_OPENING],
    )
    assert not is_mostly_recitation("pins", [SMITH_OPENING])


def test_recitation_overrides_llm_mastery():
    judgment = Judgment(
        overall=1.0,
        summary_for_student="You have the opening claim.",
        concepts=[
            ConceptScore(concept="division of labour", score="mastered", evidence="quoted", reteach_angle=""),
            ConceptScore(concept="market extent", score="mastered", evidence="ok", reteach_angle=""),
        ],
    )
    updated = apply_recitation_misses(
        judgment,
        [{"recitation": True}, {"recitation": False}],
    )
    assert updated.concepts[0].score == "miss"
    assert updated.concepts[1].score == "mastered"
    assert updated.overall == 0.5
    assert "own words" in updated.summary_for_student
    assert _should_revise(updated) is True


def test_format_judgment_pass_points_at_begin_next():
    judgment = Judgment(
        overall=1.0,
        summary_for_student="You can teach the pin factory in your own words.",
        concepts=[
            ConceptScore(concept="pins", score="mastered", evidence="x", reteach_angle=""),
        ],
    )
    text = _format_judgment(judgment, advancing=True, next_label="Book I: Of the Principle")
    assert "Begin next" in text
    assert "Book I: Of the Principle" in text
    assert "unlocked" not in text.lower()


def test_trim_drops_tools_quizzes_and_protocol():
    messages = [
        {"type": "human", "content": "[NAV] unit_id=u0000 Opened introduction."},
        {"type": "ai", "content": "Introduction claim."},
        {"type": "tool", "name": "list_curriculum", "content": "[{'id': 'u0000'}] * 132"},
        {"type": "human", "content": "[[READY_FOR_TEST]]"},
        {"type": "human", "content": '[[QUIZ_SUBMISSION]]\n{"answers":[{"id":"q1","answer":"old long paste"}]}'},
        {"type": "ai", "content": "We'll stay on this unit."},
        {"type": "human", "content": "Smith means labour is the real measure."},
        {"type": "ai", "content": "Yes — now the nominal price."},
        {"type": "tool", "name": "search_book", "content": "old hit from chapter I"},
        {"type": "human", "content": "expand on this sentence"},
        {"type": "tool", "name": "search_book", "content": "fresh hit"},
    ]
    kept = trim_model_messages(messages, keep=8)
    texts = [m["content"] for m in kept]
    assert "[NAV]" not in "".join(texts[:-2])
    assert "[[READY_FOR_TEST]]" not in texts
    assert "[[QUIZ_SUBMISSION]]" not in texts
    assert "list_curriculum" not in {m.get("name") for m in kept}
    assert "old hit from chapter I" not in texts
    assert "expand on this sentence" in texts
    assert "fresh hit" in texts
    assert "Smith means labour is the real measure." in texts
    assert "Introduction claim." in texts


def test_trim_keeps_only_a_short_window():
    messages = [{"type": "human", "content": f"turn {i}"} for i in range(20)]
    messages += [{"type": "ai", "content": f"reply {i}"} for i in range(20)]
    messages.append({"type": "human", "content": "now"})
    kept = trim_model_messages(messages, keep=6)
    assert kept[-1]["content"] == "now"
    assert len(kept) == 7


def test_last_quiz_clip_is_short():
    state = {
        "messages": [
            {
                "type": "human",
                "content": '[[QUIZ_SUBMISSION]]\n{"answers":[{"id":"q1","answer":"' + ("A" * 400) + '"}]}',
            }
        ]
    }
    clip = last_quiz_answer_clip(state, limit=40)
    assert clip.startswith("- AAAA")
    assert len(clip) < 50
