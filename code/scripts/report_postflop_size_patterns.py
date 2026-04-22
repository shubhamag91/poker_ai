#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from hand_parser import (
    identify_postflop_spec_tags,
    split_hands,
    read_file,
    extract_flop_cards,
    extract_turn_card,
    extract_river_card,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "raw"
REPORT_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "postflop_size_patterns"
DEFAULT_HERO_NAME = "Hero"


def extract_flop_actions(hand: str) -> list[tuple[str, str, str]]:
    lines = hand.splitlines()
    results = []
    for i, line in enumerate(lines):
        if not line.startswith("*** FLOP ***"):
            continue
        start = i + 1
        end = len(lines)
        for j in range(i + 1, len(lines)):
            if lines[j].startswith("*** TURN ***"):
                end = j
                break
        for line in lines[start:end]:
            line = line.strip()
            if not line or ":" not in line:
                continue
            if line.startswith("***") or line.startswith("Dealt to") or line.startswith("Uncalled"):
                continue
            actor, rest = line.split(":", 1)
            rest = rest.strip().lower()
            if rest.startswith("bets "):
                match = re.search(r"bets \$?([\d.]+)", rest)
                size = match.group(1) if match else "unknown"
                results.append(("bet", actor, size))
            elif rest.startswith("checks"):
                results.append(("check", actor, ""))
            elif rest.startswith("calls "):
                results.append(("call", actor, ""))
            elif rest.startswith("raises "):
                results.append(("raise", actor, ""))
            elif rest.startswith("folds"):
                results.append(("fold", actor, ""))
        break
    return results


def extract_turn_actions(hand: str) -> list[tuple[str, str, str]]:
    lines = hand.splitlines()
    results = []
    for i, line in enumerate(lines):
        if not line.startswith("*** TURN ***"):
            continue
        start = i + 1
        end = len(lines)
        for j in range(i + 1, len(lines)):
            if lines[j].startswith("*** RIVER ***"):
                end = j
                break
        for line in lines[start:end]:
            line = line.strip()
            if not line or ":" not in line:
                continue
            if line.startswith("***") or line.startswith("Dealt to") or line.startswith("Uncalled"):
                continue
            actor, rest = line.split(":", 1)
            rest = rest.strip().lower()
            if rest.startswith("bets "):
                match = re.search(r"bets \$?([\d.]+)", rest)
                size = match.group(1) if match else "unknown"
                results.append(("bet", actor, size))
            elif rest.startswith("checks"):
                results.append(("check", actor, ""))
            elif rest.startswith("calls "):
                results.append(("call", actor, ""))
            elif rest.startswith("raises "):
                results.append(("raise", actor, ""))
            elif rest.startswith("folds"):
                results.append(("fold", actor, ""))
        break
    return results


def extract_river_actions(hand: str) -> list[tuple[str, str, str]]:
    lines = hand.splitlines()
    results = []
    for i, line in enumerate(lines):
        if not line.startswith("*** RIVER ***"):
            continue
        start = i + 1
        end = len(lines)
        for j in range(i + 1, len(lines)):
            if lines[j].startswith("*** SUMMARY ***"):
                end = j
                break
        for line in lines[start:end]:
            line = line.strip()
            if not line or ":" not in line:
                continue
            if line.startswith("***") or line.startswith("Dealt to") or line.startswith("Uncalled"):
                continue
            actor, rest = line.split(":", 1)
            rest = rest.strip().lower()
            if rest.startswith("bets "):
                match = re.search(r"bets \$?([\d.]+)", rest)
                size = match.group(1) if match else "unknown"
                results.append(("bet", actor, size))
            elif rest.startswith("checks"):
                results.append(("check", actor, ""))
            elif rest.startswith("calls "):
                results.append(("call", actor, ""))
            elif rest.startswith("raises "):
                results.append(("raise", actor, ""))
            elif rest.startswith("folds"):
                results.append(("fold", actor, ""))
        break
    return results


def classify_size(size_str: str, pot: float) -> str:
    if not size_str or size_str == "unknown":
        return "unknown"
    try:
        size = float(size_str)
        if pot <= 0:
            return "unknown"
        ratio = size / pot
        if ratio <= 0.33:
            return "small"
        elif ratio <= 0.55:
            return "medium"
        elif ratio <= 0.8:
            return "large"
        else:
            return "overbet"
    except ValueError:
        return "unknown"


def classify_pot(flop_actions: list[tuple[str, str, str]]) -> float:
    for action, actor, size in flop_actions:
        if action == "bet" and size != "unknown":
            try:
                return float(size)
            except ValueError:
                pass
    return 0.0


def find_hero_action(actions: list[tuple[str, str, str]], hero: str) -> Optional[tuple[str, str]]:
    for action, actor, size in actions:
        if actor == hero:
            return (action, size)
    return None


def find_hero_actions_by_street(actions: list[tuple[str, str, str]], hero: str) -> list[tuple[str, str]]:
    """Find all hero actions in a street (multiple possible)."""
    result = []
    for action, actor, size in actions:
        if actor == hero:
            result.append((action, size))
    return result


def build_report(hero_name: str = DEFAULT_HERO_NAME, limit_files: int | None = None) -> dict[str, Any]:
    delayed_cbet: dict[str, Any] = defaultdict(lambda: defaultdict(int))
    donk_leads: dict[str, Any] = defaultdict(lambda: defaultdict(int))
    probe_lines: dict[str, Any] = defaultdict(lambda: defaultdict(int))
    size_distribution: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    files_scanned = 0
    hands_scanned = 0
    hands_with_tags = 0

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

            hands_with_tags += 1
            family_id = tag["family_id"]
            hero_role = tag.get("hero_role") or "participant"
            board_bucket = tag.get("board_bucket") or "UNSPECIFIED"

            flop_actions = extract_flop_actions(hand)
            turn_actions = extract_turn_actions(hand)
            river_actions = extract_river_actions(hand)

            pot = classify_pot(flop_actions)

            hero_flop = find_hero_action(flop_actions, hero_name)
            hero_turn = find_hero_action(turn_actions, hero_name)
            hero_river = find_hero_action(river_actions, hero_name)

            if hero_flop and hero_turn:
                flop_act, flop_size = hero_flop
                turn_act, turn_size = hero_turn

                if flop_act == "check" and turn_act == "bet":
                    bucket = f"{family_id} | {board_bucket}"
                    delayed_cbet[bucket]["turn"] += 1
                    if turn_size != "unknown":
                        size_class = classify_size(turn_size, pot)
                        size_distribution["delayed_cbet_turn"][size_class] += 1

                if flop_act == "bet" and turn_act == "check":
                    bucket = f"{family_id} | {board_bucket}"
                    delayed_cbet[bucket]["turn_chk_after_bet"] += 1

            if hero_turn and hero_river:
                turn_act_t, turn_size_t = hero_turn
                river_act, river_size = hero_river

                if turn_act_t == "check" and river_act == "bet":
                    bucket = f"{family_id} | {board_bucket}"
                    delayed_cbet[bucket]["river"] += 1
                    if river_size != "unknown":
                        size_class = classify_size(river_size, pot)
                        size_distribution["delayed_cbet_river"][size_class] += 1

            # Donk leads: hero bets first on flop without prior aggression
            hero_actions_flop = find_hero_actions_by_street(flop_actions, hero_name)
            if hero_actions_flop:
                action, size = hero_actions_flop[0]
                acted_before_pfr = False
                for act, actor, _ in flop_actions:
                    if actor != hero_name and act in ("bet", "raise"):
                        acted_before_pfr = True
                        break
                if action == "bet" and not acted_before_pfr:
                    bucket = f"{family_id} | {board_bucket}"
                    donk_leads[bucket]["flop"] += 1
                    if size != "unknown":
                        size_class = classify_size(size, pot)
                        size_distribution["donk_lead"][size_class] += 1

            # Probes: hero bets after checking on earlier street
            hero_actions_turn = find_hero_actions_by_street(turn_actions, hero_name)
            hero_actions_river = find_hero_actions_by_street(river_actions, hero_name)

            if hero_actions_turn and hero_flop and hero_flop[0] == "check":
                action, size = hero_actions_turn[0]
                checked_to_turn = False
                for act, actor, _ in flop_actions:
                    if actor == hero_name and act == "check":
                        checked_to_turn = True
                        break
                if action == "bet" and checked_to_turn:
                    bucket = f"{family_id} | {board_bucket}"
                    probe_lines[bucket]["turn"] += 1
                    if size != "unknown":
                        size_class = classify_size(size, pot)
                        size_distribution["probe"][size_class] += 1

            if hero_actions_river and hero_turn and hero_turn[0] == "check":
                action, size = hero_actions_river[0]
                checked_to_river = False
                for act, actor, _ in river_actions:
                    if actor != hero_name and act == "bet":
                        checked_to_river = True
                        break
                if action == "bet" and checked_to_river:
                    bucket = f"{family_id} | {board_bucket}"
                    probe_lines[bucket]["river"] += 1
                    if size != "unknown":
                        size_class = classify_size(size, pot)
                        size_distribution["probe"][size_class] += 1

            if hero_flop:
                act, size = hero_flop
                if act == "bet" and size != "unknown":
                    size_class = classify_size(size, pot)
                    size_distribution["flop_cbet"][size_class] += 1
            if hero_turn:
                act, size = hero_turn
                if act == "bet" and size != "unknown":
                    size_class = classify_size(size, pot)
                    size_distribution["turn_bet"][size_class] += 1
            if hero_river:
                act, size = hero_river
                if act == "bet" and size != "unknown":
                    size_class = classify_size(size, pot)
                    size_distribution["river_bet"][size_class] += 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "meta": {
            "hero_name": hero_name,
            "files_scanned": files_scanned,
            "hands_scanned": hands_scanned,
            "hands_with_tags": hands_with_tags,
        },
        "delayed_cbet": {k: dict(v) for k, v in delayed_cbet.items()},
        "donk_leads": {k: dict(v) for k, v in donk_leads.items()},
        "probe_lines": {k: dict(v) for k, v in probe_lines.items()},
        "size_distribution": {
            k: dict(v) for k, v in size_distribution.items()
        },
    }


def format_report(data: dict[str, Any]) -> str:
    lines = [
        "Postflop Size & Line Patterns",
        "=" * 50,
        f"Generated: {data['generated_at']}",
        f"Files scanned: {data['meta']['files_scanned']}",
        f"Hands scanned: {data['meta']['hands_scanned']}",
        f"Hands with tags: {data['meta']['hands_with_tags']}",
        "",
    ]

    if data["size_distribution"]:
        lines.append("=== SIZE DISTRIBUTION BY STREET ===")
        for street, counts in sorted(data["size_distribution"].items()):
            total = sum(counts.values())
            if total == 0:
                continue
            lines.append(f"\n--- {street} ---")
            for size, count in sorted(counts.items(), key=lambda x: -x[1]):
                pct = count / total * 100
                lines.append(f"  {size}: {count} ({pct:.0f}%)")

    if data["delayed_cbet"]:
        lines.append("\n=== DELAYED CBET ===")
        for bucket, counts in sorted(data["delayed_cbet"].items()):
            total = sum(counts.values())
            if total == 0:
                continue
            lines.append(f"\n{bucket}: {total}")
            for street, count in sorted(counts.items()):
                if count:
                    lines.append(f"  {street}: {count}")

    if data["donk_leads"]:
        lines.append("\n=== DONK LEADS ===")
        for bucket, counts in sorted(data["donk_leads"].items()):
            total = sum(counts.values())
            if total == 0:
                continue
            lines.append(f"{bucket}: {total}")

    if data["probe_lines"]:
        lines.append("\n=== PROBE LINES ===")
        for bucket, counts in sorted(data["probe_lines"].items()):
            total = sum(counts.values())
            if total == 0:
                continue
            lines.append(f"{bucket}: {total}")
            for street, count in sorted(counts.items()):
                if count:
                    lines.append(f"  {street}: {count}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Track bet sizes, delayed cbets, donk leads, probe lines"
    )
    parser.add_argument("--hero", default=DEFAULT_HERO_NAME, help="Hero name to use")
    parser.add_argument("--limit-files", type=int, help="Limit files scanned")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)

    data = build_report(hero_name=args.hero, limit_files=args.limit_files)

    json_path = REPORT_ROOT / "latest.json"
    json_path.write_text(json.dumps(data, indent=2))
    print(f"JSON: {json_path}")

    if not args.json:
        txt_path = REPORT_ROOT / "latest.txt"
        txt_path.write_text(format_report(data))
        print(f"TXT: {txt_path}")

    total_bets = sum(
        sum(s.values())
        for s in data["size_distribution"].values()
    )
    print(f"Total bet actions with size: {total_bets}")


if __name__ == "__main__":
    main()