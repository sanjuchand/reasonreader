from corpus_store import claim_lines, filter_unit_questions, student_quiz


QUESTIONS = [
    {
        "id": "q1",
        "concept": "Annual labour",
        "claim": "A nation's yearly labour is the fund that supplies it.",
        "prompt": "What does Smith treat as the original fund of a nation's supply?",
        "kind": "explain",
    },
    {
        "id": "q2",
        "concept": "Skill over numbers",
        "claim": "Abundance depends more on how labour is applied than on how many labour.",
        "prompt": "Which circumstance does Smith say matters more to a nation's supply?",
        "kind": "distinguish",
    },
    {
        "id": "q3",
        "concept": "Theories of political economy",
        "claim": "Different plans gave rise to theories that influenced princes.",
        "prompt": "How do those theories reach public policy, on Smith's account?",
        "kind": "explain",
    },
]


def test_filter_keeps_full_exam_without_weak():
    assert filter_unit_questions(QUESTIONS) == QUESTIONS


def test_filter_picks_weak_concepts():
    picked = filter_unit_questions(QUESTIONS, ["skill over numbers"])
    assert [q["id"] for q in picked] == ["q2"]


def test_filter_falls_back_when_names_do_not_match():
    picked = filter_unit_questions(QUESTIONS, ["something invented"])
    assert picked == QUESTIONS


def test_student_quiz_hides_claims():
    quiz = student_quiz(QUESTIONS)
    assert "claim" not in quiz["questions"][0]
    assert quiz["questions"][0]["prompt"].startswith("What does Smith")


def test_claim_lines_are_the_syllabus_not_the_exam():
    text = claim_lines({"questions": QUESTIONS})
    assert "Annual labour" in text
    assert "Teach toward these claims" in text
    assert "What does Smith treat as the original fund" not in text
