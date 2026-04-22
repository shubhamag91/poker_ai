from __future__ import annotations

import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
LOOKUP_PATH = PROJECT_ROOT / "docs" / "tournament_archetype_lookup.json"

_lookup_cache: dict | None = None

CLUSTER_KEYWORDS = {
    "PKO": ["Bounty", "bounty"],
    "WSOP_SC": ["WSOP-SC", "WSOP Circuit"],
    "GGMasters": ["GGMasters", "GGM"],
    "Satellite": ["Satellite"],
    "7max": ["7-Max"],
    "Hyper": ["Hyper"],
    "Monster": ["Monster"],
    "Grand_Prix": ["GRAND-PRIX", "Grand Prix"],
    "Fifty": ["Fifty", "50 Stack"],
    "Mini": ["Mini"],
    "Mega": ["MEGA"],
    "Marathon": ["Marathon"],
    "Daily": ["Daily"],
}

PAID_SEATS_LADDER = [
    (9, 3), (27, 5), (50, 7), (100, 10), (200, 15), (300, 20),
    (500, 30), (1000, 50), (2000, 75), (3000, 100), (5000, 150),
    (10000, 200), (20000, 300), (99999999, 400),
]

GG_ITM_PCT = 0.15  # GG Poker typically pays ~15% of the field

def _load_lookup() -> dict:
    global _lookup_cache
    if _lookup_cache is None:
        if LOOKUP_PATH.exists():
            try:
                with open(LOOKUP_PATH) as f:
                    _lookup_cache = json.load(f)
            except (json.JSONDecodeError, OSError):
                _lookup_cache = {}
        else:
            _lookup_cache = {}
    return _lookup_cache

def classify_tournament_tags(name: str) -> list[str]:
    tags = []
    for tag, keywords in CLUSTER_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in name.lower():
                tags.append(tag)
                break
    return sorted(tags)

def cluster_key(tags: list[str]) -> str:
    return "+".join(tags) if tags else "regular"

def paid_seats_for_field_size(n: int) -> int:
    base = max(3, round(n * GG_ITM_PCT))
    for threshold, seats in PAID_SEATS_LADDER:
        if n <= threshold:
            return max(base, seats)
    return base

def itm_pct_for_field_size(n: int) -> float:
    return round(paid_seats_for_field_size(n) / n * 100, 1) if n else 0



def lookup_archetype_by_name(tournament_name: str) -> dict | None:
    lookup = _load_lookup()
    for entry in lookup.get("clusters", []):
        if entry.get("tournament_name") == tournament_name:
            return {
                "cluster": entry.get("cluster", ""),
                "players_range": entry.get("players_range", ""),
                "buyin_range": entry.get("buyin_range", ""),
                "avg_prize_per_player": entry.get("avg_prize_per_player", 0),
                "estimated_paid_seats": entry.get("estimated_paid_seats", 0),
                "itm_pct": entry.get("itm_pct", 0),
            }
    return None

def enrich_tournament_summary(summary: dict, tournament_name: str = "") -> dict:
    total_players = summary.get("total_players")
    archetype = lookup_archetype_by_name(tournament_name) if tournament_name else None

    if not archetype and total_players:
        tags = classify_tournament_tags(tournament_name)
        cn = cluster_key(tags)
        paid = paid_seats_for_field_size(total_players)
        itm = itm_pct_for_field_size(total_players)
        archetype = {
            "cluster": cn,
            "players_range": f"{total_players}-{total_players}",
            "estimated_paid_seats": paid,
            "itm_pct": itm,
        }

    enriched = dict(summary)
    if archetype:
        paid = archetype.get("estimated_paid_seats", paid_seats_for_field_size(total_players) if total_players else 0)
        itm = archetype.get("itm_pct", itm_pct_for_field_size(total_players) if total_players else 0)
        enriched["icm"] = {
            "cluster": archetype.get("cluster", ""),
            "estimated_paid_seats": paid,
            "itm_pct": itm,
            "avg_prize_per_player": archetype.get("avg_prize_per_player", 0),
            "buyin_range": archetype.get("buyin_range", ""),
        }
        if total_players:
            enriched["icm"]["payout_density"] = round(paid / total_players * 100, 1)

    return enriched