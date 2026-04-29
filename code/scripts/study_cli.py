#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARSED_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "parsed"
LEAK_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "leak_prioritization"
REPORTS_ROOT = PROJECT_ROOT / "data" / "hand_histories"


def extract_date_from_filename(filename: str) -> Optional[tuple]:
    match = re.search(r"GG(\d{4})(\d{2})(\d{2})", filename)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        return (year, month, day)
    return None


def is_actual_mistake(mistake_value: str) -> bool:
    if not mistake_value:
        return False
    v = mistake_value.lower().strip()
    return v not in ("no clear mistake", "none", "no", "")


def cmd_weekly(args) -> None:
    """Generate weekly summary report."""
    import json
    from pathlib import Path
    
    parsed_files = list(PARSED_ROOT.glob("*_analysis.txt"))
    
    hands_by_week = defaultdict(lambda: {"total": 0, "mistakes": 0, "leaks": defaultdict(int)})
    
    for pf in parsed_files:
        date = extract_date_from_filename(pf.name)
        if date:
            week_key = f"{date[0]:04d}-W{date[1]:02d}"
        else:
            week_key = "unknown"
        
        content = pf.read_text()
        hands = re.split(r"\n={10,}\nHAND \d+", content)
        
        for block in hands[1:]:
            hands_by_week[week_key]["total"] += 1
            
            mistake_match = re.search(r"Mistake:\s*(\w+)", block)
            if mistake_match and is_actual_mistake(mistake_match.group(1)):
                hands_by_week[week_key]["mistakes"] += 1
                leak_type = mistake_match.group(1)
                hands_by_week[week_key]["leaks"][leak_type] += 1
    
    print("\n=== WEEKLY SUMMARY ===\n")
    weeks = sorted(hands_by_week.keys(), reverse=True)[:8]
    
    for week in weeks:
        data = hands_by_week[week]
        error_rate = data["mistakes"] / data["total"] * 100 if data["total"] > 0 else 0
        print(f"{week}: {data['total']} hands, {data['mistakes']} errors ({error_rate:.1f}%)")
        
        top_leaks = sorted(data["leaks"].items(), key=lambda x: -x[1])[:3]
        for leak, count in top_leaks:
            print(f"  - {leak}: {count}")
        print()


def cmd_compare(args) -> None:
    """Compare two time periods."""
    period_a = args.a or "202601"
    period_b = args.b or "202602"
    
    parsed_files = list(PARSED_ROOT.glob("*_analysis.txt"))
    
    def get_period_stats(period: str) -> dict:
        stats = {"total": 0, "mistakes": 0, "decisions": defaultdict(int)}
        for pf in parsed_files:
            if period not in pf.name:
                continue
            content = pf.read_text()
            hands = re.split(r"\n={10,}\nHAND \d+", content)
            for block in hands[1:]:
                stats["total"] += 1
                verdict = re.search(r"Decision=(\w+)", block)
                if verdict:
                    stats["decisions"][verdict.group(1)] += 1
                mistake = re.search(r"Mistake:\s*(\w+)", block)
                if mistake and is_actual_mistake(mistake.group(1)):
                    stats["mistakes"] += 1
        return stats
    
    stats_a = get_period_stats(period_a)
    stats_b = get_period_stats(period_b)
    
    print(f"\n=== COMPARISON: {period_a} vs {period_b} ===\n")
    print(f"{period_a}: {stats_a['total']} hands, {stats_a['mistakes']} mistakes")
    print(f"{period_b}: {stats_b['total']} hands, {stats_b['mistakes']} mistakes")
    
    if stats_a["total"] > 0 and stats_b["total"] > 0:
        rate_a = stats_a["mistakes"] / stats_a["total"] * 100
        rate_b = stats_b["mistakes"] / stats_b["total"] * 100
        delta = rate_b - rate_a
        print(f"\nError rate: {rate_a:.1f}% -> {rate_b:.1f}% (Δ{delta:+.1f}%)")


def cmd_progress(args) -> None:
    """Show progress over time."""
    leak_file = LEAK_ROOT / "latest.json"
    if not leak_file.exists():
        print("No leak data. Run report_leak_prioritization.py first.")
        return
    
    data = json.loads(leak_file.read_text())
    leaks = data.get("leak_rankings", [])
    
    limit = args.limit or 10
    print(f"\n=== LEAK PROGRESS (Top {limit}) ===\n")
    
    for i, leak in enumerate(leaks[:limit], 1):
        print(f"{i}. {leak.get('description', 'N/A')}")
        print(f"   Priority: {leak.get('priority_score', 0):.1f}")
        print(f"   Street: {leak.get('street', '?')}")
        print(f"   Freq: {leak.get('frequency', 0)}, EV: {leak.get('ev_cost_per_instance', 0):.1f}")
        print()


def cmd_top_leaks(args) -> None:
    leak_file = LEAK_ROOT / "latest.json"
    if not leak_file.exists():
        print("No leak data found. Run report_leak_prioritization.py first.")
        return
    
    data = json.loads(leak_file.read_text())
    leaks = data.get("leak_rankings", [])
    
    limit = args.limit or 5
    print(f"\n=== TOP {limit} LEAKS ===\n")
    
    for i, leak in enumerate(leaks[:limit], 1):
        print(f"{i}. {leak['description']}")
        print(f"   Priority: {leak['priority_score']} | Freq: {leak['frequency']} | EV: {leak['ev_cost_per_instance']}")
        if leak.get("examples"):
            print(f"   Example: {leak['examples'][0]}")
        print()


def cmd_leak_examples(args) -> None:
    leak_type = args.leak_type
    limit = args.limit or 10
    
    examples = []
    
    for pf in PARSED_ROOT.glob("*_analysis.txt"):
        content = pf.read_text()
        hands = re.split(r"\n={10,}\nHAND \d+", content)
        
        for block in hands[1:]:
            verdict_match = re.search(r"Decision=(\w+)", block)
            hand_class_match = re.search(r"HandClass=(\w+)", block)
            stack_match = re.search(r"Hero (\d+\.\d+) BB", block)
            pos_match = re.search(r"Spot:\s+(\w+)", block)
            mistake_match = re.search(r"Mistake:\s*(\w+)", block)
            
            if not verdict_match or not hand_class_match:
                continue
            
            decision = verdict_match.group(1)
            hand_class = hand_class_match.group(1)
            stack_bb = float(stack_match.group(1)) if stack_match else 0
            position = pos_match.group(1) if pos_match else "?"
            is_mistake = mistake_match and mistake_match.group(1).lower() not in ("no clear mistake", "none")
            
            match = False
            if leak_type == "call_off_fold" and decision in ("call_vs_shove", "fold_vs_shove") and is_mistake:
                match = True
            elif leak_type == "reshove_wrong" and decision == "reshove" and is_mistake:
                match = True
            elif leak_type == "3bet" and decision in ("flat_call_vs_raise", "fold_to_raise") and is_mistake:
                match = True
            elif leak_type == "open_jam" and decision in ("open_shove", "open_raise") and is_mistake:
                match = True
            
            if match:
                hero_card_match = re.search(r"Spot:\s+\w+\s+\|?\s*([A-Za-z0-9\s]+?)(?:\n|$)", block)
                hero_cards = hero_card_match.group(1).strip() if hero_card_match else "?"
                
                examples.append({
                    "file": pf.name,
                    "hand": hand_class,
                    "cards": hero_cards,
                    "position": position,
                    "stack_bb": stack_bb,
                })
                
                if len(examples) >= limit:
                    break
        if len(examples) >= limit:
            break
    
    print(f"\n=== EXAMPLES: {leak_type} (up to {limit}) ===\n")
    for i, ex in enumerate(examples, 1):
        print(f"{i}. {ex['hand']} ({ex['cards']})")
        print(f"   {ex['position']} @ {ex['stack_bb']:.1f} BB")
        print(f"   {ex['file'][:50]}...")
        print()


def cmd_node_pack(args) -> None:
    family = args.family
    position = args.position or "all"
    stack_max = args.stack or 30
    
    hands = []
    
    for pf in PARSED_ROOT.glob("*_analysis.txt"):
        content = pf.read_text()
        
        if family and family not in content:
            continue
        
        hands_section = re.split(r"\n={10,}\nHAND \d+", content)
        
        for block in hands_section[1:]:
            stack_match = re.search(r"Hero (\d+\.\d+) BB", block)
            pos_match = re.search(r"Spot:\s+(\w+)", block)
            hero_card_match = re.search(r"Spot:\s+\w+\s+\|?\s*([A-Za-z0-9\s]+?)(?:\n|$)", block)
            
            if not stack_match or not pos_match:
                continue
            
            stack_bb = float(stack_match.group(1))
            pos = pos_match.group(1)
            
            if stack_bb > stack_max:
                continue
            if position != "all" and position.lower() not in pos.lower():
                continue
            
            hero_cards = hero_card_match.group(1).strip() if hero_card_match else "?"
            
            hands.append({
                "file": pf.name[:40],
                "position": pos,
                "stack": stack_bb,
                "cards": hero_cards,
            })
    
    print(f"\n=== NODE PACK: {family or 'all'} ===")
    print(f"Filters: position={position}, stack<{stack_max} BB")
    print(f"Found: {len(hands)} hands\n")
    
    for i, h in enumerate(hands[:20], 1):
        print(f"{i}. {h['cards']:8s} {h['position']:4s} {h['stack']:5.1f} BB | {h['file']}")


def cmd_stats(args) -> None:
    parsed_files = list(PARSED_ROOT.glob("*_analysis.txt"))
    
    total_hands = 0
    total_mistakes = 0
    by_decision = defaultdict(int)
    
    for pf in parsed_files:
        content = pf.read_text()
        
        hands = re.split(r"\n={10,}\nHAND \d+", content)
        
        for block in hands[1:]:
            total_hands += 1
            
            verdict_match = re.search(r"Decision=(\w+)", block)
            mistake_match = re.search(r"Mistake:\s*(\w+)", block)
            
            if verdict_match:
                decision = verdict_match.group(1)
                by_decision[decision] += 1
            
            if mistake_match and mistake_match.group(1).lower() not in ("no clear mistake", "none"):
                total_mistakes += 1
    
    print(f"\n=== STUDY STATS ===")
    print(f"Parsed files: {len(parsed_files)}")
    print(f"Total hands: {total_hands}")
    print(f"Total mistakes: {total_mistakes} ({total_mistakes/total_hands*100:.1f}%)")
    print(f"\nDecisions:")
    for dec, count in sorted(by_decision.items(), key=lambda x: -x[1])[:10]:
        print(f"  {dec}: {count}")


def main():
    parser = argparse.ArgumentParser(description="poker_ai Study CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    top_parser = subparsers.add_parser("top", help="Show top leaks")
    top_parser.add_argument("--limit", type=int, help="Number of leaks to show")
    
    examples_parser = subparsers.add_parser("examples", help="Get example hands for a leak type")
    examples_parser.add_argument("leak_type", help="Leak type: call_off_fold, reshove_wrong, 3bet, open_jam")
    examples_parser.add_argument("--limit", type=int, help="Number of examples")
    
    node_parser = subparsers.add_parser("node", help="Generate node pack")
    node_parser.add_argument("family", nargs="?", help="Family to filter")
    node_parser.add_argument("--position", help="Position filter")
    node_parser.add_argument("--stack", type=float, help="Max stack depth")
    
    subparsers.add_parser("stats", help="Show study stats")
    
    weekly_parser = subparsers.add_parser("weekly", help="Weekly summary report")
    
    compare_parser = subparsers.add_parser("compare", help="Compare time periods")
    compare_parser.add_argument("--a", help="Period A (e.g., 2026-01)")
    compare_parser.add_argument("--b", help="Period B (e.g., 2026-02)")
    
    progress_parser = subparsers.add_parser("progress", help="Leak progress over time")
    progress_parser.add_argument("--limit", type=int, help="Number of leaks")
    
    args = parser.parse_args()
    
    if args.command == "top":
        cmd_top_leaks(args)
    elif args.command == "examples":
        cmd_leak_examples(args)
    elif args.command == "node":
        cmd_node_pack(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "weekly":
        cmd_weekly(args)
    elif args.command == "compare":
        cmd_compare(args)
    elif args.command == "progress":
        cmd_progress(args)
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python study_cli.py top --limit 5")
        print("  python study_cli.py examples call_off_fold --limit 10")
        print("  python study_cli.py node srp_ip_pfr --position SB --stack 20")
        print("  python study_cli.py stats")
        print("  python study_cli.py weekly")
        print("  python study_cli.py compare --a 2026-01 --b 2026-02")
        print("  python study_cli.py progress --limit 10")


if __name__ == "__main__":
    main()
