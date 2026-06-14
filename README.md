# Samadhan-Agentic_Customer_Resolution_Engine

Samadhan is an agentic customer resolution engine for a mock digital lending company. It uses LangGraph-controlled workflows, RAG over policy documents, mock business tools, risk-aware ticketing, human escalation, audit logs, and LLMOps evaluation to resolve or route customer support issues safely.

## Local setup (T-001 foundation)

From this directory:

```bash
uv sync --group dev
uv run uvicorn app.main:app --reload
uv run pytest -q
```

Health check: `GET http://localhost:8000/health`

Landing page: `GET http://localhost:8000/` (Jinja + HTMX + Tailwind + Alpine UI shell)

## Landing page (T-010)

The public homepage at `/` is a recruiter-testable overview with:

- Hero, problem statement, and 10 seeded demo scenarios
- Key capabilities (LangGraph, RAG, mock tools, ticketing, audit, evaluation)
- Architecture highlights and mock-demo boundaries
- CTAs linking to `/demo-access` (page content is T-011) and `/login`

The global mock-data disclaimer appears via `templates/partials/demo_disclaimer.html` in the base layout.

## Demo access page (T-011)

Demo credentials and walkthrough: `GET http://localhost:8000/demo-access`

The page includes:

- Project demo summary and mock-only disclaimer
- Shared demo password (`Demo@123`) and 12 fake demo accounts (10 customer, 1 support agent, 1 admin)
- Scenario guide, recommended customer test questions, and walkthrough order
- Role-wise testing instructions and a sign-in CTA to `/login`

Demo accounts are documented here for recruiters. User seeding is **T-016**; chat and audit views are later milestones.

## Dashboard shells (T-012)

Role-protected dashboard home pages (placeholder shells only):

| Role | URL |
|------|-----|
| Customer | `GET http://localhost:8000/customer/dashboard` |
| Support agent | `GET http://localhost:8000/agent/dashboard` |
| Admin | `GET http://localhost:8000/admin/dashboard` |

Each shell uses `templates/dashboards/` with placeholder cards for future features (loans, tickets, Human Review queue, policy/audit/eval). No real data, chat, or ticket actions are implemented in T-012. RBAC guards from T-009 remain unchanged.

## Seed data template (T-013)

Demo seed workbook contract: [`data/seed/README.md`](data/seed/README.md)

- Workbook: `data/seed/master_excel/samadhan_demo_seed_data.xlsx` (19 header-only sheets)
- Machine-readable spec: `app/seed/template_spec.py`
- Manifest: `data/seed/seed_manifest.yaml`

Regenerate headers-only Excel from the spec:

```bash
uv run python scripts/generate_seed_workbook.py
```

T-014 adds `validate-only` mode; T-015 adds `reset` and `upsert`; T-016 populates demo users and customers; T-017 adds lending seed data for all 10 demo scenarios. Passwords in the `users` sheet are plaintext demo input (`Demo@123`) and are hashed at seed time via T-007.

Validate the workbook (read-only, no MongoDB):

```bash
uv run python scripts/seed_demo_data.py --mode validate-only
uv run python scripts/seed_demo_data.py --mode validate-only --file path/to/workbook.xlsx
```

Reset or upsert demo collections (requires MongoDB in `.env`):

```bash
uv run python scripts/seed_demo_data.py --mode reset --env local
uv run python scripts/seed_demo_data.py --mode upsert --env local
```

Exit code `0` on success, `1` on validation or connection failure.

Regenerate workbook with demo personas:

```bash
uv run python scripts/generate_seed_workbook.py
```

Copy `.env.example` to `.env` to override foundation settings locally. Do not commit `.env`.

## Login and logout (T-008 / T-016)

- Login page: `GET http://localhost:8000/login`
- Logout: `POST http://localhost:8000/logout`
- Sessions use a signed cookie (`SESSION_COOKIE_NAME`, default `samadhan_session`) signed with `SECRET_KEY`
- Set `SECRET_KEY` in `.env` (see `.env.example`); local dev falls back to a dev-only key when `APP_ENV=local`
- After `uv run python scripts/seed_demo_data.py --mode reset --env local` with Mongo configured, demo accounts from `/demo-access` can sign in with `Demo@123`

## Role-based route guards (T-009)

Protected route prefixes enforce roles from the signed session:

| Prefix | Required role |
|--------|----------------|
| `/customer/*` | `customer` |
| `/agent/*` | `support_agent` |
| `/admin/*` | `admin` |

- Unauthenticated access redirects to `/login`
- Wrong-role access redirects to the user's own role home dashboard
- Inactive session users are cleared and treated as logged out
- Public routes remain open: `/`, `/demo-access`, `/health`, `/login`, `/logout`

## Project structure (T-006)

Samadhan is a **modular monolith**. Shared repository/service abstractions live in `app/common/`; database client wiring is deferred to T-007+ (`app/db/`).

| Path | Purpose | Future tasks |
|------|---------|--------------|
| `app/core/` | Config, logging, exceptions, health probes, templates | T-001–T-005 |
| `app/api/routes/` | FastAPI route handlers | T-001+ |
| `app/common/` | `Repository`/`BaseRepository`, `Service`/`BaseService` | T-006 |
| `app/db/` | `DatabaseHandle` placeholder (no Motor yet) | T-007+ |
| `app/auth/` | Login, logout, signed sessions (T-008); RBAC guards (T-009) | T-008, T-009 |
| `app/users/` | User model, password hashing (T-007); login in T-008 | T-007, T-008 |
| `app/customers/` | Customer profiles | T-016+ |
| `app/tickets/` | Ticket lifecycle | T-021+ |
| `app/messages/` | Chat message persistence (architecture doc uses `chat/`) | T-022+ |
| `app/service_requests/` | NOC, statement, callback SRs | T-023+ |
| `app/audit/` | Audit log | T-024+ |
| `app/tools/` | Mock internal tools | Later milestone |
| `app/rag/` | Policy RAG | Later milestone |
| `app/agent/` | LangGraph workflow | Later milestone |
| `app/providers/` | LLM/embedding adapters | T-046+ |
| `app/evaluation/` | Golden cases, eval runners | Later milestone |
| `app/dashboards/` | Customer/agent/admin UI shells | T-012+ |
| `app/admin/` | Admin routes and policy upload | Later milestone |

Per-domain `models.py`, `repositories.py`, and `services.py` are added in their owning tasks (T-007 onward), not in T-006.

## Environment configuration (T-005)

The full local-first environment catalog lives in [`.env.example`](.env.example). Copy it to `.env` and adjust values for your machine:

```bash
cp .env.example .env
```

Variable groups:

| Group | Examples | Notes |
|-------|----------|-------|
| Application | `APP_NAME`, `APP_ENV`, `LOG_LEVEL` | T-001 foundation |
| Auth | `SECRET_KEY`, `SESSION_COOKIE_NAME` | Placeholder only in `.env.example`; used by auth in T-008 |
| Infrastructure | `MONGODB_URI`, `QDRANT_URL`, `REDIS_URL` | T-002 Docker Compose |
| LLM | `LLM_PROVIDER`, `GEMINI_API_KEY`, `OPENAI_API_KEY` | Optional keys; app starts without them |
| Vertex AI | `VERTEX_AI_PROJECT_ID`, `VERTEX_AI_LOCATION` | Optional cloud provider |
| LangSmith | `LANGSMITH_TRACING`, `LANGSMITH_API_KEY` | Off by default |
| Cost controls | `MAX_MESSAGES_PER_USER_PER_DAY`, `MAX_LLM_CALLS_PER_DAY` | Configured here; enforced in T-079 |
| Storage | `STORAGE_BACKEND`, `LOCAL_STORAGE_PATH`, `GCS_BUCKET_NAME` | Local-first default |

Vertex AI and LangSmith are optional. Never commit real API keys or `.env`. See `Product documents/DEPLOYMENT_GUIDE.md` for cloud deployment details.

## Local infrastructure (T-002)

**Prerequisite:** Docker Desktop (Windows/macOS) or Docker Engine (Linux).

Start MongoDB, Qdrant, and Redis:

```bash
docker compose up -d mongodb qdrant redis
```

Verify services:

```bash
docker compose ps
docker compose exec mongodb mongosh --quiet --eval "db.adminCommand('ping')"
curl http://localhost:6333/readyz
docker compose exec redis redis-cli ping
```

Expected ports on localhost:

| Service | Port(s) |
|---------|---------|
| MongoDB | 27017 |
| Qdrant (HTTP / gRPC) | 6333 / 6334 |
| Redis | 6379 |

Connection settings are in `.env.example` (`MONGODB_URI`, `MONGODB_DB_NAME`, `QDRANT_URL`, `QDRANT_API_KEY`, `REDIS_URL`). Copy to `.env` after starting Compose.

**Recommended local dev flow:** Compose up → copy `.env` → (future: seed / ingest) → `uv run uvicorn app.main:app --reload`.

The FastAPI app runs on the **host** for now. A `samadhan-app` container is planned for a later deployment task (T-080).

Stop services:

```bash
docker compose down
```

Reset persisted data (destructive):

```bash
docker compose down -v
```

**Port conflicts:** If 27017, 6333, 6334, or 6379 are already in use, stop the conflicting process or change host port mappings in `docker-compose.yml`.

**Security note:** Local MongoDB and Redis run without authentication for demo development only. Do not expose these ports on untrusted networks.
