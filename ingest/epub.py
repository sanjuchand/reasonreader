from __future__ import annotations

import io
import re

from bs4 import BeautifulSoup

from ingest.unitize import clean_text

_SKIP_NAMES = re.compile(r"(nav|toc|copyright|cover|titlepage|index)", re.I)


def parse_epub(data: bytes) -> tuple[str, str, list[dict]]:
    import ebooklib
    from ebooklib import epub

    book = epub.read_epub(io.BytesIO(data))
    titles = book.get_metadata("DC", "title")
    authors = book.get_metadata("DC", "creator")
    title = titles[0][0] if titles else "Untitled"
    author = authors[0][0] if authors else ""
    chapters: list[dict] = []
    index = 0
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        name = (item.get_name() or "") + " " + (item.get_id() or "")
        if _SKIP_NAMES.search(name):
            continue
        soup = BeautifulSoup(item.get_content(), "html.parser")
        for tag in soup(["script", "style", "nav"]):
            tag.decompose()
        heading = soup.find(["h1", "h2"])
        chapter_title = clean_text(heading.get_text(" ", strip=True)) if heading else f"Chapter {index + 1}"
        if _SKIP_NAMES.search(chapter_title) and not soup.find("p"):
            continue
        blocks: list[dict] = []
        para_index = 0
        chapter_id = f"ch{index:02d}"
        for node in soup.find_all(["h3", "h4", "p"]):
            text = clean_text(node.get_text(" ", strip=True))
            if not text or len(text) < 3:
                continue
            if node.name in {"h3", "h4"}:
                blocks.append({"type": "h3", "text": text})
                continue
            blocks.append({"type": "p", "text": text, "paragraph_id": f"{chapter_id}:p{para_index}"})
            para_index += 1
        if not any(b["type"] == "p" for b in blocks):
            continue
        chapters.append(
            {
                "id": chapter_id,
                "title": chapter_title or f"Chapter {index + 1}",
                "blocks": blocks,
                "is_book_heading": False,
            }
        )
        index += 1
    return title, author, chapters
