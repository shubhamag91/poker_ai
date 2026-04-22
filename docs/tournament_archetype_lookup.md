# Tournament Archetype Lookup

A lookup table mapping tournament names → ICM context (paid seats, ITM%, bubble ratio).

## Purpose

Without an exact GG Poker API, the system derives tournament context from known archetype structures. Each entry maps a tournament name to its field-size band, estimated paid seats, and ITM percentage.

## Source

Parsed from 125 tournament summaries in `data/hand_histories/summaries/`. Covers all USD-denominated tournaments. Yen (APL series) tournaments are excluded pending currency handling.

## Schema

```json
{
  "version": 1,
  "description": "...",
  "source": "data/hand_histories/summaries/*.txt",
  "total_summaries": 125,
  "paid_seats_lookup": { "9": 3, "27": 5, ... },
  "clusters": [
    {
      "cluster": "PKO",
      "tournament_name": "Bounty Hunters Sunday Special $10.80, Hold'em No Limit",
      "count": 7,
      "players_range": "8772-16865",
      "buyin_range": "10.80",
      "avg_prize_per_player": 9.94,
      "estimated_paid_seats": 300,
      "itm_pct": 2.0
    },
    ...
  ],
  "cluster_summary": {
    "PKO": { "instances": 33, "unique_archetypes": 14, ... },
    ...
  }
}
```

## Cluster Tags

| Tag | Matches |
|-----|---------|
| PKO | Bounty Hunters, Bounty |
| WSOP_SC | WSOP-SC, WSOP Circuit |
| GGMasters | GGMasters, GGM |
| Satellite | Satellite |
| 7max | 7-Max |
| Hyper | Hyper |
| Monster | Monster |
| Grand_Prix | GRAND-PRIX, Grand Prix |
| Fifty | Fifty, 50 Stack |
| Mini | Mini |
| Mega | MEGA |
| Marathon | Marathon |
| Daily | Daily |

## ITM Model

GG Poker typically pays ~15% of the field across tournament sizes. Paid seats are computed as `max(round(n * 0.15), paid_seats_ladder_floor)` so the model stays anchored to GG's actual structure while respecting minimums for small fields.

| Players | Paid | ITM% |
|--------|------|------|
| 9 | 3 | 33% |
| 100 | 15 | 15% |
| 500 | 75 | 15% |
| 1,000 | 150 | 15% |
| 5,000 | 750 | 15% |
| 10,000 | 1,500 | 15% |
| 15,000 | 2,250 | 15% |
| 20,000 | 3,000 | 15% |

## Coverage

- **125/150** summaries parsed (83%)
- **67** unique tournament archetypes
- **25** cluster tags
- **~14** distinct buy-in levels
- **5,000–25,000** player field range for large events

## Usage

```python
from tournament_context import enrich_tournament_summary, lookup_archetype_by_name, paid_seats_for_field_size

# Enrich a summary dict
enriched = enrich_tournament_summary(raw_summary, tournament_name)

# Direct lookup
arch = lookup_archetype_by_name("Bounty Hunters Sunday Special $10.80, Hold'em No Limit")
# → {"cluster": "PKO", "estimated_paid_seats": 300, "itm_pct": 2.0, ...}

# Field-size estimate
paid = paid_seats_for_field_size(10000)  # → 200
```

## Limitations

- Paid seats are **estimates** based on GG field-size bands, not exact payout tables
- Yen-denominated tournaments (APL series) not yet covered
- One-time snapshot — new tournament formats need to be added manually
- PKO knockout EV still needs per-tournament bounty metadata from `.pko.json` sidecars

## Maintenance

When new tournament summaries are added, re-run `parse_summaries.py` and `build_lookup.py` to update the lookup table. The parser automatically uses the latest lookup table on each run.