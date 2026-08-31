"""Write the exam that defines a unit — 2–3 load-bearing claims from the copy."""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

QUESTION_PROMPT = """You write the short-answer exam that *defines* this close-reading unit.

The questions are the syllabus. A later tutor will teach toward these claims, then use these
same questions when the student asks to be tested.

Rules:
- 2 or 3 questions. No multiple choice.
- Each question is a load-bearing claim the author actually makes in the passages.
- claim: one sentence of the author's argument, not a modern slogan or textbook rewrite.
- prompt: the exam wording the student will answer in their own words.
- concept: a short label for that claim.
- Every question MUST include paragraph_ids copied from the passages below. If you cannot point to a passage, drop the question.
- Prefer mechanism, distinction, or consequence over trivia or chapter-plan recitation.
"""


class UnitQuestion(BaseModel):
    id: str
    concept: str
    claim: str
    prompt: str
    kind: Literal["explain", "apply", "distinguish"] = "explain"
    paragraph_ids: list[str] = Field(default_factory=list)


class UnitExam(BaseModel):
    questions: list[UnitQuestion] = Field(min_length=2, max_length=3)


def unit_exam_source(unit: dict, *, max_paragraphs: int | None = None) -> str:
    paragraphs = unit.get("paragraphs") or []
    if max_paragraphs is not None:
        paragraphs = paragraphs[:max_paragraphs]
    lines = []
    for paragraph in paragraphs:
        pid = paragraph.get("paragraph_id") or ""
        text = (paragraph.get("text") or "")[:700]
        lines.append(f"[{pid}] {text}")
    return "\n\n".join(lines)


def _content_words(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9']+", (text or "").lower()) if len(word) > 4}


def claim_is_on_the_page(claim: str, passages: str, *, threshold: float = 0.28) -> bool:
    needles = _content_words(claim)
    if len(needles) < 3:
        return False
    hay = _content_words(passages)
    return (len(needles & hay) / len(needles)) >= threshold


def bind_questions_to_unit(unit: dict, questions: list[dict]) -> list[dict]:
    """Drop claims the model pinned to another place, or invented from the title."""
    allowed = {
        paragraph.get("paragraph_id"): paragraph.get("text") or ""
        for paragraph in unit.get("paragraphs") or []
        if paragraph.get("paragraph_id")
    }
    bound = []
    for question in questions:
        pids = [pid for pid in (question.get("paragraph_ids") or []) if pid in allowed]
        if not pids:
            continue
        passage = " ".join(allowed[pid] for pid in pids)
        if not claim_is_on_the_page(question.get("claim") or "", passage):
            continue
        bound.append({**question, "paragraph_ids": pids})
    return bound


def generate_questions_for_unit(unit: dict) -> list[dict]:
    source = unit_exam_source(unit)
    if not source.strip():
        return []
    model = init_chat_model("gpt-4o")
    exam = model.with_structured_output(UnitExam).invoke(
        [
            SystemMessage(content=QUESTION_PROMPT),
            HumanMessage(
                content=(
                    f"Unit: {unit.get('book')}: {unit.get('title')}"
                    f"{' — ' + unit['part_title'] if unit.get('part_title') else ''}\n\n"
                    f"Passages:\n{source}"
                )
            ),
        ]
    )
    return bind_questions_to_unit(unit, [question.model_dump() for question in exam.questions])


def attach_questions(units: list[dict], *, max_workers: int = 2) -> list[dict]:
    pending = [unit for unit in units if not unit.get("questions")]
    if not pending:
        return units
    print(f"Writing exams for {len(pending)} units", flush=True)

    def work(unit: dict) -> tuple[str, list[dict]]:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return unit["id"], generate_questions_for_unit(unit)
            except Exception as exc:
                last_error = exc
                message = str(exc)
                if "429" in message or "rate_limit" in message.lower():
                    time.sleep(4 + attempt * 4)
                    continue
                break
        raise last_error or RuntimeError(f"No exam for {unit['id']}")

    done: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(work, unit): unit["id"] for unit in pending}
        for future in as_completed(futures):
            unit_id = futures[future]
            try:
                uid, questions = future.result()
                done[uid] = questions
                print(f"  {uid}: {', '.join(q['concept'] for q in questions)}", flush=True)
            except Exception as exc:
                print(f"  {unit_id}: failed ({exc})", flush=True)
                done[unit_id] = []
    for unit in units:
        if unit["id"] in done:
            unit["questions"] = done[unit["id"]]
        else:
            unit.setdefault("questions", [])
    return units
