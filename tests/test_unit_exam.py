from corpus_store import claim_lines, claim_passages, filter_unit_questions, passages_for_questions, student_quiz
from ingest.questions import bind_questions_to_unit


QUESTIONS = [
    {
        "id": "q1",
        "concept": "Annual labour",
        "claim": "A nation's yearly labour is the fund that supplies it.",
        "prompt": "What does Smith treat as the original fund of a nation's supply?",
        "kind": "explain",
        "paragraph_ids": ["u0000:p0"],
    },
    {
        "id": "q2",
        "concept": "Skill over numbers",
        "claim": "Abundance depends more on how labour is applied than on how many labour.",
        "prompt": "Which circumstance does Smith say matters more to a nation's supply?",
        "kind": "distinguish",
        "paragraph_ids": ["u0000:p2"],
    },
    {
        "id": "q3",
        "concept": "Theories of political economy",
        "claim": "Different plans gave rise to theories that influenced princes.",
        "prompt": "How do those theories reach public policy, on Smith's account?",
        "kind": "explain",
        "paragraph_ids": ["u0000:p8"],
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
    assert quiz["questions"][0]["paragraph_ids"] == ["u0000:p0"]


def test_claim_lines_are_the_syllabus_not_the_exam():
    text = claim_lines(
        {
            "questions": QUESTIONS,
            "paragraphs": [
                {"paragraph_id": "u0000:p0", "text": "The annual labour of every nation is the fund."},
                {"paragraph_id": "u0000:p2", "text": "Skill and the share of useful labour regulate supply."},
            ],
        }
    )
    assert "Annual labour" in text
    assert "Teach toward these claims" in text
    assert "[@u0000:p0]" in text
    assert "annual labour of every nation" in text
    assert "What does Smith treat as the original fund" not in text


def test_bind_questions_drops_foreign_or_invented_claims():
    unit = {
        "paragraphs": [
            {
                "paragraph_id": "u0001:p0",
                "text": "The pin factory employs eighteen distinct operations under one roof.",
            }
        ]
    }
    bound = bind_questions_to_unit(
        unit,
        [
            {
                "id": "ok",
                "claim": "The pin factory employs eighteen distinct operations.",
                "paragraph_ids": ["u0001:p0", "u0099:p0"],
            },
            {
                "id": "away",
                "claim": "Rent is the price paid for the use of land.",
                "paragraph_ids": ["u0050:p3"],
            },
            {
                "id": "slogan",
                "claim": "Healthcare systems deny claims as a cost-control mechanism.",
                "paragraph_ids": ["u0001:p0"],
            },
        ],
    )
    assert [q["id"] for q in bound] == ["ok"]
    assert bound[0]["paragraph_ids"] == ["u0001:p0"]


def test_claim_passages_are_the_exam_paragraphs():
    unit = {
        "questions": QUESTIONS,
        "paragraphs": [
            {"paragraph_id": "u0000:p0", "text": "The annual labour of every nation is the fund."},
            {"paragraph_id": "u0000:p2", "text": "Skill regulates the proportion."},
        ],
    }
    rows = claim_passages(unit, "annual labour")
    assert rows[0]["paragraph_ids"] == ["u0000:p0"]
    assert rows[0]["passages"][0]["quote"].startswith("The annual labour")
    assert passages_for_questions(unit, QUESTIONS).startswith("[u0000:p0]")
