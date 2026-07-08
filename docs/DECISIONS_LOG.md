# DECISIONS_LOG.md

Historical project log: what changed, what was decided, and why. This file gives future sessions and AI agents the memory they do not otherwise have.

## How to Use This File

- **Add new entries at the top** in reverse chronological order so the newest project state appears first.
- Use the template below.
- Do not delete or rewrite old entries. If something changes, add a new entry explaining the change.
- Add an entry when you finish a meaningful task or phase, make an architecture decision, apply a workaround, or change a previous decision.

### Template

```text
## [Date] - [Short title]

**Phase:** (example: Phase 1 - Basic backend)
**What changed:** ...
**Decisions made and why:** ...
**Alternatives considered, if relevant:** ...
**Open follow-ups / TODO:** ...
```

---

## 2026-07-08 - Phases 4 and 5 implemented: Kubernetes manifests and GitHub Actions CI

**Phase:** Phase 4 - Kubernetes / Phase 5 - CI

**What changed:** The full stack now deploys to a local Kubernetes cluster from kustomize manifests under `k8s/` (base + `local` overlay), and `.github/workflows/ci.yml` runs lint, the test suite, a Docker image build, and kustomize rendering on every push and pull request. Verified end to end against a kind cluster (`kind create cluster --name centinela`): all five deployments rolled out, a service was registered through the port-forwarded API, checks accumulated, Prometheus scraped the backend Service, and Grafana came up provisioned. The README gained a "Run on Kubernetes" section, a CI badge, and a capability table.

**Decisions made and why:**
- **Kustomize (base + overlays) instead of Helm:** kustomize ships inside kubectl (`kubectl apply -k`), needs no templating language, and the overlay pattern is enough for a local/learning deployment. The `local` overlay demonstrates a merge patch (faster scheduler tick).
- **Service names match Compose service names** (`postgres`, `backend`, `ollama`, `prometheus`), so the Prometheus scrape config and Grafana provisioning files are shared between both environments byte-for-byte. The copies under `k8s/base/config/` exist only because kustomize refuses to read files outside its root; the header comment says to keep both sides in sync.
- **Single backend replica by design:** the APScheduler lives inside the API process; two replicas would run duplicate health checks. Splitting the scheduler into its own Deployment is the documented path if scaling is ever needed.
- **Secrets are generated with `change-me` placeholder literals** in the base so a throwaway local cluster works out of the box; anything real must override them in an overlay. No real credentials in git, same rule as `.env.example`.
- **`Recreate` strategy for every pod with a ReadWriteOnce volume** (postgres, ollama, prometheus, grafana): a rolling update would try to attach the same volume to two pods at once.
- **CI has no PostgreSQL service container** because the tests run on in-memory SQLite by design — the pipeline is three parallel-friendly jobs (lint+test, image build, manifest render) and finishes in ~1 minute. Image publishing to a registry stays an optional follow-up.

**Workarounds:**
- `kind load docker-image` fails against Docker Desktop's containerd image store ("ctr: content digest not found") for images pulled from Docker Hub, because their multi-platform manifests reference blobs that `docker save` does not export. Fix: `docker save --platform linux/amd64 <image> -o file.tar` then `kind load image-archive file.tar`. Locally built single-platform images load fine either way.
- `ollama/ollama:latest` gets `imagePullPolicy: IfNotPresent` explicitly, because the `:latest` tag defaults to `Always`, which would ignore the pre-loaded image and re-download ~2 GB inside the node.

**Open follow-ups / TODO:**
- Optional: publish the backend image to GHCR from CI.
- Optional future phases from the roadmap: alerts, cloud deployment, multi-user auth, GitOps.
- The backend pod restarts once or twice on first boot while PostgreSQL initializes (migrations fail until it is ready); an initContainer that waits for the database would make first boot cleaner.

## 2026-07-08 - Phase 3 implemented: incidents with local AI summaries, plus pending hardening fixes

**Phase:** Phase 3 - Local AI incident summaries

**What changed:** Incident tracking now exists end to end: an `Incident` model + Alembic migration `0002`, detection logic in `app/services/incident_manager.py` driven by the scheduler tick, an Ollama HTTP client (`app/ai/ollama_client.py`) and prompt builder (`app/ai/prompt.py`), read-only endpoints (`GET /incidents`, `GET /services/{id}/incidents`), two new metrics (`centinela_incident_open`, `centinela_incidents_total`) with an "Open incidents" dashboard panel, and Ollama as a Compose service (internal network only, models persisted in a volume, NVIDIA GPU reserved). The suite grew from 45 to 69 tests. Verified live: the unreachable demo service opened incident #1 with the prompt stored in `raw_context`.

**Decisions made and why:**
- **Detection rule:** `INCIDENT_FAILURE_THRESHOLD` (default 3, per the Phase 0 proposal) consecutive `down` checks open an incident; an `up` check resolves it; `degraded` neither opens nor resolves (it breaks a down-streak but is not a recovery). One open incident max per service.
- **`started_at` is the beginning of the failure streak** (the oldest `down` in the streak), not the moment the threshold was crossed — closer to the truth the user cares about.
- **The AI is best-effort by design.** Any Ollama failure (down, model not pulled, timeout, bad JSON) returns `None` instead of raising; the incident opens with `ai_summary = NULL` and each later `down` check retries. Incident bookkeeping must never depend on the LLM.
- **`raw_context` stores the exact prompt** even when generation fails — transparency about what the model saw, and free debugging material.
- **Ollama has no published ports**: only the backend can reach it inside the Compose network, per the architecture's security notes. The `ollama/ollama` image is `latest` because model behavior is pinned by the model tag (`llama3.1:8b`), not the server version.
- **Incident processing is isolated in the tick** with its own try/except, same pattern as the per-service check isolation: an AI-path bug cannot stop health checks.

**Pending recommendations from the Phase 2 review, applied here:**
- Retention: a daily scheduler job deletes checks older than `CHECK_RETENTION_DAYS` (default 30; 0 disables). Incidents are kept forever.
- Failed checks now store `latency_ms = NULL` instead of the time-to-timeout, so latency graphs only show real response times.
- `find_due_services` uses one aggregate query (GROUP BY + outer join) instead of one query per service (N+1).
- The API logs a warning at startup when `API_KEY` is still `change-me`.

**Alternatives considered:**
- Counting `degraded` toward the failure threshold: rejected — a slow-but-answering service is a different problem than an outage, and mixing them would blur what an "incident" means.
- Generating summaries in a separate worker/queue: rejected at this scale; the tick tolerates the LLM latency because checks are already per-service isolated, and `max_instances=1` + `coalesce` protect against pile-ups.

**Open follow-ups / TODO:**
- Start Phase 4: Kubernetes manifests for the full stack (backend, PostgreSQL, Ollama, Prometheus, Grafana) in Minikube or Kind.
- If many services fail at once, summary generation serializes inside the tick; revisit with a queue or async checks if that ever hurts.

## 2026-07-08 - Phase 2 implemented: Prometheus metrics, Grafana dashboard, and Phase 1 hardening

**Phase:** Phase 2 - Classic observability

**What changed:** The backend now exposes Prometheus metrics at `/metrics` (`app/metrics.py`), Docker Compose gained Prometheus (`prom/prometheus:v3.5.0`) and Grafana (`grafana/grafana:12.0.2`) services, and Grafana is fully provisioned from `observability/`: datasource, dashboard provider, and a "Centinela - Service Health" dashboard with current status, availability percentage, latency history, and checks-by-result panels. Verified end-to-end with the full Compose stack: one reachable and one unreachable service, metrics scraped by Prometheus, dashboard provisioned in Grafana, and gauges restored after a backend restart. The suite grew from 33 to 45 tests.

**Decisions made and why:**
- **Metric design:** gauges hold the latest check result per service (`centinela_service_status` 0/1/2, `centinela_service_up` 0/1, `centinela_check_latency_seconds`) and a counter (`centinela_checks_total{service_name,status}`) accumulates results. Gauges fit sparse scheduled checks better than histograms; the counter lets dashboards compute availability over any range. Latency is exported in seconds because Prometheus convention is base SI units.
- **Gauges are re-seeded from the newest stored check on startup** (when the scheduler is enabled), so a backend restart does not leave the dashboard on "No data" until every service is checked again. Counters are intentionally not restored: they must only count what the current process observed.
- **Metric series follow the service lifecycle:** deleting a service removes its series, and renaming moves them (drop old name, re-seed new name), so dashboards never show stale or ghost services.
- **Grafana is provisioned from files** instead of configured by hand, so `docker compose up` produces a working dashboard with zero clicks — and the dashboard JSON is versioned in git.

**Phase 1 hardening applied in the same pass (edge cases found during review):**
- The scheduler tick now commits per service inside a try/except: one unexpected failure (or a service deleted mid-tick) no longer discards every other check result of that tick. Covered by a new test.
- `create_service`/`update_service` catch the database `IntegrityError` so two concurrent writes with the same name produce a 409 instead of a 500 (the pre-check alone was racy).
- The API-key comparison uses `secrets.compare_digest` (constant-time) instead of `==` to avoid timing attacks.
- All Compose services got `restart: unless-stopped`, and the backend got a healthcheck (used by Prometheus's `depends_on` condition).

**Alternatives considered:**
- A Prometheus `Histogram` for latency: rejected because checks are sparse (one per interval per service); a last-value gauge graphs the actual measurements directly.
- `prometheus-fastapi-instrumentator` for automatic HTTP metrics: rejected for now to keep the metric surface small and hand-written while learning; can be added later if API request metrics become interesting.

**Open follow-ups / TODO:**
- Start Phase 3: Ollama service, incident detection, and AI summaries.
- Check history grows without bound; add a retention/cleanup job before the database becomes large (noted for a later phase).

## 2026-07-07 - README renamed to README.md with real Phase 1 instructions

**Phase:** Phase 1 - Basic backend

**What changed:** The root `README` (no extension) was replaced by `README.md`, rewritten to document the now-working Phase 1: real quick-start commands, actual API usage examples, the health-check classification rules, and test instructions. References in `AGENTS.md` were updated to `README.md`.

**Decisions made and why:**
- This reverses the earlier "treat the root file as `README` without an extension" decision. GitHub only renders Markdown when the file is named `README.md`; the extension-less file was displayed as raw text, so all badges, HTML, and Mermaid diagrams appeared as unreadable source code on the repository landing page.
- The "planned/not runnable" wording was removed because the commands now work.
- Badges were toned down from `for-the-badge` to `flat-square` style and fake status badges were avoided (no CI badge until Phase 5 exists).

**Alternatives considered:**
- Keeping `README` and accepting plain-text rendering was rejected: a portfolio project's landing page must render properly.

**Open follow-ups / TODO:**
- Add a real CI badge when Phase 5 lands.

## 2026-07-07 - Phase 1 implemented: FastAPI backend with scheduled health checks

**Phase:** Phase 1 - Basic backend

**What changed:** The full Phase 1 backend now exists under `backend/`: service CRUD API, `Service`/`Check` SQLAlchemy models with an initial Alembic migration, an APScheduler background job that performs periodic HTTP health checks, a check-history endpoint, Dockerfile + `docker-compose.yml` (API + PostgreSQL), and a 33-test pytest suite. Verified end-to-end: the Compose stack was built and started, a reachable and an unreachable service were registered, and both accumulated correct `up`/`down` history in PostgreSQL.

**Decisions made and why:**
- **Layered architecture** (routes → services → models) as proposed in `AGENTS.md`. No repository pattern: at this size it would add indirection without benefit.
- **Single scheduler "tick" job** instead of one APScheduler job per service: a tick every `SCHEDULER_TICK_SECONDS` (default 10) queries the database for services whose last check is older than their interval. This keeps the scheduler stateless — CRUD operations need no scheduler bookkeeping.
- **Status classification:** no response or 5xx → `down`; 4xx → `degraded`; 2xx/3xx slower than `DEGRADED_LATENCY_MS` → `degraded`; otherwise `up`. Kept in a pure function (`health_checker.classify`) so it is unit-testable without network.
- **Synchronous SQLAlchemy** (not async) for the first phase: simpler to read, debug, and test; FastAPI runs sync endpoints in a thread pool, which is more than enough for single-user load.
- **Tests use in-memory SQLite** with a dependency override instead of PostgreSQL, so `pytest` runs in under a second with no containers. The scheduler is disabled during tests via `SCHEDULER_ENABLED=false`.
- **psycopg 3** (`postgresql+psycopg://`) as the PostgreSQL driver — actively maintained successor of psycopg2.
- **APScheduler pinned `<4.0`** because the 4.x series changes the API completely.
- **Migrations run on container start** (`alembic upgrade head && uvicorn ...`) so `docker compose up` is the only command needed.
- Write endpoints require `X-API-Key`; reads stay open (single-user tool on a local network), per `docs/ARCHITECTURE.md`.

**Alternatives considered:**
- Async SQLAlchemy + asyncpg: rejected for now; revisit if check volume ever makes the thread pool a bottleneck.
- One APScheduler job per service: rejected because create/update/delete would each need to mutate scheduler state.

**Open follow-ups / TODO:**
- Start Phase 2: expose Prometheus metrics at `/metrics` and add Prometheus + Grafana to Compose.
- Note: the `Check` timestamp column is named `checked_at` (clearer than the draft's `timestamp`); `docs/ARCHITECTURE.md` was updated to match.

## 2026-07-07 - README visual polish

**Phase:** Phase 0 - Planning

**What changed:** The root `README` was redesigned as a more attractive repository landing page. It now includes a centered project header, status and stack badges, a navigation strip, feature/status tables, Mermaid diagrams, a clearer architecture section, and a repository map.

**Decisions made and why:**
- The project now treats the root file as `README` without an extension, matching the repository's current file layout and the user's preference.
- Badges were added for project status, current phase, Python, FastAPI, Docker, and Apache 2.0 licensing to make the repository easier to scan.
- The README keeps planned commands clearly marked as non-runnable until Phase 1 exists, so the presentation is attractive without being misleading.

**Alternatives considered:**
- A simpler text-only README was rejected because the repository landing page should quickly communicate value, stack, status, and direction to visitors.

**Open follow-ups / TODO:**
- Replace planned usage examples with real commands after Phase 1 is implemented.
- Add real CI and coverage badges once those systems exist.

## 2026-07-07 - Public README improved

**Phase:** Phase 0 - Planning

**What changed:** The root `README.md` was rewritten as a stronger public-facing project introduction. It now explains the problem Centinela solves, the intended user flow, planned capabilities, current status, architecture overview, repository guide, and how to read the project before application code exists.

**Decisions made and why:**
- The file remains `README.md` because GitHub and common developer tools discover and render Markdown READMEs reliably with that filename.
- The README describes planned API usage as a target interface and clearly marks it as not runnable yet, avoiding false setup instructions before Phase 1 exists.
- A compact Mermaid diagram was added to make the planned architecture easier for visitors to understand quickly.

**Alternatives considered:**
- Renaming the file to `README` was considered, but keeping `README.md` preserves Markdown rendering and the existing repository conventions documented in `AGENTS.md`.

**Open follow-ups / TODO:**
- Replace the planned usage examples with real setup and API commands once Phase 1 is implemented.

## 2026-07-07 - AI context cleanup and English documentation

**Phase:** Phase 0 - Planning

**What changed:** The repository context documents were translated to English and aligned so AI agents can resume work more reliably. The pass covered `AGENTS.md`, `CLAUDE.md`, `README.md`, `docs/ROADMAP.md`, `docs/ARCHITECTURE.md`, and this log. Repository hygiene files were added for secret handling, shared editor defaults, and UTF-8 consistency.

**Decisions made and why:**
- Project documentation should stay in English by default because it is easier for most AI coding agents to parse consistently.
- `AGENTS.md` remains the primary instruction source, while `CLAUDE.md` stays as a thin Claude-specific companion.
- Phase 1 describes APScheduler as running inside the backend process to keep the first implementation simple. A separate worker can be introduced later if there is a clear need.
- The architecture document now separates Phase 1 architecture from the later target architecture so agents do not implement Kubernetes, observability, or Ollama too early.
- Ollama is treated as a summary service only. It receives prompts and returns text; the backend or scheduler is responsible for database writes.

**Alternatives considered:**
- Leaving project documentation in Spanish was considered, but English was chosen for better cross-agent consistency.
- Adding only documentation without repository hygiene files was considered, but `.gitignore`, `.env.example`, `.editorconfig`, and `.gitattributes` were added so the documented rules are enforceable.

**Open follow-ups / TODO:**
- Start Phase 1 by initializing the FastAPI backend structure.
- Choose the exact dependency-management approach when Phase 1 begins.

## 2026-07-07 - Initial project planning

**Phase:** Phase 0 - Planning

**What changed:** The initial project scope was defined through a guided brainstorming session. Three project ideas were evaluated: a distributed job queue, e-commerce microservices, and a monitoring platform. The monitoring platform was selected because it is the most useful for the author's day-to-day work.

**Decisions made and why:**
- Backend stack: Python + FastAPI, chosen for the AI ecosystem and a reasonable learning curve for a beginner.
- Local AI component: Ollama will generate natural-language incident summaries, taking advantage of the author's dedicated NVIDIA GPU.
- Visualization: Grafana was chosen instead of a custom dashboard to keep the focus on backend and DevOps work.
- Deployment: local Kubernetes with Minikube or Kind was chosen as a no-cost learning environment before considering a real cloud deployment.
- Development was split into 5 phases: basic backend, observability, local AI, Kubernetes, and CI. The phases are designed for incremental learning.

**Alternatives considered:**
- Node.js and Go were considered for the backend, but Python was selected because of the AI focus.
- Starting directly in a real cloud environment was considered but rejected because of cost. It remains a possible future phase.

**Open follow-ups / TODO:**
- Choose the specific Ollama model in Phase 3. Initial candidate: `llama3.1:8b`.
- Define the exact consecutive-failure threshold for opening an incident. Initial proposal: 3.
- Start Phase 1: basic backend.
