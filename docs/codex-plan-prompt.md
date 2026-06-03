# Codex task: write Clanker Courts player-client implementation plan

You are running inside `/home/hermes/clanker-courts-player-client`, a new planning wrapper repo. Your job is to create a tangible implementation-plan artifact for building a standalone Clanker Courts v9 player client/skill package.

## User goal

Build a client that can play Clanker Courts through Clankmates. The client should be usable by shell-capable coding harnesses such as Codex, Grok Build, Claude Code, OpenCode, etc. The harness should start from a skill, receive parameters such as game idea/rules, server location/base URL, game ID, Clankmates profile or new-profile instructions, and then run a loop: poll server/messages, understand visible position, record state, choose/validate/execute moves, negotiate through Clankmates, update promise/state ledgers, and continue until the game ends.

The critical design requirement is separation of concerns:

- The coaching harness/LLM should handle strategy, judgment, negotiation content, deception/credibility policy, and adaptation.
- Code/tools should handle protocol, Clankmates transport, message filtering, state persistence, visible-map summaries, legal action generation/scaffolding, order-response validation/building, conservative fallback orders, history/promise bookkeeping, and execution.

## Required output

Create this file:

```text
docs/plans/2026-06-03-clanker-courts-player-client.md
```

It must be a comprehensive implementation plan following this structure:

1. Header with goal, architecture, and tech stack.
2. Reference study summary for the three repos and exactly which files informed the plan.
3. Proposed repo/package layout for the future implementation.
4. Architecture sections for:
   - Clankmates transport adapter.
   - Server protocol/message model.
   - Durable state store and raw message archive.
   - Visible report parser/summarizer.
   - Map/connectivity tools.
   - Legal action/order-response builder and validator.
   - Candidate plan generator and plan evaluator.
   - Diplomacy agenda and promise ledger.
   - Live play loop.
   - Skill file/harness prompt design.
   - Local/sandbox testing.
5. A staged, bite-sized implementation plan with exact file paths, TDD-style steps, commands, and expected results. Make tasks small enough that another coding agent can execute them one by one.
6. Open questions / assumptions / risk register.
7. Acceptance criteria.

Also update `README.md` only if needed to ensure it links to the plan.

## Reference repositories to study

Local clones are available at:

```text
/home/hermes/clanker-client-planning-work/refs/clankmates
/home/hermes/clanker-client-planning-work/refs/diplomacy
/home/hermes/clanker-client-planning-work/refs/clanker-courts-server
```

Do not modify those repositories.

Study at least these files:

### Clankmates

- `/home/hermes/clanker-client-planning-work/refs/clankmates/README.md`
- `/home/hermes/clanker-client-planning-work/refs/clankmates/AGENTS.md`
- Official docs if useful: `https://clankmates.com/for-clankers.md` and `https://clankmates.com/for-clankers/skill.md`

Important Clankmates facts:

- Clankmates is a Phoenix/Ash web app.
- Production site: `https://clankmates.com`.
- Agents should use official CLI `clankm` for channel setup, publishing, and inbox messaging.
- Useful commands include:
  - `clankm config init --profile <profile> --base-url <url>`
  - `clankm auth whoami --json`
  - `clankm inbox list --status all --json`
  - `clankm inbox show <thread_id> --limit <n> --json`
  - `clankm inbox send @handle --body '<json>' --json`
  - `clankm inbox reply <thread_id> --body '<json>' --json`
- Local Clankmates testing should use `http://localhost:4000` and avoid mixing hostnames.

### Diplomacy / Clanker Courts rules

- `/home/hermes/clanker-client-planning-work/refs/diplomacy/README.md`
- `/home/hermes/clanker-client-planning-work/refs/diplomacy/AGENTS.md`
- `/home/hermes/clanker-client-planning-work/refs/diplomacy/rules/clanker-courts-v9.md`

Important v9 rules facts:

- Clanker Courts is a simultaneous-order diplomacy game for 3+ players on a graph of cities/towns.
- Objective: capture capitals/eliminate players or win by score at final turn.
- Turns have reinforcement then movement phases.
- Private two-sided diplomacy is allowed; promises have no direct rules effect unless reflected in orders.
- Orders are invisible to other players.
- Reinforcements: `controlled cities + floor(sqrt(controlled towns))`; can be placed only in controlled cities; default goes to capital.
- Movement orders: `move` and `support`; origins must be controlled, destinations adjacent, and troop totals cannot exceed troops at origin after reinforcement.
- Support cannot support self, cannot target own-controlled locations, and has per-target constraints.
- Movement resolution includes road battles, destination battles, support returns, capital loss, and scoring.
- The client must act only from visible reports during live play.

### Clanker Courts server

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

Important server facts:

- Server is currently transport-agnostic Elixir MVP; public API is `ClankerCourtsServer.API.handle/1` / `handle_json/1`.
- Player API commands include `submit_order_package`, `done_phase`, `get_status`, `get_reports`, `get_after_game_report`.
- Clankmates local-game harness provides concrete message shapes:
  - Join:
    ```json
    {"type":"join_game","game_id":"<game_id>","handle":"<your Clankmates handle>"}
    ```
  - Phase reply:
    ```json
    {"type":"order_response","game_id":"<game_id>","reply_to":"<phase_request.request_id>","player_id":"<player_id>","turn":1,"phase":"reinforcement","orders":[],"done":true,"table_talk":[],"messages":[],"source":"<agent>"}
    ```
  - Diplomacy entry:
    ```json
    {"to_player_id":"red","body":"Green is leading. I can pressure Eastgate if you hold the center."}
    ```
- The server repo already outlines candidate helpers: report summary, legal orders, candidate plans, plan evaluator, visible map metrics, threat model, diplomacy agenda, promise ledger, order response builder, what-if simulator, Clankmates preflight, message filter, state store, submit reply.
- The plan should prefer JSON-on-stdin/stdout scripts so different coding harnesses can call them.

## Proposed implementation language

Prefer Python for this standalone client plan unless you find a compelling reason otherwise. The plan can still note that future local testing may wrap server Elixir modules when the server repo is available, but production client tools must be standalone and use only visible reports/protocol messages.

## Planning standards

Make implementation obvious. Include exact filenames, suggested modules, CLI commands, test commands, fixtures, and expected outputs. Use DRY/YAGNI/TDD. Do not write the full client now; write the plan.
