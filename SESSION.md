# poker_ai Session Context

## Session Date
2026-04-29

## Current Status
**All milestones complete! Backlog empty.**

---

## Today's Progress (2026-04-29)

### Milestones Completed
- **D**: Leak Prioritization (D.1, D.2, D.3)
- **E**: Study Products (E.1, E.2, E.3)
- **F**: Calibrated EV (F.1, F.2, F.3)
- **G**: Knowledge Integration (G.1, G.2, G.3)

### Issues Closed
- MOS-9, MOS-18: 4-plus player buckets (deferred)
- MOS-22: Evaluation loop (already done)
- MOS-23: Feature extraction (new module)
- MOS-24: Leak analysis tooling (already done)

### New Scripts Added
- `confidence.py` - Wilson CI + tier logic
- `export_study_packet.py` - Study packet exporter
- `export_weekly_digest.py` - Weekly leak digest
- `showdown_ev.py` - Showdown EV with equity estimation
- `ev_prior_replacer.py` - EV prior replacer
- `tag_articles.py` - Article node tagger
- `extract_features.py` - Feature extraction
- `prompts/preflop_analysis_v1.json` - Prompt schema

### Bug Fixes
- tag_articles.py: Skip non-poker .md files, warn on empty index
- postflop_baseline.py: Added note about DONK_LEAD_BASELINES
- leak_v2_calibration.md: Added coverage section

---

## Linear Status
- All issues Done
- Backlog: 0 issues
- Only pending: Milestone H (data-gated)

---

## Key Files
| File | Purpose |
|------|---------|
| hand_parser.py | Main parser |
| preflop_baseline.py | Preflop baselines |
| postflop_baseline.py | Postflop baselines |
| confidence.py | Wilson CI + tier |
| report_leak_prioritization.py | Leak ranking |
| study_cli.py | CLI tool |

---

## Data-Gated Items (Need More HH Data)
- Milestone H: Long-term analytics
- Pot odds / implied odds features
- True equity (currently heuristic)
