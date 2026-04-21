#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hand_parser import identify_postflop_spec_tags, split_hands, read_file, extract_flop_cards
from postflop_trees import (
    build_flop_tree_spec_library,
    build_turn_tree_spec_library,
    build_river_tree_spec_library,
    filtered_river_specs,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "raw"
REPORT_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "postflop_study_surface"
DEFAULT_HERO_NAME = "Hero"


def build_turn_seed_id_index(flop_library: dict[str, Any]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for family_id, family in flop_library["families"].items():
        template = flop_library["templates"][family["template_ref"]]
        index[family_id] = [seed["id"] for seed in template.get("turn_seeds", [])]
    return index


def build_river_seed_id_index(turn_library: dict[str, Any]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for family_id, family in turn_library["families"].items():
        template = turn_library["templates"][family["template_ref"]]
        index[family_id] = [seed["id"] for seed in template.get("river_seeds", [])]
    return index


def _sorted_counter(counter: dict[str, int]) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def build_report(hero_name: str = DEFAULT_HERO_NAME, max_examples: int = 2, limit_files: int | None = None) -> dict[str, Any]:
    flop_library = build_flop_tree_spec_library()
    turn_library = build_turn_tree_spec_library()
    river_library = build_river_tree_spec_library()
    turn_seed_ids_by_family = build_turn_seed_id_index(flop_library)
    river_seed_ids_by_turn_family = build_river_seed_id_index(turn_library)
    turn_seed_family_map = turn_library["seed_family_map"]
    river_seed_family_map = river_library["seed_family_map"]

    family_summary: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "hand_count": 0,
            "board_bucket_counts": defaultdict(int),
            "matchup_counts": defaultdict(int),
            "reachable_turn_family_counts": defaultdict(int),
            "reachable_river_family_counts": defaultdict(int),
            "removed_river_size_branch_counts": defaultdict(int),
        }
    )
    examples: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    family_bucket_counts: dict[str, int] = defaultdict(int)
    river_policy_cache: dict[tuple[str, str], dict[str, Any]] = {}

    files_scanned = 0
    hands_scanned = 0
    tagged_flop_hands = 0
    hands_with_turn_family = 0
    hands_with_river_family = 0

    raw_files = sorted(RAW_ROOT.glob("*.txt"))
    if limit_files is not None:
        raw_files = raw_files[:limit_files]

    def resolve_river_policy(river_family_id: str, board_bucket: str) -> dict[str, Any]:
        cache_key = (river_family_id, board_bucket)
        if cache_key not in river_policy_cache:
            artifact = filtered_river_specs(family=river_family_id, board_bucket=board_bucket)
            family = artifact["families"][river_family_id]
            river_policy_cache[cache_key] = {
                "removed_size_branches": family.get("enforced_board_policy", {}).get("removed_size_branches", []),
            }
        return river_policy_cache[cache_key]

    for path in raw_files:
        files_scanned += 1
        for hand in split_hands(read_file(path)):
            hands_scanned += 1
            tag = identify_postflop_spec_tags(hand, hero_name)
            if not tag.get("available") or "family_id" not in tag:
                continue

            tagged_flop_hands += 1
            family_id = tag["family_id"]
            board_bucket = tag.get("board_bucket") or "UNSPECIFIED"
            matchup_id = tag.get("matchup_id") or "unknown"

            summary = family_summary[family_id]
            summary["hand_count"] += 1
            summary["board_bucket_counts"][board_bucket] += 1
            summary["matchup_counts"][matchup_id] += 1
            family_bucket_counts[f"{family_id} | {board_bucket}"] += 1

            reachable_turn_families: list[str] = []
            reachable_river_families: set[str] = set()
            river_removed_size_branches: dict[str, list[str]] = {}

            if family_id in turn_seed_family_map:
                mapped_turn_seed_targets = turn_seed_family_map[family_id]
                removed_turn_seed_ids = set((tag.get("enforced_board_action_policy") or {}).get("removed_turn_seeds", []))
                all_turn_seed_ids = turn_seed_ids_by_family.get(family_id, [])
                active_turn_seed_ids = [seed_id for seed_id in all_turn_seed_ids if seed_id not in removed_turn_seed_ids]
                reachable_turn_families = sorted({mapped_turn_seed_targets[seed_id] for seed_id in active_turn_seed_ids if seed_id in mapped_turn_seed_targets})
                if reachable_turn_families:
                    hands_with_turn_family += 1
                for turn_family_id in reachable_turn_families:
                    summary["reachable_turn_family_counts"][turn_family_id] += 1
                    for river_seed_id in river_seed_ids_by_turn_family.get(turn_family_id, []):
                        river_family_id = river_seed_family_map.get(turn_family_id, {}).get(river_seed_id)
                        if river_family_id:
                            reachable_river_families.add(river_family_id)

            if reachable_river_families:
                hands_with_river_family += 1
            for river_family_id in sorted(reachable_river_families):
                summary["reachable_river_family_counts"][river_family_id] += 1
                policy = resolve_river_policy(river_family_id, board_bucket)
                removed_branches = policy["removed_size_branches"]
                if removed_branches:
                    river_removed_size_branches[river_family_id] = removed_branches
                for branch in removed_branches:
                    summary["removed_river_size_branch_counts"][f"{river_family_id}:{branch}"] += 1

            bucket_examples = examples[family_id][board_bucket]
            if len(bucket_examples) < max_examples:
                bucket_examples.append(
                    {
                        "file": path.name,
                        "hand_header": hand.splitlines()[0] if hand.splitlines() else "unknown",
                        "matchup_id": matchup_id,
                        "flop_cards": extract_flop_cards(hand),
                        "reachable_turn_families": reachable_turn_families,
                        "reachable_river_families": sorted(reachable_river_families),
                        "river_removed_size_branches": river_removed_size_branches,
                    }
                )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "meta": {
            "hero_name": hero_name,
            "files_scanned": files_scanned,
            "hands_scanned": hands_scanned,
            "tagged_flop_hands": tagged_flop_hands,
            "hands_with_turn_family": hands_with_turn_family,
            "hands_with_river_family": hands_with_river_family,
            "max_examples_per_bucket": max_examples,
        },
        "top_family_bucket_counts": _sorted_counter(family_bucket_counts),
        "family_summary": {
            family_id: {
                "hand_count": summary["hand_count"],
                "board_bucket_counts": _sorted_counter(summary["board_bucket_counts"]),
                "matchup_counts": _sorted_counter(summary["matchup_counts"]),
                "reachable_turn_family_counts": _sorted_counter(summary["reachable_turn_family_counts"]),
                "reachable_river_family_counts": _sorted_counter(summary["reachable_river_family_counts"]),
                "removed_river_size_branch_counts": _sorted_counter(summary["removed_river_size_branch_counts"]),
            }
            for family_id, summary in sorted(family_summary.items(), key=lambda item: (-item[1]["hand_count"], item[0]))
        },
        "examples": {
            family_id: {bucket: rows for bucket, rows in sorted(bucket_rows.items())}
            for family_id, bucket_rows in sorted(examples.items())
        },
    }


def render_report_text(report: dict[str, Any]) -> str:
    meta = report["meta"]
    lines = [
        "Postflop study surface",
        "======================",
        f"Generated: {report['generated_at']}",
        f"Hero: {meta['hero_name']}",
        f"Files scanned: {meta['files_scanned']}",
        f"Hands scanned: {meta['hands_scanned']}",
        f"Tagged flop hands: {meta['tagged_flop_hands']}",
        f"Hands with reachable turn family: {meta['hands_with_turn_family']}",
        f"Hands with reachable river family: {meta['hands_with_river_family']}",
        f"Examples per bucket: {meta['max_examples_per_bucket']}",
        "",
        "Top family / board-bucket combinations",
        "-------------------------------------",
    ]

    for family_bucket, count in list(report["top_family_bucket_counts"].items())[:20]:
        lines.append(f"- {family_bucket}: {count}")

    lines.extend(["", "Family summaries", "----------------"])
    for family_id, summary in report["family_summary"].items():
        lines.append(f"- {family_id}: {summary['hand_count']}")
        board_buckets = ", ".join(f"{bucket}={count}" for bucket, count in list(summary["board_bucket_counts"].items())[:8]) or "none"
        matchups = ", ".join(f"{matchup}={count}" for matchup, count in list(summary["matchup_counts"].items())[:8]) or "none"
        turns = ", ".join(f"{turn_family}={count}" for turn_family, count in summary["reachable_turn_family_counts"].items()) or "none"
        rivers = ", ".join(f"{river_family}={count}" for river_family, count in summary["reachable_river_family_counts"].items()) or "none"
        removed = ", ".join(f"{branch}={count}" for branch, count in summary["removed_river_size_branch_counts"].items()) or "none"
        lines.append(f"  - board buckets: {board_buckets}")
        lines.append(f"  - matchups: {matchups}")
        lines.append(f"  - turn reach: {turns}")
        lines.append(f"  - river reach: {rivers}")
        lines.append(f"  - removed river size branches: {removed}")

    lines.extend(["", "Examples", "--------"])
    for family_id, bucket_rows in report["examples"].items():
        lines.append(f"- {family_id}")
        for bucket, rows in bucket_rows.items():
            lines.append(f"  - {bucket}")
            for row in rows:
                flop = " ".join(row.get("flop_cards") or []) or "unknown"
                turns = ", ".join(row.get("reachable_turn_families") or []) or "none"
                rivers = ", ".join(row.get("reachable_river_families") or []) or "none"
                removed = "; ".join(
                    f"{river_family}={', '.join(branches) if branches else 'none'}"
                    for river_family, branches in sorted((row.get("river_removed_size_branches") or {}).items())
                ) or "none"
                lines.append(f"    - {flop} | {row['matchup_id']} | turns={turns} | rivers={rivers} | removed={removed} | {row['file']}")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a study-oriented snapshot of the tagged postflop corpus across flop families, board buckets, and current turn/river reach."
    )
    parser.add_argument("--hero", default=DEFAULT_HERO_NAME, help="Hero name to use while tagging hands.")
    parser.add_argument("--max-examples", type=int, default=2, help="Examples to retain per family/bucket.")
    parser.add_argument("--limit-files", type=int, help="Only scan the first N raw files.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(hero_name=args.hero, max_examples=args.max_examples, limit_files=args.limit_files)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_ROOT / "latest.json"
    txt_path = REPORT_ROOT / "latest.txt"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    txt_path.write_text(render_report_text(report) + "\n", encoding="utf-8")
    print(f"JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"TXT: {txt_path.relative_to(PROJECT_ROOT)}")
    print(f"Tagged flop hands: {report['meta']['tagged_flop_hands']}")


if __name__ == "__main__":
    main()
