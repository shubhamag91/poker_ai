# Tournament archetype heuristic

The parser now adds a short `Approx stage/ICM` note when it has enough structure signals to say something useful without pretending precision.

## Inputs used

- GG Poker tournament header
- bounty / PKO keywords from the title line when present
- 8-max format
- buy-in from the title line
- tournament level
- blind and ante structure
- current table stack texture in BB
- optional tournament summary sidecar, primarily total entrants and a matching finish place when available

## What it tries to infer

- broad stage band: early-field, middle stages, late-field, very late
- field-size-aware caps so large and massive tournaments do not get treated like final-table spots too early
- rough ICM pressure: low, low-medium, medium, medium-high, high
- whether short-stack survival should matter more than pure chip EV
- a light bounded nudge for close preflop jam, reshove, and thin call-off spots

## Limitations

- It does **not** know exact players left, payout jumps, or the real bubble/final-table state. Even with a summary file, it only uses safe signals like total entrants and a lower bound from Hero's later finish place.
- It uses broad GG 8-max nightly archetypes, so the note is a banded estimate, not a precise read.
- Table stack texture can hint at pressure, but one table does not represent the full tournament.
- In bounty formats, title-based bounty detection slightly softens pure survival-pressure reads when the table texture alone would otherwise push the band upward.
- The nudge is intentionally light. It should tighten only marginal preflop decisions, not override clear push-fold fundamentals or obvious strong continues.
