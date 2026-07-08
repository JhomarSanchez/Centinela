# ROADMAP.md

Phased development plan. **Do not move to the next phase until the current phase is complete** according to the Definition of Done in `AGENTS.md`.

## Current Status

- **Current phase:** Phase 4 - Kubernetes.
- **Completed:** Phase 0 - Planning. Phase 1 - Basic backend. Phase 2 - Classic observability. Phase 3 - Local AI incident summaries.
- **Next step:** Write Kubernetes manifests for the full stack and test them in Minikube or Kind.
- **Important constraint:** Do not implement CI before Phase 4 is working.

## Phase 0 - Planning Complete

- [x] Define the problem, scope, and stack.
- [x] Document the architecture and initial decisions.
- [x] Create AI context files for future agents.
- [x] Align AI context files in English and add repository hygiene files.

## Phase 1 - Basic Backend

**Goal:** A working API that registers services, performs real health checks, and persists results.

- [x] Initialize FastAPI project and folder structure.
- [x] Add `Service` and `Check` models with Alembic migrations.
- [x] Add CRUD endpoints for `Service`.
- [x] Add an APScheduler job inside the backend process for periodic service checks.
- [x] Store every `Check` in the database.
- [x] Add an endpoint to query a service's check history.
- [x] Add backend `Dockerfile` and `docker-compose.yml` for API + PostgreSQL.
- [x] Add basic tests for CRUD and health-check logic.

**Deliverable:** You can register a URL and, after a few minutes, see its availability history stored in the database.

## Phase 2 - Classic Observability

**Goal:** See system state in dashboards, not only in the database.

- [x] Expose Prometheus metrics from the backend at `/metrics`.
- [x] Add Prometheus to `docker-compose.yml`, configured to scrape the backend.
- [x] Add Grafana connected to Prometheus.
- [x] Add a basic dashboard: current status per service, historical latency, and availability percentage.

**Deliverable:** A Grafana dashboard shows the real state of monitored services.

## Phase 3 - Local AI Incident Summaries

**Goal:** When something fails, generate a natural-language explanation.

- [x] Add Ollama as a service in `docker-compose.yml`, with a documented local model such as `llama3.1:8b`.
- [x] Add incident-detection logic: N consecutive failures create an `Incident`.
- [x] Build the context prompt from recent checks, service name, timestamps, and status data.
- [x] Add an HTTP client for Ollama's internal API.
- [x] Store the generated summary on the `Incident` and expose it through the API.
- [x] Add an endpoint to list active and historical incidents with their AI summaries.

**Deliverable:** When a service outage is simulated, Centinela creates and stores a readable incident summary.

## Phase 4 - Kubernetes

**Goal:** Run the full stack in a local Kubernetes cluster, not only in Docker Compose.

- [ ] Add Deployment and Service manifests for backend, PostgreSQL, Ollama, Prometheus, and Grafana.
- [ ] Add ConfigMaps and Secrets for configuration and credentials.
- [ ] Test the full stack in Minikube or Kind.
- [ ] Document in `README` how to start everything with `kubectl apply`.

**Deliverable:** The full project runs in a local Kubernetes cluster with one documented command flow.

## Phase 5 - CI

**Goal:** Run automated validation before changes are integrated.

- [ ] Add a GitHub Actions pipeline for linting and tests on every push or pull request.
- [ ] Build the backend Docker image as part of the pipeline.
- [ ] Optional: publish the image to Docker Hub or GitHub Container Registry.

**Deliverable:** A passing CI badge appears in `README`, and the pipeline is visible in GitHub Actions.

## Future Optional Phases

- Email or Slack alerts when an incident opens.
- Migration to a real cloud deployment on a free or low-cost tier.
- Multi-user authentication.
- GitOps with Argo CD for continuous deployment to the cluster.
