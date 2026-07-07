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
