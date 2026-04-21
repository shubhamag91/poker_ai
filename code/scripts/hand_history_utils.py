from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Optional

TEXT_EXTENSIONS = {".txt", ".log"}
TOURNAMENT_ID_PATTERN = re.compile(r"Tournament\s+#(\d+)", re.IGNORECASE)
FINISH_PLACE_PATTERNS = [
    re.compile(r"You finished the tournament in\s+([\d,]+)(?:st|nd|rd|th)\s+place", re.IGNORECASE),
    re.compile(r"([\d,]+)(?:st|nd|rd|th)\s*:\s*Hero\b", re.IGNORECASE),
]
TOTAL_PLAYERS_PATTERN = re.compile(r"([\d,]+)\s+Players\b", re.IGNORECASE)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def iter_text_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [path for path in sorted(root.rglob("*")) if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS]


def extract_tournament_id(text: str) -> Optional[str]:
    match = TOURNAMENT_ID_PATTERN.search(text)
    return match.group(1) if match else None


def is_hand_history_text(text: str) -> bool:
    head = text[:1000]
    return "Poker Hand #" in head or re.search(r"\bHand\s+#\w+", head) is not None


def is_summary_text(text: str) -> bool:
    if is_hand_history_text(text):
        return False
    head = text[:3000]
    return bool(
        extract_tournament_id(head)
        and (
            FINISH_PLACE_PATTERNS[0].search(head)
            or re.search(r"\bPlayers\b", head, re.IGNORECASE)
            or re.search(r"Total Prize Pool", head, re.IGNORECASE)
        )
    )


def parse_finish_place(text: str) -> Optional[int]:
    for pattern in FINISH_PLACE_PATTERNS:
        match = pattern.search(text)
        if match:
            return int(match.group(1).replace(",", ""))
    return None


def parse_total_players(text: str) -> Optional[int]:
    match = TOTAL_PLAYERS_PATTERN.search(text)
    return int(match.group(1).replace(",", "")) if match else None


def parse_tournament_summary_file(summary_path: Path) -> dict:
    text = read_text(summary_path)
    return {
        "path": summary_path,
        "tournament_id": extract_tournament_id(text),
        "total_players": parse_total_players(text),
        "finish_place": parse_finish_place(text),
    }


def find_matching_summary_paths(tournament_id: str, *roots: Path) -> Iterable[Path]:
    seen: set[Path] = set()
    for root in roots:
        for candidate in iter_text_files(root):
            if candidate in seen:
                continue
            seen.add(candidate)
            text = read_text(candidate)
            if not is_summary_text(text):
                continue
            if extract_tournament_id(text[:5000]) == tournament_id:
                yield candidate
