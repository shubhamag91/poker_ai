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
AUDIT_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "river_seed_audit"
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


def build_audit(hero_name: str = DEFAULT_HERO_NAME, max_examples: int = 3, limit_files: int | None = None) -> dict[str, Any]:
    flop_library = build_flop_tree_spec_library()
    turn_library = build_turn_tree_spec_library()
    river_library = build_river_tree_spec_library()
    turn_seed_ids_by_family = build_turn_seed_id_index(flop_library)
    river_seed_ids_by_turn_family = build_river_seed_id_index(turn_library)
    turn_seed_family_map = turn_library["seed_family_map"]
    river_seed_family_map = river_library["seed_family_map"]

    family_bucket_summary: dict[str, dict[str, dict[str, Any]]] = defaultdict(
        lambda: defaultdict(
            lambda: {
                "hand_count": 0,
                "reachable_turn_family_counts": defaultdict(int),
                "active_mapped_river_seed_counts": defaultdict(int),
                "active_unmapped_river_seed_counts": defaultdict(int),
                "reachable_river_family_counts": defaultdict(int),
                "removed_river_size_branch_counts": defaultdict(int),
            }
        )
    )
    river_family_source_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    river_family_turn_source_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    unmapped_river_seed_turn_family_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    examples: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    river_policy_cache: dict[tuple[str, str], dict[str, Any]] = {}

    files_scanned = 0
    hands_scanned = 0
    tagged_flop_hands = 0
    hands_with_turn_seed_map = 0
    hands_with_active_mapped_turn_seed = 0
    hands_with_reachable_turn_family = 0
    hands_with_active_mapped_river_seed = 0
    hands_with_active_unmapped_river_seed = 0
    hands_pruned_to_no_active_mapped_turn_seed = 0

    raw_files = sorted(RAW_ROOT.glob("*.txt"))
    if limit_files is not None:
        raw_files = raw_files[:limit_files]

    def resolve_river_family_policy(river_family_id: str, board_bucket: str) -> dict[str, Any]:
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
            if family_id not in turn_seed_family_map:
                continue

            hands_with_turn_seed_map += 1
            board_bucket = tag.get("board_bucket") or "UNSPECIFIED"
            mapped_turn_seed_targets = turn_seed_family_map[family_id]
            removed_turn_seed_ids = set((tag.get("enforced_board_action_policy") or {}).get("removed_turn_seeds", []))
            all_turn_seed_ids = turn_seed_ids_by_family.get(family_id, [])
            active_turn_seed_ids = [seed_id for seed_id in all_turn_seed_ids if seed_id not in removed_turn_seed_ids]
            active_mapped_turn_seed_ids = [seed_id for seed_id in active_turn_seed_ids if seed_id in mapped_turn_seed_targets]
            reachable_turn_families = sorted({mapped_turn_seed_targets[seed_id] for seed_id in active_mapped_turn_seed_ids})

            if active_mapped_turn_seed_ids:
                hands_with_active_mapped_turn_seed += 1
            else:
                hands_pruned_to_no_active_mapped_turn_seed += 1

            if reachable_turn_families:
                hands_with_reachable_turn_family += 1

            active_mapped_river_seed_ids: set[str] = set()
            active_unmapped_river_seed_ids: set[str] = set()
            reachable_river_families: set[str] = set()
            river_seed_turn_families: dict[str, str] = {}

            for turn_family_id in reachable_turn_families:
                mapped_river_seed_targets = river_seed_family_map.get(turn_family_id, {})
                for river_seed_id in river_seed_ids_by_turn_family.get(turn_family_id, []):
                    river_seed_turn_families[river_seed_id] = turn_family_id
                    if river_seed_id in mapped_river_seed_targets:
                        active_mapped_river_seed_ids.add(river_seed_id)
                        reachable_river_families.add(mapped_river_seed_targets[river_seed_id])
                    else:
                        active_unmapped_river_seed_ids.add(river_seed_id)

            if active_mapped_river_seed_ids:
                hands_with_active_mapped_river_seed += 1
            if active_unmapped_river_seed_ids:
                hands_with_active_unmapped_river_seed += 1

            river_family_removed_sizes = {
                river_family_id: resolve_river_family_policy(river_family_id, board_bucket)["removed_size_branches"]
                for river_family_id in sorted(reachable_river_families)
            }

            bucket_summary = family_bucket_summary[family_id][board_bucket]
            bucket_summary["hand_count"] += 1
            for turn_family_id in reachable_turn_families:
                bucket_summary["reachable_turn_family_counts"][turn_family_id] += 1
            for river_seed_id in sorted(active_mapped_river_seed_ids):
                bucket_summary["active_mapped_river_seed_counts"][river_seed_id] += 1
            for river_seed_id in sorted(active_unmapped_river_seed_ids):
                bucket_summary["active_unmapped_river_seed_counts"][river_seed_id] += 1
                turn_family_id = river_seed_turn_families[river_seed_id]
                unmapped_river_seed_turn_family_counts[river_seed_id][turn_family_id] += 1
            for river_family_id in sorted(reachable_river_families):
                bucket_summary["reachable_river_family_counts"][river_family_id] += 1
                river_family_source_counts[river_family_id][family_id] += 1
                for removed_branch in river_family_removed_sizes[river_family_id]:
                    bucket_summary["removed_river_size_branch_counts"][f"{river_family_id}:{removed_branch}"] += 1
            for river_family_id in sorted(reachable_river_families):
                for turn_family_id in reachable_turn_families:
                    if river_family_id in river_seed_family_map.get(turn_family_id, {}).values():
                        river_family_turn_source_counts[river_family_id][turn_family_id] += 1

            bucket_examples = examples[family_id][board_bucket]
            if len(bucket_examples) < max_examples:
                bucket_examples.append(
                    {
                        "file": path.name,
                        "hand_header": hand.splitlines()[0] if hand.splitlines() else "unknown",
                        "matchup_id": tag.get("matchup_id"),
                        "template_ref": tag.get("template_ref"),
                        "flop_cards": extract_flop_cards(hand),
                        "board_bucket": board_bucket,
                        "reachable_turn_families": reachable_turn_families,
                        "active_mapped_river_seeds": sorted(active_mapped_river_seed_ids),
                        "active_unmapped_river_seeds": sorted(active_unmapped_river_seed_ids),
                        "reachable_river_families": sorted(reachable_river_families),
                        "river_removed_size_branches": river_family_removed_sizes,
                    }
                )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "meta": {
            "hero_name": hero_name,
            "files_scanned": files_scanned,
            "hands_scanned": hands_scanned,
            "tagged_flop_hands": tagged_flop_hands,
            "hands_with_turn_seed_map": hands_with_turn_seed_map,
            "hands_with_active_mapped_turn_seed": hands_with_active_mapped_turn_seed,
            "hands_with_reachable_turn_family": hands_with_reachable_turn_family,
            "hands_with_active_mapped_river_seed": hands_with_active_mapped_river_seed,
            "hands_with_active_unmapped_river_seed": hands_with_active_unmapped_river_seed,
            "hands_pruned_to_no_active_mapped_turn_seed": hands_pruned_to_no_active_mapped_turn_seed,
            "max_examples_per_bucket": max_examples,
        },
        "river_family_source_counts": {
            river_family_id: dict(sorted(source_counts.items()))
            for river_family_id, source_counts in sorted(river_family_source_counts.items())
        },
        "river_family_turn_source_counts": {
            river_family_id: dict(sorted(source_counts.items()))
            for river_family_id, source_counts in sorted(river_family_turn_source_counts.items())
        },
        "unmapped_river_seed_turn_family_counts": {
            seed_id: dict(sorted(source_counts.items()))
            for seed_id, source_counts in sorted(unmapped_river_seed_turn_family_counts.items())
        },
        "family_bucket_summary": {
            family_id: {
                bucket: {
                    "hand_count": summary["hand_count"],
                    "reachable_turn_family_counts": dict(sorted(summary["reachable_turn_family_counts"].items())),
                    "active_mapped_river_seed_counts": dict(sorted(summary["active_mapped_river_seed_counts"].items())),
                    "active_unmapped_river_seed_counts": dict(sorted(summary["active_unmapped_river_seed_counts"].items())),
                    "reachable_river_family_counts": dict(sorted(summary["reachable_river_family_counts"].items())),
                    "removed_river_size_branch_counts": dict(sorted(summary["removed_river_size_branch_counts"].items())),
                }
                for bucket, summary in sorted(bucket_summaries.items())
            }
            for family_id, bucket_summaries in sorted(family_bucket_summary.items())
        },
        "examples": {
            family_id: {bucket: rows for bucket, rows in sorted(bucket_rows.items())}
            for family_id, bucket_rows in sorted(examples.items())
        },
    }


def render_audit_text(report: dict[str, Any]) -> str:
    meta = report["meta"]
    lines = [
        "River seed audit",
        "================",
        f"Generated: {report['generated_at']}",
        f"Hero: {meta['hero_name']}",
        f"Files scanned: {meta['files_scanned']}",
        f"Hands scanned: {meta['hands_scanned']}",
        f"Tagged flop hands: {meta['tagged_flop_hands']}",
        f"Hands with turn seed map: {meta['hands_with_turn_seed_map']}",
        f"Hands with active mapped turn seed: {meta['hands_with_active_mapped_turn_seed']}",
        f"Hands with reachable turn family: {meta['hands_with_reachable_turn_family']}",
        f"Hands with active mapped river seed: {meta['hands_with_active_mapped_river_seed']}",
        f"Hands with active unmapped river seed: {meta['hands_with_active_unmapped_river_seed']}",
        f"Hands pruned to no active mapped turn seed: {meta['hands_pruned_to_no_active_mapped_turn_seed']}",
        f"Examples per bucket: {meta['max_examples_per_bucket']}",
        "",
        "River family reach by source flop family",
        "----------------------------------------",
    ]

    for river_family_id, source_counts in report["river_family_source_counts"].items():
        total = sum(source_counts.values())
        lines.append(f"- {river_family_id}: {total}")
        for source_family_id, count in source_counts.items():
            lines.append(f"  - {source_family_id}: {count}")

    lines.extend(["", "River family reach by source turn family", "----------------------------------------"])
    for river_family_id, source_counts in report["river_family_turn_source_counts"].items():
        total = sum(source_counts.values())
        lines.append(f"- {river_family_id}: {total}")
        for source_turn_family_id, count in source_counts.items():
            lines.append(f"  - {source_turn_family_id}: {count}")

    lines.extend(["", "Unmapped active river seeds", "---------------------------"])
    for seed_id, source_counts in report["unmapped_river_seed_turn_family_counts"].items():
        total = sum(source_counts.values())
        lines.append(f"- {seed_id}: {total}")
        for source_turn_family_id, count in source_counts.items():
            lines.append(f"  - {source_turn_family_id}: {count}")

    lines.extend(["", "Source flop family / board bucket detail", "----------------------------------------"])
    for family_id, bucket_summaries in report["family_bucket_summary"].items():
        lines.append(f"- {family_id}")
        for bucket, summary in bucket_summaries.items():
            turns = ", ".join(f"{turn_family}={count}" for turn_family, count in summary["reachable_turn_family_counts"].items()) or "none"
            mapped = ", ".join(f"{seed_id}={count}" for seed_id, count in summary["active_mapped_river_seed_counts"].items()) or "none"
            unmapped = ", ".join(f"{seed_id}={count}" for seed_id, count in summary["active_unmapped_river_seed_counts"].items()) or "none"
            rivers = ", ".join(f"{river_family}={count}" for river_family, count in summary["reachable_river_family_counts"].items()) or "none"
            removed_sizes = ", ".join(f"{branch}={count}" for branch, count in summary["removed_river_size_branch_counts"].items()) or "none"
            lines.append(
                f"  - {bucket}: hands={summary['hand_count']} | turn_families={turns} | river_seeds={mapped} | unmapped={unmapped} | river_families={rivers} | removed_sizes={removed_sizes}"
            )

    lines.extend(["", "Examples", "--------"])
    for family_id, bucket_rows in report["examples"].items():
        lines.append(f"- {family_id}")
        for bucket, rows in bucket_rows.items():
            lines.append(f"  - {bucket}")
            for row in rows:
                flop = " ".join(row.get("flop_cards") or []) or "unknown"
                turns = ", ".join(row.get("reachable_turn_families") or []) or "none"
                mapped = ", ".join(row.get("active_mapped_river_seeds") or []) or "none"
                unmapped = ", ".join(row.get("active_unmapped_river_seeds") or []) or "none"
                rivers = ", ".join(row.get("reachable_river_families") or []) or "none"
                removed_sizes = "; ".join(
                    f"{river_family}={', '.join(branches) if branches else 'none'}"
                    for river_family, branches in sorted((row.get("river_removed_size_branches") or {}).items())
                ) or "none"
                lines.append(f"    - {flop} | {row['matchup_id']} | turns={turns} | river_seeds={mapped} | unmapped={unmapped} | rivers={rivers} | removed_sizes={removed_sizes} | {row['file']}")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit real tagged flop hands by reachable turn families and reachable current river placeholder families."
    )
    parser.add_argument("--hero", default=DEFAULT_HERO_NAME, help="Hero name to use while tagging hands.")
    parser.add_argument("--max-examples", type=int, default=3, help="Examples to retain per family/bucket.")
    parser.add_argument("--limit-files", type=int, help="Only scan the first N raw files.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_audit(hero_name=args.hero, max_examples=args.max_examples, limit_files=args.limit_files)
    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    json_path = AUDIT_ROOT / "latest.json"
    txt_path = AUDIT_ROOT / "latest.txt"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    txt_path.write_text(render_audit_text(report) + "\n", encoding="utf-8")
    print(f"JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"TXT: {txt_path.relative_to(PROJECT_ROOT)}")
    print(f"Hands with active mapped river seed: {report['meta']['hands_with_active_mapped_river_seed']}")


if __name__ == "__main__":
    main()
