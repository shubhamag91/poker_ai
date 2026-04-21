# poker_ai

A working project space for poker hand-history parsing, study material, and future poker-AI experiments.

## Current focus

- collect and organize poker hand histories
- keep parsing scripts in one place
- build a repeatable hand-parser workflow
- keep study/reference material close to the project

## Main folders

- `code/scripts/` runnable scripts, including `hand_parser.py`
- `code/experiments/legacy/` older or exploratory poker scripts
- `data/hand_histories/raw/` original hand-history inputs
- `data/hand_histories/parsed/` parsed outputs
- `data/hand_histories/metadata/` optional PKO sidecar metadata for bounty-to-BB conversion
- `data/hand_histories/archives/` archived hand-history bundles
- `articles/library/` poker books, guides, worksheets, and related material
- `prompts/` reusable prompts for analysis and labeling
- `docs/project_plan.md` project direction and milestones

## Starter parser workflow

1. Put raw hand-history files into `data/hand_histories/raw/`
2. Import tournament summaries when you have them:
   - `python3 code/scripts/import_tournament_summaries.py`
   - by default it scans existing `~/Downloads`, `~/PokerCraft`, and `~/PokerCraft_HH` roots recursively for GG tournament summary files
   - add `--dry-run` to preview matches before copying
3. Generate a repo-wide summary coverage report:
   - `python3 code/scripts/report_summary_coverage.py`
   - artifacts land in `data/hand_histories/summaries/coverage_report/`
4. Run summary-backed files in batches when you want:
   - `python3 code/scripts/run_summary_backed_batch.py`
   - defaults to the first 10 matched HH/summary pairs from the latest coverage manifest
   - add `--start <n>` and `--count <n>` to move through the list in batches
   - add `--only-missing` to skip parsed outputs that already exist
5. Run `code/scripts/hand_parser.py`
6. Matching tournament summaries live in `data/hand_histories/summaries/`
7. Save parsed outputs into `data/hand_histories/parsed/`
8. Iterate on parser quality and prompt design

## Notes

- The current `hand_parser.py` expects an OpenAI API key.
- `hand_parser.py` can auto-link a tournament summary sidecar by tournament ID, or you can pass `--summary <path>`.
- `hand_parser.py` can also read optional `.pko.json` sidecars from `data/hand_histories/metadata/` for bounded PKO bounty EV notes in relevant call-versus-shove spots.
- `code/scripts/postflop_trees.py` now holds both the staged postflop expansion plan and the first machine-readable flop tree specs separately from the hand parser so future street-tree work can stay modular.
- `code/scripts/postflop_trees.py` also exposes the controlled first-turn and first-river placeholder artifacts via `--artifact turn_specs`, `turn_validation`, `river_specs`, and `river_validation`.
- `import_tournament_summaries.py` scans downloaded text files, copies tournament summaries into `data/hand_histories/summaries/`, and reports imported, matched, unmatched, and duplicate files.
- `report_summary_coverage.py` scans repo hand histories plus imported summaries, writes deterministic JSON and text reports, and also emits a batch-ready matched parser manifest plus example parser commands.
- `report_postflop_coverage.py` scans raw hand histories, measures how much of the current postflop spec layer actually tags, and surfaces the top missing path shapes for the next matrix-expansion pass.
- `report_postflop_study_surface.py` builds the first study-oriented snapshot on top of the current family / board-bucket / turn-family / river-family tagging layer.
- `report_postflop_hero_flop_actions.py` adds the first hero-frequency layer by measuring Hero's first flop decision against the tagged family / board-bucket / turn-family / river-family surface.
- `run_summary_backed_batch.py` consumes the coverage manifest and runs `hand_parser.py` over matched HH/summary pairs in controlled batches.
- Large non-project clutter like app installers and overlay packs was not imported into this repo.
- Downloads, Personal, and Desktop are still treated as separate trees outside the project.
