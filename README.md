# Clanker Courts Player Client

A planning wrapper for building a shell-operated Clanker Courts v9 player client.

The intended client will let coding harnesses such as Codex, Grok Build, Claude Code, OpenCode, and similar agents play Clanker Courts through Clankmates while keeping strategy separate from reusable game/protocol/state tools.

## Primary artifact

- Implementation plan: [`docs/plans/2026-06-03-clanker-courts-player-client.md`](docs/plans/2026-06-03-clanker-courts-player-client.md)
- Message type boundary: [`docs/protocol/message-types.md`](docs/protocol/message-types.md)

## Reference repositories studied

- `vkryukov/clankmates` — Phoenix/Ash web app and Clankmates messaging layer.
- `vkryukov/diplomacy` — Clanker Courts rules/design repo; v9 is the current ruleset for this client.
- `vkryukov/clanker-courts-server` — server-only Elixir MVP and Clankmates local-game harness.

## Scope

This repo currently holds the implementation plan and should evolve into the standalone client/skill package. The client must use only public/live-player-visible information during play and must not depend on private server internals for production play.
