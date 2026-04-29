#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARSED_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "parsed"
POSTFLOP_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "postflop_hero_flop_actions"
REPORT_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "leak_prioritization"

EV_COST_ESTIMATES = {
    "preflop": {
        "open_jam_leak": 0.8,
        "min_raise_leak": 0.5,
        "call_off_fold": 1.2,
        "reshove_wrong": 0.9,
        "3bet_leak": 0.7,
    },
    "postflop": {
        "flop_cbet_miss": 0.4,
        "flop_check_raise_miss": 0.6,
        "turn_cbet_miss": 0.5,
        "river_value_miss": 0.7,
        "bluff_catch_miss": 0.5,
    },
}

ICM_SENSITIVITY_MULTIPLIERS = {
    "bubble": 2.0,
    "ft": 1.8,
    "itm": 1.3,
    "early": 1.0,
    "middle": 1.1,
    "late": 1.2,
}


def extract_icm_context(content: str) -> dict[str, Any]:
    """Extract ICM context from parsed file"""
    result = {
        "stage": "early",
        "pressure": "low",
        "field_size": 0,
        "itm_pct": 15.0,
        "hero_place": None,
        "cluster": None,
    }
    
    stage_match = re.search(r"(early-field|late-field|middle stages|early stage|late stage)", content)
    if stage_match:
        stage_text = stage_match.group(1)
        if "early" in stage_text:
            result["stage"] = "early"
        elif "late" in stage_text:
            result["stage"] = "late"
        elif "middle" in stage_text:
            result["stage"] = "middle"
    
    pressure_match = re.search(r"(high|medium|low|low-medium) pressure", content)
    if pressure_match:
        result["pressure"] = pressure_match.group(1).replace("-medium", "")
    
    field_match = re.search(r"Field (\d[\d,]*)", content)
    if field_match:
        result["field_size"] = int(field_match.group(1).replace(",", ""))
    
    itm_match = re.search(r"(\d+\.\d+)% ITM", content)
    if itm_match:
        result["itm_pct"] = float(itm_match.group(1))
    
    place_match = re.search(r"Hero later busted (\d+)th", content)
    if place_match:
        result["hero_place"] = int(place_match.group(1))
    
    cluster_match = re.search(r"cluster:\s*(\w+)", content)
    if cluster_match:
        result["cluster"] = cluster_match.group(1)
    
    return result


def get_icm_multiplier(icm_context: dict) -> float:
    """Calculate ICM multiplier based on tournament context"""
    stage = icm_context.get("stage", "early")
    pressure = icm_context.get("pressure", "low")
    hero_place = icm_context.get("hero_place")
    
    base = ICM_SENSITIVITY_MULTIPLIERS.get(stage, 1.0)
    
    if hero_place:
        if hero_place <= 27:
            return base * ICM_SENSITIVITY_MULTIPLIERS["ft"]
        elif hero_place <= 90:
            return base * ICM_SENSITIVITY_MULTIPLIERS["bubble"]
        elif hero_place <= 300:
            return base * ICM_SENSITIVITY_MULTIPLIERS["itm"]
    
    if pressure == "high":
        return base * 1.5
    elif pressure == "medium":
        return base * 1.2
    
    return base


def extract_preflop_leaks() -> dict[str, Any]:
    leaks = []
    
    for pf in PARSED_ROOT.glob("*_analysis.txt"):
        json_path = pf.with_suffix(".json")
        
        if json_path.exists():
            try:
                data = json.loads(json_path.read_text())
                for spot in data.get("spots", []):
                    decision = spot.get("decision_type", "unknown")
                    hand_class = spot.get("hand_class", "unknown")
                    stack_bb = spot.get("hero_bb", 20)
                    position = spot.get("position", "?")
                    leak_type = None
                    if decision in ("open_shove", "open_raise"):
                        leak_type = "open_jam_leak"
                    elif decision == "min_raise":
                        leak_type = "min_raise_leak"
                    elif decision in ("call_vs_shove", "fold_vs_shove"):
                        leak_type = "call_off_fold"
                    elif decision == "reshove":
                        leak_type = "reshove_wrong"
                    elif decision in ("flat_call_vs_raise", "fold_to_raise"):
                        leak_type = "3bet_leak"
                    if leak_type:
                        leaks.append({
                            "type": leak_type,
                            "street": "preflop",
                            "hand_class": hand_class,
                            "stack_bb": stack_bb,
                            "position": position,
                            "decision": decision,
                            "file": pf.name,
                        })
                continue
            except json.JSONDecodeError:
                pass
        
        content = pf.read_text()
        
        icm_context = extract_icm_context(content)
        hands = re.split(r"\n={10,}\nHAND \d+", content)
        for block in hands[1:]:
            verdict_match = re.search(r"Decision=(\w+)", block)
            hand_class_match = re.search(r"HandClass=(\w+)", block)
            stack_match = re.search(r"Hero (\d+\.\d+) BB", block)
            pos_match = re.search(r"Spot:\s+(\w+)", block)
            
            mistake_match = re.search(r"Mistake:\s*(\w+)", block)
            is_mistake = mistake_match and mistake_match.group(1).lower() not in ("no clear mistake", "none")
            
            if not verdict_match or not hand_class_match:
                continue
            
            decision = verdict_match.group(1)
            hand_class = hand_class_match.group(1)
            stack_bb = float(stack_match.group(1)) if stack_match else 20
            position = pos_match.group(1) if pos_match else "?"
            
            leak_type = None
            if decision in ("open_shove", "open_raise") and is_mistake:
                leak_type = "open_jam_leak"
            elif decision == "min_raise" and is_mistake:
                leak_type = "min_raise_leak"
            elif decision in ("call_vs_shove", "fold_vs_shove"):
                if is_mistake:
                    leak_type = "call_off_fold"
            elif decision == "reshove":
                if is_mistake:
                    leak_type = "reshove_wrong"
            elif decision in ("flat_call_vs_raise", "fold_to_raise") and is_mistake:
                leak_type = "3bet_leak"
            
            if leak_type:
                leaks.append({
                    "type": leak_type,
                    "street": "preflop",
                    "hand_class": hand_class,
                    "stack_bb": stack_bb,
                    "position": position,
                    "decision": decision,
                    "file": pf.name,
                    "icm_context": icm_context,
                    "icm_multiplier": get_icm_multiplier(icm_context),
                })
    
    return leaks


def extract_postflop_leaks() -> list[dict[str, Any]]:
    from postflop_baseline import get_cbet_baseline, compare_frequency
    
    postflop_json = POSTFLOP_ROOT / "latest.json"
    if not postflop_json.exists():
        return []
    
    try:
        data = json.loads(postflop_json.read_text())
    except json.JSONDecodeError:
        return []
    
    leaks = []
    spot_summary = data.get("spot_summary", {})
    
    for family_id, buckets in spot_summary.items():
        for bucket_key, summary in buckets.items():
            hand_count = summary.get("hand_count", 0)
            if hand_count < 3:
                continue
            
            action_counts = summary.get("hero_action_counts", {})
            total_actions = sum(action_counts.values())
            if total_actions == 0:
                continue
            
            bet_count = action_counts.get("bet", 0)
            cbet_rate = bet_count / total_actions if total_actions > 0 else 0
            
            family_short = family_id.replace("_flop", "") if "_flop" in family_id else family_id
            parts = bucket_key.split(" | ")
            # Format: "caller | board_bucket | context" or "open_raiser | board_bucket | context"
            hero_role = parts[0] if len(parts) > 0 else ""
            board_bucket = parts[1] if len(parts) > 1 else "UNKNOWN"
            # Map hero role to IP/OOP
            position = "OOP" if hero_role in ("caller", "defender") else "IP"
            
            baseline = get_cbet_baseline(family_short, position, board_bucket, "shallow")
            if not baseline:
                continue
            
            comparison = compare_frequency("small_bet", cbet_rate, baseline)
            
            if comparison["status"] == "leak" and abs(comparison["deviation"]) > 0.10:
                leaks.append({
                    "type": "flop_cbet_miss",
                    "street": "postflop",
                    "hand_class": board_bucket,
                    "stack_bb": 0,
                    "position": position,
                    "decision": family_short,
                    "file": "postflop_actions",
                    "actual_freq": cbet_rate,
                    "expected_freq": comparison["expected_freq"],
                    "deviation": comparison["deviation"],
                    "hand_count": hand_count,
                })
    
    return leaks


DEEPER_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "postflop_hero_deeper_actions"


def extract_turn_river_leaks() -> list[dict[str, Any]]:
    from postflop_baseline import get_turn_barrel_baseline, get_river_bet_baseline
    
    deeper_json = DEEPER_ROOT / "latest.json"
    if not deeper_json.exists():
        return []
    
    try:
        data = json.loads(deeper_json.read_text())
    except json.JSONDecodeError:
        return []
    
    leaks = []
    turn_summary = data.get("turn_summary", {})
    river_summary = data.get("river_summary", {})
    
    for family_id, buckets in turn_summary.items():
        for bucket_key, summary in buckets.items():
            hand_count = summary.get("hand_count", 0)
            if hand_count < 3:
                continue
            action_counts = summary.get("hero_action_counts", {})
            total = sum(action_counts.values())
            if total == 0:
                continue
            
            # Parse bucket key: "family | hero_role | board_bucket | context"
            parts = bucket_key.split(" | ")
            if len(parts) < 2:
                continue
            hero_role = parts[0]
            board_bucket = parts[1]
            position = "OOP" if hero_role in ("caller", "defender") else "IP"
            family_short = family_id.replace("_flop", "") if "_flop" in family_id else family_id
            
            baseline = get_turn_barrel_baseline(family_short, position, board_bucket, "shallow")
            if not baseline:
                continue
        for bucket_key, summary in buckets.items():
            hand_count = summary.get("hand_count", 0)
            if hand_count < 3:
                continue
            action_counts = summary.get("hero_action_counts", {})
            total = sum(action_counts.values())
            if total == 0:
                continue
            bet_count = action_counts.get("bet", 0)
            bet_rate = bet_count / total if total > 0 else 0
            
            parts = bucket_key.split(" | ")
            if len(parts) < 3:
                continue
            # Format: "family_flop | hero_role | board_bucket | context"
            hero_role = parts[1] if len(parts) > 1 else ""
            board_bucket = parts[2] if len(parts) > 2 else "UNKNOWN"
            position = "OOP" if hero_role in ("caller", "defender") else "IP"
            family_short = family_id.replace("_flop", "") if "_flop" in family_id else family_id
            
            baseline = get_turn_barrel_baseline(family_short, position, board_bucket, "shallow")
            if not baseline:
                continue
            
            deviation = bet_rate - baseline.barrel_freq
            if abs(deviation) > 0.10:
                leaks.append({
                    "type": "turn_barrel_miss",
                    "street": "postflop",
                    "hand_class": board_bucket,
                    "stack_bb": 0,
                    "position": position,
                    "decision": family_short,
                    "file": "deeper_actions",
                    "actual_freq": bet_rate,
                    "expected_freq": baseline.barrel_freq,
                    "deviation": deviation,
                    "hand_count": hand_count,
                })
    
    for family_id, buckets in river_summary.items():
        for bucket_key, summary in buckets.items():
            hand_count = summary.get("hand_count", 0)
            if hand_count < 3:
                continue
            action_counts = summary.get("hero_action_counts", {})
            total = sum(action_counts.values())
            if total == 0:
                continue
            bet_count = action_counts.get("bet", 0)
            bet_rate = bet_count / total if total > 0 else 0
            
            parts = bucket_key.split(" | ")
            if len(parts) < 3:
                continue
            hero_role = parts[1] if len(parts) > 1 else ""
            board_bucket = parts[2] if len(parts) > 2 else "UNKNOWN"
            position = "OOP" if hero_role in ("caller", "defender") else "IP"
            family_short = family_id.replace("_flop", "") if "_flop" in family_id else family_id
            
            baseline = get_river_bet_baseline(family_short, position, board_bucket, "shallow")
            if not baseline:
                continue
            
            deviation = bet_rate - baseline.bet_freq
            if abs(deviation) > 0.10:
                leaks.append({
                    "type": "river_bet_miss",
                    "street": "postflop",
                    "hand_class": board_bucket,
                    "stack_bb": 0,
                    "position": position,
                    "decision": family_short,
                    "file": "deeper_actions",
                    "actual_freq": bet_rate,
                    "expected_freq": baseline.bet_freq,
                    "deviation": deviation,
                    "hand_count": hand_count,
                })
    
    return leaks


def estimate_icm_multiplier(itm_place: int | None) -> float:
    if itm_place is None:
        return 1.0
    if itm_place <= 30:
        return ICM_SENSITIVITY_MULTIPLIERS["ft"]
    elif itm_place <= 100:
        return ICM_SENSITIVITY_MULTIPLIERS["bubble"]
    elif itm_place <= 500:
        return ICM_SENSITIVITY_MULTIPLIERS["itm"]
    return ICM_SENSITIVITY_MULTIPLIERS["early"]


def score_leak(leak: dict[str, Any], frequency: int) -> dict[str, Any]:
    street = leak["street"]
    leak_type = leak["type"]
    
    ev_cost = EV_COST_ESTIMATES.get(street, {}).get(leak_type, 0.5)
    icm_mult = leak.get("icm_multiplier", 1.0)
    icm_context = leak.get("icm_context", {})
    
    priority_score = frequency * ev_cost * icm_mult
    
    return {
        "leak_type": leak_type,
        "street": street,
        "frequency": frequency,
        "ev_cost_per_instance": ev_cost,
        "icm_multiplier": icm_mult,
        "icm_stage": icm_context.get("stage", "unknown"),
        "icm_pressure": icm_context.get("pressure", "unknown"),
        "priority_score": round(priority_score, 2),
        "description": get_leak_description(leak_type),
    }


def get_leak_description(leak_type: str) -> str:
    descriptions = {
        "open_jam_leak": "Open-jamming with wrong hand class for stack depth",
        "min_raise_leak": "Min-raising when should push/fold",
        "call_off_fold": "Folded strong hand vs shove (should call)",
        "reshove_wrong": "Reshoved weak hand (should fold)",
        "3bet_leak": "3-bet/fold decision error",
        "flop_cbet_miss": "C-bet frequency error on flop",
        "flop_check_raise_miss": "Check-raise response error",
        "turn_cbet_miss": "Turn barrel frequency error",
        "river_value_miss": "River value betting error",
        "bluff_catch_miss": "Bluff-catching error",
    }
    return descriptions.get(leak_type, "Unknown leak type")


def build_leak_report() -> dict[str, Any]:
    preflop_leaks = extract_preflop_leaks()
    postflop_leaks = extract_postflop_leaks()
    turn_river_leaks = extract_turn_river_leaks()
    
    all_leaks = preflop_leaks + postflop_leaks + turn_river_leaks
    
    leak_counts = defaultdict(int)
    leak_details = defaultdict(list)
    leak_icm_sum = defaultdict(float)
    leak_stages = defaultdict(list)
    
    for leak in all_leaks:
        key = f"{leak['street']}:{leak['type']}"
        leak_counts[key] += 1
        leak_icm_sum[key] += leak.get("icm_multiplier", 1.0)
        leak_stages[key].append(leak.get("icm_context", {}).get("stage", "unknown"))
        if len(leak_details[key]) < 3:
            leak_details[key].append({
                "hand_class": leak["hand_class"],
                "position": leak["position"],
                "stack_bb": leak["stack_bb"],
                "icm_stage": leak.get("icm_context", {}).get("stage", "unknown"),
                "icm_pressure": leak.get("icm_context", {}).get("pressure", "unknown"),
            })
    
    scored_leaks = []
    for key, freq in leak_counts.items():
        street, leak_type = key.split(":")
        avg_icm = leak_icm_sum[key] / freq if freq > 0 else 1.0
        
        ev_cost = EV_COST_ESTIMATES.get(street, {}).get(leak_type, 0.5)
        priority_score = freq * ev_cost * avg_icm
        
        stage_counts = Counter(leak_stages[key])
        top_stage = stage_counts.most_common(1)[0][0] if stage_counts else "unknown"
        
        scored_leaks.append({
            "leak_type": leak_type,
            "street": street,
            "frequency": freq,
            "ev_cost_per_instance": ev_cost,
            "icm_multiplier": round(avg_icm, 2),
            "icm_stage": top_stage,
            "priority_score": round(priority_score, 2),
            "description": get_leak_description(leak_type),
            "examples": leak_details[key],
        })
    
    scored_leaks.sort(key=lambda x: x["priority_score"], reverse=True)
    
    total_leaks = sum(leak_counts.values())
    weighted_score = sum(l["priority_score"] for l in scored_leaks)
    
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "meta": {
            "total_leaks_detected": total_leaks,
            "unique_leak_types": len(scored_leaks),
            "weighted_priority_score": round(weighted_score, 2),
        },
        "leak_rankings": scored_leaks,
    }


def format_report(data: dict[str, Any]) -> str:
    lines = [
        "Leak Prioritization Report",
        "=" * 50,
        f"Generated: {data['generated_at']}",
        f"Total leaks: {data['meta']['total_leaks_detected']}",
        f"Unique leak types: {data['meta']['unique_leak_types']}",
        f"Weighted priority score: {data['meta']['weighted_priority_score']}",
        "",
        "=== LEAK PRIORITY RANKING ===",
        "",
    ]
    
    for i, leak in enumerate(data["leak_rankings"], 1):
        lines.append(f"{i}. {leak['description']}")
        lines.append(f"   Street: {leak['street']} | Freq: {leak['frequency']} | EV: {leak['ev_cost_per_instance']} | ICM: {leak['icm_multiplier']}x")
        lines.append(f"   Priority Score: {leak['priority_score']}")
        if leak.get("examples"):
            ex = leak["examples"][0]
            lines.append(f"   Example: {ex['hand_class']} at {ex['position']} ({ex['stack_bb']} BB)")
        lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Rank detected leaks by priority")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()
    
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    
    data = build_leak_report()
    
    json_path = REPORT_ROOT / "latest.json"
    json_path.write_text(json.dumps(data, indent=2))
    print(f"JSON: {json_path}")
    
    if not args.json:
        txt_path = REPORT_ROOT / "latest.txt"
        txt_path.write_text(format_report(data))
        print(f"TXT: {txt_path}")
    
    print(format_report(data))


if __name__ == "__main__":
    main()
