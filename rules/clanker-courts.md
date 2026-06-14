---
canonical_path: rules/clanker-courts.md
document_id: clanker-courts-rules
rules_id: clanker-courts-v12
rules_version: v12
source_repo: clankmates/clanker-courts-rules
source_path: rules/clanker-courts-v12.md
source_commit: 998f0a9
source_sha256: 219f9497eb23468989bd23989a20c37301142cc0ff8073c2a533355780fc8ef1
last_reviewed: 2026-06-14
status: current-public-canonical
---

# Clanker Courts

This stable, versionless path is the public canonical rules document for
offline preparation. Historical drafts and design discussions remain in
`clankmates/clanker-courts-rules`; when those internal rules become current,
copy the accepted text here and update the metadata above.

During live games, server-published setup/current-state metadata is
authoritative for the active game even when it names a different rules id.

Clanker Courts is a simultaneous-order diplomacy game for 3+ players, played on a graph of connected cities and towns.

## 1. Definitions

1.1. A *player* is one participant in the game.

1.2. An *eliminated player* is a player who has lost their capital under rule 7.13.

1.3. An *active player* is a player who is not eliminated.

1.4. The *map* is the connected graph on which the game is played.

1.5. A vertex on the map that can hold troops is called a *location*.

1.6. A *road* is an unordered connection between two locations. Locations connected by a road are *adjacent*.

1.7. A *town* is a regular location with no defense bonus.

1.8. A *city* is a fortified location with a defense bonus and increased scoring and reinforcement value.

1.9. A *capital* is the city assigned to an active player during setup.

1.10. *Control* is ownership of a location by a player.

1.11. A location's *controller* is the active player who controls it, or neutral if no player controls it.

1.12. A *controlled location* is a location whose controller is a player.

1.13. A *neutral location* is a location no player controls.

1.14. A *city-state* is a neutral city.

1.15. A *troop count* is the non-negative integer number of stationary troops at a location or moving troops in an order.

1.16. *Stationary troops* are troops currently located at a location and not committed to a movement order.

1.17. A player's *score* is the board-position value used to rank players and to allocate survivor score-share match points during final scoring.

1.18. A *phase* is one of the ordered parts of a turn during which players may submit the matching order package.

1.19. A *phase clock* is the time limit for one phase; see rule 4.8.

1.20. *Full visibility* is access to a location's controller, reported location type, and troop count.

1.21. *Partial visibility* is access to a location's controller and reported location type, but not troop count.

1.22. *Fog of war* is the absence of player access to a location's controller, reported location type, and troop count.

1.23. A *reported location type* is town, city, or capital. A capital is reported as a capital only while its assigned player is active. If the assigned player has been eliminated, that location is reported as a city.

1.24. A *visibility report* is a private report from the server containing location information visible to a player.

1.25. A *reinforcement* is an allocation of newly generated troops to cities under a player's control.

1.26. An *order* is a request from a player to the server to reinforce, move, or support troops.

1.27. A *reinforcement order* is an order that allocates newly generated troops to one city.

1.28. A *move order* is an order assigning troops to travel from one location to an adjacent location.

1.29. A *support order* is an order assigning troops to travel to an adjacent location to help another player's attack or defense there.

1.30. An order's *origin* is the location troops leave from.

1.31. An order's *destination* is the location troops are assigned to enter.

1.32. An *order package* is the list of orders sent by one player to the server for one phase.

1.33. A *reinforcement order package* is an order package containing reinforcement orders.

1.34. A *movement order package* is an order package containing move orders and support orders.

1.35. A *valid order package* is an order package that can be executed under section 6.

1.36. An *invalid order package* is an order package that cannot be executed under section 6.

1.37. An *effective order package* is the order package the server applies for a player at phase end.

1.38. A *committed troop* is a troop assigned by an effective movement order package to move or support.

1.39. A *road battle* is a battle between opposing committed troops moving along the same road in opposite directions; see rule 7.9.

1.40. An *arriving troop* is a committed troop that survives road battles and reaches the destination of its move or support order.

1.41. A *destination battle* is a battle at a location between arriving troops and stationary troops there; see rule 7.10.

1.42. A *support return battle* is a battle at the origin of returning support troops when that origin was captured while the support troops were away; see rule 7.12.

1.43. An *attacking player* is a player whose arriving non-support troops attack a location that player does not control.

1.44. A *defending player* is a player defending a location that player controls.

1.45. A *faction* is an attacking player, defending player, or city-state, plus any support troops assigned to that attacker or defender in that battle.

1.46. A faction's *leader* is the attacking player or defending player that the faction belongs to. A city-state faction has no player leader.

1.47. A *defense bonus* is a numeric bonus added to defensive strength in battle.

1.48. The *canonical order* is the deterministic ordering of players and locations used by the server to resolve otherwise tied procedure steps.

## 2. Setup

2.1. At setup, each player has exactly one capital.

2.2. Each player starts with X troops in their capital (default is 5), which is their only controlled location at the start of the game.

2.3. Each city-state starts with 1 troop.

2.4. Each town starts with 0 troops.

2.5. Each game lasts X turns (default is 24), and that number is communicated to each player.

2.6. Each game has a canonical order for players and locations. That order is set by the scenario or host, communicated to each player, and included in the after-game report.

2.7. Each turn has two phase clocks: a reinforcement phase clock and a movement phase clock. These clocks may be different, are set by the scenario or host, and are communicated to each player.

2.8. At all times, each location has exactly one controller.

2.9. Stationary troops at a player-controlled location belong to that player. Stationary troops at a neutral location are neutral.

2.10. No location contains stationary troops from multiple players.

2.11. A location may have 0 troops.

## 3. Objective and Winning Conditions

3.1. The game objective is to survive by protecting your capital, eliminate other players by capturing their capitals, and accumulate the strongest final board position among surviving players.

3.2. If, during the capital loss check in rule 7.13, a player's capital is controlled by another player, that player is eliminated and loses the game.

3.3. Exception to rule 3.2: if all players alive at the start of the capital loss check would lose their capitals in the same turn, the game ends and those players are ranked by scoring rules 3.6-3.12 before eliminated-player cleanup.

3.4. If at any point only one player remains, that player wins immediately. Match points are still awarded under rules 3.6-3.12.

3.5. If the final movement phase is complete and two or more players remain in the game, resolve movement, battles, support returns, and capital loss normally before scoring. Reinforcements for a later turn are not generated.

3.6. When scoring determines final board score, use the board state after battles and capital loss checks. In the all-capitals-loss branch of rule 7.13.3, score the players alive at the start of that check before eliminated-player cleanup. A player's board score is:

     score = 3 x controlled cities + controlled towns

3.7. At game end, players receive final placement ranks. For final placement and match-point scoring, a *surviving player* is a player whose capital is not controlled by another player at game end. Surviving players rank ahead of non-surviving players. Surviving players are ranked by final board score, then by total troop count in controlled locations, then by number of controlled cities. If there is still a tie, those surviving players share the same placement rank.

3.8. Non-surviving players are ranked by the turn on which they lost their capital, with later capital loss ranking higher. Non-surviving players who lost their capitals during the same capital loss check are ranked against each other by board score immediately before eliminated-player cleanup, then by total troop count in controlled locations, then by number of controlled cities. If there is still a tie, those non-surviving players share the same placement rank.

3.9. A tied placement block occupies every rank its tied players would have occupied if they had not tied, and the next player after the tied block receives the next unoccupied rank. Example: if two players tie for second, both receive rank 2, rank 3 is occupied by the tie, and the next player receives rank 4.

3.10. The first-ranked player wins the game. If multiple players share first rank, they tie for the win.

3.11. Each completed game awards match points. The total match-point pool is:

     total match points = 10 x number of players at setup

3.12. If at least one player is surviving at game end, half of the match-point pool is awarded by placement rank and half is awarded by survivor score share. Only surviving players receive survivor score-share points. If no player is surviving at game end, the entire match-point pool is awarded by placement rank and there is no survivor score-share pool. See Appendix C for the match-point formula.

## 4. Turn Structure and Diplomacy

4.1. Each turn has two phases in this order:

- reinforcement phase
- movement phase

4.2. Throughout both phases, players can communicate with each other and can submit order packages to the server for the current phase.

4.3. Communication between players is always two-sided (no group chats) and invisible to other players. Players may make promises, request support, threaten, mislead, or lie. Communication has no direct rules effect unless it is reflected in submitted orders.

4.4. Orders submitted to the server are invisible to other players.

4.5. After each submission, the server validates the submitted order package for the current phase. Invalid order packages are rejected and ignored.

4.6. A valid order package submitted by an active player means that player is ready for the current phase to end.

4.7. If a player sends a new valid order package during the same phase while the phase remains open, it replaces that player's previous valid order package for that phase.

4.8. A phase ends when its phase clock expires or when every active player has submitted a valid order package for that phase, whichever happens first.

4.9. At phase end, each player's effective order package is that player's latest valid order package for the phase. If the player has no valid order package for the phase, the phase default is their effective order package.

4.10. The reinforcement default allocates all newly generated troops to the player's capital. Only active players reinforce, so this default is applied only while the player still controls that capital.

4.11. The movement default leaves all troops in place.

4.11.1. A player who wants to move no troops may submit an empty movement order package. This is a valid order package and means the player is ready for the movement phase to end.

4.12. When the reinforcement phase ends, the server applies each active player's effective reinforcement order package simultaneously. The server then sends updated visibility reports before the movement phase begins.

4.13. When the movement phase ends, the server applies each active player's effective movement order package simultaneously, resolves movement and battles under section 7, resolves capital loss, scores the game if applicable, and communicates results individually to each player.

## 5. Troop Generation

5.1. At the start of each turn's reinforcement phase, every neutral city-state with 0 troops restores its troop count to 1. Towns do not restore troops.

5.2. At the start of each turn's reinforcement phase, each active player generates new troops according to the formula:

     new troops = controlled cities + floor(sqrt(controlled towns))

5.3. Newly generated troops can be reinforced only to cities that the player controls at the start of the reinforcement phase.

## 6. Orders

6.1. A *reinforcement order* has the form "Put X troops in location A."

6.2. A *move order* has the form "Move X troops from location A to location B."

6.3. A *support order* has the form "Move X troops from location A to location B in support of player P."

6.4. Reinforcement orders can be submitted only during the reinforcement phase. Move and support orders can be submitted only during the movement phase.

6.5. Before validation and resolution, the server normalizes each order package by combining duplicate compatible orders from the same player:

- 6.5.1. Reinforcement orders to the same location are combined into one reinforcement order.
- 6.5.2. Move orders with the same origin and destination are combined into one move order.
- 6.5.3. Support orders with the same origin, destination, and supported player are combined into one support order.
- 6.5.4. Combined orders use the sum of their troop counts.

6.6. Normalization does not make an invalid troop count valid. If any submitted order uses a non-positive or non-integer troop count, the order package is invalid.

6.7. An order package is invalid if any universal condition is true:

- 6.7.1. Any referenced location does not exist.
- 6.7.2. Any referenced troop count is not a positive integer.
- 6.7.3. The package contains an order for the wrong phase.

6.8. A reinforcement order package is invalid if any reinforcement condition is true:

- 6.8.1. Any reinforced location is not a city controlled by the issuing player at the start of the reinforcement phase.
- 6.8.2. The sum of all troops in reinforcement orders is greater than the player's newly generated troops for the turn.

6.9. A movement order package is invalid if any movement condition is true:

- 6.9.1. Any move or support origin is not controlled by the issuing player.
- 6.9.2. Any move or support destination is not adjacent to its origin.
- 6.9.3. The sum of all troops moving out of any one origin, including both move orders and support orders, is greater than the troop count at that origin after reinforcement has been applied.

6.10. A movement order package is invalid if any support condition is true:

- 6.10.1. Any supported player does not exist, has been eliminated, or is the issuing player.
- 6.10.2. Any support order targets a location controlled by the issuing player.
- 6.10.3. The package contains both a move order and a support order targeting the same location.
- 6.10.4. The package contains support orders targeting the same location in support of different players.

6.11. Invalid order packages are rejected by the server; no part of that package is executed.

6.12. Valid order packages are accepted by the server according to the phase rules in section 4.

6.13. If a valid reinforcement order package allocates fewer troops than the player's newly generated troops, the remaining troops are allocated by the reinforcement default in rule 4.10.

## 7. Order Effects and Battles

7.1. Reinforcement orders have already increased troop counts before the movement phase begins.

7.2. Movement resolution occurs in this order:

- 7.2.1. Commit troops assigned to move orders and support orders.
- 7.2.2. Resolve road battles.
- 7.2.3. Move surviving arriving troops to their destinations.
- 7.2.4. Resolve destination battles.
- 7.2.5. Return surviving support troops to their origins.
- 7.2.6. Resolve support return battles.
- 7.2.7. Check capital loss.

7.3. When troops are committed, they leave their origin. Any troops not committed to move or support stay at their origin and defend it. A location may be emptied by committed orders and still remains controlled by its current controller unless a later battle or elimination changes control.

7.4. Defense bonuses are:

- 7.4.1. +2 if the location is the defending player's capital and that player still controls it.
- 7.4.2. +1 if the location is any other city controlled by the defending player.
- 7.4.3. +1 if the location is a city-state.
- 7.4.4. +0 if the location is a town.

7.5. A capital receives the +2 defense bonus only while it is controlled by its assigned player. If another player controls it, it is treated as a regular city for defense. If it becomes neutral, it is a city-state.

7.6. Defense bonuses absorb damage but never create troops.

7.7. Friendly redeployment is a move order into a location already controlled by the moving player. It is still normal movement: it can be damaged by hostile road battles, and surviving troops arrive before destination battles and join the local defender if hostile troops also arrive there.

7.8. Opposite-direction movement is not hostile when both orders are support orders and each order supports the controller of the other order's origin. In that case, both support groups pass without a road battle. All other opposite-direction movement by different players creates a road battle.

7.9. Road battles: after package normalization, if player P1 moves or supports X1 troops from A to B, and a different player P2 moves or supports X2 troops from B to A, and rule 7.8 does not exempt those orders, a *road battle* occurs in the middle of the road. In this battle, min(X1, X2) troops are destroyed for each side, and remaining troops, if any, continue their move or support motion.

### 7.10. Destination Battles

7.10.1. A *destination battle* happens at a location among arriving attacking troops, arriving support troops, and stationary troops there.

7.10.2. The *defending player* at location A is the player who controls A, if any.

7.10.3. A defensive faction exists at player-controlled location A only if the defending player has at least 1 troop participating in the battle. The defending player participates if they have at least 1 troop remaining at A or at least 1 troop arriving at A after road battles.

7.10.4. A defensive faction consists of the defending player as leader plus any support troops arriving at A in support of that defending player. Its strength is:

- defending player's troops remaining at A
- defending player's troops arriving at A
- support troops that join the defensive faction
- defense bonus at A

7.10.5. If the defending player has no participating troops, no defensive faction exists and no support troops can join it. Any defense bonus still contributes defense strength, but it is not a troop.

7.10.6. A city-state is a neutral defensive faction with strength 2: 1 neutral troop plus +1 defense bonus. Players cannot support city-states.

7.10.7. An *attacking player* at location A is a player who does not control A and has arriving non-support troops at A.

7.10.8. An attacking faction consists of the attacking player as leader plus any support troops arriving at A in support of that attacking player. Its strength is:

- attacking player's arriving non-support troops
- support troops that join the attacking faction

7.10.9. An attacking faction exists only if at least 1 troop of its leader arrives at A. If none do, that faction is ignored and its support troops do not participate in the destination battle.

7.10.10. The *casualty number* for the battle is the second-largest strength among the defensive strength and all attacking faction strengths.

7.10.11. Each faction with strength less than or equal to the casualty number loses all its troops in this battle. Therefore, at most one faction can survive.

7.10.12. If no faction survives, or if the defending faction survives, the location does not change control.

7.10.13. If an attacking faction survives and its leader has any troops remaining after casualty allocation, that leader becomes the controller of the location, and their surviving troops occupy it.

7.10.14. If an attacking faction survives but only support troops remain, control does not change. Surviving support troops return under rule 7.12.

7.10.15. An empty neutral town has defense strength 0. A single player moving troops into an empty neutral town captures it without casualties. If two or more players move troops into the same empty neutral town, they fight a destination battle there.

7.10.16. Support troops that survive road battles but do not join a destination battle still return to their origin under rule 7.12.

### 7.11. Casualty Allocation

7.11.1. If the casualty number is greater than or equal to a faction's strength, each troop in that faction is destroyed.

7.11.2. Otherwise, damage equal to the casualty number is allocated within the faction using this rule:

- 7.11.2.1. Defense bonuses absorb damage first, but never create troops.
- 7.11.2.2. Remaining damage is allocated among players in the faction proportionally to their troop participation, rounding down.
- 7.11.2.3. Any excess damage is allocated to the faction leader.
- 7.11.2.4. Any further excess damage is allocated round-robin among remaining supporting players and support groups.

7.11.3. The precise deterministic algorithms for proportional and round-robin casualty allocation are in Appendix A.

### 7.12. Support Return Battles

7.12.1. All surviving support troops return to their origin, regardless of whether they joined the destination battle and regardless of the battle outcome. Support troops can never occupy the supported location.

7.12.2. For a player P, let p[i], i=0..n-1 be the remaining troop counts returning to the same location A from their respective support orders. If location A was captured by another player Q that has q troops there, a support return battle occurs.

7.12.3. Let r = sum p[i]. Let the defense bonus at A be computed for Q. If r > q + defense bonus, location A is returned to P and will have r - q - defense bonus troops there. Otherwise, location A remains under Q control with q - max(0, r - defense bonus) troops there. Q might have 0 troops left after the support return battle resolves and still keep control of the location.

7.12.4. Support return battles are always duels between two players. A support return battle at origin A includes only P's support troops returning to A and Q's troops occupying A. If other players supported Q in its conquest of A and have remaining support troops, that support returns to its own origin and does not participate in the support return battle at A.

7.12.5. Return movement is never intercepted. Support return is not a new movement order and does not create road battles.

### 7.13. Capital Loss

7.13.1. After road battles, destination battles, and support return battles are complete, the server checks capital loss simultaneously for all players who were alive at the start of the check.

7.13.2. A capital is captured only if it is controlled by another player at the time of this check. Reducing a capital to 0 troops does not eliminate its owner if control did not change.

7.13.3. If every player alive at the start of the check would lose their capital in the same turn, the game ends and those players are ranked and scored by rules 3.6-3.12. In this all-player-loss branch, players are not eliminated and their locations are not neutralized before scoring or the after-game report.

7.13.4. Otherwise, all players whose capitals are controlled by another player are eliminated simultaneously. When a player is eliminated, all of that player's remaining troops are removed from the board. Locations controlled by eliminated players become neutral with 0 troops. Any city made neutral this way becomes a city-state.

7.13.5. If exactly one player remains after capital loss is resolved, that player wins immediately and no further order-resolution steps occur.

## 8. Visibility and Reports

8.1. Each player has full visibility into locations they control and locations 1 step away from locations they control.

8.2. Each player has partial visibility into locations 2 steps away from locations they control.

8.3. Locations 3 or more steps away from all locations a player controls are hidden by fog of war.

8.4. At the start of each reinforcement phase, each active player receives a private reinforcement report containing:

- number of reinforcements available
- list of cities they control, with reported location type and troop count
- reinforcement phase clock

8.5. After the reinforcement phase is resolved and before the movement phase begins, each active player receives a visibility report based on the post-reinforcement map state. This report contains:

- list of their controlled locations, with reported location type and troop count
- list of adjacent locations, with controller, reported location type, and troop count
- controller and reported location type of locations 2 steps away
- connectivity graph: for each location the player controls and for each adjacent location, list of all connected locations
- movement phase clock

8.6. The connectivity graph does not include connectivity between two locations that are only 2 steps away from the player, unless those locations are also visible by another rule.

8.7. Players receive full battle reports only for battles they participate in.

8.8. For a road battle, participating players receive the road, the movement or support groups involved, starting troop counts, destroyed troop counts, and remaining troop counts. Road battle reports do not include a location-control result.

8.9. For a destination battle, participating players receive, for each player P in the battle:

- P's role: attacker, defender, or supporting another player Q
- starting troop count p1 and remaining troop count p2
- status of the battle: who controls the location and how many troops are left there

8.10. For a support return battle, participating players receive the origin, the returning player, the occupying player, returning troop count, occupying troop count before the battle, defensive bonus used, final controller, and final troop count.

8.11. Players do not automatically get the details of support return battles they do not participate in. They might only learn the results of those battles through visibility reports before the start of their next turn.

## 9. After-Game Reports

9.1. After the game is over, either due to number of turns or player elimination, the server makes a full game log available to each participant. It includes the full state of the game after each turn, the full set of order packages received during each phase, final placement ranks, final board scores where used for ranking or survivor score share, and match points awarded.

9.2. Communications between players are not revealed and remain hidden.

## Appendix A. Casualty Allocation Algorithms

A.1. Proportional casualty allocation uses this algorithm:

    # A - battle location
    # S[0] - the troop count of the faction leader
    # S[i], i = 1..n - the troop count of each supporting player in the faction
    # casualty - the casualty number for this faction
    #
    # Step 1. Defense bonus absorbs damage.
    defending_bonus =
      if this faction is the defender and A is the defender's capital, 2
      otherwise if this faction is the defender and A is a city, 1
      otherwise 0
    casualty = max(0, casualty - defending_bonus)
    if casualty == 0 or sum S[i] == 0: stop
    # Step 2. Allocate initial damage proportionally to each player.
    troop_total = sum S[i]
    casualty_share[i] = floor(S[i] * casualty / troop_total) for i=0..n
    S[i] = S[i] - casualty_share[i] for i=0..n
    casualty = casualty - sum casualty_share[i] for i=0..n
    # Step 3. Allocate overflow to the faction leader.
    leader_loss = min(casualty, S[0])
    S[0] = S[0] - leader_loss
    casualty = casualty - leader_loss
    # Step 4. If there is still casualty overflow, allocate it using A.2.

A.2. Round-robin casualty allocation: if damage X needs to be applied to troop counts C[i], where sum C[i] >= X, use this algorithm:

    while X > 0:
      # let o[i], i=0..m-1 be the ordering of indexes with C[i] > 0,
      # going from largest C[i] value to smallest:
      # C[o[0]] >= C[o[1]] >= ... >= C[o[m-1]]
      # if there are ties between C[i] and C[j], use canonical order:
      # player order first, then origin location order when needed
      for j=0..m-1 while X > 0:
        C[o[j]] = C[o[j]] - 1
        X = X - 1

A.3. If a supporting player has more than one troop group contributing to support, damage assigned to that player is applied to the troop groups using the round-robin procedure in A.2.

## Appendix B. Examples and Notes

B.1. Support-only attacking faction: if player A attacks a location with 1 troop and supporters contribute 5 troops, the faction strength is 6. If A's own troop is destroyed and only support troops remain, A does not capture the location. The support troops return to their origins.

B.2. Empty neutral town: an empty neutral town has defense strength 0. One player entering it captures it without losses. Multiple players entering it fight each other there.

B.3. Support return recapture: if P sends support away from A, Q captures A, and P's support survives and returns, P and Q fight a support return battle at A. Other support troops that helped Q capture A do not defend A during that support return battle.

B.4. All-capitals-fall scoring: if every player alive at the start of capital loss check has their capital controlled by another player, the game ends and those players are ranked before eliminated-player cleanup. Board score is used to rank non-surviving players in the same capital loss check, but non-surviving players do not receive survivor score-share points.

B.5. Opposite defensive support: if P1 supports P2's defense of B by moving support troops from A to B, while P2 supports P1's defense of A by moving support troops from B to A, the two support groups pass without a road battle. This is the only opposite-direction movement that is treated as non-hostile between different players.

## Appendix C. Match Point Formula and Examples

C.1. Let N be the number of players at setup. Let T be the total match-point pool:

    T = 10 x N

C.2. If at least one player is surviving at game end:

    placement pool = T / 2
    survivor score-share pool = T / 2

If no player is surviving at game end:

    placement pool = T
    survivor score-share pool = 0

C.3. Placement points are allocated from the placement pool by descending rank weights. Rank 1 has weight N, rank 2 has weight N - 1, rank 3 has weight N - 2, and so on. The total placement weight is:

    N x (N + 1) / 2

For an untied player at rank R:

    placement points = placement pool x (N - R + 1) / (N x (N + 1) / 2)

C.4. If players are tied across multiple placement ranks, each tied player receives the average of the placement points for the tied ranks. The tied block occupies those ranks, and the next player receives the next unoccupied rank.

C.5. Survivor score-share points are allocated only to surviving players. If S is the sum of board scores for surviving players at game end, surviving player P receives:

    survivor score-share points = survivor score-share pool x P's score / S

Non-surviving players receive 0 survivor score-share points.

C.6. Example: five players start, three survive, and two were eliminated earlier. The total match-point pool is 50. The placement pool is 25 and the survivor score-share pool is 25.

| Player | Result | Rank | Final board score | Placement points | Score-share points | Total |
|---|---|---:|---:|---:|---:|---:|
| A | surviving | 1 | 18 | 8.33 | 10.47 | 18.80 |
| B | surviving | 2 | 15 | 6.67 | 8.72 | 15.39 |
| C | surviving | 3 | 10 | 5.00 | 5.81 | 10.81 |
| D | eliminated on turn 16 | 4 | not used | 3.33 | 0.00 | 3.33 |
| E | eliminated on turn 9 | 5 | not used | 1.67 | 0.00 | 1.67 |

C.7. Example: five players start and all lose their capitals in the same capital loss check. The total match-point pool is 50. There are no surviving players, so the full 50 points are allocated by placement. Board score before eliminated-player cleanup is used only to rank the simultaneous collapse.

| Player | Pre-cleanup board score | Rank | Placement points | Score-share points | Total |
|---|---:|---:|---:|---:|---:|
| A | 17 | 1 | 16.67 | 0.00 | 16.67 |
| B | 15 | 2 | 13.33 | 0.00 | 13.33 |
| C | 12 | 3 | 10.00 | 0.00 | 10.00 |
| D | 8 | tied 4 | 5.00 | 0.00 | 5.00 |
| E | 8 | tied 4 | 5.00 | 0.00 | 5.00 |
