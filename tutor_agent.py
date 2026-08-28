"""Chapter-mastery tutor for The Wealth of Nations.

Served by `langgraph dev` via langgraph.json. No in-code checkpointer — the
platform owns persistence.
"""

from __future__ import annotations

import json
import re
from typing import Annotated, Any, Literal, NotRequired

from dotenv import load_dotenv
from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import ModelRequest, ModelResponse, SummarizationMiddleware, wrap_model_call
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, SystemMessage, ToolMessage
from langchain.tools import ToolRuntime, tool
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from pydantic import BaseModel, Field

from copy_store import get_copy
from flavors import flavor_addendum
from ingest.constants import DEMO_COPY_ID
from progress_store import save_progress
from corpus_store import (
    asearch,
    curriculum_toc,
    first_unit_id,
    get_chapter_outline,
    get_unit,
    initial_mastery,
    load_book,
    next_unit_id,
)

load_dotenv()

MASTERY_THRESHOLD = 0.8
QUIZ_PREFIX = "[[QUIZ_SUBMISSION]]"
NAV_RE = re.compile(r"^\[NAV\]\s+unit_id=(\S+)")
SKIP_QUIZ_RE = re.compile(r"^\[\[SKIP_QUIZ\]\]")
READY_RE = re.compile(
    r"\b(quiz me|test me|i am ready|i'm ready|ready to be tested|give me (a |the )?quiz|i think i('ve| have) got it)\b",
    re.I,
)
SHORT_READY_RE = re.compile(r"^(quiz|test|ready)(\s+me)?[.!]?\s*$", re.I)

TEACH_PROMPT = """You are a demanding close-reading tutor of the book named in the session briefing.

Your job is that the student *internalize this author's actual argument*, not a slogan or a modern paraphrase.

Rules:
- Teach only the current unit. Do not skip ahead.
- Cite with exactly one token per claim, like [@u0003:p2], using a paragraph_id from search_book or the outline. Never invent ids. Never write ranges such as [@u0001:p1-@u0001:p3]; emit separate tokens instead.
- Quote the author sparingly (a sentence or two), then make the student work: Socratic questions, distinctions, counterexamples the author uses.
- If the student is wrong, say so plainly and point at the passage.
- When the student has engaged a claim, go deeper into this unit — a distinction, a number, a counterexample they have not yet touched. Do not call present_quiz just because they answered your last Socratic question.
- Call present_quiz only if they explicitly ask to be tested (quiz me / test me / I am ready). Never re-ask, as a form, the same points they just stated in chat.
- If the latest user message is a quiz submission and you are teaching a *new* unit, congratulate briefly, then start this unit. Do not re-score the quiz.
- Never dump a whole chapter into the chat. Use get_chapter_outline and search_book.
- Do not give exam answers the student can paste. Make them reconstruct the argument.
"""

REVISE_PROMPT = """You are reteaching the weak concepts listed in the session briefing. The student just failed or only partly grasped them.

Rules:
- Do not re-lecture the whole unit. Only the weak concepts.
- Cite with one [@u0000:p0] token per claim from search_book. Never invent ids or ranges.
- Contrast what they said with what the author actually wrote.
- Offer a different angle than the first teaching pass (a concrete example, a distinction, a failure case).
- After the reteach, call present_quiz with 2–3 short-answer questions aimed *only* at those weak concepts. No multiple choice.
- If the latest user message is a quiz submission, do not re-score it; that already happened. Start the reteach immediately.
"""


def _lww(existing, new):
    return new


class TutorState(AgentState):
    current_chapter_id: NotRequired[Annotated[str, _lww]]
    mode: NotRequired[Annotated[str, _lww]]
    mastery: NotRequired[Annotated[dict, _lww]]
    open_quiz: NotRequired[Annotated[dict | None, _lww]]
    weak_concepts: NotRequired[Annotated[list, _lww]]
    last_judgment: NotRequired[Annotated[dict | None, _lww]]
    user_id: NotRequired[Annotated[str, _lww]]
    copy_id: NotRequired[Annotated[str, _lww]]


def copy_id_of(state: dict | None) -> str:
    return (state or {}).get("copy_id") or DEMO_COPY_ID


class QuizQuestion(BaseModel):
    id: str
    prompt: str
    concept: str
    kind: Literal["explain", "apply", "distinguish"] = "explain"


class Quiz(BaseModel):
    questions: list[QuizQuestion] = Field(min_length=2, max_length=4)


class ConceptScore(BaseModel):
    concept: str
    score: Literal["miss", "partial", "mastered"]
    evidence: str
    reteach_angle: str


class Judgment(BaseModel):
    overall: float = Field(ge=0, le=1)
    concepts: list[ConceptScore]
    summary_for_student: str


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


def is_context_summary(message: Any) -> bool:
    extra = (
        message.get("additional_kwargs")
        if isinstance(message, dict)
        else getattr(message, "additional_kwargs", None)
    )
    if isinstance(extra, dict) and extra.get("lc_source") == "summarization":
        return True
    text = _message_text(message).lstrip()
    return text.startswith("Here is a summary of the conversation to date:") or text.startswith(
        "Previous conversation was too long to summarize."
    )


PARA_ID_RE = re.compile(r"u\d+:p\d+")


def normalize_citation_tokens(text: str) -> str:
    """Turn ranges and bare [chap01:p0] into one [@id] token per paragraph."""

    def from_at(match: re.Match[str]) -> str:
        inner = match.group(1)
        ids = [part.replace("@", "").strip() for part in re.split(r"-@|,", inner)]
        ids = [item for item in ids if PARA_ID_RE.fullmatch(item)]
        if not ids:
            return match.group(0)
        return " ".join(f"[@{item}]" for item in ids)

    rewritten = re.sub(r"\[@([^\]]+)\]", from_at, text)
    return re.sub(rf"\[({PARA_ID_RE.pattern})\]", r"[@\1]", rewritten)


def last_human_text(state: dict) -> str:
    for message in reversed(state.get("messages") or []):
        if _message_type(message) not in {"human", "user"}:
            continue
        if is_context_summary(message):
            continue
        return _message_text(message)
    return ""


def is_skip_quiz(text: str) -> bool:
    return bool(SKIP_QUIZ_RE.match((text or "").lstrip()))


def is_quiz_submission(text: str) -> bool:
    return text.lstrip().startswith(QUIZ_PREFIX)


def is_ready_for_test(text: str) -> bool:
    if is_quiz_submission(text):
        return False
    if NAV_RE.match(text.lstrip()):
        return False
    return bool(READY_RE.search(text or "")) or bool(SHORT_READY_RE.match((text or "").strip()))


def parse_quiz_answers(text: str) -> list[dict]:
    raw = text.lstrip()
    if raw.startswith(QUIZ_PREFIX):
        raw = raw[len(QUIZ_PREFIX) :].strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return [{"id": "answer", "answer": raw}]
    answers = payload.get("answers", payload)
    if isinstance(answers, list):
        return answers
    return [{"id": "answer", "answer": raw}]


def unit_label(unit: dict) -> str:
    part = f" — {unit['part_title']}" if unit.get("part_title") else ""
    return f"{unit['book']}: {unit['title']}{part}"


def _briefing(state: dict) -> str:
    cid = copy_id_of(state)
    unit_id = state.get("current_chapter_id") or first_unit_id(cid)
    unit = get_unit(cid, unit_id) or {}
    mastery = state.get("mastery") or {}
    unlocked = [item["id"] for item in curriculum_toc(cid, mastery) if item.get("unlocked")]
    weak = state.get("weak_concepts") or []
    nxt = next_unit_id(cid, unit_id)
    nxt_unit = get_unit(cid, nxt) if nxt else None
    book = load_book(cid).get("book") or {}
    copy = get_copy(cid) or {}
    extra = flavor_addendum(copy.get("flavor"))
    flavor_block = f"\n\nWork-specific notes:\n{extra}" if extra else ""
    return (
        f"Work: {book.get('title') or copy.get('title') or 'this book'}"
        f" — {book.get('author') or copy.get('author') or 'the author'}\n"
        f"Copy id: {cid}\n"
        f"Current unit id: {unit_id}\n"
        f"Current unit: {unit_label(unit) if unit else unit_id}\n"
        f"Mode: {state.get('mode') or 'teach'}\n"
        f"Unlocked units: {', '.join(unlocked[:12])}{'…' if len(unlocked) > 12 else ''}\n"
        f"Next locked unit: {unit_label(nxt_unit) if nxt_unit and nxt not in unlocked else (nxt or 'none')}\n"
        f"Weak concepts to hit: {', '.join(weak) if weak else 'none'}\n"
        "Citation format: one [@paragraph_id] token per claim, e.g. [@u0003:p2]. Never ranges."
        f"{flavor_block}"
    )


@wrap_model_call
async def inject_briefing(request: ModelRequest, handler) -> ModelResponse:
    extra = _briefing(request.state)
    base = request.system_message
    prior = base.content if base is not None else ""
    if isinstance(prior, list):
        prior = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block) for block in prior
        )
    merged = SystemMessage(content=f"{prior}\n\n--- session briefing ---\n{extra}")
    return await handler(request.override(system_message=merged))


@tool
async def search_book(query: str, unit_id: str | None = None, runtime: ToolRuntime = None) -> list[dict]:
    """Search this copy's text. Pass the current unit_id to stay inside this unit. Returns quotes plus paragraph_id for [@id] citations."""
    cid = copy_id_of(runtime.state if runtime is not None else None)
    hits = await asearch(cid, query, unit_id=unit_id, k=5)
    return [
        {
            "paragraph_id": hit["paragraph_id"],
            "unit_id": hit["unit_id"],
            "book": hit["book"],
            "title": hit["title"],
            "quote": hit["text"][:900],
            "score": hit["score"],
        }
        for hit in hits
    ]


@tool("get_chapter_outline")
def get_chapter_outline_tool(unit_id: str | None = None, runtime: ToolRuntime = None) -> dict:
    """Return the argument skeleton of a unit: headings and opening sentences, not the full text."""
    cid = copy_id_of(runtime.state if runtime is not None else None)
    target = unit_id or (runtime.state.get("current_chapter_id") if runtime is not None else None) or first_unit_id(cid)
    return get_chapter_outline(cid, target)


@tool
def list_curriculum(runtime: ToolRuntime) -> list[dict]:
    """Table of contents with lock/mastery status for each unit."""
    cid = copy_id_of(runtime.state)
    return curriculum_toc(cid, runtime.state.get("mastery") or {})


@tool
def present_quiz(questions: list[QuizQuestion], runtime: ToolRuntime) -> Command:
    """Present a short-answer quiz. Call only when the student asked to be tested, never to re-form answers they just gave in chat."""
    quiz = Quiz(questions=questions)
    return Command(
        update={
            "mode": "test",
            "open_quiz": quiz.model_dump(),
            "messages": [
                ToolMessage(
                    "Quiz is now on screen. Wait for the student's written answers; do not grade yet.",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )


def prep(state: TutorState) -> dict:
    cid = copy_id_of(state)
    try:
        mastery = state.get("mastery") or initial_mastery(cid)
    except Exception:
        mastery = state.get("mastery") or {}
    requested = state.get("current_chapter_id")
    text = last_human_text(state)
    nav = NAV_RE.match(text.lstrip()) if text else None
    if nav:
        requested = nav.group(1)
    unit = None
    try:
        if requested:
            unit = get_unit(cid, requested)
        if unit is None or not (mastery.get(requested) or {}).get("unlocked"):
            requested = state.get("current_chapter_id") or first_unit_id(cid)
            if not (mastery.get(requested) or {}).get("unlocked"):
                requested = first_unit_id(cid)
    except Exception:
        requested = requested or state.get("current_chapter_id")
    updates: dict[str, Any] = {
        "copy_id": cid,
        "mastery": mastery,
        "current_chapter_id": requested,
        "mode": state.get("mode") or "teach",
        "weak_concepts": state.get("weak_concepts") or [],
    }
    if nav:
        updates["mode"] = "teach"
        updates["open_quiz"] = None
        updates["weak_concepts"] = []
    elif is_skip_quiz(text) and state.get("open_quiz"):
        updates["mode"] = "teach"
        updates["open_quiz"] = None
    return updates


def route(state: TutorState) -> str:
    text = last_human_text(state)
    if is_quiz_submission(text):
        return "judge"
    if is_ready_for_test(text) or (
        (state.get("mode") == "test") and not state.get("open_quiz")
    ):
        return "test"
    if state.get("mode") == "revise":
        return "revise"
    return "teach"


def after_judge(state: TutorState) -> str:
    if state.get("mode") == "revise":
        return "revise"
    if state.get("mode") == "teach":
        return "teach"
    return END


def after_revise(state: TutorState) -> str:
    if state.get("open_quiz"):
        return END
    return "test"


async def _passages_for(copy_id: str, unit_id: str, query: str, k: int = 6) -> str:
    hits = await asearch(copy_id, query, unit_id=unit_id, k=k)
    lines = []
    for hit in hits:
        lines.append(f"[{hit['paragraph_id']}] {hit['text'][:700]}")
    return "\n\n".join(lines) if lines else "(no passages)"


async def test_node(state: TutorState) -> dict:
    cid = copy_id_of(state)
    unit_id = state.get("current_chapter_id") or first_unit_id(cid)
    unit = get_unit(cid, unit_id) or {}
    weak = state.get("weak_concepts") or []
    outline = get_chapter_outline(cid, unit_id)
    query = "; ".join(weak) if weak else (unit.get("title") or "core argument")
    passages = await _passages_for(cid, unit_id, query)
    focus = (
        f"Write questions ONLY on these weak concepts: {weak}"
        if weak
        else "Cover the unit's 2–3 load-bearing claims, including at least one distinction or application."
    )
    model = init_chat_model("gpt-4o")
    quiz = await model.with_structured_output(Quiz).ainvoke(
        [
            SystemMessage(
                content=(
                    "You write short-answer tests on this unit for a student who has just been taught it. "
                    "No multiple choice. Questions must be answerable from the passages. "
                    f"{focus}"
                )
            ),
            AIMessage(
                content=(
                    f"Unit: {unit_label(unit)}\nOutline: {json.dumps(outline.get('outline', [])[:10])}\n\n"
                    f"Passages:\n{passages}"
                )
            ),
        ]
    )
    return {
        "mode": "test",
        "open_quiz": quiz.model_dump(),
        "messages": [
            AIMessage(
                content="Time to see whether this has settled. Answer in your own words in the fields below — not slogans, not recitations."
            )
        ],
    }


def _should_revise(judgment: Judgment) -> bool:
    misses = [c for c in judgment.concepts if c.score == "miss"]
    partials = [c for c in judgment.concepts if c.score == "partial"]
    if misses:
        return True
    if judgment.overall < MASTERY_THRESHOLD:
        return True
    if judgment.concepts and len(partials) > len(judgment.concepts) / 2:
        return True
    return False


def _format_judgment(judgment: Judgment, advancing: bool, next_label: str | None) -> str:
    body = (judgment.summary_for_student or "").strip()
    if advancing:
        if next_label:
            closer = f"That's enough for this chapter. Next is {next_label}."
        else:
            closer = "That's the last unit in the book. We can keep reviewing whenever you like."
    else:
        weak = [c.concept for c in judgment.concepts if c.score != "mastered"]
        if len(weak) == 1:
            closer = f"We'll stay on this unit and come back to {weak[0]} — then I'll ask you again on that."
        elif weak:
            listed = ", ".join(weak[:-1]) + f", and {weak[-1]}"
            closer = f"We'll stay on this unit and come back to {listed} — then I'll ask you again on those."
        else:
            closer = "We'll stay on this unit a little longer, then I'll ask you again."
    return normalize_citation_tokens(f"{body}\n\n{closer}".strip())


async def judge_node(state: TutorState) -> dict:
    cid = copy_id_of(state)
    unit_id = state.get("current_chapter_id") or first_unit_id(cid)
    unit = get_unit(cid, unit_id) or {}
    quiz = state.get("open_quiz") or {"questions": []}
    answers = parse_quiz_answers(last_human_text(state))
    questions = quiz.get("questions") or []
    paired = []
    for i, question in enumerate(questions):
        answer = answers[i]["answer"] if i < len(answers) and isinstance(answers[i], dict) else ""
        if not answer:
            match = next((a for a in answers if isinstance(a, dict) and a.get("id") == question.get("id")), None)
            answer = (match or {}).get("answer", "")
        paired.append({"question": question, "answer": answer})
    concepts = [q.get("concept") or q.get("prompt", "") for q in questions]
    passages = await _passages_for(cid, unit_id, " ".join(concepts) or unit.get("title", ""), k=8)
    model = init_chat_model("gpt-4o")
    judgment = await model.with_structured_output(Judgment).ainvoke(
        [
            SystemMessage(
                content=(
                    "You are a close-reading tutor scoring a short-answer test on this unit. "
                    "Score each answer against the passages, not a modern textbook rewrite. "
                    "miss = wrong, empty, or 'I don't know'; partial = some of the idea, missing a mechanism "
                    "the author insists on; mastered = could teach it. "
                    "overall is the mean of those scores (mastered=1, partial=0.5, miss=0). "
                    "Put the technical justification in each concept's evidence field — that is internal. "
                    "summary_for_student is the only text the student will read: 3–6 sentences in second person, "
                    "spoken like a tutor across a table. Name what they got right, then what the author still needs "
                    "them to see. Cite with [@paragraph_id] tokens. "
                    "If they wrote 'I don't know' or similar, treat it as honest and name the missing claim; "
                    "do not scold, do not call it a missed opportunity, do not quote their answer back. "
                    "Never mention scores, percentages, miss/partial/mastered, 'concept scores', or that a "
                    "reteach/retest is coming."
                )
            ),
            AIMessage(
                content=(
                    f"Unit: {unit_label(unit)}\nPassages:\n{passages}\n\n"
                    f"Questions and answers:\n{json.dumps(paired, ensure_ascii=False, indent=2)}"
                )
            ),
        ]
    )

    mastery = dict(state.get("mastery") or initial_mastery(cid))
    entry = dict(mastery.get(unit_id) or {"unlocked": True})
    entry["score"] = judgment.overall
    entry["concepts"] = [c.model_dump() for c in judgment.concepts]
    revise = _should_revise(judgment)
    weak = [c.concept for c in judgment.concepts if c.score != "mastered"]
    new_current = unit_id
    next_label = None
    if revise:
        entry["status"] = "revise"
        next_mode = "revise"
    else:
        entry["status"] = "mastered"
        next_mode = "teach"
        weak = []
        nxt = next_unit_id(cid, unit_id)
        if nxt:
            nxt_entry = dict(mastery.get(nxt) or {})
            nxt_entry["unlocked"] = True
            if nxt_entry.get("status") in (None, "locked"):
                nxt_entry["status"] = "in_progress"
            mastery[nxt] = nxt_entry
            new_current = nxt
            nxt_unit = get_unit(cid, nxt)
            next_label = unit_label(nxt_unit) if nxt_unit else nxt
    mastery[unit_id] = entry
    save_progress(state.get("user_id"), cid, mastery)
    return {
        "mastery": mastery,
        "mode": next_mode,
        "weak_concepts": weak,
        "open_quiz": None,
        "last_judgment": judgment.model_dump(),
        "current_chapter_id": new_current,
        "messages": [AIMessage(content=_format_judgment(judgment, advancing=not revise, next_label=next_label))],
    }


retrieval_tools = [search_book, get_chapter_outline_tool, list_curriculum, present_quiz]

TUTOR_SUMMARY_PROMPT = """You compress a close-reading tutoring session on the student's current book.

Preserve the student's own examples, mistakes, and distinctions. Quote them. Do not recast the session as a quiz-submission workflow unless the latest student message is actually a quiz.

Structure:

## CURRENT UNIT
Which unit is being taught, and which of the author's claims have already been covered.

## STUDENT THINKING
What the student has argued, analogized, or gotten wrong.

## STILL OPEN
The tutor's last unanswered question, and what in this unit has not yet been taught.

Do not invent a SESSION INTENT. Do not mention artifacts or files.

<messages>
Messages to summarize:
{messages}
</messages>
"""


def _history_middleware() -> SummarizationMiddleware:
    return SummarizationMiddleware(
        model="gpt-4o-mini",
        trigger=("tokens", 32000),
        keep=("messages", 20),
        summary_prompt=TUTOR_SUMMARY_PROMPT,
    )


teach_agent = create_agent(
    model="gpt-4o",
    tools=retrieval_tools,
    state_schema=TutorState,
    system_prompt=TEACH_PROMPT,
    middleware=[
        inject_briefing,
        _history_middleware(),
    ],
    name="teach",
)

revise_agent = create_agent(
    model="gpt-4o",
    tools=retrieval_tools,
    state_schema=TutorState,
    system_prompt=REVISE_PROMPT,
    middleware=[
        inject_briefing,
        _history_middleware(),
    ],
    name="revise",
)

builder = StateGraph(TutorState)
builder.add_node("prep", prep)
builder.add_node("teach", teach_agent)
builder.add_node("test", test_node)
builder.add_node("judge", judge_node)
builder.add_node("revise", revise_agent)
builder.add_edge(START, "prep")
builder.add_conditional_edges("prep", route, ["teach", "test", "judge", "revise"])
builder.add_edge("teach", END)
builder.add_edge("test", END)
builder.add_conditional_edges("judge", after_judge, {"revise": "revise", "teach": "teach", END: END})
builder.add_conditional_edges("revise", after_revise, {"test": "test", END: END})

agent = builder.compile()
