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
from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, SystemMessage
from langchain.tools import ToolRuntime, tool
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from copy_store import get_copy
from flavors import flavor_addendum
from ingest.constants import DEMO_COPY_ID
from event_store import events_from_judgment, record_events
from progress_store import save_progress
from corpus_store import (
    asearch,
    claim_lines,
    claim_passages,
    curriculum_toc,
    filter_unit_questions,
    first_unit_id,
    get_chapter_outline,
    get_unit,
    initial_mastery,
    load_book,
    next_unit_id,
    passages_for_questions,
    persist_unit_questions,
    student_quiz,
)

load_dotenv()

MASTERY_THRESHOLD = 0.8
QUIZ_PREFIX = "[[QUIZ_SUBMISSION]]"
READY_PREFIX = "[[READY_FOR_TEST]]"
NAV_RE = re.compile(r"^\[NAV\]\s+unit_id=(\S+)")
SKIP_QUIZ_RE = re.compile(r"^\[\[SKIP_QUIZ\]\]")
READY_RE = re.compile(r"\b(quiz me|test me|ready to be tested|give me (a |the )?quiz)\b", re.I)
MODEL_HISTORY_KEEP = 8

TEACH_PROMPT = """You are a demanding close-reading tutor of the book named in the session briefing.

Your job is that the student *internalize this author's actual argument*, not a slogan or a modern paraphrase.

Rules:
- The briefing lists the claims that define this unit, each with the paragraph_ids that carry it. Those claims are the course. Teach them, in order, from those paragraphs.
- Call get_claim_passages before you teach a claim. Explain the mechanism in that excerpt. Do not replace it with a famous nearby example from another paragraph or chapter.
- If the student wanders, take one turn, then return to the next untaught claim. Do not invent a new syllabus from the chat.
- Teach only the current unit. Do not skip ahead.
- Cite the paragraph_ids attached to the claim you are teaching, like [@u0003:p2]. Never invent ids. Never write ranges such as [@u0001:p1-@u0001:p3]; emit separate tokens instead. Do not bolt a citation onto an explanation of a different passage.
- Ask at most one question, then stop and wait. Do not answer it yourself. Do not keep teaching after a question mark.
- If the student is wrong, say so plainly and point at the passage.
- Never write the exam questions or their wording in chat. Never give answers they can paste.
- You do not unlock units, administer a course, or announce exams.
- If this unit is already mastered, do not reteach it. Point them at Begin next.
- If they type move on, continue, or unlock while this unit is still in play, point them at Ready to be tested.
- Never say a unit is locked if the briefing lists it as unlocked or as the current unit.
- If the latest user message is a quiz submission and you are teaching a *new* unit, congratulate briefly, then start this unit. Do not re-score the quiz.
- Never dump a whole chapter into the chat. Use get_chapter_outline and search_book.
"""

REVISE_PROMPT = """You are reteaching the weak concepts listed in the session briefing. The student just failed or only partly grasped them.

Rules:
- Do not re-lecture the whole unit. Only the weak concepts.
- Call get_claim_passages for the weak concept and teach from those excerpts.
- Cite the paragraph_ids attached to that claim, like [@u0000:p0]. Never invent ids or ranges.
- Contrast what they said with what the author actually wrote in those paragraphs.
- Offer a different angle than the first teaching pass (a concrete example, a distinction, a failure case).
- Ask at most one question, then stop and wait. Do not answer it yourself. Do not bring the test back in the same turn.
- Do not close the session or ask if they have other questions. After they reconstruct the weak claim, stop. They will use Ready to be tested when they want the written question again.
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


def is_protocol_text(text: str) -> bool:
    stripped = (text or "").lstrip()
    if not stripped:
        return True
    if stripped.startswith(READY_PREFIX) or is_skip_quiz(stripped):
        return True
    return bool(NAV_RE.match(stripped))


def is_tool_message(message: Any) -> bool:
    return _message_type(message) in {"tool", "function"}


def _tool_call_ids(message: Any) -> set[str]:
    calls = []
    if isinstance(message, dict):
        calls = message.get("tool_calls") or (message.get("additional_kwargs") or {}).get("tool_calls") or []
    else:
        calls = getattr(message, "tool_calls", None) or []
        extra = getattr(message, "additional_kwargs", None) or {}
        if not calls and isinstance(extra, dict):
            calls = extra.get("tool_calls") or []
    ids: set[str] = set()
    for call in calls:
        cid = call.get("id") if isinstance(call, dict) else getattr(call, "id", None)
        if cid:
            ids.add(str(cid))
    return ids


def _tool_response_id(message: Any) -> str | None:
    if isinstance(message, dict):
        return message.get("tool_call_id")
    return getattr(message, "tool_call_id", None)


def drop_unpaired_tool_calls(messages: list) -> list:
    """OpenAI 400s if an assistant tool_calls message has no matching tool replies."""
    kept: list = []
    index = 0
    while index < len(messages):
        message = messages[index]
        ids = _tool_call_ids(message)
        if ids:
            found: set[str] = set()
            end = index + 1
            while end < len(messages) and is_tool_message(messages[end]):
                tid = _tool_response_id(messages[end])
                if tid:
                    found.add(str(tid))
                end += 1
            if ids <= found:
                kept.extend(messages[index:end])
            index = end
            continue
        if is_tool_message(message):
            index += 1
            continue
        kept.append(message)
        index += 1
    return kept


def last_quiz_answer_clip(state: dict, *, limit: int = 280) -> str:
    for message in reversed(state.get("messages") or []):
        text = _message_text(message)
        if not is_quiz_submission(text):
            continue
        lines = []
        for item in parse_quiz_answers(text)[:3]:
            answer = (item.get("answer") or "").strip()
            if answer:
                lines.append(f"- {answer[:limit]}")
        return "\n".join(lines)
    return ""


def trim_model_messages(messages: list, *, keep: int = MODEL_HISTORY_KEEP) -> list:
    """Keep a short conversational window plus the current turn.

    Drops historical tool dumps, NAV/ready tokens, old quiz JSON, and
    summarizer injections. The current human message and any tools from
    this turn stay so the agent can use fresh search hits.
    """
    if not messages:
        return []
    last_human = None
    for index in range(len(messages) - 1, -1, -1):
        if _message_type(messages[index]) not in {"human", "user"}:
            continue
        if is_context_summary(messages[index]):
            continue
        last_human = index
        break
    if last_human is None:
        return list(messages[-keep:])
    selected = []
    for message in messages[:last_human]:
        if is_tool_message(message) or is_context_summary(message) or _tool_call_ids(message):
            continue
        if _message_type(message) not in {"human", "user", "ai", "assistant"}:
            continue
        text = _message_text(message)
        if is_protocol_text(text) or is_quiz_submission(text):
            continue
        if not text.strip():
            continue
        selected.append(message)
    return drop_unpaired_tool_calls(selected[-keep:] + list(messages[last_human:]))


def is_ready_for_test(text: str) -> bool:
    if is_quiz_submission(text):
        return False
    if NAV_RE.match(text.lstrip()):
        return False
    stripped = (text or "").lstrip()
    if stripped.startswith(READY_PREFIX):
        return True
    return bool(READY_RE.search(text or ""))


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


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", (text or "").lower())


def is_mostly_recitation(answer: str, sources: list[str], *, threshold: float = 0.72) -> bool:
    words = _words(answer)
    if len(words) < 12:
        return False
    answer_line = " ".join(words)
    source_words = _words(" ".join(sources))
    if not source_words:
        return False
    source_line = " ".join(source_words)
    if len(answer_line) > 80 and answer_line in source_line:
        return True
    window = len(words)
    answer_set = set(words)
    for start in range(0, max(1, len(source_words) - window + 1)):
        chunk = source_words[start : start + window]
        union = answer_set | set(chunk)
        if union and len(answer_set & set(chunk)) / len(union) >= threshold:
            return True
    overlap = sum(1 for word in words if word in set(source_words)) / len(words)
    return overlap >= 0.88 and len(words) >= 20


def apply_recitation_misses(judgment: Judgment, paired: list[dict]) -> Judgment:
    reciting = {i for i, item in enumerate(paired) if item.get("recitation")}
    if not reciting:
        return judgment
    concepts = []
    for index, concept in enumerate(judgment.concepts):
        if index in reciting:
            concepts.append(
                concept.model_copy(
                    update={
                        "score": "miss",
                        "reteach_angle": "Ask them to reconstruct the claim in their own words.",
                    }
                )
            )
        else:
            concepts.append(concept)
    weights = {"mastered": 1.0, "partial": 0.5, "miss": 0.0}
    overall = sum(weights[item.score] for item in concepts) / len(concepts) if concepts else 0.0
    extra = "Those lines are the author's. Put the claim in your own words."
    summary = (judgment.summary_for_student or "").strip()
    if extra not in summary:
        summary = f"{summary} {extra}".strip()
    return judgment.model_copy(update={"concepts": concepts, "overall": overall, "summary_for_student": summary})


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
        f"Current unit status: {(mastery.get(unit_id) or {}).get('status') or 'in_progress'}\n"
        f"Mode: {state.get('mode') or 'teach'}\n"
        f"Unlocked units: {', '.join(unlocked[:12])}{'…' if len(unlocked) > 12 else ''}\n"
        f"Next unit: {unit_label(nxt_unit) if nxt_unit else 'none'}"
        f"{' — unlocked' if nxt and nxt in unlocked else (' — locked' if nxt else '')}\n"
        "If current unit is mastered, do not teach it. The student uses Begin next.\n"
        f"Weak concepts to hit: {', '.join(weak) if weak else 'none'}\n"
        f"{_last_test_lines(state)}"
        "Citation format: one [@paragraph_id] token per claim, e.g. [@u0003:p2]. Never ranges.\n"
        f"{claim_lines(unit)}"
        f"{flavor_block}"
    )


def _last_test_lines(state: dict) -> str:
    judgment = state.get("last_judgment") or {}
    answers = last_quiz_answer_clip(state)
    if not judgment and not answers:
        return ""
    parts = ["Last written test — do not re-score."]
    summary = (judgment.get("summary_for_student") or "").strip()
    if summary:
        parts.append(summary)
    if answers:
        parts.append("Their last answers:")
        parts.append(answers)
    return "\n".join(parts) + "\n"


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
    return await handler(
        request.override(system_message=merged, messages=trim_model_messages(request.messages))
    )


def scope_search_unit(state: dict | None, requested: str | None = None) -> str | None:
    current = (state or {}).get("current_chapter_id")
    return current or requested


@tool
async def search_book(query: str, unit_id: str | None = None, runtime: ToolRuntime = None) -> list[dict]:
    """Search the current unit only. Returns quotes plus paragraph_id for [@id] citations."""
    state = runtime.state if runtime is not None else None
    cid = copy_id_of(state)
    scoped = scope_search_unit(state, unit_id)
    hits = await asearch(cid, query, unit_id=scoped, k=5)
    return [
        {
            "paragraph_id": hit["paragraph_id"],
            "unit_id": hit["unit_id"],
            "book": hit["book"],
            "title": hit["title"],
            "quote": hit["text"][:480],
            "score": hit["score"],
        }
        for hit in hits
    ]


@tool("get_chapter_outline")
def get_chapter_outline_tool(unit_id: str | None = None, runtime: ToolRuntime = None) -> dict:
    """Return the argument skeleton of the current unit: headings and opening sentences, not the full text."""
    state = runtime.state if runtime is not None else None
    cid = copy_id_of(state)
    target = scope_search_unit(state, unit_id) or first_unit_id(cid)
    return get_chapter_outline(cid, target)


@tool
def get_claim_passages(concept: str | None = None, runtime: ToolRuntime = None) -> list[dict]:
    """Return the exam's own paragraphs for a claim in this unit. Use this before teaching or reteaching that claim."""
    state = runtime.state if runtime is not None else {}
    cid = copy_id_of(state)
    unit_id = state.get("current_chapter_id") or first_unit_id(cid)
    unit = get_unit(cid, unit_id) or {}
    return claim_passages(unit, concept)


def ensure_unit_exam(copy_id: str, unit: dict) -> list[dict]:
    questions = list(unit.get("questions") or [])
    if questions:
        return questions
    from ingest.questions import generate_questions_for_unit

    questions = generate_questions_for_unit(unit)
    if questions and unit.get("id"):
        persist_unit_questions(copy_id, unit["id"], questions)
        unit["questions"] = questions
    return questions


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
        record_events(
            [
                {
                    "user_id": state.get("user_id"),
                    "copy_id": cid,
                    "unit_id": requested,
                    "kind": "opened_unit",
                    "payload": {"source": "live"},
                }
            ]
        )
    elif is_skip_quiz(text) and state.get("open_quiz"):
        updates["mode"] = "teach"
        updates["open_quiz"] = None
        record_events(
            [
                {
                    "user_id": state.get("user_id"),
                    "copy_id": cid,
                    "unit_id": requested,
                    "kind": "keep_teaching",
                    "payload": {"source": "live"},
                }
            ]
        )
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
    questions = filter_unit_questions(ensure_unit_exam(cid, unit), state.get("weak_concepts"))
    record_events(
        [
            {
                "user_id": state.get("user_id"),
                "copy_id": cid,
                "unit_id": unit_id,
                "kind": "ready_for_test",
                "payload": {"source": "live", "question_count": len(questions)},
            }
        ]
    )
    return {
        "mode": "test",
        "open_quiz": student_quiz(questions),
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
            closer = f"That's enough for this unit. Next is {next_label}. Use Begin next when you want to start it."
        else:
            closer = "That's the last unit in the book. We can keep reviewing whenever you like."
    else:
        weak = [c.concept for c in judgment.concepts if c.score != "mastered"]
        if len(weak) == 1:
            closer = f"We'll stay on this unit and come back to {weak[0]}. Use Ready to be tested when you want that question again."
        elif weak:
            listed = ", ".join(weak[:-1]) + f", and {weak[-1]}"
            closer = f"We'll stay on this unit and come back to {listed}. Use Ready to be tested when you want those questions again."
        else:
            closer = "We'll stay on this unit a little longer. Use Ready to be tested when you want the questions again."
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
    texts = {paragraph.get("paragraph_id"): paragraph.get("text") or "" for paragraph in unit.get("paragraphs") or []}
    source_texts = list(texts.values())
    for item in paired:
        cited = [texts[pid] for pid in (item["question"].get("paragraph_ids") or []) if pid in texts]
        item["recitation"] = is_mostly_recitation(item["answer"], cited or source_texts)
    concepts = [q.get("concept") or q.get("prompt", "") for q in questions]
    passages = passages_for_questions(unit, paired and [item["question"] for item in paired] or questions)
    if not passages:
        passages = await _passages_for(cid, unit_id, " ".join(concepts) or unit.get("title", ""), k=8)
    model = init_chat_model("gpt-4o")
    judgment = await model.with_structured_output(Judgment).ainvoke(
        [
            SystemMessage(
                content=(
                    "You are a close-reading tutor scoring a short-answer test on this unit. "
                    "Score each answer against the passages attached to that question, not a nearby chapter or a modern rewrite. "
                    "When you cite, use that question's paragraph_ids. "
                    "miss = wrong, empty, 'I don't know', or a recitation of the author's sentences; "
                    "partial = some of the idea, missing a mechanism the author insists on; "
                    "mastered = could teach it in their own words. "
                    "If recitation is true for an answer, score miss and tell them to use their own words. "
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
    judgment = apply_recitation_misses(judgment, paired)

    mastery = dict(state.get("mastery") or initial_mastery(cid))
    entry = dict(mastery.get(unit_id) or {"unlocked": True})
    entry["score"] = judgment.overall
    entry["concepts"] = [c.model_dump() for c in judgment.concepts]
    revise = _should_revise(judgment)
    weak = [c.concept for c in judgment.concepts if c.score != "mastered"]
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
            nxt_unit = get_unit(cid, nxt)
            next_label = unit_label(nxt_unit) if nxt_unit else nxt
    mastery[unit_id] = entry
    save_progress(state.get("user_id"), cid, mastery)
    record_events(
        events_from_judgment(
            user_id=state.get("user_id"),
            copy_id=cid,
            unit_id=unit_id,
            paired=paired,
            judgment=judgment,
            revise=revise,
        )
    )
    return {
        "mastery": mastery,
        "mode": next_mode,
        "weak_concepts": weak,
        "open_quiz": None,
        "last_judgment": judgment.model_dump(),
        "current_chapter_id": unit_id,
        "messages": [AIMessage(content=_format_judgment(judgment, advancing=not revise, next_label=next_label))],
    }


teach_tools = [get_claim_passages, search_book, get_chapter_outline_tool]
revise_tools = [get_claim_passages, search_book, get_chapter_outline_tool]

teach_agent = create_agent(
    model="gpt-4o",
    tools=teach_tools,
    state_schema=TutorState,
    system_prompt=TEACH_PROMPT,
    middleware=[inject_briefing],
    name="teach",
)

revise_agent = create_agent(
    model="gpt-4o",
    tools=revise_tools,
    state_schema=TutorState,
    system_prompt=REVISE_PROMPT,
    middleware=[inject_briefing],
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
builder.add_edge("judge", END)
builder.add_edge("revise", END)

agent = builder.compile()
