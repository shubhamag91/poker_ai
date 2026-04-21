#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from hand_parser import identify_postflop_spec_tags, split_hands, read_file, extract_flop_cards

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "raw"
AUDIT_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "postflop_bucket_audit"
DEFAULT_HERO_NAME = "Hero"

POLICY_FAMILIES = {
    "srp_ip_pfr_flop",
    "srp_oop_caller_flop",
    "srp_oop_pfr_flop",
    "three_bet_ip_3bettor_flop",
    "three_bet_oop_3bettor_flop",
    "bvb_flop_aggressive",
    "bvb_defender_flop",
    "limped_pot_heads_up_flop",
    "raised_after_limp_ip_aggressor_flop",
    "raised_after_limp_oop_aggressor_flop",
    "four_bet_ip_aggressor_flop",
    "four_bet_oop_aggressor_flop",
    "five_bet_plus_ip_aggressor_flop",
    "five_bet_plus_oop_aggressor_flop",
    "multiway_srp_3way_oop_aggressor_flop",
    "multiway_srp_3way_middle_aggressor_flop",
    "multiway_srp_3way_ip_aggressor_flop",
    "multiway_3bp_3way_oop_aggressor_flop",
    "multiway_3bp_3way_middle_aggressor_flop",
    "multiway_3bp_3way_ip_aggressor_flop",
    "raised_after_limp_3way_middle_aggressor_flop",
    "raised_after_limp_3way_ip_aggressor_flop",
    "four_bet_3way_oop_aggressor_flop",
    "four_bet_3way_middle_aggressor_flop",
    "four_bet_3way_ip_aggressor_flop",
}


def build_audit(hero_name: str = DEFAULT_HERO_NAME, max_examples: int = 3, limit_files: int | None = None) -> dict[str, Any]:
    family_bucket_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    examples: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    lead_policy_summary: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    files_scanned = 0
    hands_scanned = 0
    tagged_hands = 0

    raw_files = sorted(RAW_ROOT.glob("*.txt"))
    if limit_files is not None:
        raw_files = raw_files[:limit_files]

    for path in raw_files:
        files_scanned += 1
        for hand in split_hands(read_file(path)):
            hands_scanned += 1
            tag = identify_postflop_spec_tags(hand, hero_name)
            if not tag.get("available"):
                continue
            if "family_id" not in tag or "board_bucket" not in tag or not tag.get("board_bucket"):
                continue

            tagged_hands += 1
            family_id = tag["family_id"]
            board_bucket = tag["board_bucket"]
            family_bucket_counts[family_id][board_bucket] += 1

            policy = tag.get("enforced_board_action_policy") or {}
            pruned = policy.get("removed_lead_branches", [])
            removed_sizes = policy.get("removed_size_branches", [])
            removed_turn_seeds = policy.get("removed_turn_seeds", [])
            pruning_state = "pruned" if pruned or removed_sizes or removed_turn_seeds else "enabled"
            if family_id in POLICY_FAMILIES:
                lead_policy_summary[family_id][board_bucket][pruning_state] += 1

            bucket_examples = examples[family_id][board_bucket]
            if len(bucket_examples) >= max_examples:
                continue

            bucket_examples.append(
                {
                    "file": path.name,
                    "hand_header": hand.splitlines()[0] if hand.splitlines() else "unknown",
                    "matchup_id": tag.get("matchup_id"),
                    "template_ref": tag.get("template_ref"),
                    "flop_cards": extract_flop_cards(hand),
                    "positions": tag.get("positions"),
                    "removed_lead_branches": pruned,
                    "removed_size_branches": removed_sizes,
                    "removed_turn_seeds": removed_turn_seeds,
                }
            )

    return {
        "meta": {
            "hero_name": hero_name,
            "files_scanned": files_scanned,
            "hands_scanned": hands_scanned,
            "tagged_hands_with_board_bucket": tagged_hands,
            "max_examples_per_bucket": max_examples,
        },
        "family_bucket_counts": {
            family_id: dict(sorted(bucket_counts.items()))
            for family_id, bucket_counts in sorted(family_bucket_counts.items())
        },
        "lead_policy_summary": {
            family_id: {bucket: dict(states) for bucket, states in sorted(bucket_counts.items())}
            for family_id, bucket_counts in sorted(lead_policy_summary.items())
        },
        "examples": {
            family_id: {bucket: rows for bucket, rows in sorted(bucket_rows.items())}
            for family_id, bucket_rows in sorted(examples.items())
        },
    }


def render_audit_text(report: dict[str, Any]) -> str:
    meta = report["meta"]
    lines = [
        "Postflop board-bucket audit",
        "==========================",
        f"Hero: {meta['hero_name']}",
        f"Files scanned: {meta['files_scanned']}",
        f"Hands scanned: {meta['hands_scanned']}",
        f"Tagged hands with board bucket: {meta['tagged_hands_with_board_bucket']}",
        f"Examples per bucket: {meta['max_examples_per_bucket']}",
        "",
        "Policy-tracked families",
        "-----------------------",
    ]

    for family_id, bucket_counts in report["lead_policy_summary"].items():
        lines.append(f"- {family_id}")
        for bucket, states in bucket_counts.items():
            enabled = states.get("enabled", 0)
            pruned = states.get("pruned", 0)
            lines.append(f"  - {bucket}: enabled={enabled}, pruned={pruned}")

    lines.extend(["", "Examples", "--------"])
    for family_id, bucket_rows in report["examples"].items():
        lines.append(f"- {family_id}")
        for bucket, rows in bucket_rows.items():
            lines.append(f"  - {bucket}")
            for row in rows:
                flop = " ".join(row.get("flop_cards") or []) or "unknown"
                removed_leads = ", ".join(row.get("removed_lead_branches") or []) or "none"
                removed_sizes = ", ".join(row.get("removed_size_branches") or []) or "none"
                removed_turns = ", ".join(row.get("removed_turn_seeds") or []) or "none"
                lines.append(f"    - {flop} | {row['matchup_id']} | leads={removed_leads} | sizes={removed_sizes} | turns={removed_turns} | {row['file']}")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit real tagged flop hands by family and board bucket.")
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
    print(f"Tagged hands with board bucket: {report['meta']['tagged_hands_with_board_bucket']}")


if __name__ == "__main__":
    main()
