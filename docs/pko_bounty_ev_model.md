# PKO bounty EV model

`code/scripts/hand_parser.py` now includes a compact PKO bounty conversion helper:

- `compute_pko_bounty_ev(starting_stack_chips, starting_bounty_cash, target_displayed_bounty_cash, current_big_blind, future_discount=0.5)`

Inputs:

- `S = starting_stack_chips`
- `B0 = starting_bounty_cash`
- `Bt = target_displayed_bounty_cash`
- `bb = current_big_blind`
- `d = future_discount`

Formulas:

- `immediate_cash = 0.5 * Bt`
- `future_cash_equiv = d * 0.5 * Bt`
- `total_effective_cash = immediate_cash + future_cash_equiv`
- `total_bounty_chips = total_effective_cash * (S / B0)`
- `immediate_bounty_bb = (immediate_cash * (S / B0)) / bb`
- `future_bounty_bb = (future_cash_equiv * (S / B0)) / bb`
- `total_bounty_bb = immediate_bounty_bb + future_bounty_bb`
- `bounty_ratio = Bt / B0`

The helper returns all of those values in a small dictionary and returns `None` when the required inputs are missing or non-positive.

For the recommended bounty-metadata workflow, see `docs/pko_bounty_sidecar_spec.md`.

## Starting stack derivation rule

`derive_starting_stack_from_hero_hands(raw_text, hero_name)` scans the raw hand-history text, finds Hero hands with a visible seat stack, and uses the earliest chronological Hero hand, not the first hand block in the file.

That matters because exported hand-history files can be reverse-ordered. If timestamps are missing, the helper falls back to the first Hero stack it can find.
