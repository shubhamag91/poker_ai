#!/usr/bin/env python3
"""Export study packets for leak classes.

For each leak bucket, export a readable .md packet with:
- Leak class, confidence tier, n/k
- Representative hands with full text
- Baseline expected action
- LLM verdict
- Notes placeholder
"""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARSED_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "parsed"
RAW_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "raw"
OUTPUT_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "study_packets"
KNOWLEDGE_ROOT = PROJECT_ROOT / "data" / "knowledge"
ARTICLE_INDEX = KNOWLEDGE_ROOT / "article_node_index.json"
LEAK_JSON = PARSED_ROOT.glob("*_analysis.json")

MAX_EXAMPLES = 5


def lookup_snippets(node_id: str, limit: int = 3) -> list[dict]:
    """Look up related snippets for a node ID."""
    if not ARTICLE_INDEX.exists():
        return []
    try:
        index = json.loads(ARTICLE_INDEX.read_text())
    except:
        return []
    
    chunk_ids = index.get("node_index", {}).get(node_id, [])[:limit]
    results = []
    for cid in chunk_ids:
        chunk = index.get("chunks", [])[cid]
        results.append({
            "source": chunk.get("source", ""),
            "text": chunk.get("text", "")[:300],
        })
    return results


def extract_hand_by_index(raw_path: Path, index: int) -> str | None:
    """Extract full hand text from raw file by position in parsed."""
    content = raw_path.read_text()
    hands = content.split("\n" + "=" * 40 + "\nHAND")
    
    if index < len(hands) and index > 0:
        return "HAND" + hands[index]
    return None


def find_hands_for_leak(leak_class: str, bucket: str, limit: int = 5) -> list[dict]:
    """Find hands matching a leak class from parsed files."""
    results = []
    
    for json_file in PARSED_ROOT.glob("*_analysis.json"):
        try:
            data = json.loads(json_file.read_text())
        except:
            continue
        
        for spot in data.get("spots", []):
            if spot.get("hand_class") == leak_class:
                results.append({
                    "file": json_file.stem,
                    "spot_index": spot.get("index"),
                    "hero_bb": spot.get("hero_bb"),
                    "position": spot.get("position"),
                    "decision_type": spot.get("decision_type"),
                    "mistake": spot.get("mistake"),
                    "better_play": spot.get("better_play"),
                    "reason": spot.get("reason"),
                    "confidence": spot.get("confidence"),
                    "verdict_source": spot.get("verdict_source"),
                })
                
                if len(results) >= limit:
                    return results
    
    return results


def find_raw_file(parsed_stem: str) -> Path | None:
    """Find raw file matching parsed file stem."""
    raw_candidates = list(RAW_ROOT.glob(f"{parsed_stem.replace('_analysis','')}*"))
    if raw_candidates:
        return raw_candidates[0]
    
    for raw in RAW_ROOT.glob("*.txt"):
        if parsed_stem.replace("_analysis", "") in raw.stem:
            return raw
    return None


def build_packet(leak_class: str, bucket: str | None = None) -> str:
    """Build study packet for a leak class."""
    hands = find_hands_for_leak(leak_class, bucket or "all", MAX_EXAMPLES)
    
    if not hands:
        return f"# Study Packet: {leak_class}\n\nNo hands found for this leak class."
    
    lines = [
        f"# Study Packet: {leak_class}",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Bucket**: {bucket or 'all'}",
        f"**Hands found**: {len(hands)}",
        "",
        "---",
        "",
        "## Representative Hands",
        "",
    ]
    
    for i, hand in enumerate(hands, 1):
        raw_file = find_raw_file(hand["file"])
        
        lines.append(f"### Hand {i}")
        lines.append(f"**File**: {hand['file']}")
        lines.append(f"**Stack**: {hand['hero_bb']} BB | **{hand['position']}**")
        lines.append(f"**Decision**: {hand['decision_type']}")
        lines.append(f"**Confidence**: {hand.get('confidence', 'unknown')}")
        lines.append("")
        
        lines.append("**LLM Analysis**:")
        lines.append(f"- Mistake: {hand.get('mistake', 'unknown')}")
        lines.append(f"- Better play: {hand.get('better_play', 'unknown')}")
        lines.append(f"- Reason: {hand.get('reason', 'unknown')[:200]}")
        lines.append("")
        
        if raw_file and raw_file.exists():
            try:
                raw_content = raw_file.read_text()
                hand_lines = raw_content.split("\n" + "=" * 40 + "\nHAND")
                idx = hand.get("spot_index", 1)
                if idx < len(hand_lines):
                    full_hand = "HAND" + hand_lines[idx]
                    lines.append("**Full Hand Text**:")
                    lines.append("```")
                    lines.append(full_hand[:1500])
                    lines.append("```")
            except:
                pass
        
        lines.append("")
        lines.append("---")
        lines.append("")
    
    lines.extend([
        "## Study Notes",
        "",
        "_Notes go here_",
    ])
    
    node_map = {
        "premium_pair": "3bet",
        "strong_broadway": "3bet",
        "weak_ace": "open_raise",
        "wheel_ace": "open_raise",
        "medium_pair": "open_raise",
    }
    node_id = node_map.get(leak_class, leak_class.split("_")[0])
    snippets = lookup_snippets(node_id)
    if snippets:
        lines.extend([
            "",
            "## Related Articles",
            "",
        ])
        for s in snippets:
            lines.append(f"**{s['source']}**")
            lines.append(f"_{s['text'][:200]}...")
            lines.append("")
    
    lines.extend([
        "## Actions Taken",
        "",
        "- [ ] Review hand 1",
        "- [ ] Review hand 2", 
        "- [ ] Review hand 3",
    ])
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export study packets")
    parser.add_argument("--leak-class", required=True, help="Leak class to export")
    parser.add_argument("--bucket", help="Bucket filter")
    parser.add_argument("--output", help="Output file (default: stdout)")
    args = parser.parse_args()
    
    packet = build_packet(args.leak_class, args.bucket)
    
    if args.output:
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_ROOT / args.output
        output_path.write_text(packet)
        print(f"Wrote: {output_path}")
    else:
        print(packet)


if __name__ == "__main__":
    main()