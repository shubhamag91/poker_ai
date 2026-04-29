#!/usr/bin/env python3
"""Showdown EV aggregator.

For hands that reach showdown, compute hero's actual chip-EV vs alternative action.
Aggregate per leak class.
"""
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARSED_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "parsed"
RAW_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "raw"
OUTPUT_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "showdown_ev"


def extract_showdown(hand_text: str) -> Optional[dict]:
    """Extract showdown info from hand text."""
    lines = hand_text.splitlines()
    
    hero_cards = None
    opponent_cards = None
    board = None
    hero_won = False
    pot = 0.0
    
    for line in lines:
        if "Dealt to Hero" in line:
            match = re.search(r"\[([\dTJQKA][cdhs] [\dTJQKA][cdhs])\]", line)
            if match:
                hero_cards = match.group(1)
        if "shows" in line and "Hero" not in line:
            match = re.search(r"\[([\dTJQKA][cdhs] [\dTJQKA][cdhs])\]", line)
            if match:
                opponent_cards = match.group(1)
        if "Board" in line:
            match = re.search(r"\[([\dTJQKA][cdhs] [\dTJQKA][cdhs] [\dTJQKA][cdhs])\]", line)
            if match:
                board = match.group(1)
        if "wins" in line and "Hero" in line:
            hero_won = True
        if "Total pot" in line:
            match = re.search(r"Total pot.*?\$?([\d.]+)", line)
            if match:
                pot = float(match.group(1))
    
    if not hero_cards or not opponent_cards or not board:
        return None
    
    return {
        "hero_cards": hero_cards,
        "opponent_cards": opponent_cards,
        "board": board,
        "hero_won": hero_won,
        "pot": pot,
    }


def find_showdowns(hand_class: str = None, limit: int = 100) -> list[dict]:
    """Find hands that reached showdown."""
    results = []
    
    for json_file in sorted(PARSED_ROOT.glob("*_analysis.json"), key=lambda p: -p.stat().st_mtime):
        try:
            data = json.loads(json_file.read_text())
        except:
            continue
        
        for spot in data.get("spots", []):
            if hand_class and spot.get("hand_class") != hand_class:
                continue
            
            parsed_stem = json_file.stem.replace("_analysis", "")
            raw_file = None
            for raw in RAW_ROOT.glob("*.txt"):
                if parsed_stem in raw.stem:
                    raw_file = raw
                    break
            
            if raw_file:
                content = raw_file.read_text()
                hands = content.split("=" * 40 + "\nHAND")
                idx = spot.get("index", 1)
                if idx < len(hands):
                    showdown = extract_showdown("HAND" + hands[idx])
                    if showdown:
                        showdown["hand_class"] = spot.get("hand_class")
                        showdown["position"] = spot.get("position")
                        showdown["stack"] = spot.get("hero_bb")
                        showdown["decision"] = spot.get("decision_type")
                        showdown["mistake"] = spot.get("mistake")
                        results.append(showdown)
            
            if len(results) >= limit:
                break
    
    return results


def aggregate_by_class() -> dict:
    """Aggregate EV by leak class."""
    all_showdowns = find_showdowns(limit=500)
    
    by_class = defaultdict(lambda: {"n": 0, "total_pot": 0.0, "hero_wins": 0})
    
    for sd in all_showdowns:
        hc = sd.get("hand_class", "unknown")
        by_class[hc]["n"] += 1
        by_class[hc]["total_pot"] += sd.get("pot", 0)
        if sd.get("hero_won"):
            by_class[hc]["hero_wins"] += 1
    
    results = {}
    for hc, data in by_class.items():
        n = data["n"]
        if n < 3:
            continue
        win_rate = data["hero_wins"] / n
        avg_pot = data["total_pot"] / n
        results[hc] = {
            "n": n,
            "win_rate": round(win_rate, 3),
            "avg_pot": round(avg_pot, 2),
        }
    
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Showdown EV aggregator")
    parser.add_argument("--leak-class", help="Filter by leak class")
    parser.add_argument("--limit", type=int, default=100, help="Max hands")
    args = parser.parse_args()
    
    if args.leak_class:
        showdowns = find_showdowns(args.leak_class, args.limit)
        print(f"Found {len(showdowns)} showdowns for {args.leak_class}")
        for sd in showdowns[:5]:
            print(f"  {sd['stack']:.1f} BB: Hero {'WON' if sd['hero_won'] else 'LOST'} ${sd['pot']:.0f}")
            print(f"    Hero: {sd['hero_cards']} vs {sd['opponent_cards']} on {sd['board']}")
    else:
        results = aggregate_by_class()
        print("Showdown EV by Leak Class")
        print("=" * 50)
        for hc, data in sorted(results.items(), key=lambda x: -x[1]["n"]):
            print(f"{hc}: n={data['n']} win_rate={data['win_rate']:.1%} avg_pot=${data['avg_pot']:.0f}")


if __name__ == "__main__":
    main()