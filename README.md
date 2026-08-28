# Wealth of Nations tutor

A local chapter-mastery tutor for Adam Smith’s *An Inquiry into the Nature and Causes of the Wealth of Nations*. The agent teaches, tests, judges, and reteaches until a unit is internalized, then unlocks the next one.

## Setup

```bash
uv sync
cp .env.example .env   # then set OPENAI_API_KEY
uv run python ingest.py --embed
```

`ingest.py --embed` parses `wealth_of_nations.htm` into `corpus/` and embeds chunks. Re-run it when the source HTML changes.

Smoke retrieval:

```bash
uv run python ingest.py --smoke
```

## Run

Terminal 1 — LangGraph server:

```bash
uv run langgraph dev --no-browser --port 2024
```

Terminal 2 — reader UI:

```bash
cd web
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). The UI talks to the graph at `http://localhost:2024` (assistant id `agent`).

## Layout

- `ingest.py` / `corpus_store.py` — Gutenberg HTML → units, chunks, embeddings
- `tutor_agent.py` — teach / test / judge / revise graph
- `langgraph.json` — LangGraph Server entry (`agent`)
- `web/` — three-pane reader (TOC, chapter, tutor chat)
