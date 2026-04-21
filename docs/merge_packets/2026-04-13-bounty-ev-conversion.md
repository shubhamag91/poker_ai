# Merge packet: bounty-ev-conversion

## Thread goal
Build a PKO bounty-to-EV conversion workflow that:
- uses immediate plus discounted future bounty value
- derives starting stack from the hand history when possible
- avoids fake precision
- stays separate from the main output flow until the bounty source is nailed down

## Decisions made

1. **PKO model**
   - Use immediate plus discounted future value
   - Formula lives in `compute_pko_bounty_ev(...)`
   - Default `future_discount = 0.5`

2. **Starting stack source**
   - Derive starting stack from the **earliest chronological Hero hand**
   - Do not trust the top block in the file, because exports can be reverse-ordered

3. **Bounty source**
   - GG raw hand histories do **not** expose reliable per-player displayed bounty values
   - So `starting_stack` can come from HH, but `starting_bounty_cash` and `target_displayed_bounty_cash` need external metadata
   - Chosen workflow: **sidecar metadata files**

4. **Bounded integration rule**
   - PKO bounty EV is now wired into the rule layer only for:
     - bounty-format hands
     - `call_or_fold_vs_shove` spots
     - a clear prior all-in actor
   - Non-bounty and non-relevant spots stay clean

## Files changed

- `code/scripts/hand_parser.py`
- `docs/pko_bounty_ev_model.md`
- `docs/pko_bounty_sidecar_spec.md`
- `data/hand_histories/metadata/GG20260307-1653 - WSOP-SC 54 Bounty Hunters Circuit Edition.pko.json`
- `tmp/find_bounty_call_vs_shove.py`

## What was added

### In `hand_parser.py`
- `extract_hand_timestamp(hand)`
- `derive_starting_stack_from_hero_hands(raw_text, hero_name)`
- `compute_pko_bounty_ev(...)`
- `load_pko_bounty_sidecar(...)`
- `resolve_pko_displayed_bounty_cash(...)`
- `build_pko_bounty_inputs(...)`
- `last_prior_all_in_actor(...)`
- `build_pko_bounty_profile(...)`

### In docs
- PKO EV model doc
- PKO sidecar spec with lookup rules and sample schema

### In metadata
- Sample sidecar for the WSOP-SC bounty file

## Verification done

1. **Parser regression check**
   - `python3 code/scripts/hand_parser.py`
   - Still parsed 180 hands and wrote 10 analyzed spots on the default GG file

2. **PKO sidecar resolution check**
   - Sample WSOP-SC sidecar resolves to:
     - `starting_stack_chips = 25000`
     - `starting_bounty_cash = 27`
     - `target_displayed_bounty_cash = 54`
     - `future_discount = 0.5`
   - Example conversion at `bb = 1200`:
     - `total_bounty_bb = 31.25 BB`

3. **Real bounty spot scan**
   - Scanned raw bounty hand histories
   - Found **304** real Hero `call_or_fold_vs_shove` spots
   - Current blocker: those files do not yet have real villain displayed bounty values attached

## Current blocker
A true end-to-end PKO test on a real hand is still blocked by missing real villain displayed bounty data.

The code path is ready.
The raw call-vs-shove spots exist.
What is missing is one real `Bt` input for a real hand.

## Suggested next step
Use one real candidate hand, add actual bounty values to a sidecar, and run the full spot.

Recommended candidate:
- file: `GG20260118-1720 - Bounty Hunters Sunday Special 5.40.txt`
- hand: `Poker Hand #TM5481750165`
- target villain: `dc0ed9e3`

## Short merge summary
Built the first PKO bounty EV foundation.

- Added immediate-plus-discounted-future PKO conversion
- Derive starting stack from earliest chronological Hero hand
- Confirmed GG raw HH does not reliably provide displayed bounty values
- Added sidecar metadata spec and loader/resolver path
- Wired PKO notes into bounded bounty call-vs-shove rule-layer spots only
- Verified normal parser flow still works
- Found many real candidate bounty spots, but end-to-end testing is still blocked on actual villain bounty values

## Discord-ready handoff
Built the first PKO bounty EV foundation for `poker_ai`. We now convert PKO bounty value using immediate plus discounted future value, derive starting stack from the earliest chronological Hero hand, and use sidecar metadata for displayed bounty values because GG raw HH does not reliably expose them. The loader/resolver path is in place and PKO notes are wired into bounded bounty call-vs-shove rule-layer spots only, so normal outputs stay clean. Normal parser flow still works. We also scanned the bounty files and found 304 real Hero call-vs-shove spots, but full real-hand testing is still blocked on actual villain displayed bounty values.
