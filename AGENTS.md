# AGENTS.md — Clanker Courts Player Client

This repository is a planning wrapper for a future Clanker Courts v9 autonomous player client.

## Current goal

Create a durable implementation plan for a shell-operated client/skill package that can be run by coding harnesses such as Codex, Claude Code, Grok Build, OpenCode, or similar agents.

## Reference context

Local reference clones may be available outside this repo under:

```text
/home/hermes/clanker-client-planning-work/refs/
├── clankmates/
├── diplomacy/
└── clanker-courts-server/
```

Study, but do not modify, those reference repositories.

## Boundary

- Client/player code owns strategy, local state, promise ledger, opponent model, and diplomacy posture.
- Reusable helper code owns transport, message filtering, state persistence, visible-map summaries, legal-action scaffolding, order-response validation, and conservative fallbacks.
- The future production client must not depend on private server modules, SQLite internals, hidden map state, or out-of-band player identity knowledge during live play.
- The live transport is Clankmates via the `clankm` CLI/API.

## Planning standards

Plans should be explicit enough for implementation by a new agent with no context:

- Exact file paths.
- Concrete data shapes and CLI commands.
- TDD-style tasks where code is proposed.
- Verification commands and expected outcomes.
- Clear separation between strategy prompts/skills and callable helper tools.

## Git hygiene

Use Conventional Commit messages. Keep reference-reading notes and implementation artifacts in `docs/` until real client code is added.
