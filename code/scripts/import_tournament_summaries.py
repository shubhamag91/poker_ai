#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional

from hand_history_utils import (
    extract_tournament_id,
    is_summary_text,
    iter_text_files,
    parse_finish_place,
    parse_total_players,
    read_text,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "raw"
SUMMARY_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "summaries"
HOME_ROOT = Path.home()
DEFAULT_SOURCE_DIRS = [
    HOME_ROOT / "Downloads",
    HOME_ROOT / "PokerCraft",
    HOME_ROOT / "PokerCraft_HH",
]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_label(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", text).strip()
    if not cleaned:
        return "Tournament"
    return re.sub(r"\s+", " ", cleaned)


def safe_filename(text: str) -> str:
    collapsed = normalize_label(text).replace(" ", "-")
    return collapsed[:120].strip("-_") or "Tournament"


def extract_summary_title(text: str) -> Optional[str]:
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if not first_line:
        return None

    patterns = [
        r"Tournament\s+#\d+,\s*(.+)$",
        r"Tournament\s+#\d+\s*-\s*(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, first_line, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


@dataclass
class SummaryCandidate:
    source_path: Path
    tournament_id: str
    title: str
    finish_place: Optional[int]
    total_players: Optional[int]
    digest: str
    text: str

    @property
    def destination_name(self) -> str:
        return f"tournament_{self.tournament_id}__{safe_filename(self.title)}.txt"


@dataclass
class ImportEntry:
    tournament_id: str
    source_path: str
    destination_path: Optional[str]
    imported: bool
    duplicate: bool
    matched_hand_histories: list[str]
    finish_place: Optional[int]
    total_players: Optional[int]
    note: str


def discover_summary_candidates(source_dirs: list[Path]) -> list[SummaryCandidate]:
    candidates: list[SummaryCandidate] = []
    seen_paths: set[Path] = set()

    for source_dir in source_dirs:
        for path in iter_text_files(source_dir):
            resolved_path = path.resolve()
            if resolved_path in seen_paths:
                continue
            seen_paths.add(resolved_path)

            text = read_text(path)
            if not is_summary_text(text):
                continue
            tournament_id = extract_tournament_id(text)
            if not tournament_id:
                continue
            title = extract_summary_title(text) or path.stem
            candidates.append(
                SummaryCandidate(
                    source_path=path,
                    tournament_id=tournament_id,
                    title=title,
                    finish_place=parse_finish_place(text),
                    total_players=parse_total_players(text),
                    digest=sha256_text(text),
                    text=text,
                )
            )

    return candidates


def resolve_source_dirs(source_dir_arg: Optional[str]) -> list[Path]:
    if source_dir_arg:
        source_dir = Path(source_dir_arg).expanduser().resolve()
        if not source_dir.exists():
            raise SystemExit(f"Source directory not found: {source_dir}")
        return [source_dir]

    resolved: list[Path] = []
    seen: set[Path] = set()
    for path in DEFAULT_SOURCE_DIRS:
        candidate = path.expanduser()
        if not candidate.exists():
            continue
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        resolved.append(candidate)

    if not resolved:
        searched = ", ".join(str(path.expanduser()) for path in DEFAULT_SOURCE_DIRS)
        raise SystemExit(f"No default summary source directories found. Checked: {searched}")

    return resolved


def build_raw_index(raw_root: Path) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    for path in iter_text_files(raw_root):
        text = read_text(path)
        if is_summary_text(text):
            continue
        tournament_id = extract_tournament_id(text[:1000])
        if tournament_id:
            index.setdefault(tournament_id, []).append(path)
    return index


def build_existing_summary_index(summary_root: Path) -> tuple[dict[str, Path], dict[str, Path]]:
    by_digest: dict[str, Path] = {}
    by_tournament: dict[str, Path] = {}
    if not summary_root.exists():
        return by_digest, by_tournament

    for path in iter_text_files(summary_root):
        text = read_text(path)
        if not is_summary_text(text):
            continue
        tournament_id = extract_tournament_id(text)
        if tournament_id and tournament_id not in by_tournament:
            by_tournament[tournament_id] = path
        by_digest[sha256_text(text)] = path
    return by_digest, by_tournament


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def import_summaries(source_dirs: list[Path], dry_run: bool = False, report_path: Optional[Path] = None) -> dict:
    summary_candidates = discover_summary_candidates(source_dirs)
    raw_index = build_raw_index(RAW_ROOT)
    existing_by_digest, existing_by_tournament = build_existing_summary_index(SUMMARY_ROOT)

    entries: list[ImportEntry] = []
    imported = 0
    duplicates = 0
    matched = 0
    unmatched = 0

    for candidate in summary_candidates:
        matched_paths = raw_index.get(candidate.tournament_id, [])
        if matched_paths:
            matched += 1
        else:
            unmatched += 1

        duplicate_path = existing_by_digest.get(candidate.digest)
        if duplicate_path:
            duplicates += 1
            entries.append(
                ImportEntry(
                    tournament_id=candidate.tournament_id,
                    source_path=str(candidate.source_path),
                    destination_path=str(duplicate_path),
                    imported=False,
                    duplicate=True,
                    matched_hand_histories=[str(path.relative_to(PROJECT_ROOT)) for path in matched_paths],
                    finish_place=candidate.finish_place,
                    total_players=candidate.total_players,
                    note="Skipped duplicate summary with identical content.",
                )
            )
            continue

        existing_tournament_path = existing_by_tournament.get(candidate.tournament_id)
        destination = SUMMARY_ROOT / candidate.destination_name
        if existing_tournament_path and existing_tournament_path != destination:
            destination = existing_tournament_path

        entries.append(
            ImportEntry(
                tournament_id=candidate.tournament_id,
                source_path=str(candidate.source_path),
                destination_path=str(destination),
                imported=not dry_run,
                duplicate=False,
                matched_hand_histories=[str(path.relative_to(PROJECT_ROOT)) for path in matched_paths],
                finish_place=candidate.finish_place,
                total_players=candidate.total_players,
                note="Matched by tournament ID." if matched_paths else "No matching repo hand history found yet.",
            )
        )

        if not dry_run:
            ensure_parent(destination)
            destination.write_text(candidate.text, encoding="utf-8")
            existing_by_digest[candidate.digest] = destination
            existing_by_tournament[candidate.tournament_id] = destination
        imported += 1

    report = {
        "source_dir": ", ".join(str(path) for path in source_dirs),
        "source_dirs": [str(path) for path in source_dirs],
        "dry_run": dry_run,
        "summary_candidates": len(summary_candidates),
        "imported": imported,
        "matched": matched,
        "unmatched": unmatched,
        "skipped_duplicates": duplicates,
        "entries": [asdict(entry) for entry in entries],
    }

    if report_path:
        ensure_parent(report_path)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


def format_report(report: dict) -> str:
    source_label = ", ".join(report.get("source_dirs", [])) or report.get("source_dir", "")
    lines = [
        "Tournament summary import report",
        "=" * 80,
        f"Source dir: {source_label}",
        f"Dry run: {'yes' if report['dry_run'] else 'no'}",
        f"Summary files found: {report['summary_candidates']}",
        f"Imported: {report['imported']}",
        f"Matched to repo hand histories: {report['matched']}",
        f"Unmatched: {report['unmatched']}",
        f"Skipped duplicates: {report['skipped_duplicates']}",
        "",
    ]

    entries: Iterable[dict] = report.get("entries", [])
    for entry in entries:
        status = "duplicate" if entry["duplicate"] else ("import" if entry["imported"] else "plan")
        matched = len(entry["matched_hand_histories"])
        lines.append(
            f"[{status}] Tournament #{entry['tournament_id']} | matched HH files: {matched} | {Path(entry['source_path']).name}"
        )
        if entry.get("destination_path"):
            lines.append(f"  -> {entry['destination_path']}")
        lines.append(f"  note: {entry['note']}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import GG tournament summary text files into the repo and auto-match them to hand histories by tournament ID."
    )
    parser.add_argument(
        "--source-dir",
        help=(
            "Optional single directory to scan for downloaded summary text files. "
            "If omitted, the importer scans existing default roots: ~/Downloads, ~/PokerCraft, and ~/PokerCraft_HH."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview the import without copying files.")
    parser.add_argument(
        "--report-json",
        help="Optional path for a JSON manifest/report. Example: data/hand_histories/summaries/import_reports/latest.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_dirs = resolve_source_dirs(args.source_dir)

    report_path = Path(args.report_json).expanduser().resolve() if args.report_json else None
    report = import_summaries(source_dirs=source_dirs, dry_run=args.dry_run, report_path=report_path)
    print(format_report(report))
    if report_path:
        print(f"\nSaved report JSON: {report_path}")


if __name__ == "__main__":
    main()
