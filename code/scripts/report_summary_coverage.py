#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from hand_history_utils import extract_tournament_id, is_summary_text, iter_text_files, read_text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HAND_HISTORY_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "raw"
SUMMARY_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "summaries"
OUTPUT_ROOT = SUMMARY_ROOT / "coverage_report"


@dataclass
class IndexedFile:
    path: str
    tournament_id: Optional[str]


@dataclass
class MatchedTournament:
    tournament_id: str
    hand_history_paths: list[str]
    summary_paths: list[str]


@dataclass
class BatchItem:
    tournament_id: str
    hand_history_path: str
    summary_path: str
    suggested_output_path: str


@dataclass
class CoverageReport:
    generated_at: str
    hand_history_root: str
    summary_root: str
    total_hand_history_files_scanned: int
    total_summary_files_available: int
    hand_histories_with_tournament_id: int
    summaries_with_tournament_id: int
    matched_tournaments: int
    matched_hand_histories: int
    unmatched_hand_histories: int
    unmatched_summaries: int
    hand_histories_missing_tournament_id: list[str]
    summaries_missing_tournament_id: list[str]
    matched: list[dict]
    unmatched_hand_histories_by_tournament: list[dict]
    unmatched_summaries_by_tournament: list[dict]
    batch_parser_inputs: list[dict]
    parser_command_examples: list[str]


def index_files(root: Path, kind: str) -> tuple[list[IndexedFile], dict[str, list[str]], list[str]]:
    indexed: list[IndexedFile] = []
    by_tournament: dict[str, list[str]] = defaultdict(list)
    missing_ids: list[str] = []

    for path in iter_text_files(root):
        text = read_text(path)
        if kind == "summary" and not is_summary_text(text):
            continue
        if kind == "hand_history" and is_summary_text(text):
            continue
        tournament_id = extract_tournament_id(text[:5000])
        rel_path = str(path.relative_to(PROJECT_ROOT))
        indexed.append(IndexedFile(path=rel_path, tournament_id=tournament_id))
        if tournament_id:
            by_tournament[tournament_id].append(rel_path)
        else:
            missing_ids.append(rel_path)

    return indexed, dict(sorted(by_tournament.items())), missing_ids


def default_parsed_output(hand_history_path: str) -> str:
    hand_history = Path(hand_history_path)
    return str(Path("data/hand_histories/parsed") / f"{hand_history.stem}_analysis.txt")


def build_report() -> CoverageReport:
    hand_histories, hh_by_tournament, hh_missing_ids = index_files(HAND_HISTORY_ROOT, kind="hand_history")
    summaries, summary_by_tournament, summary_missing_ids = index_files(SUMMARY_ROOT, kind="summary")

    matched_ids = sorted(set(hh_by_tournament) & set(summary_by_tournament), key=int)
    unmatched_hh_ids = sorted(set(hh_by_tournament) - set(summary_by_tournament), key=int)
    unmatched_summary_ids = sorted(set(summary_by_tournament) - set(hh_by_tournament), key=int)

    matched: list[dict] = []
    batch_inputs: list[dict] = []
    parser_commands: list[str] = []

    for tournament_id in matched_ids:
        hand_history_paths = sorted(hh_by_tournament[tournament_id])
        summary_paths = sorted(summary_by_tournament[tournament_id])
        matched.append(asdict(MatchedTournament(
            tournament_id=tournament_id,
            hand_history_paths=hand_history_paths,
            summary_paths=summary_paths,
        )))

        primary_summary_path = summary_paths[0]
        for hand_history_path in hand_history_paths:
            item = BatchItem(
                tournament_id=tournament_id,
                hand_history_path=hand_history_path,
                summary_path=primary_summary_path,
                suggested_output_path=default_parsed_output(hand_history_path),
            )
            batch_inputs.append(asdict(item))
            parser_commands.append(
                "python3 code/scripts/hand_parser.py "
                f"--input '{item.hand_history_path}' --summary '{item.summary_path}' "
                f"--output '{item.suggested_output_path}'"
            )

    unmatched_hand_histories_by_tournament = [
        {
            "tournament_id": tournament_id,
            "hand_history_paths": sorted(hh_by_tournament[tournament_id]),
        }
        for tournament_id in unmatched_hh_ids
    ]
    unmatched_summaries_by_tournament = [
        {
            "tournament_id": tournament_id,
            "summary_paths": sorted(summary_by_tournament[tournament_id]),
        }
        for tournament_id in unmatched_summary_ids
    ]

    return CoverageReport(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        hand_history_root=str(HAND_HISTORY_ROOT.relative_to(PROJECT_ROOT)),
        summary_root=str(SUMMARY_ROOT.relative_to(PROJECT_ROOT)),
        total_hand_history_files_scanned=len(hand_histories),
        total_summary_files_available=len(summaries),
        hand_histories_with_tournament_id=sum(1 for item in hand_histories if item.tournament_id),
        summaries_with_tournament_id=sum(1 for item in summaries if item.tournament_id),
        matched_tournaments=len(matched_ids),
        matched_hand_histories=len(batch_inputs),
        unmatched_hand_histories=sum(len(hh_by_tournament[tournament_id]) for tournament_id in unmatched_hh_ids),
        unmatched_summaries=sum(len(summary_by_tournament[tournament_id]) for tournament_id in unmatched_summary_ids),
        hand_histories_missing_tournament_id=hh_missing_ids,
        summaries_missing_tournament_id=summary_missing_ids,
        matched=matched,
        unmatched_hand_histories_by_tournament=unmatched_hand_histories_by_tournament,
        unmatched_summaries_by_tournament=unmatched_summaries_by_tournament,
        batch_parser_inputs=batch_inputs,
        parser_command_examples=parser_commands,
    )


def format_terminal_summary(report: CoverageReport, max_examples: int = 10) -> str:
    lines = [
        "Tournament summary coverage report",
        "=" * 80,
        f"Generated: {report.generated_at}",
        f"Hand-history files scanned: {report.total_hand_history_files_scanned}",
        f"Summary files available: {report.total_summary_files_available}",
        f"Matched tournaments: {report.matched_tournaments}",
        f"Matched hand histories: {report.matched_hand_histories}",
        f"Unmatched hand histories: {report.unmatched_hand_histories}",
        f"Unmatched summaries: {report.unmatched_summaries}",
        f"Hand histories missing tournament ID: {len(report.hand_histories_missing_tournament_id)}",
        f"Summaries missing tournament ID: {len(report.summaries_missing_tournament_id)}",
        "",
    ]

    if report.matched:
        lines.append("Matched tournaments")
        lines.append("-" * 80)
        for entry in report.matched[:max_examples]:
            lines.append(
                f"#{entry['tournament_id']} | HH: {len(entry['hand_history_paths'])} | summaries: {len(entry['summary_paths'])}"
            )
            lines.extend(f"  HH  {path}" for path in entry["hand_history_paths"][:max_examples])
            lines.extend(f"  SUM {path}" for path in entry["summary_paths"][:max_examples])
        lines.append("")

    if report.unmatched_hand_histories_by_tournament:
        lines.append("Unmatched hand histories")
        lines.append("-" * 80)
        for entry in report.unmatched_hand_histories_by_tournament[:max_examples]:
            lines.append(f"#{entry['tournament_id']} | HH: {len(entry['hand_history_paths'])}")
            lines.extend(f"  {path}" for path in entry["hand_history_paths"][:max_examples])
        lines.append("")

    if report.unmatched_summaries_by_tournament:
        lines.append("Unmatched summaries")
        lines.append("-" * 80)
        for entry in report.unmatched_summaries_by_tournament[:max_examples]:
            lines.append(f"#{entry['tournament_id']} | summaries: {len(entry['summary_paths'])}")
            lines.extend(f"  {path}" for path in entry["summary_paths"][:max_examples])
        lines.append("")

    if report.hand_histories_missing_tournament_id:
        lines.append("Hand histories missing tournament ID")
        lines.append("-" * 80)
        lines.extend(f"  {path}" for path in report.hand_histories_missing_tournament_id[:max_examples])
        lines.append("")

    if report.summaries_missing_tournament_id:
        lines.append("Summaries missing tournament ID")
        lines.append("-" * 80)
        lines.extend(f"  {path}" for path in report.summaries_missing_tournament_id[:max_examples])
        lines.append("")

    if report.batch_parser_inputs:
        lines.append("Batch parser-ready pairs")
        lines.append("-" * 80)
        for entry in report.batch_parser_inputs[:max_examples]:
            lines.append(
                f"#{entry['tournament_id']} | {entry['hand_history_path']} -> {entry['summary_path']}"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report which repo hand histories have linked tournament summaries and write batch-ready parser inputs."
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_ROOT),
        help=f"Directory for report artifacts. Default: {OUTPUT_ROOT}",
    )
    parser.add_argument(
        "--json-name",
        default="latest.json",
        help="JSON report filename inside --output-dir. Default: latest.json",
    )
    parser.add_argument(
        "--text-name",
        default="latest.txt",
        help="Text summary filename inside --output-dir. Default: latest.txt",
    )
    parser.add_argument(
        "--batch-name",
        default="matched_parser_inputs.json",
        help="Batch parser input manifest filename inside --output-dir. Default: matched_parser_inputs.json",
    )
    parser.add_argument(
        "--commands-name",
        default="matched_parser_commands.txt",
        help="Parser command list filename inside --output-dir. Default: matched_parser_commands.txt",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    report = build_report()
    text_report = format_terminal_summary(report)

    json_path = output_dir / args.json_name
    text_path = output_dir / args.text_name
    batch_path = output_dir / args.batch_name
    commands_path = output_dir / args.commands_name

    json_path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    text_path.write_text(text_report, encoding="utf-8")
    batch_path.write_text(json.dumps(report.batch_parser_inputs, indent=2), encoding="utf-8")
    commands_path.write_text("\n".join(report.parser_command_examples) + ("\n" if report.parser_command_examples else ""), encoding="utf-8")

    print(text_report, end="")
    print(f"Saved JSON report: {json_path}")
    print(f"Saved text summary: {text_path}")
    print(f"Saved batch parser inputs: {batch_path}")
    print(f"Saved parser commands: {commands_path}")


if __name__ == "__main__":
    main()
