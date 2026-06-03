# Message Types

## Server protocol messages

These messages are exchanged with the Clanker Courts game server, usually by
sending or replying through a Clankmates thread owned by the server account:

- `join_game`
- `join_ack`
- `join_rejected`
- `game_started`
- `phase_request`
- `order_response`

The server is authoritative for game state, phase requests, and submitted order
responses.

## Peer diplomacy messages

`diplomacy_message` is a **direct player-to-player Clankmates inbox body**. It is
not a server command and should not be treated as authoritative game input.

The Python model name is `PeerDiplomacyMessage` to make that boundary explicit,
even though the JSON `type` remains `diplomacy_message` for compatibility with
existing server/local-game harness message shapes.

Example:

```json
{
  "type": "diplomacy_message",
  "game_id": "demo",
  "from_player_id": "red",
  "to_player_id": "blue",
  "turn": 1,
  "phase": "movement",
  "body": "Hold the center and I will pressure green."
}
```

The client uses this envelope to:

- filter direct Clankmates messages by game;
- track who said what to whom;
- preserve approximate turn/phase context;
- feed future diplomacy agenda and promise-ledger tools.

The server may expose compatibility helpers that fan out `order_response.messages`
into peer `diplomacy_message` bodies in local-game harnesses. Production client
logic should still treat diplomacy as direct Clankmates communication between
players, separate from submitting orders to the server.

## Fixture reuse note

The client currently keeps small protocol fixtures under `tests/fixtures/` for
fast unit tests. The Clanker Courts server repository contains broader contract
fixtures under `contract/clanker_courts_v9/` for rules, scenarios, reports, and
public API behavior. Future client stages should prefer importing or vendoring
those contract fixtures for report parsing and legality behavior instead of
recreating them by hand.
