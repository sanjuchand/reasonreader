"""Load curriculum units and search embedded chunks for one copy."""

from __future__ import annotations

import io
import json
from functools import lru_cache

import numpy as np
from dotenv import load_dotenv

import blob_store
from ingest.constants import DEMO_COPY_ID, EMBED_MODEL, ROOT

load_dotenv(ROOT / ".env")


class CorpusNotBuiltError(FileNotFoundError):
    def __init__(self, copy_id: str, missing: str) -> None:
        super().__init__(
            f"Missing {missing} for copy {copy_id}. Seed or ingest that copy first."
        )
        self.copy_id = copy_id


def bust_copy(copy_id: str) -> None:
    load_book.cache_clear()
    _load_vectors.cache_clear()
    _ = copy_id


@lru_cache(maxsize=16)
def load_book(copy_id: str = DEMO_COPY_ID) -> dict:
    key = blob_store.copy_key(copy_id, "chapters.json")
    if not blob_store.exists(key):
        raise CorpusNotBuiltError(copy_id, key)
    return json.loads(blob_store.get_bytes(key).decode("utf-8"))


def load_units(copy_id: str = DEMO_COPY_ID) -> list[dict]:
    return load_book(copy_id)["units"]


def get_unit(copy_id: str, unit_id: str) -> dict | None:
    for unit in load_units(copy_id):
        if unit["id"] == unit_id:
            return unit
    return None


def first_unit_id(copy_id: str = DEMO_COPY_ID) -> str:
    return load_units(copy_id)[0]["id"]


def next_unit_id(copy_id: str, unit_id: str) -> str | None:
    ids = [unit["id"] for unit in load_units(copy_id)]
    try:
        index = ids.index(unit_id)
    except ValueError:
        return None
    if index + 1 >= len(ids):
        return None
    return ids[index + 1]


def previous_unit_id(copy_id: str, unit_id: str) -> str | None:
    ids = [unit["id"] for unit in load_units(copy_id)]
    try:
        index = ids.index(unit_id)
    except ValueError:
        return None
    if index <= 0:
        return None
    return ids[index - 1]


def initial_mastery(copy_id: str = DEMO_COPY_ID) -> dict[str, dict]:
    units = load_units(copy_id)
    mastery: dict[str, dict] = {}
    for i, unit in enumerate(units):
        mastery[unit["id"]] = {
            "unlocked": i == 0,
            "score": 0.0,
            "status": "in_progress" if i == 0 else "locked",
            "concepts": [],
        }
    return mastery


def get_chapter_outline(copy_id: str, unit_id: str) -> dict:
    unit = get_unit(copy_id, unit_id)
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


def curriculum_toc(copy_id: str, mastery: dict | None = None) -> list[dict]:
    mastery = mastery or {}
    items = []
    for unit in load_units(copy_id):
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


@lru_cache(maxsize=16)
def _load_vectors(copy_id: str) -> tuple[np.ndarray, list[dict]]:
    npy_key = blob_store.copy_key(copy_id, "embeddings.npy")
    meta_key = blob_store.copy_key(copy_id, "chunk_meta.json")
    if not blob_store.exists(npy_key):
        raise CorpusNotBuiltError(copy_id, npy_key)
    if not blob_store.exists(meta_key):
        raise CorpusNotBuiltError(copy_id, meta_key)
    matrix = np.load(io.BytesIO(blob_store.get_bytes(npy_key)))
    chunks = json.loads(blob_store.get_bytes(meta_key).decode("utf-8"))
    return matrix, chunks


def _embed_query(query: str) -> np.ndarray:
    from langchain_openai import OpenAIEmbeddings

    model = OpenAIEmbeddings(model=EMBED_MODEL)
    vector = np.asarray(model.embed_query(query), dtype="float32")
    norm = np.linalg.norm(vector)
    if norm:
        vector = vector / norm
    return vector


def search(copy_id: str, query: str, unit_id: str | None = None, k: int = 5) -> list[dict]:
    matrix, chunks = _load_vectors(copy_id)
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


async def asearch(copy_id: str, query: str, unit_id: str | None = None, k: int = 5) -> list[dict]:
    import asyncio

    return await asyncio.to_thread(search, copy_id, query, unit_id, k)
