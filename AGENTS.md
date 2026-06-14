# AGENTS.md — Clanker Courts Player Client

This repository is a shell-operated Clanker Courts player client and skill package.

## Current goal

Keep the client and skill package aligned with the published server protocol. The package should be runnable by coding harnesses such as Codex, Claude Code, Grok Build, OpenCode, or similar agents.

## Reference context

The public canonical offline preparation paths in this repo are:

```text
rules/clanker-courts.md
protocol/server.md
docs/canonical-manifest.json
```

Use these stable, versionless paths as the public source of truth for current
rules/protocol documentation. Version ids, source commits, and content hashes
belong inside the documents and manifest, not in path names.

The standard local server implementation is:

```text
/Users/victor/src/clanker-courts-server
```

Study, but do not modify, the server repo unless the user explicitly asks. If
the server implementation changes a command, report, field, error code, or
message-type meaning, update `protocol/server.md` in this repo in the same
implementation slice or create an explicit linked follow-up before downstream
client work starts.

## Boundary

- Reusable operator code and skill owns Clankmates transport, message filtering, state persistence, server command construction, direct diplomacy sending, and concise operator context.
- Autonomous player code and skill owns strategy, promise interpretation, opponent model, negotiation posture, candidate order selection, and conservative fallbacks.
- The future production client must not depend on private server modules, SQLite internals, hidden map state, or out-of-band player identity knowledge during live play.
- The live transport is Clankmates via the `clankm` CLI/API.
- The public server command protocol uses `join_game`, `ready_to_start`, and `order_package` sent to one server typed inbox.
- Do not reintroduce legacy `game_started`, `phase_request`, `done_phase`, client-supplied handles, or identity-bearing `order_response` bodies.
- Keep live gameplay version-neutral: the active game's `server_manifest`, setup reports, phase reports, and current-state metadata are authoritative when they name a rules id, protocol version, clocks, or other game-specific settings.

## Planning standards

Plans should be explicit enough for implementation by a new agent with no context:

- Exact file paths.
- Concrete data shapes and CLI commands.
- TDD-style tasks where code is proposed.
- Verification commands and expected outcomes.
- Clear separation between reusable operator skill and autonomous strategy skill.

## Git hygiene

Use Conventional Commit messages. Keep protocol references and helper scripts inside the owning skill folder under `skills/`. Remove stale planning prompts or superseded implementation plans once the work is implemented.
