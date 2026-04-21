# PKO bounty sidecar spec

Use a sidecar file when the raw hand history does not expose displayed bounty values directly.

## Recommended location

Store sidecars under:

`data/hand_histories/metadata/`

## Preferred file names

1. Exact raw-file match

`<raw-file-stem>.pko.json`

Example:

`GG20260307-1653 - WSOP-SC 54 Bounty Hunters Circuit Edition.pko.json`

2. Tournament fallback

`tournament_<tournament_id>.pko.json`

Example:

`tournament_267745786.pko.json`

## Minimal schema

```json
{
  "version": 1,
  "format": "PKO",
  "tournament_id": "267745786",
  "starting_bounty_cash": 27,
  "future_discount": 0.5,
  "hero": {
    "name": "Hero",
    "displayed_bounty_cash": 27
  },
  "defaults": {
    "displayed_bounty_cash": 27
  },
  "players": {
    "95c51fa7": {
      "displayed_bounty_cash": 54
    },
    "65ce5cd1": {
      "displayed_bounty_cash": 40.5
    }
  }
}
```

## Field meanings

- `version`: schema version, start with `1`
- `format`: should be `PKO`
- `tournament_id`: match the id from the hand-history header
- `starting_bounty_cash`: required cash value for the starting bounty
- `future_discount`: optional, default `0.5`
- `hero.displayed_bounty_cash`: optional current Hero bounty
- `defaults.displayed_bounty_cash`: optional fallback for unknown players, often the starting bounty early in the event
- `players.<name>.displayed_bounty_cash`: displayed bounty for a specific player name as it appears in the hand history

## Lookup rules

1. Parse the raw hand-history file and extract:
   - raw file stem
   - tournament id
   - player names
2. Look for an exact sidecar first:
   - `data/hand_histories/metadata/<raw-file-stem>.pko.json`
3. If not found, look for tournament fallback:
   - `data/hand_histories/metadata/tournament_<tournament_id>.pko.json`
4. Read `starting_bounty_cash` from the sidecar
5. Read `future_discount` from the sidecar, else use `0.5`
6. For a target villain, resolve bounty in this order:
   - `players[target_name].displayed_bounty_cash`
   - `defaults.displayed_bounty_cash`
   - no value
7. For Hero, resolve bounty in this order:
   - `hero.displayed_bounty_cash`
   - `defaults.displayed_bounty_cash`
   - no value
8. Starting stack should still come from the earliest chronological Hero hand in the raw file, not from the sidecar

## Design notes

- Keep the sidecar as bounty metadata only
- Do not duplicate blind levels or starting stack there unless truly needed
- Use the exact player labels from the hand history, including anonymized GG ids
- If a bounty is unknown, leave it missing instead of inventing a number

## Resolver helpers now present in code

`code/scripts/hand_parser.py` now includes:

- `load_pko_bounty_sidecar(input_path, raw_text=None)`
- `resolve_pko_displayed_bounty_cash(sidecar, player_name, hero_name="Hero")`
- `build_pko_bounty_inputs(input_path, raw_text, hero_name="Hero", target_name=None)`

These load the sidecar, resolve Hero or villain displayed bounty values, and package the current PKO inputs.

The parser now uses them only in bounded PKO call-vs-shove spots where bounty EV is actually relevant, so normal non-bounty outputs stay clean.

## Recommended first implementation scope

- sidecar lookup only
- no scraping
- no OCR
- no automatic inference of displayed bounties from title text alone

That keeps the parser honest and makes later automation optional, not required.
