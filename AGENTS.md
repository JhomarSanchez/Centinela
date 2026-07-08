# AGENTS.md - Instructions for AI Agents

This file is the primary source of instructions for any AI agent working in this repository. Read it fully before writing code.

## Project Context

- Prefer clarity over cleverness. Simple, readable code is better than a clever solution that is hard to explain.
- Explain the reason behind non-obvious decisions, either in short code comments or in the commit message.
- Assume the user is learning. If you introduce an uncommon pattern or tool, add one plain-language sentence explaining what it is for.
- Work by phase, following `docs/ROADMAP.md`. Do not implement a later phase until the current phase is complete and working.

## Project Mission

Centinela is a personal service-monitoring platform. It registers services, runs periodic health checks, stores availability history, exposes metrics, and later uses a local LLM through Ollama to generate natural-language incident summaries.

Read `README.md` for the product overview and `docs/ARCHITECTURE.md` for the system design.

## Current State

- Phase 0 is complete: planning, architecture, roadmap, and AI context files exist.
- Phase 1 is complete: FastAPI backend with service CRUD, APScheduler health checks, PostgreSQL persistence via Alembic migrations, Docker Compose, and a pytest suite.
- Phase 2 is complete: Prometheus metrics at `/metrics`, Prometheus and Grafana services in Docker Compose, and a provisioned Grafana dashboard under `observability/`.
- Phase 3 is complete: Ollama in Docker Compose (internal network only), incident detection on consecutive `down` checks, AI summaries stored on incidents, and incident endpoints at `/incidents` and `/services/{id}/incidents`.
- The next implementation work is Phase 4: Kubernetes manifests for the full stack, tested in Minikube or Kind.
- If the roadmap and code disagree, treat `docs/ROADMAP.md` and `docs/DECISIONS_LOG.md` as the sources of truth, then update them once the discrepancy is resolved.

## Non-Negotiable Rules

1. **Do not skip phases.** Follow `docs/ROADMAP.md`. If a better sequence seems necessary, propose it first instead of changing the plan silently.
2. **Update `docs/DECISIONS_LOG.md`** whenever you finish a meaningful task or phase, make an architecture decision, apply a workaround, or change a previous decision. Use the template in that file.
3. **Never commit secrets.** Credentials, API keys, and tokens belong in `.env`, which is ignored by git. Public placeholders belong in `.env.example`.
4. **Every service must run in a container.** Local installation is acceptable only for development tools such as linters, test runners, or editors.
5. **Run tests before calling a coding task done.** Even basic happy-path tests matter. For documentation-only tasks, validate links, formatting, and repository hygiene instead.
6. **Use small, descriptive commits** when commits are requested. Format: `phase-N: short description`.

## Stack and Code Conventions

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy ORM, Pydantic for validation, Alembic for migrations.
- **Testing:** Prefer `pytest` when tests are introduced unless a later decision changes this.
- **Style:** Follow PEP 8, use type hints in public functions, and add brief docstrings for modules and non-trivial functions.
- **Documentation language:** Keep repository documentation in English unless the user explicitly requests otherwise.
- **Local AI:** Ollama must run as a separate service. The backend talks to Ollama over HTTP; do not embed the model inside the API process.

## Proposed Repository Structure

```text
centinela/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/          # routers/endpoints
│   │   ├── models/       # SQLAlchemy models + Pydantic schemas
│   │   ├── services/     # business logic such as health checks
│   │   ├── scheduler/    # periodic jobs
│   │   └── ai/           # Ollama client and prompt building
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── observability/
│   ├── prometheus/prometheus.yml
│   └── grafana/dashboards/
├── k8s/
│   ├── base/
│   └── overlays/
├── docker-compose.yml
├── .github/workflows/ci.yml
├── .env.example
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ROADMAP.md
│   └── DECISIONS_LOG.md
├── README.md
├── AGENTS.md
└── CLAUDE.md
```

Root-level `README.md`, `AGENTS.md`, and `CLAUDE.md` are kept at the root because developer tools and AI coding agents commonly look there first. Deeper project context lives under `docs/`.

## Definition of Done

A coding task is done when:

- [ ] The relevant service runs locally without errors through Docker or Docker Compose once those files exist for the current phase.
- [ ] At least one happy-path test covers the new behavior.
- [ ] `docs/DECISIONS_LOG.md` is updated when the task involved a meaningful decision, workaround, or completed milestone.
- [ ] The relevant checklist in `docs/ROADMAP.md` is updated.
- [ ] `README.md` reflects any change in how to run or use the project.

A documentation-only task is done when:

- [ ] Internal links point to existing files.
- [ ] Markdown is readable as UTF-8.
- [ ] Any repository rules mentioned in the docs are backed by actual files when practical.
- [ ] `docs/DECISIONS_LOG.md` records the documentation/context change if it affects future agents.

## Before Starting Any Task

1. Read `docs/ROADMAP.md` to confirm the current phase and next step.
2. Read the latest 2-3 entries in `docs/DECISIONS_LOG.md`.
3. Read `docs/ARCHITECTURE.md` before changing design, data flow, deployment, or service boundaries.
4. Ask only if the scope is still unclear after reading the repository context.
