# poker_ai — Project Plan (v2)

_Replaces `docs/project_plan.md`. Last revised: 2026-04-29._

## Where we are

The project is a personal MTT study engine built on hand-history parsing, postflop spot tagging, and frequency reporting. Milestones A (tournament archetype lookup, ICM context module) and B (ICM-aware preflop benchmark with 71 spots across open-jam, call-off, and reshove baselines) are complete. The current corpus is 200 raw / 156 parsed hands, with 1,511 tracked postflop spots, 911 turn actions, 582 river actions, and 423 size-pattern observations. Eleven reports exist; a study CLI exposes `top`, `examples`, `node`, `stats`, `weekly`, `compare`, and `progress`.

The descriptive layer works. Hands flow in, get tagged, and produce frequency tables. The current roadblock is not "what to build" but "what to build that compounds" — every recent addition has been another descriptive layer, and the project has hit diminishing returns on description alone.

## Strategic frame

The single biggest unspoken issue in the codebase: **leak detection is LLM-verdict-driven, not baseline-deviation-driven.** `report_leak_prioritization.py` greps `Mistake:` fields written by the parser's OpenAI call at parse time, multiplies counts by hand-coded EV constants, and ranks the result. The 836-line `preflop_baseline.py` module — which exists specifically to define ground-truth expected actions per spot — is not imported by the leak report. Baselines and leak detector are disconnected.

Fixing that disconnect is the qualitative leap from "we count LLM opinions" to "we measure deviation from a grounded baseline." Three adjacent issues reinforce the same direction: leak prioritization is preflop-only despite EV constants existing for postflop; there is no sample-size or confidence layer anywhere in the reporting; and LLM verdicts and baseline predictions never cross-validate.

The plan below is organized around making the leak engine trustworthy first, then extending the same pattern to postflop, then turning the resulting signal into study workflows and EV calibration.

## Near-term plan (next 1–2 months)

### Phase 0 — Foundational parser fixes (week 0–1)

Goal: remove the two ambiguities in parser output that currently force downstream reports to skip data.

Scope: split the `call_or_fold_vs_shove` decision into `call_vs_shove` and `fold_vs_shove` so call-off baselines can compare hero's action; emit a JSON sidecar (`*_analysis.json`) alongside `*_analysis.txt` so reports stop relying on regex over free-text; preserve `_analysis.txt` for human readability.

Deliverables: parser change in `hand_parser.py`; one-time backfill script that re-parses the existing corpus; minor edits to existing reports to read JSON when available, fall back to text grep otherwise.

Success criteria: zero "ambiguous_action" entries when the v2 leak report runs against the backfilled corpus; existing reports continue to produce identical numbers.

Effort: 1 week. Unblocks every later phase.

### Phase 1 — Milestone D: Baseline-integrated leak engine (weeks 1–4)

Goal: convert leak detection from LLM-opinion to baseline-deviation, with the LLM verdict retained as a cross-check.

D.1 — Wire `preflop_baseline.py` into a baseline-integrated leak report. For every parsed hand, route to the right baseline family (open_jam / call_off / reshove), compute expected action, compare to actual, record a directional leak class. Replace the hand-coded EV table with directional priors (folding equity costs more than calling too loose). Add Wilson 95% intervals on every leak rate; gate priority scores on a confidence damper so n=3 buckets cannot outrank n=25 buckets at the same rate. Output a 2×2 LLM-vs-baseline agreement matrix per bucket. _Prototype already drafted as `report_leak_prioritization_v2.py` — this is the productionization pass._

D.2 — Calibration audit on the resulting disagreements. Hand-audit the top 10 LLM-vs-baseline disagreements both ways (LLM missed; LLM false-positive) and write findings to `docs/leak_v2_calibration.md`. If baseline is consistently right, file parser-prompt tickets; if baseline is consistently wrong, file baseline-correction tickets. This is the loop that makes both sides better.

D.3 — Apply the confidence layer (Wilson intervals + n-tiers) across the existing reports: `postflop_hero_flop_actions`, `postflop_hero_deeper_actions`, `postflop_size_patterns`, `preflop_baseline`. Pure plumbing. Every existing number gets a confidence interval and tier next to it.

Success criteria: v2 leak report produces a top-10 list where every entry has confidence tier ≥ medium; LLM-baseline agreement rate is reported and tracked; at least 5 calibration findings are documented.

Effort: 3–4 weeks.

### Phase 2 — Milestone C: Postflop benchmarking (weeks 4–8)

Goal: extend the baseline-deviation pattern to postflop, using the existing hero-action frequency data as the observation surface.

C.1 — Define `postflop_baseline.py` as a sibling to `preflop_baseline.py`. Start narrow: cbet, donk, probe, and turn follow-through reference frequencies for the most common families (SRP IP, SRP OOP, 3BP IP, 3BP OOP) bucketed by board texture (dry, wet, paired) and stack depth band. Hand-coded reasonable values; explicit TODO to replace with measured/solver values later. Aim for ~30–50 spots in v1 of this module.

C.2 — Add a postflop evaluator to the v2 leak engine. Reads aggregated frequencies from `report_postflop_hero_flop_actions.py` output rather than per-hand, since postflop deviation is most meaningful at the bucket level (e.g., "hero cbets SRP IP dry boards at 0.31 vs baseline 0.55"). Same Wilson-interval, confidence-tier, and priority-scoring pipeline as preflop.

C.3 — Extend the same approach to turn and river using `report_postflop_hero_deeper_actions.py` data. The turn layer measures follow-through-after-cbet rates; the river layer measures probe and bet-when-checked-to rates.

Success criteria: postflop layer produces a top-N leak list mergeable with the preflop layer in a single ranked output; at least 3 high-confidence postflop leaks identified.

Effort: 4 weeks.

## Roadmap (3–6 months)

### Phase 3 — Milestone E: Study workflow polish

Goal: convert the leak signal into hand-level study artifacts.

E.1 — Hand-level study packet exporter. For each top-N leak spot, export a readable `.md` file containing: the leak class and confidence; up to 5 representative hands with full hand text (not just the parsed summary); the baseline expected action; the LLM verdict; and a free-text "study notes" section the user can fill in. The current `study_cli.py node` command is a useful skeleton but doesn't pull in the actual hand text.

E.2 — Weekly leak digest as a single artifact (markdown or PDF) combining: top-N leaks this week, week-over-week deltas from `study_cli.py compare`, and 3 hands per top leak embedded inline. Schedule via the existing `schedule` skill or as a manual run.

E.3 — Hand-level "search" command in `study_cli.py` that filters by node, hand class, position, stack band, and leak status. Effectively a CLI version of what `node_pack` is sketching toward.

Effort: 3–4 weeks.

### Phase 4 — Milestone F: Calibrated EV

Goal: replace hand-coded EV priors with measured deltas.

F.1 — Showdown EV aggregator. For hands that reach showdown, compute hero's actual chip-EV vs. an estimated EV of the alternative action. Aggregate per leak class. This requires a baseline EV estimator — start with simple equity-vs-range using PokerKit or an equivalent library; evolve to a proper solver call later.

F.2 — Replace the directional priors in the v2 EV table with measured per-leak-class EV deltas. Confidence-gate: only swap priors for buckets with n ≥ 30 measured cases.

F.3 — Per-leak-class EV trend over time, surfaced in the weekly digest.

Effort: 4–6 weeks. Data-dependent — viable once the corpus reaches roughly 500+ parsed hands with showdown coverage.

### Phase 5 — Milestone G: Knowledge integration

Goal: connect the strategy content already sitting in `articles/library/` and `prompts/` to the node taxonomy, so leak reports can surface relevant snippets per spot.

G.1 — Node-tagging pipeline. Extract content chunks from `articles/library/`, tag each chunk with relevant node IDs (spot family, stack band, position, archetype) using either keyword rules or LLM-assisted tagging. Persist as a JSON index.

G.2 — Snippet attachment in study packets. For each top-N leak, surface 1–3 strategy snippets matched to its node. This is what makes the study packet a learning tool, not just a data dump.

G.3 — Prompt library standardization. Move `prompts/` to a versioned format with explicit input/output schemas so prompts are reproducible across parser runs.

Effort: 3–4 weeks. Parallelizable with Phase 3 or 4.

### Phase 6 — Milestone H: Long-term self-tendency analytics (data-dependent)

Goal: leverage the compounding hand-history database for personal-leak pattern analysis that no off-the-shelf tracker provides.

H.1 — Cohort comparisons: leak rate by tournament archetype cluster, by buy-in band, by time-of-day, by session length. Surface "you play 10% looser in $5 bounty late stages."

H.2 — Recurrence detection: leaks that show up across multiple tournament types vs. leaks specific to one cluster. Recurrence ranks higher in priority — they're real patterns, not noise.

H.3 — Cross-stream pattern detection: e.g., "after losing a flip in late stages, hero's next-orbit aggression frequency rises 15%." This is the long tail and requires meaningful sample size (1000+ hands).

Effort: open-ended; revisit when corpus size makes it viable.

## Cross-cutting initiatives (run alongside phases)

A small set of ongoing efforts that protect the investment.

**Testing.** Adopt `make_test_corpus.py` (delivered with v2 prototype) as a regression-test harness. Every report should run against the synthetic corpus in CI and produce stable outputs; deviations get flagged in the next session's start-of-day check.

**Schema versioning.** Version the parser output (`schema_version` field in the JSON sidecar from Phase 0). Every report declares the minimum schema version it supports. Bump the schema, not the regex.

**Documentation cadence.** After each phase, update `docs/<milestone>_findings.md` with the calibration results, the leaks that were promoted/demoted, and any baseline corrections made. The v2 work has already produced one such candidate file (`docs/leak_v2_calibration.md`).

**Data hygiene.** The corpus is the strategic asset. Continue importing PokerCraft histories on a regular cadence; archive old format runs; keep the metadata (PKO sidecars, summaries) tightly linked. No phase succeeds without this.

## Parking lot (explicitly deferred)

The following are real ideas, but they are not the right next moves and should not absorb attention until prior phases land.

Four-plus player postflop buckets — defer until 2-way and 3-way trees are stable. True ICM solver integration — current heuristic is good enough; replace only after baseline-integrated leak engine has run for 3+ months and ICM heuristic limitations are concretely demonstrated. Live HUD / real-time desktop integration — out of scope for a study tool. Multi-format support (cash, sit-n-go) — distraction for now; MTT focus is the moat. Self-hosted UI — terminal + markdown digest is enough until the workflow is mature.

## Sequencing and dependencies

```
Phase 0 ──► Phase 1 (Milestone D) ──► Phase 2 (Milestone C) ──► Phase 4 (F)
   │              │                          │                    │
   │              ▼                          ▼                    ▼
   └──► Cross-cutting (tests, schema, docs) runs continuously
                  │
                  ▼
             Phase 3 (E) ◄──── Phase 5 (G) (parallelizable)
                  │
                  ▼
             Phase 6 (H) (data-gated)
```

Phase 0 is the only true precondition. Phase 1 is the central spine. Phase 2 reuses Phase 1's architecture. Phase 3 depends on Phase 1's signal but not Phase 2. Phase 4 and 5 can run in parallel with Phase 3 once Phase 1 is stable. Phase 6 waits for data.

## Open milestone tracker

Replaces the milestone checklist at the end of the previous `project_plan.md`. Mark items in Linear once tickets are filed.

- [x] Milestone A — Tournament archetype lookup (completed 2026-04-22)
- [x] Milestone B — ICM-aware preflop benchmark (completed 2026-04-22)
- [ ] Phase 0 — Parser foundational fixes (call_or_fold split + JSON sidecar)
- [ ] Milestone D.1 — Baseline-integrated leak engine v2
- [ ] Milestone D.2 — LLM↔baseline calibration audit
- [ ] Milestone D.3 — Confidence layer across existing reports
- [ ] Milestone C.1 — Postflop baseline module
- [ ] Milestone C.2 — Postflop evaluator wired into v2 leak engine
- [ ] Milestone C.3 — Turn/river extension of postflop baselines
- [ ] Milestone E.1 — Hand-level study packet exporter
- [ ] Milestone E.2 — Weekly leak digest artifact
- [ ] Milestone E.3 — `study_cli` filtering command
- [ ] Milestone F.1 — Showdown EV aggregator
- [ ] Milestone F.2 — Replace EV priors with measured deltas
- [ ] Milestone F.3 — EV trend in weekly digest
- [ ] Milestone G.1 — Node-tagging pipeline for `articles/library/`
- [ ] Milestone G.2 — Snippet attachment in study packets
- [ ] Milestone G.3 — Prompt library standardization
- [ ] Milestone H — Long-term self-tendency analytics (data-gated)

## Notes on what changed from v1 of this plan

The previous `project_plan.md` listed tagging-layer milestones (preflop coverage, flop families, river pruning, study surface, hero-action frequencies) as the unit of progress. Most of those are done. This v2 plan replaces "tag more spots" with "trust the signal we already have" as the dominant theme. The next year of work is about converting tagging into prescriptive guidance — and the foundation for everything is wiring the baselines that already exist into the leak engine that already exists.
