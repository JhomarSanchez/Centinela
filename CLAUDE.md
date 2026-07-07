# CLAUDE.md

Este proyecto usa [`AGENTS.md`](./AGENTS.md) como fuente principal de instrucciones. Léelo primero — contiene el contexto del proyecto, las reglas no negociables, la estructura de carpetas y la definición de "hecho".

Este archivo solo añade notas específicas para Claude Code.

## Al iniciar una sesión

1. Lee, en este orden: `AGENTS.md` → `docs/ROADMAP.md` → `docs/DECISIONS_LOG.md` (últimas entradas) → `docs/ARCHITECTURE.md` si vas a tocar diseño.
2. Confirma en qué fase del roadmap estamos antes de escribir código.

## Preferencias de ejecución

- Usa el sandbox de Bash para levantar y probar el proyecto con `docker-compose` antes de dar una tarea por terminada.
- Corre linter y tests localmente antes de reportar que algo está listo.
- Al terminar una tarea o tomar una decisión de arquitectura, añade la entrada correspondiente en `docs/DECISIONS_LOG.md` usando su plantilla — no lo dejes para "después".
- Si vas a hacer un cambio que se desvía del plan en `docs/ROADMAP.md`, dilo explícitamente antes de proceder, no lo hagas silenciosamente.

## Recuerda

El usuario está aprendiendo. Explica brevemente las decisiones no obvias mientras trabajas, no solo el resultado final.
