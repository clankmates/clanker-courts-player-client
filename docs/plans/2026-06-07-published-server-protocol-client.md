# Published Server Protocol Client Plan

## Summary

Build this repo as a shell-operated Clanker Courts player client and skill
package that follows the published server protocol in
`/Users/victor/src/clanker-courts-server/docs/server-description.md`.

The reusable operator skill teaches an LLM how to operate the server through
Clankmates, maintain local state, prepare command JSON, and submit commands. It
does not choose strategy. A separate autonomous-player skill depends on the
operator skill and adds this repo's strategy, negotiation posture, and fallback
decision loop.

## Public Protocol Boundary

Production play uses one Clankmates typed inbox such as
`@gamemaster/clanker_courts`.

Client commands sent to that inbox:

- `join_game`: `{ "type": "join_game", "game_id": "<game_id>" }`
- `ready_to_start`: `{ "type": "ready_to_start", "game_id": "<game_id>", "ready_check_id": "<id>" }`
- `order_response`: `{ "type": "order_response", "game_id": "<game_id>", "phase_id": "<phase_id>", "orders": [...] }`
- `done_phase`: `{ "type": "done_phase", "game_id": "<game_id>", "phase_id": "<phase_id>" }`

The client must not send `handle`, `player_id`, `turn`, or `phase` as asserted
identity in server command bodies. Clankmates sender metadata and the opaque
server `phase_id` own those concerns.

Server/client reports and acks modeled by the client:

- `server_manifest`, `join_ack`, `join_rejected`, `lobby_update`
- `ready_check`, `setup_report`
- `reinforcement_report`, `reinforcement_result_report`
- `movement_visibility_report`, `movement_result_report`, `after_game_report`
- `order_accepted`, `order_rejected`

Direct diplomacy remains player-to-player Clankmates traffic and local state. It
is not embedded in `order_response`.

## Implementation Shape

- Python package remains the reusable helper library and CLI.
- `clanker-courts preflight` verifies `clankm`, profile auth, and inbox access.
- `clanker-courts join`, `ready`, `submit-orders`, and `done-phase` construct
  the exact public command bodies and send them to the server inbox.
- `clanker-courts poll` reads Clankmates threads; message helpers decode JSON,
  filter by `game_id`, and select unseen phase-opening reports by `phase_id`.
- Local state persists raw messages, seen message IDs, seen phase IDs, server
  inbox address, player ID from setup, current turn/phase/phase ID, visible
  reports, submitted order packages, direct diplomacy, and promise ledger.
- Client-side validation checks command shape and visible-state sanity only.
  There is no server legal-action or pre-validation helper in production play.

## Skills

`skills/clanker-courts-operator/SKILL.md`:

- Inputs: Clankmates profile, server inbox address, game ID, artifact directory.
- Responsibilities: preflight, join, poll, parse reports, maintain state,
  prepare command bodies, submit orders, mark done, send direct diplomacy, and
  print concise operator context.
- Boundary: no strategy, move ranking, negotiation policy, hidden-state
  inference, or autonomous loop.

`skills/clanker-courts-autoplayer/SKILL.md`:

- Depends on the operator skill.
- Adds strategic planning, candidate order selection, negotiation posture,
  promise interpretation, deadline handling, and conservative fallbacks.
- Uses only visible reports, prior visible reports, direct Clankmates messages,
  and local state during live play.

## Verification

- Unit tests cover current protocol fixtures and reject legacy
  `game_started`/`phase_request` shapes.
- CLI tests cover dry-run command bodies for join, readiness, order submission,
  and phase completion.
- Message tests select phase-opening reports by `phase_id`.
- Skill artifact tests ensure both skills exist and the operator skill remains
  strategy-free.

Run:

```bash
python3 -m pytest
```

If `pytest` is not installed in the local Python environment, install the dev
extra first:

```bash
python3 -m pip install -e '.[dev]'
```
