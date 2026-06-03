# Clanker Courts Player Client Implementation Plan

Date: 2026-06-03

## 1. Goal, Architecture, And Tech Stack

### Goal

Build a standalone Clanker Courts v9 player-client and skill package that shell-capable coding harnesses can run through Clankmates. The package must let a harness join a game, poll server and diplomacy messages, preserve raw state, summarize the visible board, generate and validate legal orders, submit phase responses, track promises and diplomacy posture, and continue until the game ends.

The core design boundary is:

- Harness/LLM owns strategy, judgment, negotiation content, deception/credibility policy, opponent modeling, and final plan selection.
- Code/tools own protocol handling, Clankmates CLI transport, message filtering, state persistence, visible-map summaries, legal action scaffolding, order-response validation/building, conservative fallbacks, raw archives, and bookkeeping.

The production client must use only live-player-visible reports and Clankmates messages. It must not depend on private server modules, SQLite internals, hidden map state, or out-of-band player identity knowledge.

### Architecture

Use a Python package plus JSON-on-stdin/stdout CLIs. Every helper command accepts `--input -` or a named file and emits JSON to stdout so Codex, Claude Code, Grok Build, OpenCode, and similar harnesses can compose them.

High-level flow:

1. `clanker-courts preflight` verifies `clankm`, profile, auth, base URL, and inbox readability.
2. `clanker-courts join` sends `join_game` to the configured server account/handle and records the server thread.
3. `clanker-courts poll` reads bounded inbox pages, archives raw messages, decodes JSON bodies, and filters by `game_id`.
4. `clanker-courts summarize` turns latest visible reports into compact tactical context.
5. `clanker-courts legal-actions` and `clanker-courts validate-response` provide deterministic legality scaffolding from the latest visible report.
6. The harness chooses a strategy and messages from candidate plans and diplomacy context.
7. `clanker-courts build-response` creates canonical `order_response` JSON.
8. `clanker-courts submit` replies to the phase-request thread and optionally sends peer diplomacy messages through Clankmates.
9. `clanker-courts play-loop` wires the above with a prompt-driven decision hook and conservative fallbacks.

### Tech Stack

- Language: Python 3.11+.
- Packaging: `pyproject.toml` with Hatchling or Setuptools.
- CLI: `argparse` first; add Typer only if typed subcommands become unwieldy.
- Validation: `pydantic` v2 for internal models, or `jsonschema` if public schemas become the dominant artifact. Start with Pydantic because it gives Python callers typed objects.
- Storage: plain JSON files plus JSONL raw archives. Use atomic write via temp file and `os.replace`.
- Tests: `pytest`, `pytest-cov`, optional `hypothesis` for legality invariants.
- Formatting/linting: `ruff format`, `ruff check`, `mypy` after models stabilize.
- Transport: official `clankm` CLI via `subprocess.run`; never direct HTTP for production unless a future Clankmates API integration is explicitly requested.

## 2. Reference Study Summary

### Clankmates

Files and pages studied:

- `/home/hermes/clanker-client-planning-work/refs/clankmates/README.md`
- `/home/hermes/clanker-client-planning-work/refs/clankmates/AGENTS.md`
- `https://clankmates.com/for-clankers.md`
- `https://clankmates.com/for-clankers/skill.md`

Plan-relevant findings:

- Clankmates is a Phoenix/Ash app; production is `https://clankmates.com`.
- Agents should operate through the official `clankm` CLI for setup, publishing, inbox reads, first messages, and replies.
- Local testing should use `http://localhost:4000` consistently. Do not mix `localhost` and `127.0.0.1` because auth cookies and local setup are host-bound.
- CLI collection reads are bounded and paginated. The client must keep cursors or last-seen message IDs and archive raw pages.
- Useful commands:
  - `clankm config init --profile <profile> --base-url <url>`
  - `clankm auth whoami --json`
  - `clankm inbox list --status all --json`
  - `clankm inbox show <thread_id> --limit <n> --json`
  - `clankm inbox send @handle --body '<json>' --json`
  - `clankm inbox reply <thread_id> --body '<json>' --json`

### Diplomacy / Clanker Courts Rules

Files studied:

- `/home/hermes/clanker-client-planning-work/refs/diplomacy/README.md`
- `/home/hermes/clanker-client-planning-work/refs/diplomacy/AGENTS.md`
- `/home/hermes/clanker-client-planning-work/refs/diplomacy/rules/clanker-courts-v9.md`

Plan-relevant findings:

- Clanker Courts v9 is a simultaneous-order diplomacy game for 3+ players on a connected graph of cities and towns.
- The objective is capital capture/elimination or highest score at final turn.
- Each turn has reinforcement then movement phases.
- Private two-sided diplomacy is allowed. Promises, threats, misleading statements, and lies have no rules effect unless reflected in submitted orders.
- Reinforcements are `controlled cities + floor(sqrt(controlled towns))`; they can be placed only in controlled cities, and unallocated/default troops go to the capital.
- Movement orders are `move` and `support`; origins must be controlled, destinations adjacent, and total committed troops per origin cannot exceed post-reinforcement troops.
- Support cannot support self, cannot target an own-controlled location, cannot coexist with a move to the same target, and cannot support different players at the same target within one package.
- Movement resolution includes troop commitment, road battles, destination battles, support returns, support return battles, capital loss, and scoring.
- Visibility is limited: full visibility for controlled and adjacent locations; controller-only visibility at distance two; fog beyond that. The client must act only from these visible reports in live play.

### Clanker Courts Server

Files studied:

- `/home/hermes/clanker-client-planning-work/refs/clanker-courts-server/README.md`
- `/home/hermes/clanker-client-planning-work/refs/clanker-courts-server/AGENTS.md`
- `/home/hermes/clanker-client-planning-work/refs/clanker-courts-server/docs/mvp-spec.md`
- `/home/hermes/clanker-client-planning-work/refs/clanker-courts-server/docs/player-helper-scripts.md`
- `/home/hermes/clanker-client-planning-work/refs/clanker-courts-server/prompts/clanker_client_skill_prep.md`
- `/home/hermes/clanker-client-planning-work/refs/clanker-courts-server/prompts/clanker_client_live_play.md`
- `/home/hermes/clanker-client-planning-work/refs/clanker-courts-server/lib/clanker_courts_server/api.ex`
- `/home/hermes/clanker-client-planning-work/refs/clanker-courts-server/lib/clanker_courts_server/protocol.ex`
- `/home/hermes/clanker-client-planning-work/refs/clanker-courts-server/lib/clanker_courts_server/clients/clankmates_cli.ex`
- `/home/hermes/clanker-client-planning-work/refs/clanker-courts-server/lib/clanker_courts_server/clients/local_game/messages.ex`
- `/home/hermes/clanker-client-planning-work/refs/clanker-courts-server/lib/clanker_courts_server/clients/local_game/threads.ex`
- `/home/hermes/clanker-client-planning-work/refs/clanker-courts-server/lib/clanker_courts_server/clients/llm_bot_fallback.ex`
- `/home/hermes/clanker-client-planning-work/refs/clanker-courts-server/lib/clanker_courts_server/clients/local_game.ex`
- `/home/hermes/clanker-client-planning-work/refs/clanker-courts-server/lib/clanker_courts_server/clients/clankmates_server.ex`
- `/home/hermes/clanker-client-planning-work/refs/clanker-courts-server/lib/clanker_courts_server/rules/visibility.ex`
- `/home/hermes/clanker-client-planning-work/refs/clanker-courts-server/test/local_game_messages_test.exs`

Plan-relevant findings:

- The server is a transport-agnostic Elixir MVP. Its public API is `ClankerCourtsServer.API.handle/1` and `handle_json/1`.
- Public player commands include `submit_order_package`, `done_phase`, `get_status`, `get_reports`, and `get_after_game_report`.
- Server protocol responses use `schema_version: 1`, `request_id`, `ok`, and either `result` or `error`.
- Clankmates live/local harness message shapes are concrete enough for a standalone client:

```json
{"type":"join_game","game_id":"<game_id>","handle":"<your Clankmates handle>"}
```

```json
{
  "type": "phase_request",
  "game_id": "<game_id>",
  "request_id": "<request-id>",
  "player_id": "<player_id>",
  "turn": 1,
  "phase": "reinforcement",
  "status": {},
  "reports": [],
  "deadline_ms": 60000
}
```

```json
{
  "type": "order_response",
  "game_id": "<game_id>",
  "reply_to": "<phase_request.request_id>",
  "player_id": "<player_id>",
  "turn": 1,
  "phase": "reinforcement",
  "orders": [],
  "done": true,
  "table_talk": [],
  "messages": [],
  "source": "<agent>"
}
```

```json
{"to_player_id":"red","body":"Green is leading. I can pressure Eastgate if you hold the center."}
```

- `join_ack` reports waiting state; `game_started` includes `player_id`, rules info, reports, communication rules, and status.
- The local-game harness fans `messages` entries out as peer `diplomacy_message` bodies with `type`, `game_id`, `from_player_id`, `to_player_id`, `turn`, `phase`, and `body`.
- Message filtering must decode `attributes.body` when it is JSON, preserve plain text, handle timestamp field variants, select only matching `game_id`, and keep recent diplomacy involving the player.
- Report payloads include `setup_report`, `reinforcement_report`, `reinforcement_result_report`, `movement_visibility_report`, and `movement_result_report`.
- Existing helper backlog maps directly to this client: report summary, legal orders, candidate plans, plan evaluator, visible map metrics, threat model, diplomacy agenda, promise ledger, response builder, what-if simulator, Clankmates preflight, message filter, state store, and submit reply.

## 3. Proposed Future Repo / Package Layout

```text
clanker-courts-player-client/
├── README.md
├── AGENTS.md
├── pyproject.toml
├── docs/
│   ├── plans/
│   │   └── 2026-06-03-clanker-courts-player-client.md
│   ├── protocol/
│   │   ├── clankmates-message-shapes.md
│   │   └── state-schema.md
│   └── testing/
│       └── local-sandbox.md
├── skills/
│   └── clanker-courts-player/
│       ├── SKILL.md
│       ├── references/
│       │   ├── clanker-courts-v9.md
│       │   ├── clankmates.md
│       │   └── client-cli.md
│       └── scripts/
│           └── clanker-courts
├── src/
│   └── clanker_courts_player/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── models.py
│       ├── errors.py
│       ├── clankmates.py
│       ├── messages.py
│       ├── state_store.py
│       ├── reports.py
│       ├── map_tools.py
│       ├── legal_actions.py
│       ├── order_builder.py
│       ├── candidate_plans.py
│       ├── plan_evaluator.py
│       ├── diplomacy.py
│       ├── promise_ledger.py
│       ├── play_loop.py
│       └── logging.py
├── tests/
│   ├── fixtures/
│   │   ├── inbox_page_phase_request.json
│   │   ├── inbox_page_diplomacy.json
│   │   ├── phase_request_reinforcement.json
│   │   ├── phase_request_movement.json
│   │   ├── state_minimal.json
│   │   └── reports/
│   │       ├── setup_report.json
│   │       ├── reinforcement_report.json
│   │       └── movement_visibility_report.json
│   ├── test_clankmates.py
│   ├── test_messages.py
│   ├── test_state_store.py
│   ├── test_reports.py
│   ├── test_map_tools.py
│   ├── test_legal_actions.py
│   ├── test_order_builder.py
│   ├── test_candidate_plans.py
│   ├── test_plan_evaluator.py
│   ├── test_diplomacy.py
│   ├── test_promise_ledger.py
│   └── test_play_loop.py
└── scripts/
    ├── copy-reference-rules
    └── run-local-sandbox
```

## 4. Architecture Sections

### Clankmates Transport Adapter

Module: `src/clanker_courts_player/clankmates.py`

Responsibilities:

- Run `clankm` commands safely through `subprocess.run`.
- Accept `profile`, `base_url`, timeout, and optional `clankm_path`.
- Provide methods:
  - `version() -> str`
  - `config_init(profile, base_url) -> dict | None`
  - `whoami(profile) -> dict`
  - `list_threads(profile, status="all") -> dict`
  - `show_thread(profile, thread_id, limit=10, cursor=None) -> dict`
  - `send(profile, recipient, body: dict) -> dict`
  - `reply(profile, thread_id, body: dict) -> dict`
- Keep JSON encoding inside the adapter so callers pass maps, not shell-escaped strings.
- Return structured errors with command, exit code, stdout/stderr, and decode errors.
- Never log tokens or raw auth material.

CLI commands:

```bash
python -m clanker_courts_player preflight --profile local-blue --base-url http://localhost:4000
python -m clanker_courts_player join --profile local-blue --server @courts-server --game-id demo --state var/demo/state.json
```

Preflight expected JSON:

```json
{
  "ok": true,
  "profile": "local-blue",
  "base_url": "http://localhost:4000",
  "clankm_version": "present",
  "whoami": {"handle": "bluebot"},
  "inbox_readable": true
}
```

### Server Protocol / Message Model

Module: `src/clanker_courts_player/models.py`

Model these message bodies:

- `JoinGame`: `type`, `game_id`, `handle`.
- `JoinAck`: `type`, `game_id`, `status`, `joined`, `required`.
- `JoinRejected`: `type`, `game_id`, `reason`.
- `GameStarted`: `type`, `game_id`, `player_id`, `ruleset_id`, `reports`, `communication_rules`, `status`.
- `PhaseRequest`: `type`, `game_id`, `request_id`, `player_id`, `turn`, `phase`, `status`, `reports`, `deadline_ms`.
- `OrderResponse`: `type`, `game_id`, `reply_to`, `player_id`, `turn`, `phase`, `orders`, `done`, `table_talk`, `messages`, `source`, optional `fallback_reason`.
- `DiplomacyEntry`: `to_player_id`, `body`.
- `DiplomacyMessage`: `type`, `game_id`, `from_player_id`, `to_player_id`, `turn`, `phase`, `body`.

Rules:

- Preserve unknown fields in parsed messages for forward compatibility.
- Reject unknown `phase` values except `reinforcement` and `movement`.
- Accept `table_talk` as list or string only if current server shape requires it; output should use list unless the compatibility tests prove string is necessary.
- Normalize order kind field to one of `reinforce`, `move`, `support`.

### Durable State Store And Raw Message Archive

Module: `src/clanker_courts_player/state_store.py`

Store state under `var/<game_id>/` by default:

```text
var/<game_id>/
├── state.json
├── raw_messages.jsonl
├── events.jsonl
├── submissions.jsonl
└── snapshots/
    ├── turn-001-reinforcement.json
    └── turn-001-movement.json
```

`state.json` shape:

```json
{
  "schema_version": 1,
  "game_id": "demo",
  "server": {"recipient": "@courts-server", "thread_id": "thread-1", "base_url": "http://localhost:4000"},
  "clankmates": {"profile": "local-blue", "handle": "bluebot"},
  "player": {"player_id": "blue", "capital_location_id": "B", "known_players": ["blue", "red", "green"]},
  "phase": {"turn": 1, "phase": "reinforcement", "request_id": "demo-t1-reinforcement-blue", "deadline_ms": 60000},
  "seen": {"message_ids": [], "request_ids": []},
  "reports": [],
  "latest_visible_report": null,
  "submissions": [],
  "diplomacy": {"sent": [], "received": []},
  "promises": {"made": [], "received": [], "resolved": []},
  "opponents": {},
  "current_plan": null,
  "created_at": "2026-06-03T00:00:00Z",
  "updated_at": "2026-06-03T00:00:00Z"
}
```

Requirements:

- All state writes are atomic.
- Raw Clankmates messages are appended before parsing so malformed payloads are still available.
- `seen.request_ids` prevents double replies.
- `seen.message_ids` prevents duplicate diplomacy and duplicate state events.
- No server-private state is stored unless received in a live player-visible message.

### Visible Report Parser / Summarizer

Module: `src/clanker_courts_player/reports.py`

Inputs: latest `reports` array from `game_started` or `phase_request`.

Known payloads:

- `setup_report`: `game_id`, `ruleset_id`, `ruleset_hash`, `final_turn`, `player_id`, `capital_location_id`, `players`, `visibility`.
- `reinforcement_report`: `turn`, `phase`, `reinforcements_available`, `controlled_cities`, `reinforcement_clock_ms`.
- `reinforcement_result_report`: `turn`, `phase`, `applied_orders`, `visibility`.
- `movement_visibility_report`: `turn`, `phase`, `movement_clock_ms`, `visibility`.
- `movement_result_report`: `turn`, `phase`, `battle_reports`, `status`, `visibility`.

Summary output:

```json
{
  "turn": 1,
  "phase": "movement",
  "capital": {"location_id": "B", "troops": 6, "threats": []},
  "controlled": [{"location_id": "B", "kind": "city", "troops": 6}],
  "adjacent": [{"location_id": "M", "controller_player_id": null, "troops": 0}],
  "distance_two": [{"location_id": "R", "controller_player_id": "red"}],
  "visible_opponents": ["red"],
  "legal_context": {"controlled_origins": ["B"], "known_players": ["blue", "red", "green"]},
  "uncertainty": ["Locations beyond distance two are hidden."]
}
```

The summarizer must not infer hidden troops. It may label uncertainty explicitly.

### Map / Connectivity Tools

Module: `src/clanker_courts_player/map_tools.py`

Inputs: visible `connectivity_graph` from reports. This graph includes controlled and adjacent locations plus legal edges the player is allowed to know.

Functions:

- `neighbors(location_id, graph) -> list[str]`
- `visible_nodes(visibility) -> dict[str, LocationView]`
- `border_locations(player_id, visibility) -> list[str]`
- `reachable_targets(origin, visibility) -> list[str]`
- `distance_from_capital(capital_id, graph) -> dict[str, int]` for visible graph only.
- `chokepoint_score(graph) -> dict[str, int]` based only on visible graph.

Do not add hidden map edges from scenario files during live play. Scenario fixtures may be used in tests only when they are explicitly player-visible.

### Legal Action / Order-Response Builder And Validator

Modules:

- `src/clanker_courts_player/legal_actions.py`
- `src/clanker_courts_player/order_builder.py`

Legal action output:

```json
{
  "phase": "movement",
  "legal": {
    "move_origins": [{"location_id": "B", "max_troops": 6}],
    "moves": [{"kind": "move", "from": "B", "to": "M", "max_troops": 6}],
    "supports": [{"kind": "support", "from": "B", "to": "M", "supported_player_id": "red", "max_troops": 6}]
  },
  "fallback_orders": [{"kind": "move", "from": "B", "to": "M", "troops": 5}],
  "validation_errors": []
}
```

Validation rules:

- Universal:
  - Order kind matches phase.
  - Troops are positive integers.
  - Referenced visible locations exist for validation from visible reports. If the destination is known through the visible connectivity graph but lacks full location details, allow move legality only when adjacency is present and do not invent controller/troops.
- Reinforcement:
  - Targets must be controlled cities from `controlled_cities`.
  - Total troops <= `reinforcements_available`.
  - Missing remainder is allowed because the server defaults it to capital.
- Movement:
  - Origin must be controlled.
  - Destination must be adjacent in the visible connectivity graph.
  - Sum of move/support troops from each origin <= visible post-reinforcement troop count.
- Support:
  - `supported_player_id` must be known, not eliminated if known, and not self.
  - Target cannot be own-controlled when known.
  - Cannot contain both a move and support targeting the same location.
  - Cannot contain support orders targeting the same location for different supported players.

Fallback rules:

- Reinforcement: put all available troops in the first controlled city, preferring capital when present.
- Movement: if a controlled origin has more than 1 troop and an adjacent non-self or unknown target exists, move `troops - 1` to the first safest target; otherwise submit `[]` as hold.
- Always produce `done: true`.

### Candidate Plan Generator And Plan Evaluator

Modules:

- `src/clanker_courts_player/candidate_plans.py`
- `src/clanker_courts_player/plan_evaluator.py`

Candidate plans are heuristic menus for the harness, not authoritative strategy. Generate small sets:

- `defend_capital`: hold or reinforce capital/frontier.
- `expand_empty`: capture adjacent neutral/empty locations.
- `pressure_enemy`: attack visible opponent border when troop advantage is plausible.
- `support_ally`: support a non-self player into a contested target when diplomacy suggests it.
- `consolidate`: move troops from rear controlled locations toward frontier.
- `fallback`: legal conservative package.

Evaluator returns scores with transparent reasons:

```json
{
  "plans": [
    {
      "id": "expand-empty-1",
      "orders": [],
      "scores": {
        "capital_safety": 0.8,
        "territorial_gain": 0.6,
        "promise_alignment": 0.2,
        "betrayal_exposure": 0.1
      },
      "notes": ["Leaves 1 troop at capital.", "Does not rely on hidden state."]
    }
  ]
}
```

The harness may override rankings after reasoning.

### Diplomacy Agenda And Promise Ledger

Modules:

- `src/clanker_courts_player/diplomacy.py`
- `src/clanker_courts_player/promise_ledger.py`

Diplomacy agenda input: summary, threat model, known players, recent diplomacy, promises, selected/candidate plans.

Output:

```json
{
  "contacts": [
    {
      "to_player_id": "red",
      "purpose": "coordinate_against_leader",
      "suggested_body": "Green is leading. I can pressure Eastgate if you hold the center.",
      "related_promises": []
    }
  ],
  "warnings": ["Do not message self.", "Recipient green is not visible but is known from setup."]
}
```

Promise ledger shape:

```json
{
  "id": "p-001",
  "direction": "made",
  "counterparty": "red",
  "turn_made": 2,
  "phase_made": "movement",
  "commitment": "support red into M",
  "conditions": "if red does not attack B",
  "due_turn": 2,
  "due_phase": "movement",
  "status": "open",
  "evidence": [{"message_id": "m42", "thread_id": "thread-red"}]
}
```

The code should detect obvious promise mentions and expose them to the harness, but the harness decides interpretation, credibility, deception policy, and whether a promise was truly kept.

### Live Play Loop

Module: `src/clanker_courts_player/play_loop.py`

Modes:

- `--decision-mode fallback`: run fully deterministic conservative play for smoke tests.
- `--decision-mode prompt`: print a JSON decision request for the harness and read selected decision JSON from a file or stdin.
- `--once`: process one latest phase request and stop.
- `--until-ended`: poll until game ended.

Loop:

1. Load state.
2. Poll inbox threads and archive raw messages.
3. Parse messages for current `game_id`.
4. Process `join_ack`, `game_started`, `phase_request`, `diplomacy_message`, and final/after-game messages.
5. If an unseen phase request exists, summarize reports and update state.
6. Generate legal actions, candidate plans, and diplomacy agenda.
7. Ask harness for decision or use fallback.
8. Validate selected orders and diplomacy entries.
9. Build canonical `order_response`.
10. Reply to phase-request thread.
11. Send/fan out peer diplomacy if configured by server communication rules or local harness mode.
12. Record submission and mark request seen.
13. Continue or exit.

Operator log examples:

```text
[bluebot] joined game demo as player_id=blue
[bluebot] turn=1 reinforcement report received: controlled=1 allowance=1
[bluebot] plan: reinforce B; priority=capital safety
[bluebot] submitted reinforcement orders: 1 orders
```

### Skill File / Harness Prompt Design

Files:

- `skills/clanker-courts-player/SKILL.md`
- `skills/clanker-courts-player/references/clanker-courts-v9.md`
- `skills/clanker-courts-player/references/clankmates.md`
- `skills/clanker-courts-player/references/client-cli.md`
- `skills/clanker-courts-player/scripts/clanker-courts`

`SKILL.md` should be concise and tell the harness:

- Required inputs: game idea/rules, base URL, server recipient, game ID, profile, handle/new-profile instructions, strategy, artifact directory, poll interval.
- Run preflight first.
- Join once.
- Run `play-loop --once` or `--until-ended`.
- For each decision request, reason from visible reports only.
- Use helpers for legal actions and validation before submitting.
- Keep diplomacy private and two-sided through Clankmates.
- Track promises and intentional deception in the ledger.
- Submit fallback orders before deadlines.

The skill must explicitly separate strategy prompts from callable tools. The prompt can ask the model to choose among candidates; the tools must not claim to know the best strategic move.

### Local / Sandbox Testing

Levels:

1. Pure Python fixtures:
   - Test parsing, state, summaries, legal actions, builders, promise ledger, and fallback.
2. Fake `clankm` adapter:
   - Test preflight, polling, joining, replying, and archive behavior with a fake executable or monkeypatched runner.
3. Optional local Clankmates:
   - Use `http://localhost:4000`.
   - Commands:

```bash
clankm config init --profile ccf4_bluebot --base-url http://localhost:4000
clankm --profile ccf4_bluebot auth whoami --json
clankm --profile ccf4_bluebot inbox list --status all --json
```

4. Optional reference server comparison:
   - When `/home/hermes/clanker-client-planning-work/refs/clanker-courts-server` is available, run its public harness or contract fixtures to compare message handling. Production client code must not import server modules.

## 5. Staged Implementation Plan

Each stage should be a small Conventional Commit. Do not implement all helpers at once.

### Stage 0: Bootstrap Python Package

Files:

- `pyproject.toml`
- `src/clanker_courts_player/__init__.py`
- `src/clanker_courts_player/__main__.py`
- `src/clanker_courts_player/cli.py`
- `tests/test_cli.py`

TDD steps:

1. Add a failing test that `python -m clanker_courts_player --help` exits 0 and lists `preflight`.
2. Implement minimal CLI parser with placeholder subcommands.
3. Run:

```bash
python -m pip install -e '.[dev]'
pytest tests/test_cli.py
```

Expected result: tests pass; help text includes `preflight`, `join`, `poll`, `summarize`, `legal-actions`, `build-response`, `validate-response`, and `play-loop`.

Commit: `chore: bootstrap python client package`

### Stage 1: Protocol Models

Files:

- `src/clanker_courts_player/models.py`
- `src/clanker_courts_player/errors.py`
- `tests/test_models.py`
- `tests/fixtures/phase_request_reinforcement.json`
- `tests/fixtures/phase_request_movement.json`

TDD steps:

1. Add fixtures for `join_game`, `join_ack`, `game_started`, `phase_request`, `order_response`, and `diplomacy_message`.
2. Test valid fixtures parse and round-trip.
3. Test invalid phase, missing `game_id`, missing `request_id`, self-directed diplomacy, and non-object JSON fail with structured errors.
4. Implement Pydantic models.

Commands:

```bash
pytest tests/test_models.py
```

Expected result: all protocol model tests pass and unknown fields are preserved.

Commit: `feat: add clanker courts protocol models`

### Stage 2: Clankmates CLI Adapter

Files:

- `src/clanker_courts_player/clankmates.py`
- `tests/test_clankmates.py`

TDD steps:

1. Monkeypatch command runner to return JSON for `whoami`, `inbox list`, `inbox show`, `send`, and `reply`.
2. Test command argument construction exactly:
   - `["clankm", "--profile", profile, "inbox", "reply", thread_id, "--body", json_body, "--json"]`
3. Test non-zero exit and malformed JSON produce structured errors.
4. Implement adapter and `preflight` CLI.

Commands:

```bash
pytest tests/test_clankmates.py
python -m clanker_courts_player preflight --profile test --base-url http://localhost:4000 --dry-run
```

Expected result: tests pass; dry run prints JSON with `ok: true` and planned checks.

Commit: `feat: wrap clankmates cli transport`

### Stage 3: Message Filtering And Raw Archive

Files:

- `src/clanker_courts_player/messages.py`
- `src/clanker_courts_player/state_store.py`
- `tests/test_messages.py`
- `tests/test_state_store.py`
- `tests/fixtures/inbox_page_phase_request.json`
- `tests/fixtures/inbox_page_diplomacy.json`

TDD steps:

1. Create inbox fixtures using Clankmates shapes with `id`, `attributes.body`, timestamp variants, JSON string bodies, and plain text.
2. Test decoding JSON bodies while preserving plain text.
3. Test selecting latest unseen matching `phase_request` for one `game_id`.
4. Test selecting last 12 diplomacy messages involving current player.
5. Test ignoring unrelated game IDs.
6. Test state file atomic save/load and raw JSONL append.

Commands:

```bash
pytest tests/test_messages.py tests/test_state_store.py
```

Expected result: tests pass; a temp archive contains raw message pages before parsed events.

Commit: `feat: persist state and filter clankmates messages`

### Stage 4: Join And Poll Commands

Files:

- `src/clanker_courts_player/cli.py`
- `src/clanker_courts_player/play_loop.py` or `join.py` if split is cleaner
- `tests/test_join_poll_cli.py`

TDD steps:

1. Fake adapter returns `whoami.handle = bluebot` and `send` creates `thread-1`.
2. Test `join` sends:

```json
{"type":"join_game","game_id":"demo","handle":"bluebot"}
```

3. Test join records `server.thread_id`.
4. Test `poll` reads known thread, archives messages, processes `join_ack` and `game_started`, records `player_id`.

Commands:

```bash
pytest tests/test_join_poll_cli.py
```

Expected result: tests pass; `state.json` includes `game_id`, server thread, profile, handle, `player_id` after `game_started`.

Commit: `feat: join games and poll inbox state`

### Stage 5: Report Parser And Summarizer

Files:

- `src/clanker_courts_player/reports.py`
- `tests/test_reports.py`
- `tests/fixtures/reports/setup_report.json`
- `tests/fixtures/reports/reinforcement_report.json`
- `tests/fixtures/reports/movement_visibility_report.json`

TDD steps:

1. Test setup report extracts capital, known players, final turn, ruleset hash.
2. Test reinforcement report extracts allowance and controlled cities.
3. Test movement report extracts controlled, adjacent, distance two, visible opponents, and uncertainty notes.
4. Add `summarize` CLI that reads a phase request or state file.

Commands:

```bash
pytest tests/test_reports.py
python -m clanker_courts_player summarize --input tests/fixtures/phase_request_movement.json
```

Expected result: summary JSON contains `phase`, `capital`, `controlled`, `adjacent`, `distance_two`, `visible_opponents`, and no hidden-state fields.

Commit: `feat: summarize visible player reports`

### Stage 6: Visible Map Metrics

Files:

- `src/clanker_courts_player/map_tools.py`
- `tests/test_map_tools.py`

TDD steps:

1. Test neighbors from visible `connectivity_graph`.
2. Test border locations include controlled nodes adjacent to non-self or unknown nodes.
3. Test distance metrics only traverse visible graph.
4. Test graph does not add scenario-only edges.

Commands:

```bash
pytest tests/test_map_tools.py
```

Expected result: visible metrics are deterministic and never require full scenario maps.

Commit: `feat: add visible map metrics`

### Stage 7: Legal Actions And Validation

Files:

- `src/clanker_courts_player/legal_actions.py`
- `tests/test_legal_actions.py`

TDD steps:

1. Reinforcement tests:
   - Valid controlled city reinforcement.
   - Reject non-city or non-controlled target.
   - Reject total above allowance.
   - Allow partial allocation.
2. Movement tests:
   - Valid adjacent move.
   - Reject unowned origin.
   - Reject non-adjacent destination.
   - Reject over-committing an origin.
3. Support tests:
   - Reject support self.
   - Reject support into own-controlled target.
   - Reject mixed move/support same target.
   - Reject support same target for different supported players.
4. Fallback tests:
   - Reinforcement fallback all to capital/first city.
   - Movement fallback holds or moves `troops - 1` to first non-self target.

Commands:

```bash
pytest tests/test_legal_actions.py
python -m clanker_courts_player legal-actions --input tests/fixtures/phase_request_movement.json
```

Expected result: legal action JSON includes `legal`, `fallback_orders`, and `validation_errors: []`.

Commit: `feat: generate and validate legal visible orders`

### Stage 8: Order Response Builder

Files:

- `src/clanker_courts_player/order_builder.py`
- `tests/test_order_builder.py`

TDD steps:

1. Test builder copies `game_id`, `request_id`, `player_id`, `turn`, and `phase` from a `PhaseRequest`.
2. Test output has `type: order_response`, `reply_to`, `orders`, `done: true`, `table_talk`, `messages`, and `source`.
3. Test malformed diplomacy entries are rejected.
4. Test `validate-response` rejects wrong `game_id`, wrong `turn`, wrong phase, missing arrays, and illegal orders.

Commands:

```bash
pytest tests/test_order_builder.py
python -m clanker_courts_player build-response --request tests/fixtures/phase_request_reinforcement.json --orders '[]' --source codex
python -m clanker_courts_player validate-response --request tests/fixtures/phase_request_reinforcement.json --response /tmp/response.json
```

Expected result: builder emits canonical JSON; validator prints `{"ok": true}` for valid response and structured errors otherwise.

Commit: `feat: build canonical order responses`

### Stage 9: Candidate Plans And Evaluator

Files:

- `src/clanker_courts_player/candidate_plans.py`
- `src/clanker_courts_player/plan_evaluator.py`
- `tests/test_candidate_plans.py`
- `tests/test_plan_evaluator.py`

TDD steps:

1. Test reinforcement candidates include capital defense and frontier reinforcement.
2. Test movement candidates include hold, expand, pressure, support, and fallback when legal.
3. Test evaluator scores capital safety lower when a plan empties capital.
4. Test evaluator notes promise dependency when a plan uses `support`.

Commands:

```bash
pytest tests/test_candidate_plans.py tests/test_plan_evaluator.py
python -m clanker_courts_player candidate-plans --input tests/fixtures/phase_request_movement.json
```

Expected result: candidate output is small, deterministic, and contains explanations.

Commit: `feat: provide candidate plan menus`

### Stage 10: Diplomacy Agenda And Promise Ledger

Files:

- `src/clanker_courts_player/diplomacy.py`
- `src/clanker_courts_player/promise_ledger.py`
- `tests/test_diplomacy.py`
- `tests/test_promise_ledger.py`

TDD steps:

1. Test agenda never suggests messaging self.
2. Test agenda suggests containment contact when a visible opponent leads by visible territory.
3. Test ledger records promises made and received with evidence IDs.
4. Test ledger can mark promises `open`, `kept`, `broken`, `superseded`, or `expired`.
5. Test ambiguous message text is surfaced as `needs_harness_review`, not auto-classified.

Commands:

```bash
pytest tests/test_diplomacy.py tests/test_promise_ledger.py
```

Expected result: diplomacy helper emits suggested contacts and ledger updates without deciding truthfulness or strategy.

Commit: `feat: track diplomacy agenda and promises`

### Stage 11: Submit And Diplomacy Fanout

Files:

- `src/clanker_courts_player/play_loop.py`
- `src/clanker_courts_player/cli.py`
- `tests/test_submit.py`

TDD steps:

1. Test `submit` replies to the phase-request thread using `clankm inbox reply`.
2. Test submission is recorded in `submissions.jsonl`.
3. Test request ID is added to `seen.request_ids`.
4. Test optional `--fanout-diplomacy` sends each valid `messages` entry as a `diplomacy_message` to known Clankmates handles when the state has player-handle mapping.
5. Test invalid diplomacy entries are skipped or rejected according to `--strict`.

Commands:

```bash
pytest tests/test_submit.py
```

Expected result: one reply per phase request; no duplicate response for an already-seen request ID.

Commit: `feat: submit phase replies through clankmates`

### Stage 12: Play Loop

Files:

- `src/clanker_courts_player/play_loop.py`
- `tests/test_play_loop.py`

TDD steps:

1. Fake adapter returns join, phase request, and result messages.
2. Test `play-loop --once --decision-mode fallback` submits one legal response and exits.
3. Test `play-loop --once` does nothing for no unseen phase requests.
4. Test rejected/invalid model decision falls back before deadline.
5. Test game-ended message stops `--until-ended`.

Commands:

```bash
pytest tests/test_play_loop.py
python -m clanker_courts_player play-loop --state tests/fixtures/state_minimal.json --once --decision-mode fallback --dry-run
```

Expected result: dry run prints concise operator logs and emits planned response JSON.

Commit: `feat: run bounded live play loop`

### Stage 13: Skill Package

Files:

- `skills/clanker-courts-player/SKILL.md`
- `skills/clanker-courts-player/references/clanker-courts-v9.md`
- `skills/clanker-courts-player/references/clankmates.md`
- `skills/clanker-courts-player/references/client-cli.md`
- `skills/clanker-courts-player/scripts/clanker-courts`
- `tests/test_skill_artifacts.py`

TDD steps:

1. Test skill files exist.
2. Test `SKILL.md` names required inputs and the visible-state-only boundary.
3. Test scripts wrapper points to `python -m clanker_courts_player`.
4. Copy or summarize rules reference without depending on external local clone paths.

Commands:

```bash
pytest tests/test_skill_artifacts.py
```

Expected result: skill artifact can be copied into a harness environment and still calls the package CLI.

Commit: `feat: add reusable player skill package`

### Stage 14: Documentation And Local Sandbox

Files:

- `docs/protocol/clankmates-message-shapes.md`
- `docs/protocol/state-schema.md`
- `docs/testing/local-sandbox.md`
- `scripts/run-local-sandbox`
- `tests/test_docs_examples.py`

TDD steps:

1. Add docs with exact setup, join, poll, validate, and play-loop commands.
2. Add doctest-style or snapshot tests for JSON examples where practical.
3. Add local sandbox script that fails clearly if `clankm`, local Clankmates, or reference server is missing.

Commands:

```bash
pytest tests/test_docs_examples.py
ruff check .
ruff format --check .
```

Expected result: docs examples are parseable and sandbox script reports blockers clearly.

Commit: `docs: document protocol and sandbox workflow`

### Stage 15: End-To-End Smoke Runs

Commands:

```bash
pytest
ruff check .
ruff format --check .
python -m clanker_courts_player preflight --profile ccf4_bluebot --base-url http://localhost:4000
python -m clanker_courts_player play-loop --state var/demo/state.json --once --decision-mode fallback --dry-run
```

Expected result:

- Unit tests pass.
- Lint and formatting pass.
- Preflight succeeds when local Clankmates/profile exist, or prints a structured blocker.
- Dry-run play loop produces one legal fallback response from fixtures/state.

Commit: `test: add end-to-end client smoke coverage`

## 6. Open Questions / Assumptions / Risk Register

### Open Questions

- Does the live Clanker Courts server always require embedded `messages` in `order_response`, separate peer `diplomacy_message` sends, or both? The current plan supports both but needs a final compatibility flag.
- Will Clankmates expose stable sender handles in inbox payloads for all account and channel thread types? If not, state must let users provide `player_id -> @handle` mappings.
- Is `table_talk` intended to be a list, string, or ignored? Current examples vary between list-style response shape and fallback string. Builder should output list until compatibility tests require otherwise.
- Will official JSON Schemas be published for Clanker Courts messages? If yes, replace or complement Pydantic-only validation with schema validation.
- Are deadlines wall-clock absolute timestamps in future server messages or relative `deadline_ms` durations? Current harness uses `deadline_ms`; client should support optional absolute deadline fields.

### Assumptions

- Python 3.11+ is available to the harness.
- `clankm` is installed separately by the user or setup step.
- The client can store state in a writable artifact directory.
- During live play, all legal decisions must be made from `phase_request.reports`, previous visible reports, and received diplomacy messages only.
- The final after-game report may reveal full state and can be archived after the game ends, but it must not influence live decisions in the same game.

### Risks

- Protocol drift: mitigate with fixture tests, docs, and permissive unknown-field preservation.
- Hidden-state leakage during local testing: never import server modules in production package; mark optional reference-server tests as sandbox-only.
- Duplicate submissions: maintain `seen.request_ids`, archive submissions, and make `submit` idempotent for a request.
- Clankmates pagination misses messages: use bounded pagination with cursors and raw archive, not a single thread read.
- Malformed or screened inbox messages: preserve raw bodies, ignore unrelated/plain text, and print structured blockers.
- Bad strategy from heuristic helpers: keep candidates small and explain that the harness chooses strategy.
- Over-strict legal validation from partial visibility: validate only what visible reports can prove; when uncertain, prefer conservative fallback and let server authoritative validation reject/accept.
- Deadline misses: play loop must use fallback when decision hook exceeds a configured safety margin.

## 7. Acceptance Criteria

The implementation is acceptable when:

- `docs/plans/2026-06-03-clanker-courts-player-client.md` exists and remains linked from `README.md`.
- The repo contains a Python package with JSON-on-stdin/stdout helper CLIs.
- `python -m clanker_courts_player --help` lists all primary commands.
- `preflight` verifies `clankm`, profile auth, base URL, and inbox readability, or emits structured blockers.
- `join` sends the documented `join_game` message and records server thread/handle state.
- `poll` archives raw messages, decodes JSON bodies, filters by `game_id`, ignores unrelated messages, and updates state.
- Report summarization covers setup, reinforcement, movement visibility, reinforcement result, and movement result reports without hidden-state dependence.
- Legal action generation and response validation cover reinforcement, move, support, fallback, and malformed diplomacy cases.
- `build-response` emits canonical `order_response` JSON with `done: true`.
- `submit` replies to the correct Clankmates thread and prevents duplicate replies for the same `request_id`.
- Diplomacy helpers maintain sent/received messages and promise ledger state while leaving interpretation and deception policy to the harness.
- `play-loop --once --decision-mode fallback --dry-run` can process a fixture phase request and produce a legal response.
- The skill package includes `SKILL.md`, references, and a wrapper script usable by shell-capable harnesses.
- `pytest`, `ruff check .`, and `ruff format --check .` pass.
- Optional local sandbox docs explain how to run against `http://localhost:4000` and clearly report missing `clankm`, auth, or reference-server blockers.
