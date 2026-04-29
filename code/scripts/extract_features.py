#!/usr/bin/env python3
"""Feature extraction for poker evaluation."""
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARSED_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "parsed"


def extract_features(spot: dict) -> dict:
    """Extract features from parsed spot."""
    return {
        "stack_bb": round(spot.get("hero_bb", 0), 2),
        "position": spot.get("position"),
        "hand_class": spot.get("hand_class"),
        "decision_type": spot.get("decision_type"),
        "confidence": spot.get("confidence"),
        "verdict_source": spot.get("verdict_source"),
        "mistake": spot.get("mistake", "")[:50] if spot.get("mistake") else "",
    }


def build_feature_export(limit: int = 100) -> dict:
    """Build feature export from parsed corpus."""
    results = []
    
    for json_file in list(PARSED_ROOT.glob("*_analysis.json"))[:limit]:
        try:
            data = json.loads(json_file.read_text())
        except:
            continue
        
        for spot in data.get("spots", []):
            features = extract_features(spot)
            results.append(features)
    
    return {
        "total_features": len(results),
        "sample_size": min(limit * 5, len(results)),
        "features": results[:limit * 5],
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output")
    args = parser.parse_args()
    
    data = build_feature_export(args.limit)
    
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(data, indent=2))
        print(f"Wrote: {args.output}")
    else:
        print(f"Features: {data['total_features']}")
        print(f"Sample: {data['features'][0] if data['features'] else 'none'}")