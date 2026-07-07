# DECISIONS_LOG.md

Bitácora histórica del proyecto: qué se hizo, qué se decidió y por qué. Sirve tanto para el autor como para cualquier agente de IA que retome el trabajo en una sesión nueva (los agentes no tienen memoria entre sesiones — este archivo es esa memoria).

## Cómo usar este archivo

- **Añade una entrada nueva arriba de todo** (orden cronológico inverso: lo más reciente primero), para que al abrir el archivo lo primero que se vea sea el estado más actual.
- Usa la plantilla de abajo. No borres ni reescribas entradas viejas — si algo cambió, añade una entrada nueva que lo explique.
- Añade una entrada cuando: termines una fase o tarea significativa, tomes una decisión de arquitectura, encuentres un problema que requirió un workaround, o cambies algo ya decidido previamente.

### Plantilla

```
## [Fecha] — [Título corto]

**Fase:** (ej. Fase 1 — Backend básico)
**Qué se hizo:** ...
**Decisiones tomadas y por qué:** ...
**Alternativas consideradas (si aplica):** ...
**Pendientes / TODO que queda abierto:** ...
```

---

## 2026-07-07 — Planeación inicial del proyecto

**Fase:** Fase 0 — Planeación

**Qué se hizo:** Definición completa del alcance del proyecto a través de una sesión de brainstorming guiada. Se evaluaron 3 ideas de proyecto (job queue distribuido, microservicios de e-commerce, plataforma de monitoreo) y se eligió la plataforma de monitoreo por ser la más útil en el día a día del autor.

**Decisiones tomadas y por qué:**
- Stack backend: Python + FastAPI, por el ecosistema de IA y la curva de aprendizaje razonable para un principiante.
- Se incorporó un componente de IA local (Ollama) para generar resúmenes de incidentes en lenguaje natural, aprovechando que el autor cuenta con GPU dedicada NVIDIA.
- Visualización con Grafana en vez de un dashboard propio, para enfocar el esfuerzo en backend/DevOps y no en frontend.
- Despliegue local con Kubernetes (Minikube/Kind), sin costo, como entorno de aprendizaje antes de considerar cloud real.
- Se definieron 5 fases de desarrollo (backend básico → observabilidad → IA local → Kubernetes → CI), pensadas para que el aprendizaje sea incremental.

**Alternativas consideradas:**
- Node.js y Go como alternativas de backend — se descartaron a favor de Python por el enfoque en IA.
- Cloud real desde el inicio — se descartó por costo, dejándolo como fase futura opcional.

**Pendientes / TODO que queda abierto:**
- Elegir modelo específico de Ollama a usar en la Fase 3 (candidato inicial: `llama3.1:8b`).
- Definir el umbral exacto de fallos consecutivos para disparar un incidente (propuesta inicial: 3).
- Iniciar Fase 1: backend básico.
