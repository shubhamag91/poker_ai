# poker_ai — Agent Instructions

## Session Start Protocol

At the **start of every session**:

1. Read `SESSION.md` — this is your context file
2. Check Linear for the current milestone's issues: `npx @schpet/linear-cli issue query --team MOS --no-pager | grep milestone`
3. Pick the next 1-2 open sub-issues to tackle
4. Start implementing — do NOT start multiple milestones at once

At the **end of every session**:

1. Run `python3 code/scripts/update_session_context.py` — interactive update
2. Update Linear: comment on completed issues, close done ones
3. Verbally summarize progress to the user

## Current Milestone
Milestone B: ICM-aware preflop benchmark

## Linear Quick Commands

```bash
# List current milestone issues
npx @schpet/linear-cli issue query --team MOS | grep milestone

# Start an issue
npx @schpet/linear-cli issue start <id>

# View an issue
npx @schpet/linear-cli issue view <id>

# Close an issue
npx @schpet/linear-cli issue update <id> --state Completed
```

## Project Structure

```
code/scripts/hand_parser.py        — main parser + analysis
code/scripts/tournament_context.py — ICM context module (Milestone A)
code/scripts/postflop_trees.py      — postflop tree specs
code/scripts/update_session_context.py — session updater

docs/tournament_archetype_lookup.json — tournament lookup table
docs/final_direction_gap_map.md — full project plan

data/hand_histories/summaries/  — tournament summaries
data/hand_histories/parsed/   — parsed outputs
data/hand_histories/raw/       — raw hand histories
data/hand_histories/metadata/   — PKO sidecars
```

## Key Conventions

- **Do not commit** without asking the user
- **Test before closing** Linear issues — run the parser on a real HH file
- **One milestone at a time** — context overflows otherwise
- **Update SESSION.md** at the end of every session
- Use the Linear CLI for all issue management

## Milestone Order
A → B → C → D → E

## Testing
```bash
# Quick test of parser
python3 code/scripts/hand_parser.py --input "data/hand_histories/raw/<file>.txt" --limit 1

# Update session context
python3 code/scripts/update_session_context.py
```