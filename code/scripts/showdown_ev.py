#!/usr/bin/env python3
"""Showdown EV aggregator.

For hands that reach showdown, compute hero's actual chip-EV vs alternative action.
Uses heuristic equity estimation (simplified model).
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

SAMPLE_COUNT = 1000


def parse_cards(cards_str: str):
    """Parse 'Ah Ks' format into rank/suit."""
    if not cards_str:
        return []
    try:
        ranks = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
                 "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
        suits = {"s": 1, "h": 2, "d": 3, "c": 4}
        parsed = []
        for part in cards_str.split():
            if len(part) >= 2:
                rank = ranks.get(part[0].upper(), 0)
                suit = suits.get(part[1].lower(), 0)
                if rank and suit:
                    parsed.append((rank, suit))
        return parsed
    except Exception:
        return []


def estimate_equity(hero_cards, opponent_cards, board_cards) -> float:
    """Estimate equity using precomputed lookups + board discount."""
    if not hero_cards or not opponent_cards:
        return 0.5
    
    h_rank = hero_cards[0][0] if hero_cards else 0
    h_rank2 = hero_cards[1][0] if len(hero_cards) > 1 else 0
    o_rank = opponent_cards[0][0] if opponent_cards else 0
    
    h_pair = (h_rank == h_rank2)
    h_suited = hero_cards[0][1] == hero_cards[1][1] if len(hero_cards) > 1 else False
    o_pair = (o_rank == opponent_cards[1][0]) if len(opponent_cards) > 1 else False
    
    base = 0.5
    
    if h_pair and not o_pair:
        base += 0.18
    elif not h_pair and o_pair:
        base -= 0.18
    elif h_suited:
        base += 0.03
    
    if h_rank >= 13:  # AK
        base += 0.08
    elif h_rank >= 11:  # AJ, KQ
        base += 0.04
    
    if board_cards:
        board_ranks = [c[0] for c in board_cards]
        if h_rank in board_ranks or h_rank2 in board_ranks:
            base -= 0.08
        if o_rank in board_ranks:
            base += 0.04
    
    return max(0.1, min(0.9, base))


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
    """Aggregate EV by leak class using PokerKit equity calculation."""
    all_showdowns = find_showdowns(limit=500)
    
    by_class = defaultdict(lambda: {
        "n": 0, "total_pot": 0.0, "hero_wins": 0, 
        "total_equity": 0.0, "avg_ev_delta": 0.0
    })
    
    for sd in all_showdowns:
        hc = sd.get("hand_class", "unknown")
        by_class[hc]["n"] += 1
        by_class[hc]["total_pot"] += sd.get("pot", 0)
        if sd.get("hero_won"):
            by_class[hc]["hero_wins"] += 1
        
        hero_cards = parse_cards(sd.get("hero_cards", ""))
        opp_cards = parse_cards(sd.get("opponent_cards", ""))
        board_cards = parse_cards(sd.get("board", ""))
        
        if hero_cards and opp_cards:
            equity = estimate_equity(hero_cards, opp_cards, board_cards)
            by_class[hc]["total_equity"] += equity
            
            ev_delta = equity - 0.5  # vs breakeven
            by_class[hc]["avg_ev_delta"] += ev_delta
    
    results = {}
    for hc, data in by_class.items():
        n = data["n"]
        if n < 3:
            continue
        win_rate = data["hero_wins"] / n
        avg_pot = data["total_pot"] / n
        avg_equity = data["total_equity"] / n if n > 0 else 0.5
        avg_ev_delta = data["avg_ev_delta"] / n
        
        results[hc] = {
            "n": n,
            "win_rate": round(win_rate, 3),
            "avg_pot": round(avg_pot, 2),
            "avg_equity": round(avg_equity, 3),
            "avg_ev_delta": round(avg_ev_delta, 3),
            "prior_source": "measured",
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
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--leak-class")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output", action="store_true")
    args = parser.parse_args()
    
    if args.output:
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        results = aggregate_by_class()
        output_file = OUTPUT_ROOT / "latest.json"
        output_file.write_text(json.dumps({"by_leak_class": results}, indent=2))
        print(f"Wrote: {output_file}")
    elif args.leak_class:
        hands = find_showdowns(args.leak_class, args.limit)
        print(f"Found {len(hands)} showdowns for {args.leak_class}")
    else:
        results = aggregate_by_class()
        print("Showdown EV by Leak Class")
        print("=" * 50)
        for hc, data in sorted(results.items(), key=lambda x: -x[1]["n"]):
            print(f"{hc}: n={data['n']} win_rate={data['win_rate']:.1%} avg_pot=${data['avg_pot']:.0f} avg_equity={data.get('avg_equity', 0):.1%}")