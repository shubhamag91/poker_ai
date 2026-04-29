#!/usr/bin/env python3
"""Article node tagger.

Walks articles/library/, tags chunks with relevant node IDs.
"""
import json
import re
from pathlib import Path
from collections import defaultdict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIBRARY_ROOT = PROJECT_ROOT / "articles" / "library"
OUTPUT_ROOT = PROJECT_ROOT / "data" / "knowledge"
ARTICLE_INDEX = OUTPUT_ROOT / "article_node_index.json"

NODE_KEYWORDS = {
    "open_raise": ["open", "raise", "rfi", "first in"],
    "3bet": ["3bet", "re-raise", "triple barrel"],
    "cbet": ["cbet", "continuation bet", "flop bet"],
    "check_raise": ["check-raise", "check raise", "float"],
    "push_fold": ["push", "shove", "all-in", "fold"],
    "blind_defense": ["blind", "defend", "call defense"],
    "bubble": ["bubble", "icm", "pressure"],
    "short_stack": ["short stack", "15bb", "20bb", "depth"],
}


def extract_chunks(file_path: Path) -> list[dict]:
    """Extract chunks from article."""
    if file_path.suffix == ".md":
        content = file_path.read_text()
        chunks = content.split("\n## ")
        return [{"text": c.strip(), "source": file_path.name} for c in chunks if c.strip()]
    return []


def tag_chunk(text: str) -> list[str]:
    """Tag chunk with node IDs based on keywords."""
    text_lower = text.lower()
    nodes = []
    
    for node, keywords in NODE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            nodes.append(node)
    
    return nodes


def build_index() -> dict:
    """Build article-node index."""
    index = {"articles": [], "node_index": defaultdict(list), "chunks": []}
    
    for md_file in LIBRARY_ROOT.rglob("*.md"):
        chunks = extract_chunks(md_file)
        
        for chunk in chunks:
            nodes = tag_chunk(chunk["text"])
            chunk_id = len(index["chunks"])
            index["chunks"].append({
                "id": chunk_id,
                "source": chunk["source"],
                "text": chunk["text"][:500],
                "nodes": nodes,
            })
            for node in nodes:
                index["node_index"][node].append(chunk_id)
    
    return index


def query_articles(node_id: str, limit: int = 5) -> list[dict]:
    """Query articles by node ID."""
    index = build_index()
    chunk_ids = index["node_index"].get(node_id, [])[:limit]
    
    results = []
    for cid in chunk_ids:
        chunk = index["chunks"][cid]
        results.append({
            "source": chunk["source"],
            "text": chunk["text"],
        })
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Article node tagger")
    parser.add_argument("--query", help="Query by node ID")
    parser.add_argument("--build", action="store_true", help="Build index")
    args = parser.parse_args()
    
    if args.build:
        index = build_index()
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        ARTICLE_INDEX.write_text(json.dumps(index, indent=2))
        print(f"Indexed {len(index['chunks'])} chunks")
        print(f"Wrote: {ARTICLE_INDEX}")
    
    elif args.query:
        results = query_articles(args.query)
        print(f"Found {len(results)} chunks for '{args.query}'")
        for r in results:
            print(f"- {r['source']}: {r['text'][:100]}...")


if __name__ == "__main__":
    main()