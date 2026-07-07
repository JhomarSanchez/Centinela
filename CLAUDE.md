# CLAUDE.md

This project uses [`AGENTS.md`](./AGENTS.md) as the primary instruction file. Read it first; it contains the project context, non-negotiable rules, repository structure, and definition of done.

This file only adds Claude Code-specific reminders.

## Session Startup

1. Read, in this order: `AGENTS.md`, `docs/ROADMAP.md`, the latest entries in `docs/DECISIONS_LOG.md`, and `docs/ARCHITECTURE.md` if you will touch design.
2. Confirm the current roadmap phase before writing code.

## Execution Preferences

- Use the shell environment available in the coding session to run Docker Compose, linters, and tests before marking a coding task complete.
- When a task ends or an architecture decision is made, add the matching entry to `docs/DECISIONS_LOG.md` immediately.
- If a change would deviate from `docs/ROADMAP.md`, state that explicitly before proceeding.

## Remember

The user is learning. Explain non-obvious choices briefly while you work, not only in the final result.
