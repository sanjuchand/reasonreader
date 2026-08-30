from ingest.gutenberg import SOURCE, parse_chapters
from ingest.questions import unit_exam_source
from ingest.unitize import assign_opaque_ids, build_chunks, build_units, public_units


def _units() -> list[dict]:
    html = SOURCE.read_text(encoding="utf-8")
    return assign_opaque_ids(build_units(parse_chapters(html), track_smith_books=True))


def test_source_exists():
    assert SOURCE.exists()


def test_introduction_is_first_unit():
    units = _units()
    assert units[0]["id"] == "u0000"
    assert units[0]["source_chapter_id"] == "chap01"
    assert units[0]["book"] == "Introduction"
    assert "INTRODUCTION" in units[0]["title"].upper()
    assert units[0]["paragraphs"][0]["paragraph_id"] == "u0000:p0"


def test_empty_book_headings_are_not_units():
    ids = {unit["source_chapter_id"] for unit in _units()}
    assert "chap02" not in ids
    assert "chap20" not in ids
    assert "chap35" not in ids
    assert "chap14" in ids
    assert "chap25" in ids


def test_division_of_labour_is_book_i_chapter_i():
    units = _units()
    labour = next(unit for unit in units if unit["source_chapter_id"] == "chap03")
    labour_units = [unit for unit in units if unit["source_chapter_id"] == "chap03"]
    assert len(labour_units) == 1
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
    assert all(unit["id"].startswith("u") for unit in rent_parts)
    assert all(unit["word_count"] <= 4300 for unit in rent_parts)


def test_paragraph_ids_are_stable_and_unique():
    units = _units()
    ids = [p["paragraph_id"] for unit in units for p in unit["paragraphs"]]
    assert len(ids) == len(set(ids))
    assert ids[0] == "u0000:p0"


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
    labour_id = next(unit["id"] for unit in units if unit["source_chapter_id"] == "chap03")
    labour_chunks = [c for c in chunks if c["unit_id"] == labour_id]
    assert labour_chunks
    assert all("paragraph_id" in c and "unit_id" in c for c in labour_chunks)


def test_exam_source_uses_paragraph_ids():
    units = _units()
    source = unit_exam_source(units[0])
    assert "[u0000:p0]" in source
    assert "labour" in source.lower() or "labor" in source.lower()


def test_public_units_keep_questions_and_drop_full_text():
    units = _units()
    units[0]["questions"] = [
        {
            "id": "q1",
            "concept": "annual labour",
            "claim": "Labour is the fund.",
            "prompt": "What is the fund?",
            "kind": "explain",
        }
    ]
    public = public_units(units)
    assert "text" not in public[0]
    assert "html" not in public[0]
    assert public[0]["questions"][0]["concept"] == "annual labour"
