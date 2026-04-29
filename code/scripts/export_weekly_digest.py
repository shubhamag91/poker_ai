#!/usr/bin/env python3
"""Export weekly leak digest with EV trends."""
import argparse
import json
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARSED_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "parsed"
OUTPUT_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "digests"
LEAK_REPORT = PROJECT_ROOT / "data" / "hand_histories" / "leak_prioritization" / "latest.json"
SHOWDOWN_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "showdown_ev"

TOP_N = 10
SHOWDOWN_MIN_N = 30


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


def load_showdown_ev() -> dict:
    showdown_file = SHOWDOWN_ROOT / "latest.json"
    if not showdown_file.exists():
        return {}
    try:
        return json.loads(showdown_file.read_text())
    except:
        return {}


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
        
        lines.append(f"### {i}. {leak_type}")
        lines.append(f"**Priority Score**: {priority}")
        lines.append(f"**Description**: {description}")
        lines.append("")
    
    lines.extend([
        "## Study Plan",
        "",
        "Review in order:",
    ])
    for i, leak in enumerate(leaks[:TOP_N], 1):
        lines.append(f"- [ ] {i}. {leak.get('leak_type', 'unknown')}")
    
    showdown_ev = load_showdown_ev()
    if showdown_ev:
        measured = [(hc, d) for hc, d in showdown_ev.items() if d.get("n", 0) >= SHOWDOWN_MIN_N]
        if measured:
            lines.extend(["", "## EV Trends (Measured)", ""])
            for hc, d in measured[:5]:
                lines.append(f"- **{hc}**: n={d['n']}, win_rate={d.get('win_rate', 0):.1%}")
    
    lines.extend(["", "## Notes", "", "_Notes_"])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export weekly leak digest")
    parser.add_argument("--output", help="Output file")
    args = parser.parse_args()
    
    digest = build_digest()
    week_id = get_week_identifier()
    
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_ROOT / (args.output or f"digest_{week_id}.md")
    output_path.write_text(digest)
    print(f"Wrote: {output_path}")


if __name__ == "__main__":
    main()