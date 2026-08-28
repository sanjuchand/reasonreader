"""Parse the Gutenberg HTML of The Wealth of Nations into curriculum units and embeddings."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "wealth_of_nations.htm"
CORPUS = ROOT / "corpus"
WORD_CAP = 3500
SOFT_CAP = 4200
MIN_TAIL_WORDS = 800
EMBED_MODEL = "text-embedding-3-small"
EMBED_BATCH = 64
MIN_CHUNK_WORDS = 40
MAX_CHUNK_WORDS = 220

load_dotenv(ROOT / ".env")


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _word_count(text: str) -> int:
    return len(text.split()) if text else 0


def _title_from_h2(h2: Tag) -> str:
    return _clean_text(h2.get_text(" ", strip=True))


def _is_book_heading(title: str) -> bool:
    return bool(re.match(r"^BOOK\s+[IVX]+\.", title, re.I))


def _book_label(title: str) -> tuple[str, str]:
    match = re.match(r"^(BOOK\s+([IVX]+))\.\s*(.*)$", title, re.I)
    if not match:
        return title, ""
    return f"Book {match.group(2).upper()}", _clean_text(match.group(3))


def parse_chapters(html: str) -> list[dict]:
    """Return raw chapter dicts in document order, including empty book-title chapters."""
    soup = BeautifulSoup(html, "html.parser")
    chapters: list[dict] = []
    for section in soup.select("div.chapter"):
        h2 = section.find("h2")
        if h2 is None:
            continue
        anchor = h2.find("a", id=True)
        chapter_id = anchor["id"] if anchor else f"chap{len(chapters) + 1:02d}"
        title = _title_from_h2(h2)
        blocks: list[dict] = []
        para_index = 0
        for child in section.children:
            if isinstance(child, NavigableString) or not isinstance(child, Tag):
                continue
            if child.name == "h2":
                continue
            if child.name == "h3":
                heading = _clean_text(child.get_text(" ", strip=True))
                if heading:
                    blocks.append({"type": "h3", "text": heading})
                continue
            if child.name != "p":
                continue
            text = _clean_text(child.get_text(" ", strip=True))
            if not text:
                continue
            blocks.append(
                {
                    "type": "p",
                    "text": text,
                    "paragraph_id": f"{chapter_id}:p{para_index}",
                }
            )
            para_index += 1
        chapters.append(
            {
                "id": chapter_id,
                "title": title,
                "blocks": blocks,
                "is_book_heading": _is_book_heading(title) and not any(
                    b["type"] == "p" for b in blocks
                ),
            }
        )
    return chapters


def _bucket_paragraphs(paragraphs: list[dict], cap: int = WORD_CAP) -> list[list[dict]]:
    if not paragraphs:
        return []
    buckets: list[list[dict]] = []
    current: list[dict] = []
    current_words = 0
    for para in paragraphs:
        words = _word_count(para["text"])
        if current and current_words + words > cap:
            buckets.append(current)
            current = []
            current_words = 0
        current.append(para)
        current_words += words
    if current:
        buckets.append(current)
    # Don't leave a stub part when the leftover would make a weak mastery gate.
    while len(buckets) > 1:
        tail_words = sum(_word_count(p["text"]) for p in buckets[-1])
        prev_words = sum(_word_count(p["text"]) for p in buckets[-2])
        if tail_words >= MIN_TAIL_WORDS or prev_words + tail_words > SOFT_CAP:
            break
        buckets[-2].extend(buckets[-1])
        buckets.pop()
    return buckets


def _group_by_heading(blocks: list[dict]) -> list[tuple[str | None, list[dict]]]:
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


def _outline_for(paragraphs: list[dict], part_title: str | None) -> list[str]:
    outline: list[str] = []
    if part_title:
        outline.append(part_title)
    for para in paragraphs[:12]:
        sentence = re.split(r"(?<=[.!?])\s", para["text"], maxsplit=1)[0]
        if sentence:
            outline.append(sentence[:240])
    return outline


def _unit_html(title: str, part_title: str | None, paragraphs: list[dict]) -> str:
    parts = [f"<h2>{title}</h2>"]
    if part_title:
        parts.append(f"<h3>{part_title}</h3>")
    for para in paragraphs:
        parts.append(f'<p id="{para["paragraph_id"]}">{para["text"]}</p>')
    return "\n".join(parts)


def build_units(chapters: list[dict]) -> list[dict]:
    units: list[dict] = []
    book = "Introduction"
    book_title = "Introduction and Plan of the Work"
    for chapter in chapters:
        if chapter["id"] == "chap01":
            book = "Introduction"
            book_title = "Introduction and Plan of the Work"
        if _is_book_heading(chapter["title"]):
            book, book_title = _book_label(chapter["title"])
            if chapter["is_book_heading"]:
                continue
        groups = _group_by_heading(chapter["blocks"])
        if not groups:
            continue
        pieces: list[tuple[str | None, list[dict]]] = []
        for heading, paras in groups:
            buckets = _bucket_paragraphs(paras)
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
                    "word_count": _word_count(text),
                    "paragraphs": paragraphs,
                    "html": _unit_html(chapter["title"], part_title, paragraphs),
                    "outline": _outline_for(paragraphs, part_title),
                    "text": text,
                }
            )
    return units


def build_chunks(units: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    for unit in units:
        buf: list[dict] = []
        buf_words = 0
        for para in unit["paragraphs"]:
            words = _word_count(para["text"])
            if buf and buf_words + words > MAX_CHUNK_WORDS:
                chunks.append(_flush_chunk(unit, buf))
                buf = []
                buf_words = 0
            buf.append(para)
            buf_words += words
            if buf_words >= MIN_CHUNK_WORDS and words >= MIN_CHUNK_WORDS and buf_words >= MAX_CHUNK_WORDS * 0.6:
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


def _public_units(units: list[dict]) -> list[dict]:
    public = []
    for unit in units:
        public.append({k: v for k, v in unit.items() if k not in {"text", "html"}})
    return public


def embed_chunks(chunks: list[dict]) -> None:
    import numpy as np
    from langchain_openai import OpenAIEmbeddings

    embeddings_model = OpenAIEmbeddings(model=EMBED_MODEL)
    vectors: list[list[float]] = []
    texts = [chunk["text"] for chunk in chunks]
    for start in range(0, len(texts), EMBED_BATCH):
        batch = texts[start : start + EMBED_BATCH]
        print(f"Embedding chunks {start + 1}–{start + len(batch)} of {len(texts)}")
        vectors.extend(embeddings_model.embed_documents(batch))
    matrix = np.asarray(vectors, dtype="float32")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    matrix = matrix / norms
    CORPUS.mkdir(parents=True, exist_ok=True)
    np.save(CORPUS / "embeddings.npy", matrix)
    (CORPUS / "chunk_meta.json").write_text(
        json.dumps(
            [{k: v for k, v in chunk.items() if k != "text"} | {"text": chunk["text"]} for chunk in chunks],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def write_corpus(units: list[dict], chunks: list[dict], embed: bool) -> None:
    CORPUS.mkdir(parents=True, exist_ok=True)
    payload = {
        "book": {
            "title": "An Inquiry into the Nature and Causes of the Wealth of Nations",
            "author": "Adam Smith",
        },
        "units": _public_units(units),
    }
    (CORPUS / "chapters.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (CORPUS / "chunks.json").write_text(
        json.dumps(chunks, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote {len(units)} units and {len(chunks)} chunks to {CORPUS}")
    if embed:
        embed_chunks(chunks)
        print(f"Wrote embeddings to {CORPUS / 'embeddings.npy'}")


def smoke_search(query: str = "pin factory") -> None:
    from corpus_store import search

    hits = search(query, k=5)
    if not hits:
        raise SystemExit("Smoke search returned no hits. Did you run ingest with --embed?")
    print(f"Smoke search for {query!r}:")
    for hit in hits:
        print(f"  {hit['score']:.3f}  {hit['book']} / {hit['title']}  [{hit['paragraph_id']}]")
        print(f"    {hit['text'][:180]}...")
    top = hits[0]
    if "chap03" not in top["unit_id"] and "chap03" not in top["chapter_id"]:
        print("Warning: expected Book I Chapter I (chap03) near the top for 'pin factory'.", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--embed", action="store_true", help="Create OpenAI embeddings (requires OPENAI_API_KEY).")
    parser.add_argument("--smoke", action="store_true", help="Search 'pin factory' against the saved corpus.")
    args = parser.parse_args()

    if args.smoke and not args.embed:
        smoke_search()
        return

    html = SOURCE.read_text(encoding="utf-8")
    chapters = parse_chapters(html)
    units = build_units(chapters)
    chunks = build_chunks(units)
    write_corpus(units, chunks, embed=args.embed)
    if args.smoke:
        smoke_search()


if __name__ == "__main__":
    main()
