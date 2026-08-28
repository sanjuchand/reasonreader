from __future__ import annotations

import io
import json

import numpy as np
from langchain_openai import OpenAIEmbeddings

import blob_store
import copy_store
from ingest.constants import DEMO_COPY_ID, EMBED_BATCH, EMBED_MODEL, SMITH_HTML
from ingest.gutenberg import parse_chapters
from ingest.unitize import assign_opaque_ids, build_chunks, build_units, public_units


def detect_kind(content_type: str | None, filename: str) -> str:
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    if "epub" in ctype or name.endswith(".epub"):
        return "epub"
    if "pdf" in ctype or name.endswith(".pdf"):
        return "pdf"
    if "html" in ctype or name.endswith(".htm") or name.endswith(".html"):
        return "html"
    raise ValueError(f"Unsupported file type: {content_type or filename}")


def chapters_from_source(data: bytes, kind: str) -> tuple[str, str, list[dict], bool]:
    if kind == "html":
        chapters = parse_chapters(data.decode("utf-8", errors="replace"))
        return (
            "An Inquiry into the Nature and Causes of the Wealth of Nations",
            "Adam Smith",
            chapters,
            True,
        )
    if kind == "epub":
        from ingest.epub import parse_epub

        title, author, chapters = parse_epub(data)
        return title, author, chapters, False
    if kind == "pdf":
        from ingest.pdf import parse_pdf

        title, author, chapters = parse_pdf(data)
        return title, author, chapters, False
    raise ValueError(kind)


def embed_chunks(chunks: list[dict]) -> tuple[np.ndarray, list[dict]]:
    model = OpenAIEmbeddings(model=EMBED_MODEL)
    vectors: list[list[float]] = []
    texts = [chunk["text"] for chunk in chunks]
    for start in range(0, len(texts), EMBED_BATCH):
        batch = texts[start : start + EMBED_BATCH]
        print(f"Embedding chunks {start + 1}–{start + len(batch)} of {len(texts)}")
        vectors.extend(model.embed_documents(batch))
    matrix = np.asarray(vectors, dtype="float32")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    matrix = matrix / norms
    return matrix, chunks


def write_copy_artifacts(
    copy_id: str,
    title: str,
    author: str,
    units: list[dict],
    chunks: list[dict],
    matrix: np.ndarray,
) -> None:
    payload = json.dumps(
        {"book": {"title": title, "author": author}, "copy_id": copy_id, "units": public_units(units)},
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")
    blob_store.put_bytes(blob_store.copy_key(copy_id, "chapters.json"), payload, "application/json")
    blob_store.put_bytes(
        blob_store.copy_key(copy_id, "chunk_meta.json"),
        json.dumps(chunks, ensure_ascii=False).encode("utf-8"),
        "application/json",
    )
    buf = io.BytesIO()
    np.save(buf, matrix)
    blob_store.put_bytes(
        blob_store.copy_key(copy_id, "embeddings.npy"),
        buf.getvalue(),
        "application/octet-stream",
    )


def ingest_copy(copy_id: str, *, embed: bool = True) -> dict:
    copy = copy_store.get_copy(copy_id)
    if not copy:
        raise ValueError(f"Unknown copy {copy_id}")
    source = blob_store.get_bytes(blob_store.copy_key(copy_id, "source"))
    kind = detect_kind(copy.get("source_content_type"), copy.get("source_filename") or "")
    copy_store.set_copy_status(copy_id, "ingesting")
    try:
        title, author, chapters, smith = chapters_from_source(source, kind)
        if copy.get("kind") == "demo":
            title = copy.get("title") or title
            author = copy.get("author") or author
            smith = True
        units = assign_opaque_ids(build_units(chapters, track_smith_books=smith))
        chunks = build_chunks(units)
        if not embed:
            raise ValueError("Ingest requires embeddings")
        matrix, chunks = embed_chunks(chunks)
        write_copy_artifacts(copy_id, title, author, units, chunks, matrix)
        copy_store.set_copy_status(copy_id, "ready", title=title, author=author, error=None)
        from corpus_store import bust_copy

        bust_copy(copy_id)
        return {"copy_id": copy_id, "units": len(units), "chunks": len(chunks), "title": title}
    except Exception as exc:
        copy_store.set_copy_status(copy_id, "failed", error=str(exc)[:500])
        raise


def seed_demo(*, embed: bool = True) -> dict:
    html = SMITH_HTML.read_bytes()
    blob_store.put_bytes(blob_store.copy_key(DEMO_COPY_ID, "source"), html, "text/html")
    copy_store.upsert_demo_copy()
    return ingest_copy(DEMO_COPY_ID, embed=embed)
