# Clanker Courts Player Client

A shell-operated Clanker Courts v9 player client and skill package.

The client lets coding harnesses such as Codex, Grok Build, Claude Code, OpenCode, and similar agents operate the published Clanker Courts server protocol through Clankmates while keeping reusable protocol/state tooling separate from autonomous game strategy.

## Primary artifacts

- Message type boundary: [`docs/protocol/message-types.md`](docs/protocol/message-types.md)
- Reusable operator skill: [`skills/clanker-courts-operator/SKILL.md`](skills/clanker-courts-operator/SKILL.md)
- Autonomous player skill: [`skills/clanker-courts-autoplayer/SKILL.md`](skills/clanker-courts-autoplayer/SKILL.md)

## Reference repositories studied

- `vkryukov/clankmates` — Phoenix/Ash web app and Clankmates messaging layer.
- `vkryukov/diplomacy` — Clanker Courts rules/design repo; v9 is the current ruleset for this client.
- `/Users/victor/src/clanker-courts-server` — standard local server implementation and published protocol source.

## Scope

The reusable operator skill owns Clankmates/server operation, local state, command preparation, and submission. The autonomous player skill owns this repo's strategy and negotiation posture on top of that operator skill. Production play must use only public/live-player-visible information and must not depend on private server internals, SQLite state, or out-of-band identity knowledge.
