# ROADMAP.md

Plan de desarrollo por fases. **No avanzar a la siguiente fase sin cerrar la actual** (ver Definition of Done en `AGENTS.md`).

## Fase 0 — Planeación ✅

- [x] Definir problema, alcance y stack.
- [x] Documentar arquitectura y decisiones iniciales.
- [x] Crear archivos de contexto para agentes de IA.

## Fase 1 — Backend básico

**Objetivo:** API funcional que registra servicios y hace health checks reales, con persistencia.

- [ ] Inicializar proyecto FastAPI + estructura de carpetas.
- [ ] Modelos `Service` y `Check` + migraciones con Alembic.
- [ ] Endpoints CRUD de `Service`.
- [ ] Scheduler (APScheduler) que hace ping periódico a cada servicio registrado.
- [ ] Guardar cada `Check` en la base de datos.
- [ ] Endpoint para consultar histórico de un servicio.
- [ ] Dockerfile del backend + `docker-compose.yml` (API + Postgres).
- [ ] Tests básicos (CRUD + lógica de check).

**Entregable:** puedes registrar una URL, y en unos minutos ver en la base de datos su historial de disponibilidad.

## Fase 2 — Observabilidad clásica

**Objetivo:** ver el estado del sistema en dashboards, no solo en la base de datos.

- [ ] Exponer métricas en formato Prometheus (`/metrics`) desde el backend.
- [ ] Añadir Prometheus a `docker-compose.yml`, configurado para scrapear el backend.
- [ ] Añadir Grafana, conectado a Prometheus.
- [ ] Dashboard básico: estado actual de cada servicio, latencia histórica, % de disponibilidad.

**Entregable:** un dashboard de Grafana mostrando el estado real de tus servicios monitoreados.

## Fase 3 — IA local para resumen de incidentes

**Objetivo:** cuando algo falla, obtener una explicación en lenguaje natural.

- [ ] Añadir servicio de Ollama a `docker-compose.yml`, con modelo descargado (ej. `llama3.1:8b`).
- [ ] Lógica de detección de incidente (N fallos seguidos → crear `Incident`).
- [ ] Construcción del prompt de contexto (últimos checks, nombre del servicio, etc.).
- [ ] Cliente HTTP hacia la API de Ollama para pedir el resumen.
- [ ] Guardar el resumen en el `Incident` y exponerlo vía API.
- [ ] Endpoint para listar incidentes (activos e históricos) con su resumen de IA.

**Entregable:** al simular una caída de un servicio, Centinela genera y guarda un resumen legible del incidente.

## Fase 4 — Kubernetes

**Objetivo:** correr todo el stack en un clúster local, no solo en Docker Compose.

- [ ] Manifiestos de Deployment/Service para: backend, Postgres, Ollama, Prometheus, Grafana.
- [ ] ConfigMaps/Secrets para configuración y credenciales.
- [ ] Probar el stack completo en Minikube o Kind.
- [ ] Documentar en el README cómo levantar todo con `kubectl apply`.

**Entregable:** el proyecto corre completo en un clúster de Kubernetes local, con un solo set de comandos documentado.

## Fase 5 — CI

**Objetivo:** validación automática antes de integrar cambios.

- [ ] Pipeline de GitHub Actions: lint + tests en cada push/PR.
- [ ] Build de la imagen Docker del backend como parte del pipeline.
- [ ] (Opcional) publicar la imagen en un registry (Docker Hub o GitHub Container Registry).

**Entregable:** badge de CI pasando en el README, pipeline visible en GitHub Actions.

## Fases futuras (opcionales, fuera del alcance inicial)

- Alertas por email/Slack cuando se abre un incidente.
- Migración de despliegue a un cloud real (AWS/GCP capa gratuita).
- Autenticación multi-usuario.
- GitOps (ArgoCD) para despliegue continuo real al clúster.
