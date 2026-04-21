#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from hand_history_utils import is_summary_text, iter_text_files, read_text
from hand_parser import DEFAULT_HERO_NAME, RAW_ROOT, identify_postflop_spec_tags, split_hands

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HAND_HISTORY_ROOT = RAW_ROOT
OUTPUT_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "postflop_coverage_report"


def relative_to_project(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except Exception:
        return str(path)


def build_path_shape(tag: dict) -> str:
    structure = tag.get("structure") if isinstance(tag.get("structure"), dict) else None
    if not structure or not structure.get("available"):
        return "unknown"
    return structure.get("grouped_path_shape", "unknown")


def example_record(file_path: Path, hand_index: int, tag: dict) -> dict:
    structure = tag.get("structure") if isinstance(tag.get("structure"), dict) else {}
    return {
        "file": relative_to_project(file_path),
        "hand_index": hand_index,
        "reason": tag.get("reason", "unknown"),
        "path_shape": build_path_shape(tag),
        "pot_type": structure.get("pot_type"),
        "open_raiser_position": structure.get("open_raiser_position"),
        "caller_position": structure.get("caller_position"),
        "three_bettor_position": structure.get("three_bettor_position"),
        "open_raiser_group": structure.get("open_raiser_group"),
        "caller_group": structure.get("caller_group"),
        "three_bettor_group": structure.get("three_bettor_group"),
    }


def build_report(hero_name: str, max_examples_per_bucket: int = 5, limit_files: int | None = None) -> dict:
    files = []
    for path in iter_text_files(HAND_HISTORY_ROOT):
        text = read_text(path)
        if is_summary_text(text):
            continue
        files.append((path, text))

    if limit_files is not None:
        files = files[:limit_files]

    family_counts: Counter[str] = Counter()
    matchup_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    unsupported_path_counts: Counter[str] = Counter()
    examples_by_reason: dict[str, list[dict]] = defaultdict(list)
    examples_by_path_shape: dict[str, list[dict]] = defaultdict(list)

    total_hands = 0
    flop_hands = 0
    tagged_hands = 0

    for file_path, text in files:
        hands = split_hands(text)
        total_hands += len(hands)

        for hand_index, hand in enumerate(hands, start=1):
            if "*** FLOP ***" not in hand:
                continue
            flop_hands += 1
            tag = identify_postflop_spec_tags(hand, hero_name)
            if tag.get("available"):
                tagged_hands += 1
                family_counts[tag["family_id"]] += 1
                matchup_counts[tag["matchup_id"]] += 1
                continue

            reason = tag.get("reason", "unknown")
            reason_counts[reason] += 1
            path_shape = build_path_shape(tag)
            unsupported_path_counts[path_shape] += 1
            record = example_record(file_path, hand_index, tag)
            if len(examples_by_reason[reason]) < max_examples_per_bucket:
                examples_by_reason[reason].append(record)
            if len(examples_by_path_shape[path_shape]) < max_examples_per_bucket:
                examples_by_path_shape[path_shape].append(record)

    untagged_hands = flop_hands - tagged_hands
    tagged_pct = round((tagged_hands / flop_hands) * 100, 2) if flop_hands else 0.0

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hero_name": hero_name,
        "hand_history_root": relative_to_project(HAND_HISTORY_ROOT),
        "total_files_scanned": len(files),
        "total_hands_scanned": total_hands,
        "hands_reaching_flop": flop_hands,
        "tagged_hands": tagged_hands,
        "untagged_hands": untagged_hands,
        "tagged_pct": tagged_pct,
        "family_counts": dict(sorted(family_counts.items(), key=lambda item: (-item[1], item[0]))),
        "matchup_counts": dict(sorted(matchup_counts.items(), key=lambda item: (-item[1], item[0]))),
        "untagged_reason_counts": dict(sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))),
        "unsupported_path_counts": dict(sorted(unsupported_path_counts.items(), key=lambda item: (-item[1], item[0]))),
        "example_untagged_hands_by_reason": dict(examples_by_reason),
        "example_untagged_hands_by_path_shape": dict(examples_by_path_shape),
    }


def format_terminal_summary(report: dict, max_rows: int = 15) -> str:
    lines = [
        "Postflop coverage report",
        "=" * 80,
        f"Generated: {report['generated_at']}",
        f"Hero: {report['hero_name']}",
        f"Files scanned: {report['total_files_scanned']}",
        f"Total hands scanned: {report['total_hands_scanned']}",
        f"Hands reaching flop: {report['hands_reaching_flop']}",
        f"Tagged flop hands: {report['tagged_hands']} ({report['tagged_pct']}%)",
        f"Untagged flop hands: {report['untagged_hands']}",
        "",
    ]

    if report["family_counts"]:
        lines.append("Tagged family coverage")
        lines.append("-" * 80)
        for family_id, count in list(report["family_counts"].items())[:max_rows]:
            lines.append(f"{family_id}: {count}")
        lines.append("")

    if report["matchup_counts"]:
        lines.append("Tagged matchup coverage")
        lines.append("-" * 80)
        for matchup_id, count in list(report["matchup_counts"].items())[:max_rows]:
            lines.append(f"{matchup_id}: {count}")
        lines.append("")

    if report["unsupported_path_counts"]:
        lines.append("Top missing path shapes")
        lines.append("-" * 80)
        for path_shape, count in list(report["unsupported_path_counts"].items())[:max_rows]:
            lines.append(f"{path_shape}: {count}")
            for example in report["example_untagged_hands_by_path_shape"].get(path_shape, [])[:3]:
                lines.append(f"  {example['file']} | hand {example['hand_index']} | reason: {example['reason']}")
        lines.append("")

    if report["untagged_reason_counts"]:
        lines.append("Untagged reasons")
        lines.append("-" * 80)
        for reason, count in list(report["untagged_reason_counts"].items())[:max_rows]:
            lines.append(f"{reason}: {count}")
            for example in report["example_untagged_hands_by_reason"].get(reason, [])[:3]:
                lines.append(f"  {example['file']} | hand {example['hand_index']} | path: {example['path_shape']}")
        lines.append("")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan raw hand histories and report postflop family/matchup coverage using the current spec-tagging layer."
    )
    parser.add_argument("--hero", default=DEFAULT_HERO_NAME, help="Hero/player name used in the hand histories.")
    parser.add_argument("--max-examples", type=int, default=5, help="Max example hands to store per reason/path bucket.")
    parser.add_argument("--limit-files", type=int, help="Optional limit on how many raw hand-history files to scan.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(hero_name=args.hero, max_examples_per_bucket=args.max_examples, limit_files=args.limit_files)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_ROOT / "latest.json"
    text_path = OUTPUT_ROOT / "latest.txt"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    text_path.write_text(format_terminal_summary(report), encoding="utf-8")

    print(f"JSON: {relative_to_project(json_path)}")
    print(f"TXT: {relative_to_project(text_path)}")
    print(f"Tagged flop hands: {report['tagged_hands']} / {report['hands_reaching_flop']} ({report['tagged_pct']}%)")


if __name__ == "__main__":
    main()
