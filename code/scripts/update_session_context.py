#!/usr/bin/env python3
"""
End-of-session context updater.
Run this at the end of each session: python3 scripts/update_session_context.py

It reads SESSION.md, prompts for this session's work, and updates it.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SESSION_FILE = SCRIPT_DIR.parent / "SESSION.md"
MILESTONE_LABELS = ["milestone-A", "milestone-B", "milestone-C", "milestone-D", "milestone-E"]

def read_session() -> str:
    if SESSION_FILE.exists():
        return SESSION_FILE.read_text()
    return ""

def parse_current_milestone(content: str) -> str:
    m = re.search(r"## Current Milestone\s*\n\*\*Milestone ([A-E])", content)
    return m.group(1) if m else "?"

def parse_history(content: str) -> list[str]:
    return re.findall(r"### Milestone ([A-E])", content)

def next_milestone(history: list[str]) -> str:
    for label in ["A", "B", "C", "D", "E"]:
        if label not in history:
            return label
    return "?"

def update_session(
    current: str,
    work_done: str,
    issues_closed: str,
    files_changed: str,
    next_milestone: str,
    blockers: str,
) -> str:
    today = datetime.now().strftime("%Y-%m-%d")

    new_section = f"\n### Milestone {current} (Completed {today})\n{work_done}\n"
    if issues_closed:
        new_section += f"- Issues closed: {issues_closed}\n"
    if files_changed:
        new_section += f"- Files: {files_changed}\n"

    lines = [
        "# poker_ai Session Context",
        "# Auto-managed by opencode agent",
        f"# Last updated: {today}",
        "",
        "## Current Milestone",
        f"**Milestone {next_milestone}** — In progress",
        "",
        "## Project Status",
        "- Linear project: https://linear.app/mose/project/poker-ai-e33721cdc012/overview",
        "- GitHub: https://github.com/shubhamag91/poker_ai",
        "",
        "## Milestone History",
    ]

    history_sections = re.findall(r"(### Milestone [A-E].*?)(?=### Milestone [A-E]|$)", current, re.DOTALL)
    if not history_sections:
        history_sections = re.findall(r"(### Milestone [A-E].*)", content, re.DOTALL)

    for h in history_sections:
        if h.strip():
            lines.append(h.strip())
            lines.append("")

    lines.append(new_section)
    lines.extend([
        "",
        "## Key Context",
        "- Parser entry: code/scripts/hand_parser.py",
        "- Summary root: data/hand_histories/summaries/",
        "- Parsed output: data/hand_histories/parsed/",
        "- Raw HH: data/hand_histories/raw/",
        "- Lookup table: docs/tournament_archetype_lookup.json",
        "- PKO sidecar: data/hand_histories/metadata/*.pko.json",
        "",
        "## Next Session Plan",
        f"- Start Milestone {next_milestone}",
        f"- Blockers: {blockers or 'None'}",
        "",
        "## Session Workflow",
        "1. Read SESSION.md at start",
        "2. Check Linear for current milestone issues",
        "3. Pick next 1-2 sub-issues",
        "4. Implement + test",
        "5. Update Linear",
        "6. Write SESSION.md at end",
    ])

    return "\n".join(lines)

def main():
    content = read_session()
    current = parse_current_milestone(content) or "?"
    history = parse_history(content)
    next_m = next_milestone(history)

    print(f"Current milestone: {current}")
    print(f"Milestones done: {history}")
    print(f"Next: {next_m}")
    print()

    print("=== End of Session Update ===")
    work_done = input("What did you complete this session? ").strip()
    issues_closed = input("Linear issues closed (e.g., MOS-41, MOS-42)? ").strip()
    files_changed = input("Files changed (comma-separated)? ").strip()
    blockers = input("Blockers for next session? ").strip()
    print()

    if not work_done:
        print("Skipped update.")
        return

    updated = update_session(
        content,
        work_done,
        issues_closed,
        files_changed,
        next_m,
        blockers,
    )

    SESSION_FILE.write_text(updated)
    print(f"Updated: {SESSION_FILE}")


if __name__ == "__main__":
    main()