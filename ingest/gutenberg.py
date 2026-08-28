"""Gutenberg HTML adapter — used to seed the Smith demo copy."""

from __future__ import annotations

from bs4 import BeautifulSoup, NavigableString, Tag

from ingest.constants import SMITH_HTML
from ingest.unitize import clean_text, is_book_heading

SOURCE = SMITH_HTML


def parse_chapters(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    chapters: list[dict] = []
    for section in soup.select("div.chapter"):
        h2 = section.find("h2")
        if h2 is None:
            continue
        anchor = h2.find("a", id=True)
        chapter_id = anchor["id"] if anchor else f"chap{len(chapters) + 1:02d}"
        title = clean_text(h2.get_text(" ", strip=True))
        blocks: list[dict] = []
        para_index = 0
        for child in section.children:
            if isinstance(child, NavigableString) or not isinstance(child, Tag):
                continue
            if child.name == "h2":
                continue
            if child.name == "h3":
                heading = clean_text(child.get_text(" ", strip=True))
                if heading:
                    blocks.append({"type": "h3", "text": heading})
                continue
            if child.name != "p":
                continue
            text = clean_text(child.get_text(" ", strip=True))
            if not text:
                continue
            blocks.append({"type": "p", "text": text, "paragraph_id": f"{chapter_id}:p{para_index}"})
            para_index += 1
        chapters.append(
            {
                "id": chapter_id,
                "title": title,
                "blocks": blocks,
                "is_book_heading": is_book_heading(title) and not any(b["type"] == "p" for b in blocks),
            }
        )
    return chapters
