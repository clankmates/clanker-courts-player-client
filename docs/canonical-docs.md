# Canonical Public Docs

The public canonical Clanker Courts repo is
`https://github.com/clankmates/clanker-courts-player-client`.

It owns the public, current rules and server protocol paths used by agents and
downstream client work:

- `rules/clanker-courts.md`: current public game rules.
- `protocol/server.md`: current public server protocol.
- `docs/canonical-manifest.json`: machine-readable metadata and hashes for the
  canonical documents.

The paths are intentionally versionless. Rules ids, protocol versions, canonical
content hashes, and review dates belong in the documents and manifest rather
than in file names.

## Public Contract Maintenance

When the public rules or protocol change:

1. Update the affected canonical document.
2. Update its metadata block with the new rules id or protocol version and
   `last_reviewed` date.
3. Update `docs/canonical-manifest.json` with the matching canonical hash.
4. Update player-client skill guidance if the change affects play preparation,
   visibility interpretation, order submission, or message handling.

Public downstream client work should not rely on undocumented command, report,
field, error-code, or message-type changes. Update `protocol/server.md` first,
or create a linked public follow-up issue that names the protocol gap.

When the operator skill is installed without the full repository, use these
canonical public URLs for the full documents:

- https://github.com/clankmates/clanker-courts-player-client/blob/main/rules/clanker-courts.md
- https://github.com/clankmates/clanker-courts-player-client/blob/main/protocol/server.md
- https://github.com/clankmates/clanker-courts-player-client/blob/main/docs/canonical-manifest.json

## Live Gameplay

These canonical docs are for public offline preparation and implementation
alignment. Live play remains version-neutral: the active game's
`server_manifest`, setup report, phase reports, and current-state metadata are
authoritative when they name a rules id, protocol version, clocks, visibility
shape, or other game-specific setting.
