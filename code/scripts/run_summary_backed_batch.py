#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "hand_histories" / "summaries" / "coverage_report" / "matched_parser_inputs.json"
DEFAULT_BATCH_SIZE = 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run hand_parser.py over summary-backed hand histories in manageable batches."
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help=f"Matched parser manifest JSON. Default: {DEFAULT_MANIFEST}",
    )
    parser.add_argument("--start", type=int, default=0, help="Zero-based start index inside the manifest. Default: 0")
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"How many manifest items to run in this batch. Default: {DEFAULT_BATCH_SIZE}",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional --limit value passed through to hand_parser.py for each file.",
    )
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Skip items whose suggested parsed output already exists.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest_path = Path(args.manifest).expanduser().resolve()
    items = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise SystemExit(f"Expected a list manifest at {manifest_path}")

    batch = items[args.start : args.start + args.count]
    if not batch:
        raise SystemExit("No batch items selected. Check --start/--count.")

    total = len(batch)
    processed = 0
    skipped = 0
    failed = 0

    for offset, item in enumerate(batch, start=1):
        output_path = PROJECT_ROOT / item["suggested_output_path"]
        if args.only_missing and output_path.exists():
            skipped += 1
            print(f"[{offset}/{total}] skip existing -> {item['hand_history_path']}")
            continue

        cmd = [
            sys.executable,
            "code/scripts/hand_parser.py",
            "--input",
            item["hand_history_path"],
            "--summary",
            item["summary_path"],
            "--output",
            item["suggested_output_path"],
        ]
        if args.limit is not None:
            cmd.extend(["--limit", str(args.limit)])

        print(f"[{offset}/{total}] run -> {item['hand_history_path']}")
        try:
            subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
            processed += 1
        except subprocess.CalledProcessError:
            failed += 1
            print(f"[{offset}/{total}] failed -> {item['hand_history_path']}")

    print(
        f"Batch complete. processed={processed} skipped={skipped} failed={failed} "
        f"start={args.start} count={len(batch)}"
    )


if __name__ == "__main__":
    main()
