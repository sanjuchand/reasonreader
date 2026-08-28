from __future__ import annotations

import re

from ingest.constants import (
    MAX_CHUNK_WORDS,
    MIN_CHUNK_WORDS,
    MIN_TAIL_WORDS,
    SOFT_CAP,
    WORD_CAP,
)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def word_count(text: str) -> int:
    return len(text.split()) if text else 0


def is_book_heading(title: str) -> bool:
    return bool(re.match(r"^BOOK\s+[IVX]+\.", title, re.I))


def book_label(title: str) -> tuple[str, str]:
    match = re.match(r"^(BOOK\s+([IVX]+))\.\s*(.*)$", title, re.I)
    if not match:
        return title, ""
    return f"Book {match.group(2).upper()}", clean_text(match.group(3))


def bucket_paragraphs(paragraphs: list[dict], cap: int = WORD_CAP) -> list[list[dict]]:
    if not paragraphs:
        return []
    buckets: list[list[dict]] = []
    current: list[dict] = []
    current_words = 0
    for para in paragraphs:
        words = word_count(para["text"])
        if current and current_words + words > cap:
            buckets.append(current)
            current = []
            current_words = 0
        current.append(para)
        current_words += words
    if current:
        buckets.append(current)
    while len(buckets) > 1:
        tail_words = sum(word_count(p["text"]) for p in buckets[-1])
        prev_words = sum(word_count(p["text"]) for p in buckets[-2])
        if tail_words >= MIN_TAIL_WORDS or prev_words + tail_words > SOFT_CAP:
            break
        buckets[-2].extend(buckets[-1])
        buckets.pop()
    return buckets


def group_by_heading(blocks: list[dict]) -> list[tuple[str | None, list[dict]]]:
    groups: list[tuple[str | None, list[dict]]] = []
    heading: str | None = None
    paras: list[dict] = []
    for block in blocks:
        if block["type"] == "h3":
            if paras:
                groups.append((heading, paras))
            heading = block["text"]
            paras = []
            continue
        paras.append(block)
    if paras:
        groups.append((heading, paras))
    return groups


def outline_for(paragraphs: list[dict], part_title: str | None) -> list[str]:
    outline: list[str] = []
    if part_title:
        outline.append(part_title)
    for para in paragraphs[:12]:
        sentence = re.split(r"(?<=[.!?])\s", para["text"], maxsplit=1)[0]
        if sentence:
            outline.append(sentence[:240])
    return outline


def unit_html(title: str, part_title: str | None, paragraphs: list[dict]) -> str:
    parts = [f"<h2>{title}</h2>"]
    if part_title:
        parts.append(f"<h3>{part_title}</h3>")
    for para in paragraphs:
        parts.append(f'<p id="{para["paragraph_id"]}">{para["text"]}</p>')
    return "\n".join(parts)


def build_units(chapters: list[dict], *, track_smith_books: bool = False) -> list[dict]:
    units: list[dict] = []
    book = "The work"
    book_title = ""
    if track_smith_books:
        book = "Introduction"
        book_title = "Introduction and Plan of the Work"
    for chapter in chapters:
        if track_smith_books and chapter["id"] == "chap01":
            book = "Introduction"
            book_title = "Introduction and Plan of the Work"
        if track_smith_books and is_book_heading(chapter["title"]):
            book, book_title = book_label(chapter["title"])
            if chapter.get("is_book_heading"):
                continue
        groups = group_by_heading(chapter["blocks"])
        if not groups:
            continue
        pieces: list[tuple[str | None, list[dict]]] = []
        for heading, paras in groups:
            buckets = bucket_paragraphs(paras)
            if len(buckets) == 1:
                pieces.append((heading, buckets[0]))
            else:
                for i, bucket in enumerate(buckets, start=1):
                    label = heading or f"Part {i}"
                    if len(buckets) > 1 and heading:
                        label = f"{heading} ({i}/{len(buckets)})"
                    elif len(buckets) > 1:
                        label = f"Part {i} of {len(buckets)}"
                    pieces.append((label, bucket))

        multi = len(pieces) > 1
        for index, (part_title, paragraphs) in enumerate(pieces, start=1):
            unit_id = f"{chapter['id']}-p{index}" if multi else chapter["id"]
            text = "\n\n".join(p["text"] for p in paragraphs)
            units.append(
                {
                    "id": unit_id,
                    "source_chapter_id": chapter["id"],
                    "book": book,
                    "book_title": book_title,
                    "title": chapter["title"],
                    "part_title": part_title,
                    "order": len(units),
                    "word_count": word_count(text),
                    "paragraphs": paragraphs,
                    "html": unit_html(chapter["title"], part_title, paragraphs),
                    "outline": outline_for(paragraphs, part_title),
                    "text": text,
                }
            )
    return units


def assign_opaque_ids(units: list[dict]) -> list[dict]:
    for i, unit in enumerate(units):
        unit_id = f"u{i:04d}"
        unit["id"] = unit_id
        unit["order"] = i
        for j, para in enumerate(unit["paragraphs"]):
            para["paragraph_id"] = f"{unit_id}:p{j}"
        unit["html"] = unit_html(unit["title"], unit.get("part_title"), unit["paragraphs"])
    return units


def build_chunks(units: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    for unit in units:
        buf: list[dict] = []
        buf_words = 0
        for para in unit["paragraphs"]:
            words = word_count(para["text"])
            if buf and buf_words + words > MAX_CHUNK_WORDS:
                chunks.append(_flush_chunk(unit, buf))
                buf = []
                buf_words = 0
            buf.append(para)
            buf_words += words
            if (
                buf_words >= MIN_CHUNK_WORDS
                and words >= MIN_CHUNK_WORDS
                and buf_words >= MAX_CHUNK_WORDS * 0.6
            ):
                chunks.append(_flush_chunk(unit, buf))
                buf = []
                buf_words = 0
        if buf:
            chunks.append(_flush_chunk(unit, buf))
    return chunks


def _flush_chunk(unit: dict, paragraphs: list[dict]) -> dict:
    text = " ".join(p["text"] for p in paragraphs)
    return {
        "id": paragraphs[0]["paragraph_id"],
        "unit_id": unit["id"],
        "chapter_id": unit["source_chapter_id"],
        "book": unit["book"],
        "title": unit["title"],
        "part_title": unit["part_title"],
        "paragraph_id": paragraphs[0]["paragraph_id"],
        "paragraph_ids": [p["paragraph_id"] for p in paragraphs],
        "text": text,
    }


def public_units(units: list[dict]) -> list[dict]:
    return [{k: v for k, v in unit.items() if k not in {"text", "html"}} for unit in units]
