# AGENTS.md — Instrucciones para agentes de IA

Este archivo es la fuente principal de instrucciones para cualquier agente de IA (Codex, Claude Code, Cursor, etc.) que trabaje en este repositorio. Léelo completo antes de escribir código.

## Contexto importante
- Prioriza claridad sobre "cleverness". Código simple, bien comentado, sobre soluciones ingeniosas difíciles de entender.
- Explica brevemente el *por qué* de decisiones no triviales (en comentarios de código o en el mensaje de commit), no solo el qué.
- No asumas conocimiento avanzado previo. Si usas un patrón o herramienta poco común, añade una línea explicando para qué sirve.
- Avanza **por fases**, según `ROADMAP.md`. No implementes la Fase 3 si la Fase 1 no está terminada y funcionando.

## Misión del proyecto

Ver `README.md` y `ARCHITECTURE.md` para el contexto completo. En resumen: una plataforma de monitoreo de servicios que usa un LLM local (Ollama) para generar resúmenes de incidentes en lenguaje natural.

## Reglas no negociables

1. **No saltarse fases.** Sigue el orden de `docs/ROADMAP.md`. Si crees que hay una mejor secuencia, propónlo — no lo cambies unilateralmente.
2. **Actualiza `docs/DECISIONS_LOG.md`** cada vez que: termines una tarea/fase, tomes una decisión de arquitectura, encuentres un problema que requirió un workaround, o cambies algo ya decidido. Usa la plantilla que está en ese archivo.
3. **Nunca commitees secretos.** Credenciales, API keys y tokens van en `.env` (ignorado por git). Usa `.env.example` como plantilla pública.
4. **Todo servicio corre en contenedor.** Nada de "instala esto localmente sin Docker", salvo herramientas de desarrollo (linters, etc.).
5. **Tests antes de dar por terminada una tarea.** Aunque sean tests básicos — un proyecto de portafolio sin tests resta puntos.
6. **Commits pequeños y descriptivos**, formato: `fase-N: descripción corta del cambio`.

## Stack y convenciones de código

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy (ORM), Pydantic para validación, Alembic para migraciones.
- **Estilo:** PEP8, type hints en funciones públicas, docstrings breves en módulos y funciones no triviales.
- **Estructura de carpetas propuesta:**

```
centinela/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/          # routers/endpoints
│   │   ├── models/       # modelos SQLAlchemy + esquemas Pydantic
│   │   ├── services/     # lógica de negocio (health checks, IA, etc.)
│   │   ├── scheduler/    # jobs periódicos
│   │   └── ai/           # cliente de Ollama, construcción de prompts
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

> Nota de convención: `README.md`, `AGENTS.md` y `CLAUDE.md` viven en la raíz porque las herramientas de IA y Git los buscan ahí por defecto. Todo lo demás (arquitectura, roadmap, bitácora) vive en `docs/` para no saturar la raíz del repo.

- **IA local:** Ollama expuesto como servicio separado (contenedor propio); el backend le habla vía HTTP a su API interna. No incrustar el modelo dentro del proceso de la API.

## Definición de "hecho" (Definition of Done) por tarea

Una tarea se considera terminada cuando:

- [ ] El código corre localmente sin errores (`docker-compose up`).
- [ ] Hay al menos un test que cubre el caso feliz.
- [ ] Se actualizó `docs/DECISIONS_LOG.md` si hubo una decisión relevante.
- [ ] Se actualizó el checklist correspondiente en `docs/ROADMAP.md`.
- [ ] El README refleja cualquier cambio en cómo correr el proyecto.

## Antes de empezar cualquier tarea

1. Lee `docs/ROADMAP.md` para saber en qué fase estamos y qué sigue.
2. Lee las últimas 2-3 entradas de `docs/DECISIONS_LOG.md` para tener contexto reciente.
3. Si algo del alcance no está claro, pregunta antes de asumir.
