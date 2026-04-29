from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from preflop_baseline import (
    bucket_stack_depth, get_baseline, classify_action, compare_decision,
    get_call_off_baseline, get_reshove_baseline
)

PARSED_DIR = Path(__file__).parent.parent.parent / "data" / "hand_histories" / "parsed"

def extract_all_preflop_decisions(parsed_dir: Path) -> list[dict]:
    decisions = []
    
    pos_map = {
        "UTG": "early", "UTG+1": "early", "UTG+2": "early", "UTG+3": "early",
        "MP": "middle", "MP+1": "middle", "MP+2": "middle",
        "CO": "late", "BTN": "late", "HJ": "late",
        "SB": "blind", "BB": "blind",
    }
    
    for pf in parsed_dir.glob("*_analysis.txt"):
        content = pf.read_text()
        hands = re.split(r"\n={10,}\nHAND \d+", content)
        
        for hand_block in hands[1:]:
            stack_match = re.search(r"Hero (\d+\.\d+) BB", hand_block)
            if not stack_match:
                continue
            
            stack_bb = float(stack_match.group(1))
            if stack_bb > 30:
                continue
            
            verdict_match = re.search(
                r"Rule verdict:.*?Decision=(\w+), PositionGroup=(\w+), StackBucket=(\w+), HandClass=(\w+)",
                hand_block
            )
            
            if not verdict_match:
                continue
            
            decision = verdict_match.group(1)
            position_group = verdict_match.group(2)
            stack_bucket = verdict_match.group(3)
            hand_class = verdict_match.group(4)
            
            spot_type = None
            action = None
            
            if "an unopened pot" in hand_block:
                spot_type = "open"
                if decision == "open_shove":
                    action = "push"
                elif decision in {"open_raise", "min_raise"}:
                    action = "min_raise"
                elif decision == "fold":
                    action = "fold"
                else:
                    action = "other"
            elif "facing a" in hand_block:
                if decision in ("call_vs_shove", "fold_vs_shove"):
                    spot_type = "call_off"
                    action = "call" if "calls" in hand_block else "fold"
                elif decision == "reshove":
                    spot_type = "reshove"
                    action = "reshove"
                else:
                    continue
            else:
                continue
            
            decisions.append({
                "file": pf.name,
                "stack_bb": stack_bb,
                "bucket": bucket_stack_depth(stack_bb),
                "position_group": position_group,
                "stack_bucket": stack_bucket,
                "hand_class": hand_class,
                "action": action,
                "spot_type": spot_type,
            })
    
    return decisions

def analyze_hero_frequency(decisions: list[dict]) -> dict:
    bucket_stats = defaultdict(lambda: {
        "total": 0,
        "pushes": 0,
        "min_raises": 0,
        "folds": 0,
        "push_hands": defaultdict(int),
        "min_raise_hands": defaultdict(int),
        "fold_hands": defaultdict(int),
        "leaks": [],
    })
    call_stats = defaultdict(lambda: {"calls": 0, "folds": 0, "leaks": []})
    reshove_stats = defaultdict(lambda: {"reshoves": 0, "leaks": []})
    
    for d in decisions:
        spot_type = d.get("spot_type")
        
        if spot_type == "open":
            bucket = (d["bucket"], d["position_group"])
            hand_class = d["hand_class"]
            action = d["action"]
            
            baseline = get_baseline(d["bucket"], d["position_group"])
            
            bucket_stats[bucket]["total"] += 1
            
            if action == "push":
                bucket_stats[bucket]["pushes"] += 1
                bucket_stats[bucket]["push_hands"][hand_class] += 1
            elif action == "min_raise":
                bucket_stats[bucket]["min_raises"] += 1
                bucket_stats[bucket]["min_raise_hands"][hand_class] += 1
            else:
                bucket_stats[bucket]["folds"] += 1
                bucket_stats[bucket]["fold_hands"][hand_class] += 1
            
            if baseline:
                comparison = compare_decision(hand_class, action, baseline)
                if comparison["status"] == "leak":
                    bucket_stats[bucket]["leaks"].append({
                        "hand": hand_class,
                        "actual": action,
                        "expected": comparison["expected"],
                    })
        
        elif spot_type == "call_off":
            bucket = (d["stack_bucket"], d["position_group"])
            hand_class = d["hand_class"]
            action = d["action"]
            
            baseline = get_call_off_baseline(d["stack_bucket"], d["position_group"])
            
            if action == "call":
                call_stats[bucket]["calls"] += 1
            else:
                call_stats[bucket]["folds"] += 1
            
            if baseline:
                expected = "call" if hand_class in baseline.call_hands else "fold"
                if action != expected:
                    call_stats[bucket]["leaks"].append({
                        "hand": hand_class,
                        "actual": action,
                        "expected": expected,
                    })
        
        elif spot_type == "reshove":
            bucket = (d["stack_bucket"], d["position_group"])
            hand_class = d["hand_class"]
            
            baseline = get_reshove_baseline(d["stack_bucket"], d["position_group"])
            
            reshove_stats[bucket]["reshoves"] += 1
            
            if baseline:
                if hand_class not in baseline.reshove_hands:
                    reshove_stats[bucket]["leaks"].append({
                        "hand": hand_class,
                        "actual": "reshove",
                        "expected": "fold/call",
                    })
    
    return {"open": dict(bucket_stats), "call_off": dict(call_stats), "reshove": dict(reshove_stats)}

def generate_baseline_report() -> str:
    decisions = extract_all_preflop_decisions(PARSED_DIR)
    stats = analyze_hero_frequency(decisions)
    
    open_stats = stats.get("open", {})
    call_stats = stats.get("call_off", {})
    reshove_stats = stats.get("reshove", {})
    
    lines = [
        "Preflop Baseline Comparison Report",
        "=" * 60,
        f"Total spots analyzed: {len(decisions)}",
        "",
    ]
    
    total_leaks = 0
    total_hands = 0
    
    if open_stats:
        lines.append("=== B1: OPEN-JAM / MIN-RAISE SPOTS ===")
        
        for bucket in sorted(open_stats.keys()):
            depth, pos = bucket
            s = open_stats[bucket]
            baseline = get_baseline(depth, pos)
            
            if not baseline:
                continue
            
            total_hands += s["total"]
            total_leaks += len(s["leaks"])
            
            push_rate = s["pushes"] / s["total"] * 100 if s["total"] > 0 else 0
            min_rate = s["min_raises"] / s["total"] * 100 if s["total"] > 0 else 0
            fold_rate = s["folds"] / s["total"] * 100 if s["total"] > 0 else 0
            
            lines.append(f"--- {depth} BB {pos.upper()} ---")
            lines.append(f"  Hands: {s['total']} | Push: {s['pushes']} ({push_rate:5.0f}%) | Min-raise: {s['min_raises']:2d} ({min_rate:5.0f}%) | Fold: {s['folds']:2d} ({fold_rate:5.0f}%)")
            
            if s["leaks"]:
                lines.append(f"  LEAKS ({len(s['leaks'])}):")
                for leak in s["leaks"][:3]:
                    lines.append(f"    - {leak['hand']}: did {leak['actual']}, expected {leak['expected']}")
            lines.append("")
    
    if call_stats:
        lines.append("=== B2: CALL-OFF VS SHOVE SPOTS ===")
        
        for bucket in sorted(call_stats.keys()):
            stack_bucket, pos = bucket
            s = call_stats[bucket]
            total = s["calls"] + s["folds"]
            
            if total == 0:
                continue
            
            total_leaks += len(s["leaks"])
            total_hands += total
            
            call_rate = s["calls"] / total * 100
            lines.append(f"--- {stack_bucket} {pos.upper()} ---")
            lines.append(f"  Hands: {total} | Call: {s['calls']} ({call_rate:5.0f}%) | Fold: {s['folds']}")
            
            if s["leaks"]:
                lines.append(f"  LEAKS ({len(s['leaks'])}):")
                for leak in s["leaks"][:3]:
                    lines.append(f"    - {leak['hand']}: did {leak['actual']}, expected {leak['expected']}")
            lines.append("")
    
    if reshove_stats:
        lines.append("=== B2: RESHOVE SPOTS ===")
        
        for bucket in sorted(reshove_stats.keys()):
            stack_bucket, pos = bucket
            s = reshove_stats[bucket]
            
            if s["reshoves"] == 0:
                continue
            
            total_leaks += len(s["leaks"])
            total_hands += s["reshoves"]
            
            lines.append(f"--- {stack_bucket} {pos.upper()} ---")
            lines.append(f"  Hands: {s['reshoves']} | Reshove: {s['reshoves']}")
            
            if s["leaks"]:
                lines.append(f"  LEAKS ({len(s['leaks'])}):")
                for leak in s["leaks"][:3]:
                    lines.append(f"    - {leak['hand']}: did {leak['actual']}, expected {leak['expected']}")
            lines.append("")
    
    lines.append(f"SUMMARY: {total_leaks} potential leaks in {total_hands} hands")
    
    return "\n".join(lines)

if __name__ == "__main__":
    print(generate_baseline_report())