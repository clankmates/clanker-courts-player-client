# AGENTS.md — Clanker Courts Player Client

This repository is a shell-operated Clanker Courts v9 player client and skill package.

## Current goal

Keep the client and skill package aligned with the published server protocol. The package should be runnable by coding harnesses such as Codex, Claude Code, Grok Build, OpenCode, or similar agents.

## Reference context

The standard local server implementation is:

```text
/Users/victor/src/clanker-courts-server
```

Study, but do not modify, the server repo unless the user explicitly asks. The current public client/server contract is in that repo's `docs/server-description.md`.

## Boundary

- Reusable operator code and skill owns Clankmates transport, message filtering, state persistence, server command construction, direct diplomacy sending, and concise operator context.
- Autonomous player code and skill owns strategy, promise interpretation, opponent model, negotiation posture, candidate order selection, and conservative fallbacks.
- The future production client must not depend on private server modules, SQLite internals, hidden map state, or out-of-band player identity knowledge during live play.
- The live transport is Clankmates via the `clankm` CLI/API.
- The public server command protocol uses `join_game`, `ready_to_start`, `order_response`, and `done_phase` sent to one server typed inbox.
- Do not reintroduce legacy `game_started`, `phase_request`, client-supplied handles, or identity-bearing `order_response` bodies.

## Planning standards

Plans should be explicit enough for implementation by a new agent with no context:

- Exact file paths.
- Concrete data shapes and CLI commands.
- TDD-style tasks where code is proposed.
- Verification commands and expected outcomes.
- Clear separation between reusable operator skill and autonomous strategy skill.

## Git hygiene

Use Conventional Commit messages. Keep durable plans in `docs/`, protocol examples in `docs/protocol/`, and skill artifacts in `skills/`.
