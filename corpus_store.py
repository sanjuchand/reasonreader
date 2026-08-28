"""Load curriculum units and search embedded chunks."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "corpus"
EMBED_MODEL = "text-embedding-3-small"

load_dotenv(ROOT / ".env")


class CorpusNotBuiltError(FileNotFoundError):
    def __init__(self, missing: Path) -> None:
        super().__init__(
            f"Missing {missing}. Run `uv run python ingest.py --embed` from the project root first."
        )


@lru_cache(maxsize=1)
def load_book() -> dict:
    path = CORPUS / "chapters.json"
    if not path.exists():
        raise CorpusNotBuiltError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def load_units() -> list[dict]:
    return load_book()["units"]


def get_unit(unit_id: str) -> dict | None:
    for unit in load_units():
        if unit["id"] == unit_id:
            return unit
    return None


def first_unit_id() -> str:
    return load_units()[0]["id"]


def next_unit_id(unit_id: str) -> str | None:
    ids = [unit["id"] for unit in load_units()]
    try:
        index = ids.index(unit_id)
    except ValueError:
        return None
    if index + 1 >= len(ids):
        return None
    return ids[index + 1]


def previous_unit_id(unit_id: str) -> str | None:
    ids = [unit["id"] for unit in load_units()]
    try:
        index = ids.index(unit_id)
    except ValueError:
        return None
    if index <= 0:
        return None
    return ids[index - 1]


def initial_mastery() -> dict[str, dict]:
    units = load_units()
    mastery: dict[str, dict] = {}
    for i, unit in enumerate(units):
        mastery[unit["id"]] = {
            "unlocked": i == 0,
            "score": 0.0,
            "status": "in_progress" if i == 0 else "locked",
            "concepts": [],
        }
    return mastery


def get_chapter_outline(unit_id: str) -> dict:
    unit = get_unit(unit_id)
    if unit is None:
        return {"error": f"Unknown unit {unit_id}"}
    paragraphs = unit["paragraphs"]
    return {
        "id": unit["id"],
        "book": unit["book"],
        "book_title": unit["book_title"],
        "title": unit["title"],
        "part_title": unit["part_title"],
        "word_count": unit["word_count"],
        "outline": unit["outline"],
        "first_paragraph_id": paragraphs[0]["paragraph_id"] if paragraphs else None,
        "last_paragraph_id": paragraphs[-1]["paragraph_id"] if paragraphs else None,
        "paragraph_count": len(paragraphs),
    }


def curriculum_toc(mastery: dict | None = None) -> list[dict]:
    mastery = mastery or {}
    items = []
    for unit in load_units():
        entry = mastery.get(unit["id"]) or {}
        items.append(
            {
                "id": unit["id"],
                "book": unit["book"],
                "title": unit["title"],
                "part_title": unit["part_title"],
                "unlocked": bool(entry.get("unlocked")),
                "status": entry.get("status", "locked"),
                "score": entry.get("score", 0.0),
            }
        )
    return items


@lru_cache(maxsize=1)
def _load_vectors() -> tuple[np.ndarray, list[dict]]:
    npy = CORPUS / "embeddings.npy"
    meta = CORPUS / "chunk_meta.json"
    if not npy.exists():
        raise CorpusNotBuiltError(npy)
    if not meta.exists():
        raise CorpusNotBuiltError(meta)
    matrix = np.load(npy)
    chunks = json.loads(meta.read_text(encoding="utf-8"))
    return matrix, chunks


def _embed_query(query: str) -> np.ndarray:
    from langchain_openai import OpenAIEmbeddings

    model = OpenAIEmbeddings(model=EMBED_MODEL)
    vector = np.asarray(model.embed_query(query), dtype="float32")
    norm = np.linalg.norm(vector)
    if norm:
        vector = vector / norm
    return vector


def search(query: str, unit_id: str | None = None, k: int = 5) -> list[dict]:
    matrix, chunks = _load_vectors()
    query_vec = _embed_query(query)
    scores = matrix @ query_vec
    if unit_id:
        mask = np.array([chunk.get("unit_id") == unit_id for chunk in chunks], dtype=bool)
        scores = np.where(mask, scores, -1.0)
    top = np.argsort(-scores)[:k]
    hits = []
    for index in top:
        if float(scores[index]) < 0:
            continue
        chunk = dict(chunks[int(index)])
        chunk["score"] = round(float(scores[index]), 4)
        hits.append(chunk)
    return hits


async def asearch(query: str, unit_id: str | None = None, k: int = 5) -> list[dict]:
    import asyncio

    return await asyncio.to_thread(search, query, unit_id, k)


if __name__ == "__main__":
    import sys

    query = " ".join(sys.argv[1:]) or "pin factory"
    for hit in search(query, k=5):
        print(f"{hit['score']:.3f} {hit['book']} {hit['title']} [{hit['paragraph_id']}]")
        print(f"  {hit['text'][:200]}")
