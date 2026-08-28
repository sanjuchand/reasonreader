from ingest.epub import parse_epub
from ingest.pdf import parse_pdf
from ingest.unitize import assign_opaque_ids, build_units


def test_epub_extracts_chapter_and_paragraph(tmp_path):
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("test-pins")
    book.set_title("Pins")
    book.add_author("Tester")
    chapter = epub.EpubHtml(title="One", file_name="one.xhtml", lang="en")
    chapter.content = (
        "<html><body><h1>Chapter One</h1>"
        "<p>The pin factory employs eighteen men.</p></body></html>"
    )
    book.add_item(chapter)
    book.toc = (chapter,)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", chapter]
    path = tmp_path / "pins.epub"
    epub.write_epub(str(path), book)
    title, author, chapters = parse_epub(path.read_bytes())
    assert title == "Pins"
    assert author == "Tester"
    units = assign_opaque_ids(build_units(chapters))
    blob = " ".join(p["text"] for unit in units for p in unit["paragraphs"])
    assert "pin factory" in blob.lower()
    assert units[0]["id"] == "u0000"


def test_pdf_extracts_text():
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Chapter One", fontsize=18)
    page.insert_text((72, 120), "The pin factory employs eighteen men.", fontsize=11)
    data = doc.tobytes()
    doc.close()
    title, _author, chapters = parse_pdf(data)
    units = assign_opaque_ids(build_units(chapters))
    blob = " ".join(p["text"] for unit in units for p in unit["paragraphs"])
    assert "pin factory" in blob.lower()
    assert title
