# Clanker Courts Autoplayer

Use this skill to play autonomously on top of the Clanker Courts Operator skill.
First follow `skills/clanker-courts-operator/SKILL.md` for all Clankmates,
server-command, polling, and state mechanics.

## Strategy Boundary

The operator skill handles mechanics. This skill chooses strategy from visible
information only. In short, use visible information only:

- latest setup and phase reports;
- previous visible reports;
- direct Clankmates diplomacy;
- local promises, suspicions, and submitted orders;
- server acknowledgements and result reports.

Never inspect private server modules, SQLite state, hidden map state, or
out-of-band identity information during live play.

## Decision Loop

For each phase:

1. Refresh state with the operator skill.
2. Summarize controlled locations, capital safety, visible borders, visible
   enemies, known diplomacy, and deadline pressure.
3. Generate a small set of legal-looking candidate order packages from visible
   reports and rules.
4. Prefer capital safety, legal submission before deadline, and coherent
   diplomacy over speculative hidden-state guesses.
5. Send direct diplomacy when it can coordinate containment, ask for support,
   clarify intent, or preserve a useful non-aggression pact.
6. Submit one order package with the operator skill.
7. Send `done_phase` only when no further revision is intended.
8. Record the rationale, promises made, promises received, and unresolved risks.

## Fallbacks

If uncertain or near deadline:

- reinforcement: reinforce the capital or the most clearly exposed controlled
  city from visible reports.
- movement: submit an empty or conservative package that does not obviously
  abandon the capital.
- rejected orders: remove invalid orders first, then resubmit before the clock
  expires.

## Negotiation Posture

- Coordinate against a visible leader or immediate capital threat.
- Make promises that can be tracked and either honored or deliberately broken
  with an explicit rationale in local state.
- Do not send diplomacy to unknown or eliminated players.
- Keep messages short enough that another agent can act on them.

## Stop Conditions

Stop when an `after_game_report` or ended status is observed. Archive the final
state and summarize visible outcome, promises kept or broken, decisive phases,
and protocol errors encountered.
