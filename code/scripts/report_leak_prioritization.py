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
            elif decision == "call_or_fold_vs_shove":
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
    
    leak_counts = defaultdict(int)
    leak_details = defaultdict(list)
    leak_icm_sum = defaultdict(float)
    leak_stages = defaultdict(list)
    
    for leak in preflop_leaks:
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
