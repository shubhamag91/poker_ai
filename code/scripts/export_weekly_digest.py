#!/usr/bin/env python3
"""Export weekly leak digest.

Creates a single artifact summarizing leak state, deltas, and example hands.
"""
import argparse
import json
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARSED_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "parsed"
RAW_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "raw"
OUTPUT_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "digests"
LEAK_REPORT = PROJECT_ROOT / "data" / "hand_histories" / "leak_prioritization" / "latest.json"

TOP_N = 10


def get_week_identifier() -> str:
    now = datetime.now()
    week = now.isocalendar()[1]
    return f"{now.year}-W{week:02d}"


def load_leak_ranking() -> list[dict]:
    if not LEAK_REPORT.exists():
        return []
    try:
        data = json.loads(LEAK_REPORT.read_text())
        return data.get("leak_rankings", [])[:TOP_N]
    except:
        return []


def find_hand_for_leak(leak_class: str) -> dict | None:
    for json_file in sorted(PARSED_ROOT.glob("*_analysis.json"), key=lambda p: -p.stat().st_mtime):
        try:
            data = json.loads(json_file.read_text())
        except:
            continue
        for spot in data.get("spots", []):
            if spot.get("hand_class") == leak_class:
                return {
                    "file": json_file.stem,
                    "hero_bb": spot.get("hero_bb"),
                    "position": spot.get("position"),
                    "decision_type": spot.get("decision_type"),
                    "mistake": spot.get("mistake"),
                    "better_play": spot.get("better_play"),
                }
    return None


def build_digest() -> str:
    week_id = get_week_identifier()
    leaks = load_leak_ranking()
    
    lines = [
        f"# Weekly Leak Digest: {week_id}",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Top Leaks**: {len(leaks)}",
        "",
        "---",
        "",
        "## Top Priority Leaks",
        "",
    ]
    
    for i, leak in enumerate(leaks[:TOP_N], 1):
        leak_type = leak.get("leak_type", "unknown")
        priority = leak.get("priority_score", 0)
        description = leak.get("description", "")
        examples = leak.get("examples", [])
        hand_class = examples[0].get("hand_class", "") if examples else ""
        
        lines.append(f"### {i}. {leak_type}")
        lines.append(f"**Priority Score**: {priority}")
        lines.append(f"**Description**: {description}")
        if hand_class:
            lines.append(f"**Example Hand Class**: {hand_class}")
        if leak.get("icm_stage"):
            lines.append(f"**ICM Stage**: {leak.get('icm_stage')}")
        lines.append("")
        
        if hand_class:
            hand = find_hand_for_leak(hand_class)
            if hand:
                lines.append(f"**Sample**: {hand['hero_bb']} BB @ {hand['position']}")
                lines.append(f"- Mistake: {hand.get('mistake', '?')}")
                lines.append(f"- Better: {hand.get('better_play', '?')}")
                lines.append("")
        
        lines.append("---")
        lines.append("")
    
    lines.extend([
        "## Study Plan",
        "",
        "Review in order:",
    ])
    for i, leak in enumerate(leaks[:TOP_N], 1):
        lines.append(f"- [ ] {i}. {leak.get('leak_type', 'unknown')}")
    
    lines.extend([
        "",
        "## Notes",
        "",
        "_Notes_",
    ])
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export weekly leak digest")
    parser.add_argument("--output", help="Output file")
    args = parser.parse_args()
    
    digest = build_digest()
    week_id = get_week_identifier()
    
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    if args.output:
        output_path = OUTPUT_ROOT / args.output
    else:
        output_path = OUTPUT_ROOT / f"digest_{week_id}.md"
    
    output_path.write_text(digest)
    print(f"Wrote: {output_path}")


if __name__ == "__main__":
    main()