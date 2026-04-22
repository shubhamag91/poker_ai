#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from hand_parser import identify_postflop_spec_tags, split_hands, read_file, extract_flop_cards, extract_turn_card, extract_river_card
from postflop_trees import build_flop_tree_spec_library, build_turn_tree_spec_library, build_river_tree_spec_library

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "raw"
REPORT_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "postflop_hero_deeper_actions"
DEFAULT_HERO_NAME = "Hero"


def extract_turn_action_lines(hand: str) -> list[str]:
    lines = hand.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("*** TURN ***"):
            start = i + 1
            break
    if start is None:
        return []

    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("*** RIVER ***") or lines[i].startswith("*** SUMMARY ***"):
            end = i
            break
    return [line.strip() for line in lines[start:end] if line.strip()]


def extract_river_action_lines(hand: str) -> list[str]:
    lines = hand.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("*** RIVER ***"):
            start = i + 1
            break
    if start is None:
        return []

    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("*** SUMMARY ***"):
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


def extract_hero_turn_decision(hand: str, hero_name: str) -> Optional[dict[str, Any]]:
    prior_events: list[dict[str, str]] = []
    for line in extract_turn_action_lines(hand):
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


def extract_hero_river_decision(hand: str, hero_name: str) -> Optional[dict[str, Any]]:
    prior_events: list[dict[str, str]] = []
    for line in extract_river_action_lines(hand):
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
    turn_summary: dict[str, Any] = defaultdict(
        lambda: defaultdict(
            lambda: {
                "hand_count": 0,
                "hero_action_counts": defaultdict(int),
            }
        )
    )
    river_summary: dict[str, Any] = defaultdict(
        lambda: defaultdict(
            lambda: {
                "hand_count": 0,
                "hero_action_counts": defaultdict(int),
            }
        )
    )
    
    overall_turn_counts: dict[str, int] = defaultdict(int)
    overall_river_counts: dict[str, int] = defaultdict(int)
    
    turn_examples: dict[str, Any] = defaultdict(lambda: defaultdict(list))
    river_examples: dict[str, Any] = defaultdict(lambda: defaultdict(list))

    files_scanned = 0
    hands_scanned = 0
    tagged_hands = 0
    hands_with_hero_turn_decision = 0
    hands_with_hero_river_decision = 0

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

            tagged_hands += 1
            family_id = tag["family_id"]
            hero_role = tag.get("hero_role") or "participant"
            board_bucket = tag.get("board_bucket") or "UNSPECIFIED"
            matchup_id = tag.get("matchup_id") or "unknown"

            hero_turn_decision = extract_hero_turn_decision(hand, hero_name)
            if hero_turn_decision:
                hands_with_hero_turn_decision += 1
                hero_action = hero_turn_decision["hero_action"]
                hero_context = hero_turn_decision["hero_context"]
                
                spot_key = f"{family_id} | {hero_role} | {board_bucket} | {hero_context}"
                turn_summary[family_id][spot_key]["hand_count"] += 1
                turn_summary[family_id][spot_key]["hero_action_counts"][hero_action] += 1
                overall_turn_counts[hero_action] += 1
                
                bucket_examples = turn_examples[family_id][spot_key]
                if len(bucket_examples) < max_examples:
                    bucket_examples.append({
                        "file": path.name,
                        "flop_cards": extract_flop_cards(hand),
                        "turn_card": extract_turn_card(hand),
                        "hero_action": hero_action,
                        "prior": hero_turn_decision["prior_actions"],
                    })

            hero_river_decision = extract_hero_river_decision(hand, hero_name)
            if hero_river_decision:
                hands_with_hero_river_decision += 1
                hero_action = hero_river_decision["hero_action"]
                hero_context = hero_river_decision["hero_context"]
                
                spot_key = f"{family_id} | {hero_role} | {board_bucket} | {hero_context}"
                river_summary[family_id][spot_key]["hand_count"] += 1
                river_summary[family_id][spot_key]["hero_action_counts"][hero_action] += 1
                overall_river_counts[hero_action] += 1
                
                bucket_examples = river_examples[family_id][spot_key]
                if len(bucket_examples) < max_examples:
                    bucket_examples.append({
                        "file": path.name,
                        "flop_cards": extract_flop_cards(hand),
                        "turn_card": extract_turn_card(hand),
                        "river_card": extract_river_card(hand),
                        "hero_action": hero_action,
                        "prior": hero_river_decision["prior_actions"],
                    })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "meta": {
            "hero_name": hero_name,
            "files_scanned": files_scanned,
            "hands_scanned": hands_scanned,
            "tagged_hands": tagged_hands,
            "hands_with_hero_turn_decision": hands_with_hero_turn_decision,
            "hands_with_hero_river_decision": hands_with_hero_river_decision,
        },
        "overall_turn_actions": dict(overall_turn_counts),
        "overall_river_actions": dict(overall_river_counts),
        "turn_summary": {k: dict(v) for k, v in turn_summary.items()},
        "river_summary": {k: dict(v) for k, v in river_summary.items()},
        "turn_examples": {k: {kk: vv for kk, vv in v.items()} for k, v in turn_examples.items()},
        "river_examples": {k: {kk: vv for kk, vv in v.items()} for k, v in river_examples.items()},
    }


def format_report(data: dict[str, Any]) -> str:
    lines = [
        "Postflop Hero Deeper Actions (Turn + River)",
        "=" * 50,
        f"Generated: {data['generated_at']}",
        f"Hero: {data['meta']['hero_name']}",
        f"Files scanned: {data['meta']['files_scanned']}",
        f"Hands scanned: {data['meta']['hands_scanned']}",
        f"Tagged hands: {data['meta']['tagged_hands']}",
        f"Hands with hero turn decision: {data['meta']['hands_with_hero_turn_decision']}",
        f"Hands with hero river decision: {data['meta']['hands_with_hero_river_decision']}",
        "",
    ]

    if data["overall_turn_actions"]:
        lines.append("=== OVERALL TURN ACTIONS ===")
        for action, count in sorted(data["overall_turn_actions"].items(), key=lambda x: -x[1]):
            lines.append(f"  {action}: {count}")
        lines.append("")

    if data["overall_river_actions"]:
        lines.append("=== OVERALL RIVER ACTIONS ===")
        for action, count in sorted(data["overall_river_actions"].items(), key=lambda x: -x[1]):
            lines.append(f"  {action}: {count}")
        lines.append("")

    if data["turn_summary"]:
        lines.append("=== TURN ACTIONS BY FAMILY ===")
        for family_id in sorted(data["turn_summary"].keys()):
            lines.append(f"\n--- {family_id} ---")
            for spot_key, summary in sorted(data["turn_summary"][family_id].items()):
                actions_str = ", ".join(f"{k}={v}" for k, v in sorted(summary["hero_action_counts"].items()))
                lines.append(f"  {spot_key}: hands={summary['hand_count']} | {actions_str}")
        lines.append("")

    if data["river_summary"]:
        lines.append("=== RIVER ACTIONS BY FAMILY ===")
        for family_id in sorted(data["river_summary"].keys()):
            lines.append(f"\n--- {family_id} ---")
            for spot_key, summary in sorted(data["river_summary"][family_id].items()):
                actions_str = ", ".join(f"{k}={v}" for k, v in sorted(summary["hero_action_counts"].items()))
                lines.append(f"  {spot_key}: hands={summary['hand_count']} | {actions_str}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Track Hero's turn and river actions postflop")
    parser.add_argument("--hero", default=DEFAULT_HERO_NAME, help="Hero name to use")
    parser.add_argument("--max-examples", type=int, default=2, help="Examples per bucket")
    parser.add_argument("--limit-files", type=int, help="Limit files scanned")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)

    data = build_report(hero_name=args.hero, max_examples=args.max_examples, limit_files=args.limit_files)

    json_path = REPORT_ROOT / "latest.json"
    json_path.write_text(json.dumps(data, indent=2))
    print(f"JSON: {json_path}")

    if not args.json:
        txt_path = REPORT_ROOT / "latest.txt"
        txt_path.write_text(format_report(data))
        print(f"TXT: {txt_path}")

    print(f"Hands with hero turn decision: {data['meta']['hands_with_hero_turn_decision']}")
    print(f"Hands with hero river decision: {data['meta']['hands_with_hero_river_decision']}")


if __name__ == "__main__":
    main()
