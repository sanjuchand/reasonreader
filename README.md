# Ken

Bring a book you have the right to read. We tutor you through your copy. We do not become the library.

Adam Smith’s *Wealth of Nations* is the public demo so you can try the loop without uploading.

## Setup

```bash
uv sync
cp .env.example .env   # then set OPENAI_API_KEY
cp web/.env.example web/.env.local
docker compose up -d
cd web && pnpm install && pnpm db:migrate
cd ..
uv run python -m ingest --seed-demo --embed
```

`--seed-demo` writes the Gutenberg HTML into object storage (MinIO if `S3_ENDPOINT` is set, otherwise `data/blobs/`) and embeds units for the demo copy.

## Run

Terminal 1 — LangGraph (set `POSTGRES_URI` in `.env` so threads persist):

```bash
uv run langgraph dev --no-browser --port 2024
```

Terminal 2 — UI:

```bash
cd web
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). Sign in, open the Smith demo, or upload a PDF/EPUB you have the right to read.

## Layout

- `ingest/` — format adapters (Gutenberg, EPUB, digital PDF) and unitizer
- `blob_store.py` — per-copy source + corpus artifacts
- `corpus_store.py` / `tutor_agent.py` — copy-scoped teach / test / judge / revise
- `web/` — library, three-pane studio at `/read/[copyId]`
