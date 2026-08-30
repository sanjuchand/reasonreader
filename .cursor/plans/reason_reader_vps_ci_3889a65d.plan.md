---
name: Reason Reader VPS CI
overview: Point this repo at GitHub `sanjuchand/reasonreader`, put Ken behind the existing Caddy on `emailvps` at reasonreader.com (DNS-only at Cloudflare), and gate every deploy on pytest + Vitest.
todos:
  - id: health-tdd
    content: Add /api/health and a test that fails first, then passes
    status: in_progress
  - id: ci-workflow
    content: "GitHub Actions: pytest + pnpm test on PR and main"
    status: pending
  - id: git-remote
    content: Create reasonreader repo, retarget origin, keep wealth-of-nations remote
    status: pending
  - id: cloudflare-dns
    content: Grey-cloud A/CNAME for reasonreader.com → 144.126.135.134
    status: pending
  - id: vps-compose-caddy
    content: Prod compose (localhost ports), Caddy site, secrets, demo ingest
    status: pending
  - id: deploy-workflow
    content: SSH deploy on main after CI; read-only deploy key on the VPS
    status: pending
isProject: false
---

# Reason Reader production and CI/CD

Ken stays the product name. **reasonreader.com** is the public hostname. The VPS already runs ForgeMail and FoundryStack; we add a compose project and a Caddy site and do not touch mail or existing hostnames.

```mermaid
flowchart LR
  user[Browser] --> dns[Cloudflare DNS grey]
  dns --> caddy[Caddy on emailvps]
  caddy --> next[Next.js 127.0.0.1:3080]
  next --> graph[LangGraph 127.0.0.1:2024]
  next --> pg[Postgres]
  graph --> pg
  next --> minio[MinIO 127.0.0.1:9100]
```

## Constraints from this box

- SSH: `emailvps` → `sanju@email-vps` (public IPv4 **144.126.135.134**).
- Reverse proxy: Caddy (`/etc/caddy/Caddyfile`). HTTPS is automatic once the hostname resolves here. Tenant files under `/etc/caddy/tenants/` are FoundryStack agents — **do not** put reasonreader there.
- Port **9000** is already `auth.foundrystack.app`. Prod MinIO must not bind `:9000`.
- Current git `origin` is [git@github.com:sanjuchand/wealth-of-nations.git](https://github.com/sanjuchand/wealth-of-nations). Keep that as `wealth-of-nations` and make `reasonreader` the new `origin`.
- Local tree has uncommitted tutor/event work. Commit or stash before the first push (only when you ask).

## 1. Git remote

- Create `sanjuchand/reasonreader` on GitHub if it does not exist (`gh repo create`, public, no README).
- `git remote rename origin wealth-of-nations`
- `git remote add origin git@github.com:sanjuchand/reasonreader.git`
- Push `main` after tests pass locally. Do not force-push.

## 2. Cloudflare DNS (grey cloud)

Locate the existing Cloudflare credentials on this machine (do not commit them). Create:

- `A` `reasonreader.com` → `144.126.135.134` (proxied **off**)
- `CNAME` `www` → `reasonreader.com` (proxied **off**)

Caddy will then issue Let’s Encrypt for both names.

## 3. Production compose on the VPS

Add a prod compose file (new), leave local [docker-compose.yml](docker-compose.yml) for dev.

Suggested checkout: `/srv/reasonreader/prod` (same pattern as `/srv/foundrystack/...`). Bind **localhost only**:

- Next.js → `127.0.0.1:3080`
- LangGraph → `127.0.0.1:2024`
- Postgres → `127.0.0.1:5435` (avoid colliding with anything on 5432/5434)
- MinIO → `127.0.0.1:9100` (API) / `9101` (console, localhost only)

New Dockerfiles: repo root for the graph (`langgraph.json` + `tutor_agent.py`), [web/](web/) for Next standalone. Graph command is the existing LangGraph server with `POSTGRES_URI` (not `langgraph dev` as a public process). Env file lives on the VPS only (copy from [.env.example](.env.example) / [web/.env.example](web/.env.example)): strong `SECRET_KEY`, real Google client id, OpenAI key, `LANGGRAPH_URL=http://127.0.0.1:2024`, `S3_ENDPOINT=http://127.0.0.1:9100`.

One-time on the box: `pnpm db:migrate` equivalent (apply [web/drizzle/0000_init.sql](web/drizzle/0000_init.sql) + [web/drizzle/0001_tutor_events.sql](web/drizzle/0001_tutor_events.sql)) and `uv run python -m ingest --seed-demo --embed` so Smith is the public try path.

Caddy (append a **new** managed block, do not edit ForgeMail/Foundry blocks):

```
reasonreader.com {
	reverse_proxy 127.0.0.1:3080
}
www.reasonreader.com {
	redir https://reasonreader.com{uri} permanent
}
```

Then `caddy reload`. Google Cloud Console: authorized origin and redirect `https://reasonreader.com`.

## 4. Test-gated CI/CD

TDD here means: **no merge/deploy unless the suite is green**; new deploy plumbing gets a test first.

- Add [`.github/workflows/ci.yml`](.github/workflows/ci.yml): on `pull_request` and `push` to `main`, two jobs:
  - `uv sync` + `uv run pytest` (existing [tests/](tests/): routing, ingest, events, adapters)
  - `pnpm test` in `web/` (existing [web/src/lib/auth/session.test.ts](web/src/lib/auth/session.test.ts), [google.test.ts](web/src/lib/auth/google.test.ts))
- Add a small **prod contract test** first (fail until health exists): e.g. Next `GET /api/health` returns `{ ok: true }` when DB is reachable; pytest or a Node test hits the route in CI with a stub or skipped-unless-env. Deploy job only starts after `ci` succeeds on `main`.
- Add [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml): `workflow_run` or `needs: ci` on `main` → SSH to `emailvps` and run `/srv/reasonreader/prod/scripts/deploy.sh` (`git pull`, `compose up -d --build`, migrate if needed). Secrets: `VPS_SSH_KEY`, `VPS_HOST` (`email-vps` / 144.126.135.134). VPS clone uses a **read-only deploy key** on `reasonreader`.
- GitHub branch protection on `main`: require the CI workflow.

No staging hostname in this pass.

## 5. What we will not do

- Touch ForgeMail containers, FoundryStack Caddy sites, or port 9000.
- Orange-cloud / Cloudflare as TLS terminator.
- Commit `.env`, OpenAI keys, or Cloudflare tokens.
- Expose MinIO or Postgres on the public interface.
- Share uploaded copies (product thesis unchanged).

## Order of work (after you approve)

1. Write `/api/health` + its failing test, then implement until CI-local green.
2. Add CI workflow; confirm pytest + Vitest on a branch.
3. GitHub repo + remotes; push `main` when you ask to commit.
4. Cloudflare grey-cloud records.
5. VPS checkout, prod compose, Caddy site, secrets, demo ingest.
6. Deploy workflow + deploy key; one green production deploy to https://reasonreader.com.
