# poker_ai Session Context
# Auto-managed by opencode agent
# Last updated: 2026-04-22

## Current Milestone
**Milestone B: ICM-aware preflop benchmark** — Completed

## Project Status
- Linear project: https://linear.app/mose/project/poker-ai-e33721cdc012/overview
- GitHub: https://github.com/shubhamag91/poker_ai

## Milestone History

### Milestone A (Completed 2026-04-22)
- Built tournament archetype lookup table
- New module: code/scripts/tournament_context.py
- Lookup data: docs/tournament_archetype_lookup.json
- Parser enriched with paid seats, ITM%, cluster tags
- 125/150 summaries parsed (83% coverage)
- 67 unique tournament archetypes, 25 cluster tags
- ITM model: 15% of field (GG standard)

### Milestone B (Completed 2026-04-22)
- ICM-aware preflop benchmark
- Baseline module: code/scripts/preflop_baseline.py
- B1: Open-jam baselines (21 spots)
- B2: Call-off & reshove baselines (50 spots)
- B3: PKO-adjust preflop baseline

### Milestones C-E (Backlog)
- C: Postflop tendency deepening
- D: Leak prioritization engine
- E: Study products and workflow

## Key Context
- Parser entry: code/scripts/hand_parser.py
- Summary root: data/hand_histories/summaries/
- Parsed output: data/hand_histories/parsed/
- Raw HH: data/hand_histories/raw/
- Lookup table: docs/tournament_archetype_lookup.json
- PKO sidecar: data/hand_histories/metadata/*.pko.json

## Full Corpus Run (2026-04-22)

### All Reports Executed
- Raw files: 200
- Parsed files: 156
- All reports run on full corpus

### Reports Working
| Report | Hands Tracked |
|--------|--------------|
| postflop_hero_flop_actions | 1511 |
| postflop_hero_deeper_actions | 911 turn, 582 river |
| postflop_size_patterns | 423 bet sizes (NEW) |
| leak_prioritization | 247 total leaks |
| preflop_baseline | 50 spots |

### NEW: Postflop Size Patterns
- code/scripts/report_postflop_size_patterns.py (NEW)
- Tracks: bet sizes (small/medium/large/overbet)
- Tracks: delayed cbets (check flop → bet turn/river)
- Tracks: donk leads, probe lines
- Output: data/hand_histories/postflop_size_patterns/

### NEW: Study CLI Commands
- study_cli.py updated with temporal features:
  - weekly: weekly summary report
  - compare: period-over-period comparison
  - progress: leak priority tracking

## Gap Map Remaining
- Section 4 (Deeper frequency layers): DONE
- Section 5 (Study workflow UX): DONE
- Full corpus covered (200 raw / 156 parsed)

## Next Session Plan
- Refine baselines with more HH data
- Add more ICM context to deeper streets
- Continue study workflow features
- Wait for more HH data to improve statistical confidence

## Session Workflow
1. Read SESSION.md at start
2. Check Linear for current milestone issues
3. Pick next 1-2 sub-issues
4. Implement + test
5. Update Linear
6. Write SESSION.md at end

(End of file - total 93 lines)