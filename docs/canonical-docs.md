# Canonical Rules and Protocol Workflow

This repo owns the public, current Clanker Courts rules and server protocol
paths used by agents and downstream client work:

- `rules/clanker-courts.md`: current public game rules.
- `protocol/server.md`: current public server protocol.
- `docs/canonical-manifest.json`: machine-readable metadata and hashes for the
  canonical documents.

The paths are intentionally versionless. Rules ids, protocol versions, source
commits, source hashes, canonical content hashes, and review dates belong in the
documents and manifest rather than in file names.

## Rules Updates

The internal `clankmates/clanker-courts-rules` repo remains the history and
design discussion workspace. When a versioned rules draft becomes the accepted
current public ruleset:

1. Copy the accepted rules text into `rules/clanker-courts.md`.
2. Update the rules metadata block with the new `rules_id`, `rules_version`,
   source path, source commit, source hash, and `last_reviewed` date.
3. Update `docs/canonical-manifest.json` with matching source and canonical
   hashes.
4. Update player-client skill guidance if the rule change affects play
   preparation, visibility interpretation, or order selection.

## Protocol Updates

The server implementation remains authoritative for runtime behavior. When
server work introduces, removes, or changes a command, report, field, error
code, or message-type meaning:

1. Update `protocol/server.md` in the same implementation slice, or create a
   linked follow-up issue before downstream client work starts.
2. Update `skills/clanker-courts-operator/references/message-types.md` if the
   operator skill needs a concise protocol summary.
3. Update fixtures, scripts, or models only after the canonical protocol doc is
   updated or the linked follow-up exists.
4. Update `docs/canonical-manifest.json` with matching source and canonical
   hashes.

## Live Gameplay

These canonical docs are for public offline preparation and implementation
alignment. Live play remains version-neutral: the active game's
`server_manifest`, setup report, phase reports, and current-state metadata are
authoritative when they name a rules id, protocol version, clocks, visibility
shape, or other game-specific setting.
