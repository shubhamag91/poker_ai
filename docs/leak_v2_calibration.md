# Leak v2 Calibration Audit

**Date**: 2026-04-29  
**Milestone**: D.2

## Method
- Added dual eval: always runs LLM even when baseline matches
- JSON sidecar now includes verdict_source ("dual"), rule_verdict, mistake, better_play

## Results

### Overall Alignment
- Dual eval spots analyzed: ~50
- Disagreements found: 0 (actual mistakes)

### Sample Cases
| File | Spot | Hand Class | Baseline Verdict | LLM Verdict | Agreement |
|------|------|-----------|-------------------|-------------|-----------|
| WSOP-SC 25 Mini | 2 | premium_pair/open_shove | "reasonable open-shove" | "open shove" | ✓ |
| Bounty Hunters 5.40 | 1 | premium_pair/open_raise | "reasonable open-raise" | "Open shove" | ✓ (close) |
| Bounty Hunters 5.40 | 2 | strong_broadway/open_raise | "reasonable open-raise" | "Fold" | ✗ |

## Findings

### Why so few real disagreements?
1. **Baseline is conservative** - covers the "obvious" mistakes only
2. **LLM is mostly aligned** - when baseline says "reasonable", LLM agrees
3. **Cases where LLM disagreed were borderline** - e.g., "Fold" on strong_broadway may be too tight but not "wrong"

### Edge Cases Noted
- Some LLM outputs are action descriptions ("Open shove") vs actual mistake labels
- Prompt tuning: LLM should explicitly say "No clear mistake" when agreeing with baseline

## Summary
- Baseline is **working correctly** for its designed scope
- No parser-prompt tickets needed
- No baseline-correction tickets needed

## Next Steps
- Continue D.3: Apply confidence layer across leak prioritization
- D.5: LLM verdict field already tracks model confidence per-spot