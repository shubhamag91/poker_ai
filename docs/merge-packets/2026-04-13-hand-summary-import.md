# Merge Packet: hand-summary-import thread

## Scope
This thread built and verified the tournament-summary import and linking workflow for `poker_ai`, then used the linked summaries to refresh parsed outputs.

## What changed
- Added optional tournament-summary sidecar support to `code/scripts/hand_parser.py`.
  - Auto-discovers matching summary files by tournament ID.
  - Supports explicit `--summary`.
  - Uses total field size and finish-place hints to tighten stage / ICM notes without claiming exact players-left precision.
- Added `code/scripts/import_tournament_summaries.py`.
  - Scans Downloads recursively for GG tournament summary text files.
  - Ignores hand-history files.
  - Imports summaries into `data/hand_histories/summaries/`.
  - Matches by tournament ID.
  - Skips duplicates.
  - Can emit JSON import reports.
- Added `code/scripts/report_summary_coverage.py`.
  - Scans repo hand histories plus imported summaries.
  - Reports matched / unmatched coverage.
  - Writes deterministic artifacts under `data/hand_histories/summaries/coverage_report/`.
  - Emits batch-ready parser input manifests and example parser commands.
- Updated docs in:
  - `README.md`
  - `code/scripts/README.md`
  - `docs/example_run.md`
  - `docs/tournament_archetype_heuristic.md`
  - `data/README.md`

## Imported summaries now in repo
- `data/hand_histories/summaries/tournament_264778916__APL-Series-110-Zodiac-Evening-Classic-Horse-Hold-em-No-Limit.txt`
- `data/hand_histories/summaries/GG20260315 - Tournament #269551090 - WSOP-SC 15 Sunday Bounty Dream of Spring.txt`

## Current linked coverage
- Summary files in repo: 2
- Matched tournaments: 2
- Matched hand-history files: 3
- Unmatched hand-history files: 229

### Matched tournaments
- `#264778916`
  - `data/hand_histories/raw/GG20260216-1212 - APL Series 110 Zodiac Evening Classic + Horse.txt`
  - `data/hand_histories/raw/GG20260216-1224 - APL Series 110 Zodiac Evening Classic + Horse.txt`
- `#269551090`
  - `data/hand_histories/raw/GG20260315-1420 - WSOP-SC 15 Sunday Bounty Dream of Spring.txt`

## Refreshed parsed outputs
- `data/hand_histories/parsed/GG20260216-1212 - APL Series 110 Zodiac Evening Classic + Horse_analysis.txt`
- `data/hand_histories/parsed/GG20260216-1224 - APL Series 110 Zodiac Evening Classic + Horse_analysis.txt`
- `data/hand_histories/parsed/GG20260315-1420 - WSOP-SC 15 Sunday Bounty Dream of Spring_analysis.txt`

## Verified behavior
- The parser now auto-links imported summaries correctly.
- Example APL output now includes summary-aware context such as:
  - field size `1,062`
  - lower-bound alive count derived from Hero finishing `18th`
- Example WSOP output includes summary-aware context such as:
  - field size `18,350`
  - lower-bound alive count derived from Hero finishing `10,518th`

## Report artifacts
- Import report:
  - `data/hand_histories/summaries/import_reports/latest.json`
- Coverage reports:
  - `data/hand_histories/summaries/coverage_report/latest.json`
  - `data/hand_histories/summaries/coverage_report/latest.txt`
  - `data/hand_histories/summaries/coverage_report/matched_parser_inputs.json`
  - `data/hand_histories/summaries/coverage_report/matched_parser_commands.txt`

## Important fixes made during thread
- Fixed coverage reporting so generated report text files are not miscounted as summary sidecars.
- Tightened parser summary discovery so report artifacts cannot be mistaken for real tournament summaries.
- Broadened importer default source from `~/Downloads/PokerCraft_HH` to the full `~/Downloads` tree after finding real summary files outside the PokerCraft folder.

## Current blocker
- Matching logic is working.
- The remaining bottleneck is summary inventory: most repo hand histories still do not yet have downloaded tournament summary files available.

## Recommended next step
- Import more GG tournament summary text files from Downloads, rerun coverage, then batch-refresh the parsed outputs for newly linked tournaments.

## One-paragraph Discord-ready version
Merged the hand-summary-import work into `poker_ai`: the parser now supports tournament summary sidecars, we added a batch importer that scans `~/Downloads` for GG summary `.txt` files and links them by tournament ID, plus a coverage-report script that shows which hand histories are linked. We imported 2 real summaries into the repo, which now link to 2 tournaments and 3 hand-history files total, and refreshed the parsed outputs for those linked files. The parser is now using field-size and finish-place context in its stage/ICM notes without pretending exact players-left precision. Main bottleneck from here is simply getting more tournament summary files into Downloads so we can import and link more of the backlog.
