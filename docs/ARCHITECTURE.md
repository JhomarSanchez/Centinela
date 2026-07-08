# ARCHITECTURE.md

## Context and Goal

Centinela is a monitoring platform for personal use and as a portfolio project. The goal is to help the author monitor personal services and demonstrate backend, DevOps, observability, and local AI integration skills.

The system is not designed for massive scale or multi-tenant production use. It should run well on one machine or a local cluster while still following production-minded practices such as containers, observability, and CI.

## Phase 1 Architecture

Phase 1 should stay intentionally small:

- A FastAPI backend exposes service-management endpoints.
- PostgreSQL stores services and health-check history.
- APScheduler runs inside the backend process and checks registered services periodically.
- Docker Compose runs the backend and PostgreSQL locally.

This keeps the first implementation easy to understand. A separate worker process can be introduced later only if the scheduler becomes too complex for the backend process.

```mermaid
flowchart LR
    User((User)) -->|API requests| API[FastAPI backend]
    API --> DB[(PostgreSQL)]
    API --> SCHED[APScheduler in backend process]
    SCHED -->|periodic HTTP checks| EXT[Monitored external services]
    SCHED -->|stores check results| DB
```

## Phase 2 Architecture (implemented)

Phase 2 adds classic observability on top of Phase 1, still in Docker Compose:

- The backend exposes Prometheus metrics at `GET /metrics` (no API key; it only reveals service names and statuses).
- Every health check updates in-memory metric series: latest status per service (`centinela_service_status`), a 0/1 availability gauge (`centinela_service_up`), latest latency in seconds (`centinela_check_latency_seconds`), and a cumulative counter by result (`centinela_checks_total`).
- On startup the backend re-seeds the gauges from the newest stored check per service, so restarts do not blank the dashboard. Deleting or renaming a service drops/moves its series.
- Prometheus scrapes the backend every 15 seconds.
- Grafana is provisioned from files under `observability/grafana/`: the Prometheus datasource and a "Centinela - Service Health" dashboard (current status, availability %, latency history, checks by result) exist immediately after `docker compose up`.

```mermaid
flowchart LR
    SCHED[Scheduler tick] -->|stores Check| DB[(PostgreSQL)]
    SCHED -->|updates in-memory series| MET[/GET /metrics/]
    MET -->|scraped every 15s| PROM[Prometheus]
    PROM --> GRAF[Grafana dashboard]
```

## Phase 3 Architecture (implemented)

Phase 3 adds incident tracking and local AI summaries:

- Ollama runs as a separate Compose service with no published ports: only the backend can reach it over the internal network. Models persist in the `ollama_models` volume (`docker compose exec ollama ollama pull llama3.1:8b` is a one-time step).
- After each stored check, the scheduler runs incident logic: `INCIDENT_FAILURE_THRESHOLD` (default 3) consecutive `down` checks open an `Incident`; an `up` check resolves it; `degraded` does neither (it breaks a down-streak but is not a recovery).
- When an incident opens, the backend builds a prompt from real data (service name, URL, incident start, last 10 checks) and asks Ollama for a 3-4 sentence summary. The prompt is stored on the incident (`raw_context`) for transparency.
- The AI is strictly best-effort: if Ollama is disabled, unreachable, or the model is not pulled yet, the incident still opens with `ai_summary = NULL`, and each later `down` check retries the summary. Incident bookkeeping never depends on the LLM.
- Incidents are exposed at `GET /incidents` (filter `?active=true|false`) and `GET /services/{id}/incidents`, and on the dashboard via the `centinela_incident_open` and `centinela_incidents_total` metrics.

## Target Architecture

Later phases add observability, local AI incident summaries, and Kubernetes deployment.

```mermaid
flowchart TB
    subgraph Cluster["Local Kubernetes cluster (Minikube/Kind)"]
        API[FastAPI backend]
        DB[(PostgreSQL)]
        SCHED[Health-check scheduler]
        AI[Ollama - local LLM]
        PROM[Prometheus]
        GRAF[Grafana]
    end

    EXT[Monitored external services]

    SCHED -->|periodic HTTP checks| EXT
    SCHED -->|stores checks and incidents| DB
    SCHED -->|incident context prompt| AI
    AI -->|summary response only| SCHED
    API --> DB
    API -->|exposes /metrics| PROM
    PROM --> GRAF
    User((User)) -->|queries API / views dashboards| API
    User --> GRAF
```

Ollama does not write to the database. The backend or scheduler sends a prompt to Ollama, receives a summary, and stores that summary in PostgreSQL.

## Draft Data Model

**Service**

- `id`
- `name`
- `url`
- `check_interval_seconds`
- `created_at`

**Check** - historical record of each health check

- `id`
- `service_id`
- `checked_at`
- `status` (`up`, `down`, or `degraded`)
- `latency_ms` (nullable)
- `http_code` (nullable; empty when no response was received at all)

**Incident**

- `id`
- `service_id`
- `started_at`
- `resolved_at` (nullable)
- `ai_summary` (text generated by Ollama)
- `raw_context` (checks and metadata used to generate the summary)

## Incident Detection Flow

1. The scheduler checks each service based on `check_interval_seconds`.
2. If a service fails N consecutive times, using a configurable threshold such as 3, the system creates an `Incident`.
3. The backend or scheduler builds a prompt with the service name, recent checks, status, latency, HTTP code, and incident start time.
4. The prompt is sent to Ollama over the internal service network.
5. Ollama returns a short incident summary.
6. The backend or scheduler stores the summary on the `Incident`.
7. When the service responds successfully again, the system sets `resolved_at`.

## Key Decisions and Alternatives

| Decision | Alternative Considered | Reason |
|---|---|---|
| FastAPI | Flask, Django | Native async support, Pydantic typing, and a strong ecosystem for services that integrate with AI. |
| PostgreSQL first | TimescaleDB from the start | PostgreSQL is enough for a portfolio MVP; TimescaleDB can be added later if time-series volume justifies it. |
| Ollama local | OpenAI or Anthropic API | Local AI keeps data on the machine, avoids paid external APIs, and demonstrates self-hosted AI skills. |
| Grafana instead of a custom dashboard | Custom frontend dashboard | Grafana saves frontend time and is an industry-standard observability tool. |
| Local Kubernetes | Cloud deployment from the start | Minikube or Kind avoids cloud cost while still teaching Kubernetes concepts. |

## Basic Security

- The API should require a simple API key in the `X-API-Key` header for write operations.
- Secrets such as database passwords must live in environment variables, not in source code.
- `.env` is ignored by git; `.env.example` contains only safe placeholders.
- Ollama should only be reachable inside the container or cluster network, not exposed publicly.

## Out of Scope for Now

- Multi-user authentication.
- Email or Slack alerts.
- Real cloud deployment.
