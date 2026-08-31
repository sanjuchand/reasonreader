from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO_COPY_ID = "a0000000-0000-4000-8000-000000000001"
SMITH_HTML = ROOT / "wealth_of_nations.htm"
WORD_CAP = 3500
SOFT_CAP = 4200
MIN_TAIL_WORDS = 800
EMBED_MODEL = "text-embedding-3-small"
EMBED_BATCH = 64
MIN_UNIT_WORDS = 250
MIN_CHUNK_WORDS = 40
MAX_CHUNK_WORDS = 220
MAX_UPLOAD_BYTES = 40 * 1024 * 1024
ALLOWED_TYPES = {
    "application/epub+zip": "epub",
    "application/pdf": "pdf",
    "text/html": "html",
}
