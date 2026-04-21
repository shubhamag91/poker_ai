#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from hand_parser import identify_postflop_spec_tags, split_hands, read_file, extract_flop_cards
from postflop_trees import build_flop_tree_spec_library, build_turn_tree_spec_library, build_river_tree_spec_library

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "raw"
REPORT_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "postflop_hero_flop_actions"
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


def extract_flop_action_lines(hand: str) -> list[str]:
    lines = hand.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("*** FLOP ***"):
            start = i + 1
            break
    if start is None:
        return []

    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("*** TURN ***") or lines[i].startswith("*** RIVER ***") or lines[i].startswith("*** SUMMARY ***"):
            end = i
            break
    return [line.strip() for line in lines[start:end] if line.strip()]


def parse_postflop_action_line(line: str) -> Optional[dict[str, str]]:
    if not line or ":" not in line or line.startswith("***") or line.startswith("Dealt to ") or line.startswith("Uncalled bet"):
        return None
    actor, rest = line.split(":", 1)
    rest = rest.strip().lower()
    if rest.startswith("checks"):
        return {"actor": actor, "type": "check"}
    if rest.startswith("bets "):
        return {"actor": actor, "type": "bet"}
    if rest.startswith("calls "):
        return {"actor": actor, "type": "call"}
    if rest.startswith("raises "):
        return {"actor": actor, "type": "raise"}
    if rest.startswith("folds"):
        return {"actor": actor, "type": "fold"}
    return None


def extract_first_hero_flop_decision(hand: str, hero_name: str) -> Optional[dict[str, Any]]:
    prior_events: list[dict[str, str]] = []
    for line in extract_flop_action_lines(hand):
        event = parse_postflop_action_line(line)
        if not event:
            continue
        if event["actor"] == hero_name:
            if any(prior["type"] == "raise" for prior in prior_events):
                hero_context = "facing_raise"
            elif any(prior["type"] == "bet" for prior in prior_events):
                hero_context = "facing_bet"
            elif any(prior["type"] == "check" for prior in prior_events):
                hero_context = "checked_to_hero"
            else:
                hero_context = "first_to_act"
            return {
                "hero_action": event["type"],
                "hero_context": hero_context,
                "prior_actions": [prior["type"] for prior in prior_events],
            }
        prior_events.append(event)
    return None


def build_report(hero_name: str = DEFAULT_HERO_NAME, max_examples: int = 2, limit_files: int | None = None) -> dict[str, Any]:
    flop_library = build_flop_tree_spec_library()
    turn_library = build_turn_tree_spec_library()
    river_library = build_river_tree_spec_library()
    turn_seed_ids_by_family = build_turn_seed_id_index(flop_library)
    river_seed_ids_by_turn_family = build_river_seed_id_index(turn_library)
    turn_seed_family_map = turn_library["seed_family_map"]
    river_seed_family_map = river_library["seed_family_map"]

    spot_summary: dict[str, dict[str, dict[str, Any]]] = defaultdict(
        lambda: defaultdict(
            lambda: {
                "hand_count": 0,
                "hero_action_counts": defaultdict(int),
                "reachable_turn_family_counts": defaultdict(int),
                "reachable_river_family_counts": defaultdict(int),
            }
        )
    )
    family_context_counts: dict[str, int] = defaultdict(int)
    overall_action_counts: dict[str, int] = defaultdict(int)
    examples: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))

    files_scanned = 0
    hands_scanned = 0
    tagged_flop_hands = 0
    hands_with_hero_flop_decision = 0

    raw_files = sorted(RAW_ROOT.glob("*.txt"))
    if limit_files is not None:
        raw_files = raw_files[:limit_files]

    for path in raw_files:
        files_scanned += 1
        for hand in split_hands(read_file(path)):
            hands_scanned += 1
            tag = identify_postflop_spec_tags(hand, hero_name)
            if not tag.get("available") or "family_id" not in tag:
                continue

            tagged_flop_hands += 1
            hero_flop_decision = extract_first_hero_flop_decision(hand, hero_name)
            if not hero_flop_decision:
                continue

            hands_with_hero_flop_decision += 1
            family_id = tag["family_id"]
            hero_role = tag.get("hero_role") or "participant"
            board_bucket = tag.get("board_bucket") or "UNSPECIFIED"
            hero_context = hero_flop_decision["hero_context"]
            hero_action = hero_flop_decision["hero_action"]
            matchup_id = tag.get("matchup_id") or "unknown"

            spot_key = f"{family_id} | {hero_role} | {board_bucket} | {hero_context}"
            family_context_counts[spot_key] += 1
            overall_action_counts[hero_action] += 1

            summary = spot_summary[family_id][f"{hero_role} | {board_bucket} | {hero_context}"]
            summary["hand_count"] += 1
            summary["hero_action_counts"][hero_action] += 1

            reachable_turn_families: list[str] = []
            reachable_river_families: set[str] = set()
            if family_id in turn_seed_family_map:
                mapped_turn_seed_targets = turn_seed_family_map[family_id]
                removed_turn_seed_ids = set((tag.get("enforced_board_action_policy") or {}).get("removed_turn_seeds", []))
                all_turn_seed_ids = turn_seed_ids_by_family.get(family_id, [])
                active_turn_seed_ids = [seed_id for seed_id in all_turn_seed_ids if seed_id not in removed_turn_seed_ids]
                reachable_turn_families = sorted({mapped_turn_seed_targets[seed_id] for seed_id in active_turn_seed_ids if seed_id in mapped_turn_seed_targets})
                for turn_family_id in reachable_turn_families:
                    summary["reachable_turn_family_counts"][turn_family_id] += 1
                    for river_seed_id in river_seed_ids_by_turn_family.get(turn_family_id, []):
                        river_family_id = river_seed_family_map.get(turn_family_id, {}).get(river_seed_id)
                        if river_family_id:
                            reachable_river_families.add(river_family_id)
            for river_family_id in sorted(reachable_river_families):
                summary["reachable_river_family_counts"][river_family_id] += 1

            bucket_examples = examples[family_id][f"{hero_role} | {board_bucket} | {hero_context}"]
            if len(bucket_examples) < max_examples:
                bucket_examples.append(
                    {
                        "file": path.name,
                        "hand_header": hand.splitlines()[0] if hand.splitlines() else "unknown",
                        "matchup_id": matchup_id,
                        "hero_role": hero_role,
                        "flop_cards": extract_flop_cards(hand),
                        "hero_action": hero_action,
                        "prior_actions": hero_flop_decision["prior_actions"],
                        "reachable_turn_families": reachable_turn_families,
                        "reachable_river_families": sorted(reachable_river_families),
                    }
                )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "meta": {
            "hero_name": hero_name,
            "files_scanned": files_scanned,
            "hands_scanned": hands_scanned,
            "tagged_flop_hands": tagged_flop_hands,
            "hands_with_hero_flop_decision": hands_with_hero_flop_decision,
            "max_examples_per_bucket": max_examples,
        },
        "overall_action_counts": _sorted_counter(overall_action_counts),
        "top_family_context_counts": _sorted_counter(family_context_counts),
        "spot_summary": {
            family_id: {
                bucket_context: {
                    "hand_count": summary["hand_count"],
                    "hero_action_counts": _sorted_counter(summary["hero_action_counts"]),
                    "reachable_turn_family_counts": _sorted_counter(summary["reachable_turn_family_counts"]),
                    "reachable_river_family_counts": _sorted_counter(summary["reachable_river_family_counts"]),
                }
                for bucket_context, summary in sorted(bucket_summaries.items(), key=lambda item: (-item[1]["hand_count"], item[0]))
            }
            for family_id, bucket_summaries in sorted(
                spot_summary.items(), key=lambda item: (-sum(entry["hand_count"] for entry in item[1].values()), item[0])
            )
        },
        "examples": {
            family_id: {bucket_context: rows for bucket_context, rows in sorted(bucket_rows.items())}
            for family_id, bucket_rows in sorted(examples.items())
        },
    }


def render_report_text(report: dict[str, Any]) -> str:
    meta = report["meta"]
    lines = [
        "Postflop hero flop actions",
        "==========================",
        f"Generated: {report['generated_at']}",
        f"Hero: {meta['hero_name']}",
        f"Files scanned: {meta['files_scanned']}",
        f"Hands scanned: {meta['hands_scanned']}",
        f"Tagged flop hands: {meta['tagged_flop_hands']}",
        f"Hands with hero flop decision: {meta['hands_with_hero_flop_decision']}",
        f"Examples per bucket: {meta['max_examples_per_bucket']}",
        "",
        "Overall hero flop actions",
        "-------------------------",
    ]

    for action, count in report["overall_action_counts"].items():
        lines.append(f"- {action}: {count}")

    lines.extend(["", "Top family / hero-role / board-bucket / context spots", "-----------------------------------------------------"])
    for spot, count in list(report["top_family_context_counts"].items())[:25]:
        lines.append(f"- {spot}: {count}")

    lines.extend(["", "Spot summaries", "--------------"])
    for family_id, bucket_rows in report["spot_summary"].items():
        lines.append(f"- {family_id}")
        for bucket_context, summary in bucket_rows.items():
            hero_actions = ", ".join(f"{action}={count}" for action, count in summary["hero_action_counts"].items()) or "none"
            turns = ", ".join(f"{turn_family}={count}" for turn_family, count in summary["reachable_turn_family_counts"].items()) or "none"
            rivers = ", ".join(f"{river_family}={count}" for river_family, count in summary["reachable_river_family_counts"].items()) or "none"
            lines.append(f"  - {bucket_context}: hands={summary['hand_count']} | hero_actions={hero_actions} | turn_reach={turns} | river_reach={rivers}")

    lines.extend(["", "Examples", "--------"])
    for family_id, bucket_rows in report["examples"].items():
        lines.append(f"- {family_id}")
        for bucket_context, rows in bucket_rows.items():
            lines.append(f"  - {bucket_context}")
            for row in rows:
                flop = " ".join(row.get("flop_cards") or []) or "unknown"
                prior = ", ".join(row.get("prior_actions") or []) or "none"
                turns = ", ".join(row.get("reachable_turn_families") or []) or "none"
                rivers = ", ".join(row.get("reachable_river_families") or []) or "none"
                lines.append(f"    - {flop} | {row['matchup_id']} | hero_action={row['hero_action']} | prior={prior} | turns={turns} | rivers={rivers} | {row['file']}")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the first hero-action-frequency layer by measuring Hero's first flop decision on top of the tagged postflop study surface."
    )
    parser.add_argument("--hero", default=DEFAULT_HERO_NAME, help="Hero name to use while tagging hands.")
    parser.add_argument("--max-examples", type=int, default=2, help="Examples to retain per family / hero-role / board-bucket / context.")
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
    print(f"Hands with hero flop decision: {report['meta']['hands_with_hero_flop_decision']}")


if __name__ == "__main__":
    main()
