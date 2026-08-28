from pathlib import Path

from ingest import SOURCE, build_chunks, build_units, parse_chapters


def _units() -> list[dict]:
    html = SOURCE.read_text(encoding="utf-8")
    return build_units(parse_chapters(html))


def test_source_exists():
    assert SOURCE.exists()


def test_introduction_is_first_unit():
    units = _units()
    assert units[0]["id"] == "chap01"
    assert units[0]["book"] == "Introduction"
    assert "INTRODUCTION" in units[0]["title"].upper()


def test_empty_book_headings_are_not_units():
    ids = {unit["id"] for unit in _units()}
    assert "chap02" not in ids
    assert "chap20" not in ids
    assert "chap35" not in ids
    # Book II/IV headings include real introductory prose, so they stay in the curriculum.
    assert "chap14" in ids
    assert "chap25" in ids


def test_division_of_labour_is_book_i_chapter_i():
    units = _units()
    labour = next(unit for unit in units if unit["source_chapter_id"] == "chap03")
    labour_units = [unit for unit in units if unit["source_chapter_id"] == "chap03"]
    assert len(labour_units) == 1
    assert labour["id"] == "chap03"
    assert labour["source_chapter_id"] == "chap03"
    assert labour["book"] == "Book I"
    assert "DIVISION OF LABOUR" in labour["title"].upper()
    assert "pin" in labour["paragraphs"][0]["text"].lower() or any(
        "pin" in p["text"].lower() for p in labour["paragraphs"]
    )


def test_pin_factory_lives_in_chapter_i():
    units = _units()
    labour = next(unit for unit in units if unit["source_chapter_id"] == "chap03")
    blob = " ".join(p["text"] for p in labour["paragraphs"]).lower()
    assert "pin" in blob


def test_long_chapters_split_into_parts():
    units = _units()
    rent_parts = [unit for unit in units if unit["source_chapter_id"] == "chap13"]
    assert len(rent_parts) > 1
    assert all(unit["id"].startswith("chap13-p") for unit in rent_parts)
    assert all(unit["word_count"] <= 4300 for unit in rent_parts)


def test_paragraph_ids_are_stable_and_unique():
    units = _units()
    ids = [p["paragraph_id"] for unit in units for p in unit["paragraphs"]]
    assert len(ids) == len(set(ids))
    assert ids[0].startswith("chap01:p")


def test_later_books_keep_their_labels():
    units = _units()
    by_source = {unit["source_chapter_id"]: unit for unit in units}
    assert by_source["chap15"]["book"] == "Book II"
    assert by_source["chap21"]["book"] == "Book III"
    assert by_source["chap26"]["book"] == "Book IV"
    assert by_source["chap36"]["book"] == "Book V"


def test_chunks_keep_unit_metadata():
    units = _units()
    chunks = build_chunks(units)
    assert chunks
    labour_chunks = [c for c in chunks if c["chapter_id"] == "chap03"]
    assert labour_chunks
    assert all("paragraph_id" in c and "unit_id" in c for c in labour_chunks)
