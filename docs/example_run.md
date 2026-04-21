# Example hand_parser run flow

## Project env file

Before running the parser, add your key to:

`/Users/shubham/Projects/poker_ai/.env`

Example:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
```

## Default input

If you run the parser without `--input`, it will now prefer this file:

`/Users/shubham/Projects/poker_ai/data/hand_histories/raw/GG20260216-1224 - APL Series 110 Zodiac Evening Classic + Horse.txt`

## Default run command

```bash
cd /Users/shubham/Projects/poker_ai
python3 code/scripts/hand_parser.py
```

## Explicit run command

```bash
cd /Users/shubham/Projects/poker_ai
python3 code/scripts/hand_parser.py \
  --input "data/hand_histories/raw/GG20260216-1224 - APL Series 110 Zodiac Evening Classic + Horse.txt"
```

## Tournament summary sidecar run

If a matching summary lives under `data/hand_histories/summaries/`, the parser will auto-discover it by tournament ID. You can also pass it explicitly:

```bash
cd /Users/shubham/Projects/poker_ai
python3 code/scripts/hand_parser.py \
  --input "data/hand_histories/raw/GG20260315-1420 - WSOP-SC 15 Sunday Bounty Dream of Spring.txt" \
  --summary "data/hand_histories/summaries/GG20260315 - Tournament #269551090 - WSOP-SC 15 Sunday Bounty Dream of Spring.txt"
```

## Expected output location

`/Users/shubham/Projects/poker_ai/data/hand_histories/parsed/GG20260216-1224 - APL Series 110 Zodiac Evening Classic + Horse_analysis.txt`

## VS Code quick run guide

### Run the exact sample file

1. Open the `poker_ai` folder in VS Code.
2. Open **Terminal -> Run Task**.
3. Choose **Run hand_parser (sample GG file)**.
4. Watch output in the integrated terminal.

### Run the latest raw file

1. Open **Run and Debug** in the left sidebar.
2. Choose **hand_parser.py: latest raw file**.
3. Click the green run button.

### Debug a specific file

1. Open **Run and Debug**.
2. Choose **hand_parser.py: choose input file**.
3. Enter the raw hand-history path when prompted.
4. Click the green run button.

### Environment note

The VS Code setup is wired to:

- use the workspace `.env`
- use the configured Python interpreter
- run from the project root so relative paths resolve cleanly

## Notes

- The script loads `.env` automatically if present.
- If the default GG file is missing, the script falls back to the newest `.txt` or `.log` file under `data/hand_histories/raw/`.
- Use `--hero <name>` if the player name is not `Hero` in the hand history.
- Use `--limit <n>` to control how many actionable hands are analyzed.
- Use `--summary <path>` to point at a tournament summary sidecar manually, or drop summaries into `data/hand_histories/summaries/` for auto-discovery.
- The output may include a short `Approx stage/ICM` line based on a non-scraping tournament archetype heuristic plus optional summary field-size context. See `docs/tournament_archetype_heuristic.md`.
