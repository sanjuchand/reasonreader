from __future__ import annotations

import re

from ingest.unitize import clean_text

_JUNK_PAGE = re.compile(
    r"^(copyright|contents|table of contents|index|title page|titlepage|isbn)\b",
    re.I,
)


def parse_pdf(data: bytes) -> tuple[str, str, list[dict]]:
    import fitz

    doc = fitz.open(stream=data, filetype="pdf")
    meta = doc.metadata or {}
    title = clean_text(meta.get("title") or "") or "Untitled"
    author = clean_text(meta.get("author") or "")
    sizes: list[float] = []
    pages: list[tuple[str, list[tuple[float, str]]]] = []
    for page in doc:
        page_title = ""
        lines: list[tuple[float, str]] = []
        blocks = page.get_text("dict").get("blocks") or []
        for block in blocks:
            for line in block.get("lines") or []:
                spans = line.get("spans") or []
                text = clean_text("".join(span.get("text") or "" for span in spans))
                if not text:
                    continue
                size = max((float(span.get("size") or 0) for span in spans), default=0)
                sizes.append(size)
                if not page_title:
                    page_title = text
                lines.append((size, text))
        pages.append((page_title, lines))
    doc.close()

    median = sorted(sizes)[len(sizes) // 2] if sizes else 12
    heading_cut = median * 1.25
    chapters: list[dict] = []
    current: dict | None = None

    def flush() -> None:
        nonlocal current
        if current and any(b["type"] == "p" for b in current["blocks"]):
            chapters.append(current)
        current = None

    for page_title, lines in pages:
        if lines and _JUNK_PAGE.search(page_title) and len(lines) < 12:
            continue
        for size, text in lines:
            if size >= heading_cut and len(text) < 120:
                flush()
                cid = f"ch{len(chapters):02d}"
                current = {
                    "id": cid,
                    "title": text,
                    "blocks": [],
                    "is_book_heading": False,
                }
                continue
            if current is None:
                current = {
                    "id": "ch00",
                    "title": title if title != "Untitled" else "Beginning",
                    "blocks": [],
                    "is_book_heading": False,
                }
            para_n = sum(1 for b in current["blocks"] if b["type"] == "p")
            current["blocks"].append(
                {"type": "p", "text": text, "paragraph_id": f"{current['id']}:p{para_n}"}
            )
    flush()
    if not chapters:
        raise ValueError("No extractable text. Scanned PDFs are not supported yet.")
    return title, author, chapters
