# Centinela — Plataforma de Monitoreo Inteligente

> Vigila la salud de tus servicios y APIs, y cuando algo falla, una IA local te explica qué pasó.

## ¿Qué es esto?

Centinela es una plataforma de monitoreo personal: registra los servicios que te importan (una API, un sitio web, un endpoint interno), los revisa periódicamente, guarda el historial de disponibilidad y latencia, y lo visualiza en Grafana.

Cuando un servicio empieza a fallar, en vez de solo mostrar "DOWN", Centinela usa un modelo de lenguaje corriendo **localmente** (sin depender de APIs externas de pago) para generar un resumen del incidente en lenguaje natural, a partir de los checks y el historial reciente.

Este proyecto nació como pieza de portafolio, pero está pensado para usarse de verdad en el día a día.

## Estado actual

📍 **Fase 0 — Planeación completada.** Aún no hay código. Ver [`docs/ROADMAP.md`](./docs/ROADMAP.md) para el plan de fases.

## Stack técnico

| Capa | Tecnología |
|---|---|
| Backend / API | Python + FastAPI |
| Base de datos | PostgreSQL |
| Scheduler de health checks | APScheduler |
| IA de resúmenes | Ollama (modelo local, ej. Llama 3.1 8B) con GPU |
| Métricas | Prometheus |
| Dashboards | Grafana |
| Contenedores | Docker / Docker Compose |
| Orquestación | Kubernetes (Minikube / Kind, local) |
| CI | GitHub Actions |

## Documentación del proyecto

Estos archivos son la fuente de verdad del proyecto — tanto para ti como para cualquier IA (Codex, Claude Code, etc.) que trabaje en el repo:

- [`AGENTS.md`](./AGENTS.md) — instrucciones para agentes de IA que trabajen en este repo.
- [`CLAUDE.md`](./CLAUDE.md) — notas específicas para Claude Code.
- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — diseño del sistema, modelo de datos y decisiones técnicas.
- [`docs/ROADMAP.md`](./docs/ROADMAP.md) — plan de desarrollo por fases, con checklist.
- [`docs/DECISIONS_LOG.md`](./docs/DECISIONS_LOG.md) — bitácora histórica de decisiones y avances.

## Quick start

_(Se completará al terminar la Fase 1 — por ahora, ver `ROADMAP.md`)_

## Autor

Proyecto personal de portafolio, desarrollado con asistencia de IA como parte de un proceso de aprendizaje en DevOps y backend.
