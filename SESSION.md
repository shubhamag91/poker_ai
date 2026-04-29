# poker_ai Session Context
# Auto-managed by opencode agent
# Last updated: 2026-04-29

## Current Milestone
**Milestone G: Knowledge Integration** — Completed

## Project Status

## Completed Today (2026-04-29)
- D: Leak prioritization (D.1, D.2, D.3)
- E: Study products (E.1, E.2, E.3)
- F: Calibrated EV (F.1, F.2, F.3)
- G: Knowledge integration (G.1, G.2, G.3)

## Key Context

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

### Milestone C (Completed 2026-04-29)
- C.1: postflop_baseline.py — 45 spots (cbet/donk/probe)
- C.2: Postflop evaluator in leak report (13 flop leaks)
- C.3: Turn/river baselines (15 turn + 8 river) + extractor
- Total: 533 leaks in ranking (491 preflop + 42 postflop)

### Milestone D (Completed 2026-04-29)
- D.1: Wire preflop_baseline into leak report + Wilson CI
- D.2: LLM↔baseline calibration (dual eval adds verdict_source, rule_verdict)
- D.3: Shared confidence.py + wired into all reports
- No parser/baseline corrections needed (aligned)
- Confidence tier: high≥20 / medium≥8 / low<8

### Milestone E (Completed 2026-04-29)
- E.1: Study packet exporter (export_study_packet.py)
- E.2: Weekly leak digest (export_weekly_digest.py)
- E.3: study_cli filter command

### Milestone F (Completed 2026-04-29)
- F.1: Showdown EV skeleton (data-gated)
- F.2: EV prior replacer (ev_prior_replacer.py)
- F.3: EV trends in weekly digest

### Milestone G (Completed 2026-04-29)
- G.1: Article node tagger (tag_articles.py)
- G.2: Snippet attachment in study packets
- G.3: Prompt standardization (prompts/ + prompt_version in JSON)

### Phase 0 (Completed 2026-04-29)
- MOS-55: Foundational parser fixes
- MOS-56: call_vs_shove / fold_vs_shove split
- MOS-57: JSON sidecar emission

### Milestone H (Backlog)
- Long-term self-tendency analytics (data-gated)

## Project Status
- Linear project: https://linear.app/mose/project/poker_ai-e33721cdc012/overview
- GitHub: https://github.com/shubhamag91/poker_ai

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