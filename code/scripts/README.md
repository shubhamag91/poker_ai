# Scripts

## Files

- `hand_parser.py` — updated project-wired version
- `postflop_trees.py` — separate source of truth for the staged postflop expansion tree, kept outside the parser so later postflop work can import it cleanly
- `hand_history_utils.py` — shared tournament-ID, summary-detection, and text-file helpers used by the parser/import/report scripts
- `import_tournament_summaries.py` — batch import helper for GG tournament summary text files
- `report_summary_coverage.py` — repo-wide summary coverage report and batch parser manifest generator
- `report_postflop_coverage.py` — repo-wide postflop family/matchup coverage report and missing-path finder for the current spec layer
- `report_postflop_bucket_audit.py` — corpus audit report for real tagged flop hands grouped by family and resolved board bucket, with sample boards and lead-pruning state
- `report_turn_seed_audit.py` — corpus audit report for real tagged flop hands grouped by reachable turn seeds and current turn-family handoff targets
- `report_river_seed_audit.py` — corpus audit report for real tagged flop hands grouped by reachable turn families and current river placeholder-family handoff targets
- `report_postflop_study_surface.py` — study-oriented corpus snapshot that rolls family, board-bucket, turn-family, and river-family reach into one descriptive report
- `report_postflop_hero_flop_actions.py` — first hero-frequency layer, measuring Hero's first flop decision by tagged family, hero structural role, board bucket, and simple flop-action context
- `run_summary_backed_batch.py` — batch runner for HH files that already have matched tournament summaries
- `hand_parser_original.py` — original reference copy

## hand_parser.py

Current starter parser for poker hand-history analysis. It stays focused on parsing plus preflop decision analysis, while postflop tree design lives separately in `postflop_trees.py`.

### Intended flow

- input: files from `../../data/hand_histories/raw/`
- output: parsed files into `../../data/hand_histories/parsed/`

## postflop_trees.py

Stores the clean staged rollout for postflop work:

- flop-only foundation first
- turn follow-through second
- river resolution last

The flop stage now includes:

- a concrete build order for the first heads-up SRP and 3-bet trees
- reusable node-family definitions
- naming examples for later parser integration
- machine-readable matchup instances for concrete spots like `UTG_open_vs_BTN_flat`

Typical usage:

```bash
python3 code/scripts/postflop_trees.py
python3 code/scripts/postflop_trees.py --stage flop
python3 code/scripts/postflop_trees.py --format json
python3 code/scripts/postflop_trees.py --artifact specs --format json
python3 code/scripts/postflop_trees.py --artifact specs --family srp_ip_pfr_flop
python3 code/scripts/postflop_trees.py --artifact specs --matchup UTG_open_vs_BTN_flat
python3 code/scripts/postflop_trees.py --artifact specs --family four_bet_ip_aggressor_flop --board-bucket MONOTONE
python3 code/scripts/postflop_trees.py --artifact turn_specs --family turn_heads_up_ip_aggressor_after_flop_bet_called
python3 code/scripts/postflop_trees.py --artifact turn_validation
python3 code/scripts/postflop_trees.py --artifact river_specs
python3 code/scripts/postflop_trees.py --artifact river_specs --family river_multiway_oop_aggressor_resolution
python3 code/scripts/postflop_trees.py --artifact river_specs --family river_heads_up_oop_first_resolution --board-bucket A_HIGH_DRY
python3 code/scripts/postflop_trees.py --artifact river_validation
```

Because it is a plain Python module, future parser-side postflop work can import either the high-level roadmap or the machine-readable flop tree specs instead of duplicating street trees in `hand_parser.py`.

When `--board-bucket` is supplied in specs mode, lead-enabled families with `board_action_policy` now prune unavailable lead/probe branches instead of only annotating those preferences.

When `--board-bucket` is supplied in `river_specs` mode, river families with `board_size_policy` now prune unavailable large river size branches and render the removed branches explicitly.

`--artifact turn_specs` exposes the controlled first-turn library that seeds only from the most stable high-volume flop families, rather than trying to open a full turn tree all at once.

`--artifact turn_validation` runs a structural sanity check on the turn library, verifying template wiring, size-profile references, source-family links, and seed-to-family mappings before widening turn coverage further.

`--artifact river_specs` exposes the new first-river placeholder library that stays anchored to the already stabilized turn families instead of widening into broader river strategy.

`--artifact river_validation` runs the matching structural sanity check for the river placeholder layer, verifying template wiring, size-profile references, source-turn-family links, and river-seed-to-family mappings.

## import_tournament_summaries.py

Batch-imports GG tournament summary text files into `../../data/hand_histories/summaries/`.

### Typical usage

```bash
python3 code/scripts/import_tournament_summaries.py
```

By default it scans existing `~/Downloads`, `~/PokerCraft`, and `~/PokerCraft_HH` roots recursively for GG tournament summary files.

### Helpful flags

- `--dry-run` preview imports and tournament-ID matches without copying files
- `--report-json <path>` save a JSON manifest for later review
- `--source-dir <path>` override the default auto-scan roots with one explicit folder

## report_summary_coverage.py

Scans repo hand histories plus imported summaries, matches them by tournament ID, and writes deterministic coverage artifacts under `../../data/hand_histories/summaries/coverage_report/`.

### Typical usage

```bash
python3 code/scripts/report_summary_coverage.py
```

### Outputs

- `latest.json` full machine-readable coverage report
- `latest.txt` concise terminal-friendly summary
- `matched_parser_inputs.json` batch-ready matched hand-history and summary pairs
- `matched_parser_commands.txt` example `hand_parser.py` commands for the matched pairs

## report_postflop_coverage.py

Scans raw hand histories, runs the current postflop spec tagger over flop-reaching hands, and writes coverage artifacts under `../../data/hand_histories/postflop_coverage_report/`.

### Typical usage

```bash
python3 code/scripts/report_postflop_coverage.py
```

### Outputs

- `latest.json` full machine-readable coverage report
- `latest.txt` concise terminal-friendly summary
- top missing path shapes so SRP-matrix expansion can follow real corpus frequency instead of guesswork

### Helpful flags

- `--hero <name>` override the default hero name
- `--max-examples <n>` control how many example hands are stored per unsupported bucket
- `--limit-files <n>` scan only the first N raw files while iterating quickly

## report_postflop_bucket_audit.py

Scans raw hand histories, resolves the current postflop family plus flop board bucket for each tagged hand, and writes audit artifacts under `../../data/hand_histories/postflop_bucket_audit/`.

### Typical usage

```bash
python3 code/scripts/report_postflop_bucket_audit.py
```

### Outputs

- `latest.json` machine-readable family-by-bucket counts plus stored examples
- `latest.txt` terminal-friendly audit summary with example boards and pruning status

### Helpful flags

- `--hero <name>` override the default hero name
- `--max-examples <n>` control how many sample hands are kept per family/bucket
- `--limit-files <n>` scan only the first N raw files while iterating quickly

## report_turn_seed_audit.py

Scans raw hand histories, resolves the current postflop family, applies any board-based turn-seed pruning already encoded in the flop family, and writes audit artifacts showing which current turn families are actually reachable from real tagged hands.

### Typical usage

```bash
python3 code/scripts/report_turn_seed_audit.py
```

### Outputs

- `latest.json` machine-readable source-family, board-bucket, active-turn-seed, and reachable-turn-family counts
- `latest.txt` terminal-friendly summary with source-family detail and stored examples

### Helpful flags

- `--hero <name>` override the default hero name
- `--max-examples <n>` control how many sample hands are kept per family/bucket
- `--limit-files <n>` scan only the first N raw files while iterating quickly

## report_river_seed_audit.py

Scans raw hand histories, resolves the current postflop family, applies the stabilized flop-to-turn seed handoff first, then audits which current river placeholder families remain reachable from those real tagged hands through the existing turn layer. It also reports any river-side size branches removed by active `board_size_policy` rules.

### Typical usage

```bash
python3 code/scripts/report_river_seed_audit.py
```

### Outputs

- `latest.json` machine-readable source-flop-family, source-turn-family, active-river-seed, reachable-river-family, and removed-river-size-branch counts
- `latest.txt` terminal-friendly summary with source-family detail, active river pruning, and stored examples

### Helpful flags

- `--hero <name>` override the default hero name
- `--max-examples <n>` control how many sample hands are kept per family/bucket
- `--limit-files <n>` scan only the first N raw files while iterating quickly

## report_postflop_study_surface.py

Builds a study-oriented snapshot of the tagged postflop corpus, combining family frequency, board-bucket distribution, current turn-family reach, current river-family reach, and active river-side pruning into one descriptive report.

### Typical usage

```bash
python3 code/scripts/report_postflop_study_surface.py
```

### Outputs

- `latest.json` machine-readable family summary, top family/bucket combinations, and stored examples
- `latest.txt` terminal-friendly study surface report for quick review

### Helpful flags

- `--hero <name>` override the default hero name
- `--max-examples <n>` control how many sample hands are kept per family/bucket
- `--limit-files <n>` scan only the first N raw files while iterating quickly

## report_postflop_hero_flop_actions.py

Builds the first actual hero-action-frequency layer on top of the tagged postflop study surface. The current scope is intentionally narrow and descriptive: it measures Hero's **first flop decision** and groups it by family, hero structural role, resolved board bucket, and simple action context (`first_to_act`, `checked_to_hero`, `facing_bet`, `facing_raise`).

### Typical usage

```bash
python3 code/scripts/report_postflop_hero_flop_actions.py
```

### Outputs

- `latest.json` machine-readable hero-action counts, top family/role/bucket/context spots, reachable turn and river families, and stored examples
- `latest.txt` terminal-friendly hero flop action report for quick review

### Helpful flags

- `--hero <name>` override the default hero name
- `--max-examples <n>` control how many sample hands are kept per family / role / bucket / context
- `--limit-files <n>` scan only the first N raw files while iterating quickly

## run_summary_backed_batch.py

Runs `hand_parser.py` over the matched HH/summary pairs from the coverage manifest.

### Typical usage

```bash
python3 code/scripts/run_summary_backed_batch.py --only-missing
```

### Helpful flags

- `--start <n>` begin from a later offset in the manifest
- `--count <n>` control batch size
- `--limit <n>` pass through a per-file actionable-hand limit to `hand_parser.py`
- `--only-missing` skip outputs that already exist

This report workflow does not require an OpenAI API key.

### API key setup

The updated script auto-loads the project root `.env` file if it exists.

Expected file:

`/Users/shubham/Projects/poker_ai/.env`

Example:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
```
