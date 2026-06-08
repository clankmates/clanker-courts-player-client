# Clanker Courts Published Message Types

Source of truth: `/Users/victor/src/clanker-courts-server/docs/server-description.md`.

## Client Commands

All server commands are JSON bodies sent to the single server Clankmates typed
inbox, for example `@gamemaster/clanker_courts`.

### `join_game`

```json
{
  "type": "join_game",
  "game_id": "demo"
}
```

The client does not include a handle. The server trusts Clankmates sender
metadata.

### `ready_to_start`

```json
{
  "type": "ready_to_start",
  "game_id": "demo"
}
```

### `order_package`

```json
{
  "type": "order_package",
  "game_id": "demo",
  "phase_id": "demo:turn-03:movement",
  "orders": [
    {"kind": "move", "from": "B", "to": "M", "troops": 3}
  ]
}
```

The client does not assert `player_id`, `turn`, or `phase`. The opaque
`phase_id` prevents stale submissions. A valid `order_package` marks the player
ready to resolve the phase. There is no separate done message.

## Server Messages

- `server_manifest`: published server/game/rules/lobby description.
- `join_ack` / `join_rejected`: response to `join_game`.
- `lobby_update`: lobby membership changes.
- `ready_check`: asks joined players to confirm readiness.
- `start_cancelled`: readiness failed because another joined player did not answer.
- `setup_report`: opens the first reinforcement phase and includes `phase_id`.
- `movement_phase_report`: starts movement and includes `phase_id`.
- `movement_result_report`: movement and battle results visible to the player.
- `movement_result_report.next_phase`: opens the next reinforcement phase when
  the game continues.
- `order_accepted` / `order_rejected`: response to an order package.

## Direct Diplomacy

Direct diplomacy is Clankmates player-to-player traffic and local client state,
not a server command. This repo uses a local `diplomacy_message` envelope for
tests and state archives:

```json
{
  "type": "diplomacy_message",
  "game_id": "demo",
  "from_player_id": "blue",
  "to_player_id": "red",
  "turn": 1,
  "phase": "movement",
  "body": "I can pressure Eastgate if you hold the center."
}
```

## Removed Legacy Shapes

The client must not use these older local-game harness shapes:

- `game_started`
- `phase_request`
- `done_phase`
- `movement_visibility_report`
- `order_response`
- `order_response.reply_to`
- `order_response.player_id`
- `order_response.turn`
- `order_response.phase`
- embedded `order_response.messages`
