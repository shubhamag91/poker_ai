#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from hand_history_utils import extract_tournament_id, is_summary_text, parse_tournament_summary_file, read_text
from openai import OpenAI
import urllib.request
import urllib.error
from postflop_trees import build_flop_tree_spec_library, filtered_flop_specs
from tournament_context import enrich_tournament_summary, paid_seats_for_field_size, itm_pct_for_field_size

DEFAULT_HERO_NAME = "Hero"
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "raw"
PARSED_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "parsed"
SUMMARY_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "summaries"
METADATA_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "metadata"
DEFAULT_INPUT_FILE = RAW_ROOT / "GG20260216-1224 - APL Series 110 Zodiac Evening Classic + Horse.txt"
ENV_FILE = PROJECT_ROOT / ".env"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def read_file(file_path: Path) -> str:
    return read_text(file_path)


def discover_tournament_summary(input_path: Path, explicit_summary: Optional[str]) -> Optional[dict]:
    if explicit_summary:
        summary_path = Path(explicit_summary).expanduser().resolve()
        if not summary_path.exists():
            raise FileNotFoundError(f"Summary file not found: {summary_path}")
        raw_summary = parse_tournament_summary_file(summary_path)
        return enrich_tournament_summary(raw_summary, raw_summary.get("tournament_name", ""))

    if not input_path.exists():
        return None

    tournament_id = extract_tournament_id(read_file(input_path)[:5000])
    if not tournament_id:
        return None

    candidate_roots = [SUMMARY_ROOT, input_path.parent]
    seen = set()
    for root in candidate_roots:
        if not root.exists():
            continue
        for candidate in sorted(root.rglob("*")):
            if candidate in seen or not candidate.is_file() or candidate.suffix.lower() not in {".txt", ".log"}:
                continue
            seen.add(candidate)
            text = read_file(candidate)
            if not is_summary_text(text):
                continue
            parsed = parse_tournament_summary_file(candidate)
            if parsed.get("tournament_id") == tournament_id:
                return enrich_tournament_summary(parsed, parsed.get("tournament_name", ""))
    return None


def describe_field_size(total_players: Optional[int]) -> str:
    if not total_players:
        return "unknown"
    if total_players >= 5000:
        return "massive"
    if total_players >= 1000:
        return "large"
    if total_players >= 250:
        return "medium"
    return "small"


def format_int(value: Optional[int]) -> str:
    return f"{value:,}" if isinstance(value, int) else "unknown"


def build_summary_stage_hint(summary: Optional[dict]) -> dict:
    if not summary or not summary.get("total_players"):
        return {"available": False}

    total_players = summary["total_players"]
    finish_place = summary.get("finish_place")
    field_band = describe_field_size(total_players)
    note_parts = [f"field size {format_int(total_players)} ({field_band})"]
    lower_bound_players_remaining = None

    if finish_place and 1 <= finish_place <= total_players:
        lower_bound_players_remaining = finish_place
        note_parts.append(
            f"Hero later busted {finish_place:,}th, so this hand was played with at least {finish_place:,} players still alive"
        )

    icm = summary.get("icm", {})
    if icm:
        paid = icm.get("estimated_paid_seats")
        itm = icm.get("itm_pct")
        cluster = icm.get("cluster")
        if paid:
            note_parts.append(f"~{paid} paid ({itm}% ITM)")
        if cluster:
            note_parts.append(f"cluster: {cluster}")

    return {
        "available": True,
        "field_size_band": field_band,
        "total_players": total_players,
        "finish_place": finish_place,
        "min_players_remaining": lower_bound_players_remaining,
        "icm_cluster": icm.get("cluster") if icm else None,
        "estimated_paid_seats": icm.get("estimated_paid_seats") if icm else None,
        "itm_pct": icm.get("itm_pct") if icm else None,
        "note": "; ".join(note_parts),
    }


def split_hands(text: str):
    hands = re.split(r'(Hand #\w+:|Poker Hand #\w+:)', text)
    combined = []
    for i in range(1, len(hands), 2):
        combined.append(hands[i] + hands[i + 1])
    return combined


def extract_hand_timestamp(hand: str) -> Optional[datetime]:
    first_line = hand.splitlines()[0] if hand.splitlines() else ""
    match = re.search(r"-\s+(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})\s*$", first_line)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y/%m/%d %H:%M:%S")
    except ValueError:
        return None


def derive_starting_stack_from_hero_hands(raw_text: str, hero_name: str) -> Optional[int]:
    earliest_stack = None
    earliest_timestamp = None

    for hand in split_hands(raw_text):
        hero_chips = extract_hero_chips(hand, hero_name)
        if hero_chips is None:
            continue

        hand_timestamp = extract_hand_timestamp(hand)
        if hand_timestamp is None:
            if earliest_stack is None:
                earliest_stack = hero_chips
            continue

        if earliest_timestamp is None or hand_timestamp < earliest_timestamp:
            earliest_timestamp = hand_timestamp
            earliest_stack = hero_chips

    return earliest_stack


def compute_pko_bounty_ev(
    starting_stack_chips: Optional[int],
    starting_bounty_cash: Optional[float],
    target_displayed_bounty_cash: Optional[float],
    current_big_blind: Optional[int],
    future_discount: float = 0.5,
) -> Optional[dict]:
    if (
        starting_stack_chips is None
        or current_big_blind is None
        or not starting_bounty_cash
        or not target_displayed_bounty_cash
        or starting_stack_chips <= 0
        or current_big_blind <= 0
        or starting_bounty_cash <= 0
        or target_displayed_bounty_cash <= 0
    ):
        return None

    chips_per_bounty_dollar = starting_stack_chips / starting_bounty_cash
    immediate_cash = 0.5 * target_displayed_bounty_cash
    future_cash_equiv = future_discount * 0.5 * target_displayed_bounty_cash
    total_effective_cash = immediate_cash + future_cash_equiv
    immediate_bounty_bb = (immediate_cash * chips_per_bounty_dollar) / current_big_blind
    future_bounty_bb = (future_cash_equiv * chips_per_bounty_dollar) / current_big_blind

    return {
        "starting_stack_chips": starting_stack_chips,
        "starting_bounty_cash": round(starting_bounty_cash, 4),
        "target_displayed_bounty_cash": round(target_displayed_bounty_cash, 4),
        "current_big_blind": current_big_blind,
        "future_discount": future_discount,
        "immediate_cash": round(immediate_cash, 4),
        "future_cash_equiv": round(future_cash_equiv, 4),
        "total_effective_cash": round(total_effective_cash, 4),
        "total_bounty_chips": round(total_effective_cash * chips_per_bounty_dollar, 2),
        "immediate_bounty_bb": round(immediate_bounty_bb, 2),
        "future_bounty_bb": round(future_bounty_bb, 2),
        "total_bounty_bb": round(immediate_bounty_bb + future_bounty_bb, 2),
        "bounty_ratio": round(target_displayed_bounty_cash / starting_bounty_cash, 4),
    }


def coerce_positive_float(value) -> Optional[float]:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def load_pko_bounty_sidecar(input_path: Path, raw_text: Optional[str] = None) -> Optional[dict]:
    raw_text = raw_text if raw_text is not None else read_file(input_path)
    tournament_id = extract_tournament_id(raw_text[:5000])

    candidates = [METADATA_ROOT / f"{input_path.stem}.pko.json"]
    if tournament_id:
        candidates.append(METADATA_ROOT / f"tournament_{tournament_id}.pko.json")

    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if str(payload.get("format", "")).upper() != "PKO":
            continue
        payload_tournament_id = payload.get("tournament_id")
        if tournament_id and payload_tournament_id and str(payload_tournament_id) != str(tournament_id):
            continue
        payload["source_path"] = str(candidate)
        return payload

    return None


def resolve_pko_displayed_bounty_cash(sidecar: Optional[dict], player_name: Optional[str], hero_name: str = DEFAULT_HERO_NAME) -> Optional[float]:
    if not sidecar or not player_name:
        return None

    defaults = sidecar.get("defaults") if isinstance(sidecar.get("defaults"), dict) else {}
    default_value = coerce_positive_float(defaults.get("displayed_bounty_cash"))

    if player_name == hero_name:
        hero = sidecar.get("hero") if isinstance(sidecar.get("hero"), dict) else {}
        return coerce_positive_float(hero.get("displayed_bounty_cash")) or default_value

    players = sidecar.get("players") if isinstance(sidecar.get("players"), dict) else {}
    player_entry = players.get(player_name) if isinstance(players.get(player_name), dict) else {}
    return coerce_positive_float(player_entry.get("displayed_bounty_cash")) or default_value


def build_pko_bounty_inputs(
    input_path: Path,
    raw_text: str,
    hero_name: str = DEFAULT_HERO_NAME,
    target_name: Optional[str] = None,
) -> dict:
    sidecar = load_pko_bounty_sidecar(input_path, raw_text)
    starting_bounty_cash = coerce_positive_float(sidecar.get("starting_bounty_cash")) if sidecar else None
    future_discount = sidecar.get("future_discount", 0.5) if sidecar else 0.5
    try:
        future_discount = float(future_discount)
    except (TypeError, ValueError):
        future_discount = 0.5

    return {
        "available": sidecar is not None,
        "sidecar_path": sidecar.get("source_path") if sidecar else None,
        "starting_stack_chips": derive_starting_stack_from_hero_hands(raw_text, hero_name),
        "starting_bounty_cash": starting_bounty_cash,
        "future_discount": future_discount,
        "hero_displayed_bounty_cash": resolve_pko_displayed_bounty_cash(sidecar, hero_name, hero_name),
        "target_displayed_bounty_cash": resolve_pko_displayed_bounty_cash(sidecar, target_name, hero_name),
    }


def last_prior_all_in_actor(context: dict) -> Optional[str]:
    for line in reversed(context.get("prior_actions", [])):
        if "all-in" in line.lower() and ":" in line:
            return line.split(":", 1)[0].strip()
    return None


def build_pko_bounty_profile(
    input_path: Optional[Path],
    raw_text: Optional[str],
    hand: str,
    info: dict,
    hero_name: str,
    context: dict,
) -> dict:
    if input_path is None or raw_text is None or not is_bounty_tournament(hand):
        return {"available": False}

    if context.get("decision_type") != "call_or_fold_vs_shove":
        return {"available": False}

    target_name = last_prior_all_in_actor(context)
    if not target_name or target_name == hero_name:
        return {"available": False}

    inputs = build_pko_bounty_inputs(input_path, raw_text, hero_name, target_name)
    ev = compute_pko_bounty_ev(
        inputs.get("starting_stack_chips"),
        inputs.get("starting_bounty_cash"),
        inputs.get("target_displayed_bounty_cash"),
        info.get("bb"),
        inputs.get("future_discount", 0.5),
    )
    if not ev:
        return {"available": False}

    total_bounty_bb = ev["total_bounty_bb"]
    if total_bounty_bb >= 15:
        pull = "strong"
    elif total_bounty_bb >= 8:
        pull = "meaningful"
    else:
        pull = "light"

    note = (
        f"PKO note: {target_name} bounty is worth about {ev['total_bounty_bb']} BB total "
        f"({ev['immediate_bounty_bb']} BB immediate + {ev['future_bounty_bb']} BB discounted future). "
        "This can justify slightly wider continues in close all-in spots, but should not override dominated-trash folds or heavy survival pressure."
    )

    return {
        "available": True,
        "target_name": target_name,
        "inputs": inputs,
        "ev": ev,
        "pull": pull,
        "note": note,
    }


def extract_positions(hand: str, hero_name: str):
    lines = hand.split("\n")
    button_seat = None
    hero_seat = None
    active_seats = []

    for line in lines:
        if "is the button" in line:
            match = re.search(r'Seat #(\d+)', line)
            if match:
                button_seat = int(match.group(1))

        if line.strip().startswith("Seat") and "in chips" in line:
            if "sitting out" in line.lower():
                continue
            match = re.search(r'Seat (\d+):', line)
            if match:
                seat = int(match.group(1))
                active_seats.append(seat)
                if f" {hero_name} " in line or f": {hero_name}" in line:
                    hero_seat = seat

    return button_seat, hero_seat, sorted(active_seats)


def assign_positions(button_seat, seats):
    if not seats:
        return {}
    if button_seat not in seats:
        potential_btns = [s for s in seats if s <= button_seat]
        button_seat = potential_btns[-1] if potential_btns else seats[-1]

    btn_index = seats.index(button_seat)
    ordered = seats[btn_index + 1 :] + seats[: btn_index + 1]
    num_players = len(ordered)

    if num_players == 2:
        positions_order = ["SB/BTN", "BB"]
    elif num_players == 3:
        positions_order = ["SB", "BB", "BTN"]
    else:
        core = ["SB", "BB"]
        middle_count = num_players - 4
        middles = ["UTG"] + [f"UTG+{i}" for i in range(1, middle_count + 1)] if middle_count >= 0 else []
        positions_order = core + middles + ["CO", "BTN"]

    while len(positions_order) < len(ordered):
        positions_order.insert(2, "MP")

    return {seat: positions_order[i] for i, seat in enumerate(ordered)}


def extract_bb_value(hand: str):
    level_match = re.search(r'Level \d+ \([\d,]+/([\d,]+)\)', hand)
    if level_match:
        return int(level_match.group(1).replace(",", ""))

    header_match = re.search(r'\(([\d,]+)/([\d,]+)\)', hand)
    if header_match:
        return int(header_match.group(2).replace(",", ""))

    bb_literal = re.search(r'Big Blind ([\d,]+)', hand, re.IGNORECASE)
    if bb_literal:
        return int(bb_literal.group(1).replace(",", ""))

    return None


def extract_hero_chips(hand: str, hero_name: str):
    match = re.search(rf'Seat \d+: {re.escape(hero_name)} \((\d[\d,]*)\s+in chips\)', hand)
    if match:
        return int(match.group(1).replace(",", ""))
    return None


def extract_info(hand: str, hero_name: str):
    bb = extract_bb_value(hand)
    chips = extract_hero_chips(hand, hero_name)

    if not bb:
        first_line = hand.split('\n')[0]
        m = re.search(r'/([\d,]+)\)', first_line)
        if m:
            bb = int(m.group(1).replace(",", ""))

    info = {
        "hero_cards": "Unknown",
        "hero_chips": chips,
        "bb": bb,
        "hero_vpip": False,
        "hero_all_in": False,
        "position": "UNKNOWN",
    }

    btn, hero_s, seats = extract_positions(hand, hero_name)
    if btn is not None and hero_s is not None:
        pos_map = assign_positions(btn, seats)
        info["position"] = pos_map.get(hero_s, "UNKNOWN")

    if info["hero_chips"] is not None and info["bb"]:
        info["hero_bb"] = round(info["hero_chips"] / info["bb"], 2)
    else:
        info["hero_bb"] = "N/A"

    lines = hand.split("\n")
    for line in lines:
        if f"Dealt to {hero_name}" in line:
            info["hero_cards"] = line.split("[")[-1].split("]")[0] if "[" in line else "Unknown"
        if line.startswith(f"{hero_name}:"):
            if any(x in line for x in ["calls", "raises", "bets"]):
                info["hero_vpip"] = True
            if "all-in" in line.lower():
                info["hero_all_in"] = True
    return info


def is_important(hand: str, info: dict, hero_name: str):
    if info["hero_vpip"] or info["hero_all_in"]:
        return True
    if info["position"] in ["BB", "SB"] and ("raises" in hand or "all-in" in hand.lower()):
        if f"{hero_name}: folds" in hand:
            return True
    return False


def normalize_analysis_text(text: str) -> str:
    desired = ["Mistake:", "Better play:", "Reason:", "Confidence:"]
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    picked = []
    for prefix in desired:
        match = next((line for line in lines if line.startswith(prefix)), None)
        if match:
            picked.append(match)
    return "\n".join(picked) if len(picked) >= 3 else text.strip()


def parse_analysis_fields(text: str) -> dict:
    normalized = normalize_analysis_text(text)
    fields = {
        "Mistake": "Unknown",
        "Better play": "Unknown",
        "Reason": normalized,
        "Confidence": "unknown",
    }
    for line in normalized.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in fields and value:
            fields[key] = value
    return fields


def summarize_rule_verdict(context: dict) -> str:
    mapping = {
        "under_1bb_no_fold": "Under 1 BB, folding away equity is a rule-based mistake.",
        "under_1bb_correct_commit": "With 1 BB or less, committing the stack is protected by the rule layer.",
        "raise_too_small_short_stack": "At a critical short stack, a small raise should usually become an open shove.",
        "reasonable_open_shove": "This stack-depth and hand-class combination fits a reasonable open-shove rule bucket.",
        "reasonable_open_raise": "This stack-depth and hand-class combination fits a reasonable min-raise rule bucket.",
        "strong_hand_call_vs_shove": "Strong aces and solid pairs are protected continue hands in call-versus-shove spots at these stack depths.",
        "conservative_blind_fold_vs_shove": "In blind defense versus a shove, conservative folds with weak dominated hands are protected by the rule layer.",
        "overdefend_blind_call_vs_shove": "The rule layer flags this as an over-defend in a blind-versus-shove spot.",
        "disciplined_multiway_sb_fold": "Short-stack multi-way small-blind folds with weak suited hands are protected by the rule layer.",
        "sb_reshove_candidate": "This looks like a short-stack small-blind reshove candidate rather than a fold.",
    }
    if context.get("matched_rule") in mapping:
        return mapping[context["matched_rule"]]
    return (
        f"Decision={context.get('decision_type', 'unknown')}, "
        f"PositionGroup={context.get('position_group', 'unknown')}, "
        f"StackBucket={context.get('stack_bucket', 'unknown')}, "
        f"HandClass={context.get('hand_class', 'unknown')}"
    )


def format_analysis_output(fields: dict, verdict_source: str, confidence_source: str, rule_verdict: str, ai_explanation: str) -> str:
    return "\n".join(
        [
            f"Mistake: {fields['Mistake']}",
            f"Better play: {fields['Better play']}",
            f"Reason: {fields['Reason']}",
            f"Confidence: {fields['Confidence']}",
            f"Verdict source: {verdict_source}",
            f"Confidence source: {confidence_source}",
            f"Rule verdict: {rule_verdict}",
            f"AI explanation: {ai_explanation}",
        ]
    )


RANK_ORDER = "23456789TJQKA"


def rank_value(rank: str) -> int:
    return RANK_ORDER.index(rank)


def describe_hole_cards(cards: str) -> dict:
    parts = cards.split()
    if len(parts) != 2 or len(parts[0]) < 2 or len(parts[1]) < 2:
        return {}
    r1, s1 = parts[0][0], parts[0][1]
    r2, s2 = parts[1][0], parts[1][1]
    high, low = sorted([r1, r2], key=rank_value, reverse=True)
    return {
        "ranks": (r1, r2),
        "high": high,
        "low": low,
        "pair": r1 == r2,
        "suited": s1 == s2,
        "gap": abs(rank_value(r1) - rank_value(r2)),
    }


def extract_preflop_lines(hand: str):
    lines = hand.splitlines()
    hole_idx = next((i for i, line in enumerate(lines) if line.startswith("*** HOLE CARDS ***")), 0)
    flop_idx = next((i for i, line in enumerate(lines) if line.startswith("*** FLOP ***")), len(lines))
    return lines[hole_idx:flop_idx]


def extract_flop_cards(hand: str) -> list[str]:
    for line in hand.splitlines():
        if not line.startswith("*** FLOP ***"):
            continue
        match = re.search(r"\[(..)\s+(..)\s+(..)\]", line)
        if match:
            return [match.group(1), match.group(2), match.group(3)]
    return []


def extract_turn_card(hand: str) -> Optional[str]:
    for line in hand.splitlines():
        if not line.startswith("*** TURN ***"):
            continue
        match = re.search(r"\[(..)\s+(..)\s+(..)\s+(..)\]", line)
        if match:
            return match.group(4)
    return None


def extract_river_card(hand: str) -> Optional[str]:
    for line in hand.splitlines():
        if not line.startswith("*** RIVER ***"):
            continue
        match = re.search(r"\[(..)\s+(..)\s+(..)\s+(..)\s+(..)\]", line)
        if match:
            return match.group(5)
    return None


def flop_texture_features(cards: list[str]) -> dict:
    if len(cards) != 3:
        return {}

    ranks = [card[0] for card in cards]
    suits = [card[1] for card in cards]
    rank_indices = sorted(rank_value(rank) for rank in ranks)
    unique_rank_indices = sorted(set(rank_indices))
    suit_counts = {suit: suits.count(suit) for suit in set(suits)}
    gaps = [
        unique_rank_indices[i + 1] - unique_rank_indices[i]
        for i in range(len(unique_rank_indices) - 1)
    ]
    broadway_count = sum(rank in {"T", "J", "Q", "K", "A"} for rank in ranks)
    high_rank = max(ranks, key=rank_value)
    second_high_rank = sorted(ranks, key=rank_value, reverse=True)[1]
    low_rank = min(ranks, key=rank_value)
    low_card_gap = abs(rank_value(second_high_rank) - rank_value(low_rank))
    span = unique_rank_indices[-1] - unique_rank_indices[0]
    monotone = len(suit_counts) == 1
    two_tone = max(suit_counts.values()) == 2
    paired = len(unique_rank_indices) < 3
    straight_pressure = len(unique_rank_indices) == 3 and (
        span <= 4
        or (high_rank not in {"A", "K", "Q"} and span <= 5)
        or (high_rank == "A" and low_card_gap <= 2)
    )
    ace_high_dry = (
        high_rank == "A"
        and second_high_rank not in {"J", "Q", "K"}
        and low_rank in {"2", "3", "4", "5", "6", "7", "8"}
        and low_card_gap >= 3
        and not two_tone
        and not monotone
        and not straight_pressure
    )

    return {
        "ranks": ranks,
        "suits": suits,
        "high_rank": high_rank,
        "second_high_rank": second_high_rank,
        "low_rank": low_rank,
        "broadway_count": broadway_count,
        "span": span,
        "gaps": gaps,
        "low_card_gap": low_card_gap,
        "monotone": monotone,
        "two_tone": two_tone,
        "paired": paired,
        "straight_pressure": straight_pressure,
        "ace_high_dry": ace_high_dry,
    }


def classify_core_flop_bucket(cards: list[str]) -> Optional[str]:
    features = flop_texture_features(cards)
    if not features:
        return None
    if features["monotone"]:
        return "MONOTONE"
    if features["paired"]:
        return "PAIRED"
    if features["ace_high_dry"]:
        return "A_HIGH_DRY"
    if features["straight_pressure"]:
        return "MID_CONNECTED"
    if features["two_tone"]:
        return "TWO_TONE"
    return "BROADWAY_STATIC"


def classify_three_bet_flop_bucket(cards: list[str]) -> Optional[str]:
    features = flop_texture_features(cards)
    if not features:
        return None
    if features["monotone"]:
        return "MONOTONE"
    if features["paired"]:
        return "PAIRED"
    if features["high_rank"] == "A":
        return "ACE_HIGH"
    if features["high_rank"] == "K":
        return "KING_HIGH"
    if features["straight_pressure"] or features["two_tone"]:
        return "MID_DYNAMIC"
    return "LOW_STATIC"


def classify_blind_battle_flop_bucket(cards: list[str]) -> Optional[str]:
    features = flop_texture_features(cards)
    if not features:
        return None
    if features["monotone"]:
        return "MONOTONE"
    if features["paired"]:
        return "PAIRED"
    if features["straight_pressure"]:
        return "LOW_CONNECTED"
    if features["high_rank"] in {"A", "K", "Q", "J", "T"}:
        return "HIGH_CARD_STATIC"
    return "LOW_DISCONNECTED"


def classify_flop_board_bucket(hand: str, board_bucket_set_ref: str) -> Optional[str]:
    cards = extract_flop_cards(hand)
    if board_bucket_set_ref == "core_flop_textures_v1":
        return classify_core_flop_bucket(cards)
    if board_bucket_set_ref == "three_bet_textures_v1":
        return classify_three_bet_flop_bucket(cards)
    if board_bucket_set_ref == "blind_battle_textures_v1":
        return classify_blind_battle_flop_bucket(cards)
    return None


def canonical_position_label(position: str) -> str:
    mapping = {
        "SB/BTN": "BTN",
        "UTG+1": "HJ",
        "UTG+2": "LJ",
    }
    return mapping.get(position, position)


def raw_position_label(position: str) -> str:
    return "BTN" if position == "SB/BTN" else position


def position_order_key(position: str) -> int:
    canonical = canonical_position_label(position)
    if canonical == "SB":
        return 0
    if canonical == "BB":
        return 1
    if canonical == "UTG":
        return 2
    if canonical == "MP":
        return 50
    if canonical == "LJ":
        return 55
    if canonical == "HJ":
        return 60
    if canonical == "CO":
        return 90
    if canonical == "BTN":
        return 100
    if canonical.startswith("UTG+"):
        try:
            return 2 + int(canonical.split("+", 1)[1])
        except ValueError:
            return 40
    return 40


def preflop_action_order_key(position: str) -> int:
    raw = raw_position_label(position)
    if raw == "UTG":
        return 0
    if raw.startswith("UTG+"):
        try:
            return int(raw.split("+", 1)[1]) + 1
        except ValueError:
            return 20
    if raw == "MP":
        return 30
    if raw == "LJ":
        return 40
    if raw == "HJ":
        return 50
    if raw == "CO":
        return 60
    if raw == "BTN":
        return 70
    if raw == "SB":
        return 80
    if raw == "BB":
        return 90
    return 20


def build_position_group_map(position_labels: list[str]) -> dict[str, str]:
    raw_labels = []
    for label in position_labels:
        raw = raw_position_label(label)
        if raw not in raw_labels:
            raw_labels.append(raw)

    groups: dict[str, str] = {}
    for label in raw_labels:
        if label == "BB":
            groups[label] = "BB"
        elif label == "SB":
            groups[label] = "SB"
        elif label == "BTN":
            groups[label] = "BTN"
        elif label == "CO":
            groups[label] = "LP"

    remaining = sorted([label for label in raw_labels if label not in groups], key=preflop_action_order_key)
    remaining_count = len(remaining)
    if remaining_count == 1:
        groups[remaining[0]] = "EP"
    elif remaining_count == 2:
        groups[remaining[0]] = "EP"
        groups[remaining[1]] = "MP"
    elif remaining_count == 3:
        groups[remaining[0]] = "EP"
        groups[remaining[1]] = "EP"
        groups[remaining[2]] = "MP"
    elif remaining_count == 4:
        groups[remaining[0]] = "EP"
        groups[remaining[1]] = "EP"
        groups[remaining[2]] = "MP"
        groups[remaining[3]] = "MP"
    elif remaining_count >= 5:
        for index, label in enumerate(remaining):
            groups[label] = "EP" if index < 3 else "MP"

    return groups


def grouped_path_shape_for_structure(structure: dict) -> str:
    if not structure.get("available"):
        return "unknown"

    pot_type = structure.get("pot_type")
    open_group = structure.get("open_raiser_group", "UNKNOWN")
    caller_group = structure.get("caller_group", "UNKNOWN")
    three_bettor_group = structure.get("three_bettor_group", "UNKNOWN")
    open_raw = structure.get("open_raiser_raw_position", "UNKNOWN")
    caller_raw = structure.get("caller_raw_position", "UNKNOWN")
    three_bettor_raw = structure.get("three_bettor_raw_position", "UNKNOWN")

    if pot_type == "single_raised_pot":
        if caller_group not in {"SB", "BB"} and preflop_action_order_key(caller_raw) <= preflop_action_order_key(open_raw):
            return "invalid_grouping"
        if caller_group == "BB":
            return f"SRP {open_group} open vs BB defend"
        if caller_group == "SB":
            return f"SRP {open_group} open vs SB flat"
        return f"SRP {open_group} open vs {caller_group} flat"

    if pot_type == "three_bet_pot":
        if preflop_action_order_key(three_bettor_raw) <= preflop_action_order_key(open_raw):
            return "invalid_grouping"
        return f"3BP {three_bettor_group} 3bets vs {open_group} open"

    return "unknown"


def extract_preflop_structure(hand: str, hero_name: str) -> dict:
    if "*** FLOP ***" not in hand:
        return {"available": False, "reason": "Hand did not reach the flop."}

    players = extract_player_stacks(hand)
    btn, hero_seat, seats = extract_positions(hand, hero_name)
    position_map = assign_positions(btn, seats) if btn is not None and seats else {}
    if not position_map:
        return {"available": False, "reason": "Could not resolve table positions."}

    canonical_position_map = {seat: canonical_position_label(label) for seat, label in position_map.items()}
    raw_position_map = {seat: raw_position_label(label) for seat, label in position_map.items()}
    position_group_map = build_position_group_map(list(raw_position_map.values()))

    active_players = set(players)
    raise_count = 0
    open_raiser = None
    three_bettor = None
    last_raiser = None
    aggressor_history = []
    callers_after_final_raise = []
    unopened_callers = []

    for line in extract_preflop_lines(hand):
        if line.startswith("Uncalled bet (") and " returned to " in line and not callers_after_final_raise and len(aggressor_history) >= 2:
            prior_aggressor = aggressor_history[-2]
            if prior_aggressor in active_players and prior_aggressor != aggressor_history[-1]:
                callers_after_final_raise = [prior_aggressor]
            continue

        if ":" not in line or line.startswith("Dealt to ") or line.startswith("***"):
            continue
        if ": posts " in line:
            continue

        actor = line.split(":", 1)[0]
        lower = line.lower()

        if ": folds" in line:
            active_players.discard(actor)
            continue

        if ": calls " in line:
            if raise_count == 0:
                unopened_callers.append(actor)
            elif actor != last_raiser:
                callers_after_final_raise.append(actor)
            continue

        if ": raises " in line:
            raise_count += 1
            if raise_count == 1:
                open_raiser = actor
            elif raise_count == 2:
                three_bettor = actor
            aggressor_history.append(actor)
            last_raiser = actor
            callers_after_final_raise = []
            continue


    if unopened_callers:
        return {"available": False, "reason": "Unsupported limped or overcalled preflop path."}
    if raise_count not in {1, 2}:
        return {"available": False, "reason": f"Unsupported raise count {raise_count} for current spec library."}
    if len(active_players) != 2:
        return {"available": False, "reason": f"Expected heads-up flop, found {len(active_players)} players."}
    if len(callers_after_final_raise) != 1 and last_raiser in active_players:
        remaining_non_raiser = [player for player in active_players if player != last_raiser]
        if len(remaining_non_raiser) == 1:
            callers_after_final_raise = [remaining_non_raiser[0]]
    if len(callers_after_final_raise) != 1:
        return {"available": False, "reason": "Could not identify one clean caller to the final raise."}

    caller = callers_after_final_raise[0]
    if open_raiser not in players or caller not in players:
        return {"available": False, "reason": "Could not map preflop actors back to seats."}

    open_raiser_position = canonical_position_map.get(players[open_raiser]["seat"], "UNKNOWN")
    caller_position = canonical_position_map.get(players[caller]["seat"], "UNKNOWN")
    three_bettor_position = canonical_position_map.get(players[three_bettor]["seat"], "UNKNOWN") if three_bettor else None
    open_raiser_raw_position = raw_position_map.get(players[open_raiser]["seat"], "UNKNOWN")
    caller_raw_position = raw_position_map.get(players[caller]["seat"], "UNKNOWN")
    three_bettor_raw_position = raw_position_map.get(players[three_bettor]["seat"], "UNKNOWN") if three_bettor else None

    structure = {
        "available": True,
        "pot_type": "three_bet_pot" if raise_count == 2 else "single_raised_pot",
        "raise_count": raise_count,
        "open_raiser": open_raiser,
        "caller": caller,
        "three_bettor": three_bettor,
        "open_raiser_position": open_raiser_position,
        "caller_position": caller_position,
        "three_bettor_position": three_bettor_position,
        "open_raiser_raw_position": open_raiser_raw_position,
        "caller_raw_position": caller_raw_position,
        "three_bettor_raw_position": three_bettor_raw_position,
        "open_raiser_group": position_group_map.get(open_raiser_raw_position, "UNKNOWN"),
        "caller_group": position_group_map.get(caller_raw_position, "UNKNOWN"),
        "three_bettor_group": position_group_map.get(three_bettor_raw_position, "UNKNOWN") if three_bettor_raw_position else None,
        "hero_role": (
            "three_bettor"
            if hero_name == three_bettor
            else "open_raiser"
            if hero_name == open_raiser
            else "caller"
            if hero_name == caller
            else "other"
        ),
        "hero_position": canonical_position_map.get(hero_seat, "UNKNOWN"),
        "hero_group": position_group_map.get(raw_position_map.get(hero_seat, "UNKNOWN"), "UNKNOWN"),
        "hero_is_ip": position_order_key(canonical_position_map.get(hero_seat, "UNKNOWN"))
        > position_order_key(caller_position if hero_name == open_raiser else open_raiser_position),
    }
    structure["grouped_path_shape"] = grouped_path_shape_for_structure(structure)
    return structure


def scan_preflop_path_basics(hand: str, hero_name: str) -> dict:
    if "*** FLOP ***" not in hand:
        return {"available": False, "reason": "Hand did not reach the flop."}

    players = extract_player_stacks(hand)
    btn, _, seats = extract_positions(hand, hero_name)
    position_map = assign_positions(btn, seats) if btn is not None and seats else {}
    canonical_position_map = {seat: canonical_position_label(label) for seat, label in position_map.items()}
    raw_position_map = {seat: raw_position_label(label) for seat, label in position_map.items()}

    active_players = set(players)
    raise_count = 0
    unopened_callers = []
    last_raiser = None

    for line in extract_preflop_lines(hand):
        if ":" not in line or line.startswith("Dealt to ") or line.startswith("***"):
            continue
        if ": posts " in line:
            continue

        actor = line.split(":", 1)[0]
        if ": folds" in line:
            active_players.discard(actor)
            continue
        if ": calls " in line:
            if raise_count == 0:
                unopened_callers.append(actor)
            continue
        if ": raises " in line:
            raise_count += 1
            last_raiser = actor
            continue

    aggressor_is_ip = None
    aggressor_position = None
    other_position = None
    oop_position = None
    ip_position = None
    ordered_active_positions = []
    aggressor_flop_order = None

    active_position_rows = []
    if position_map:
        for player in active_players:
            seat = players.get(player, {}).get("seat")
            position = canonical_position_map.get(seat)
            if not position:
                continue
            active_position_rows.append((position_order_key(position), player, position))
        active_position_rows.sort(key=lambda row: row[0])
        ordered_active_positions = [row[2] for row in active_position_rows]

    if last_raiser in players and position_map:
        aggressor_position = canonical_position_map.get(players[last_raiser]["seat"])
        if aggressor_position and ordered_active_positions:
            try:
                aggressor_index = ordered_active_positions.index(aggressor_position)
                aggressor_flop_order = {0: "first", 1: "middle", 2: "last"}.get(aggressor_index)
            except ValueError:
                aggressor_flop_order = None

    if len(active_players) == 2 and ordered_active_positions:
        oop_position = ordered_active_positions[0]
        ip_position = ordered_active_positions[-1]
        other_position = oop_position if aggressor_position == ip_position else ip_position
        if aggressor_position and oop_position and ip_position:
            aggressor_is_ip = aggressor_position == ip_position

    return {
        "available": True,
        "raise_count": raise_count,
        "unopened_callers_count": len(unopened_callers),
        "has_unopened_callers": bool(unopened_callers),
        "flop_player_count": len(active_players),
        "last_raiser": last_raiser,
        "aggressor_is_ip": aggressor_is_ip,
        "aggressor_position": aggressor_position,
        "other_position": other_position,
        "oop_position": oop_position,
        "ip_position": ip_position,
        "ordered_active_positions": ordered_active_positions,
        "aggressor_flop_order": aggressor_flop_order,
    }


def exact_complex_matchup_id(family_id: str, scan: dict, library: dict) -> Optional[str]:
    oop = scan.get("oop_position")
    ip = scan.get("ip_position")
    ordered_positions = scan.get("ordered_active_positions") or []
    aggressor_position = scan.get("aggressor_position")

    prefix_map = {
        "raised_after_limp_ip_aggressor_flop": f"raised_after_limp_ip_aggr_{ip}_vs_{oop}" if oop and ip else None,
        "raised_after_limp_oop_aggressor_flop": f"raised_after_limp_oop_aggr_{oop}_vs_{ip}" if oop and ip else None,
        "four_bet_ip_aggressor_flop": f"four_bet_ip_aggr_{ip}_vs_{oop}" if oop and ip else None,
        "four_bet_oop_aggressor_flop": f"four_bet_oop_aggr_{oop}_vs_{ip}" if oop and ip else None,
        "five_bet_plus_ip_aggressor_flop": f"five_bet_plus_ip_aggr_{ip}_vs_{oop}" if oop and ip else None,
        "five_bet_plus_oop_aggressor_flop": f"five_bet_plus_oop_aggr_{oop}_vs_{ip}" if oop and ip else None,
        "multiway_srp_3way_oop_aggressor_flop": f"multiway_srp_3way_oop_aggr_{ordered_positions[0]}_{ordered_positions[1]}_{ordered_positions[2]}" if len(ordered_positions) == 3 else None,
        "multiway_srp_3way_middle_aggressor_flop": f"multiway_srp_3way_middle_aggr_{ordered_positions[0]}_{ordered_positions[1]}_{ordered_positions[2]}" if len(ordered_positions) == 3 else None,
        "multiway_srp_3way_ip_aggressor_flop": f"multiway_srp_3way_ip_aggr_{ordered_positions[0]}_{ordered_positions[1]}_{ordered_positions[2]}" if len(ordered_positions) == 3 else None,
        "multiway_3bp_3way_oop_aggressor_flop": f"multiway_3bp_3way_oop_aggr_{ordered_positions[0]}_{ordered_positions[1]}_{ordered_positions[2]}" if len(ordered_positions) == 3 else None,
        "multiway_3bp_3way_middle_aggressor_flop": f"multiway_3bp_3way_middle_aggr_{ordered_positions[0]}_{ordered_positions[1]}_{ordered_positions[2]}" if len(ordered_positions) == 3 else None,
        "multiway_3bp_3way_ip_aggressor_flop": f"multiway_3bp_3way_ip_aggr_{ordered_positions[0]}_{ordered_positions[1]}_{ordered_positions[2]}" if len(ordered_positions) == 3 else None,
        "raised_after_limp_3way_oop_aggressor_flop": f"raised_after_limp_3way_oop_aggr_{ordered_positions[0]}_{ordered_positions[1]}_{ordered_positions[2]}" if len(ordered_positions) == 3 else None,
        "raised_after_limp_3way_middle_aggressor_flop": f"raised_after_limp_3way_middle_aggr_{ordered_positions[0]}_{ordered_positions[1]}_{ordered_positions[2]}" if len(ordered_positions) == 3 else None,
        "raised_after_limp_3way_ip_aggressor_flop": f"raised_after_limp_3way_ip_aggr_{ordered_positions[0]}_{ordered_positions[1]}_{ordered_positions[2]}" if len(ordered_positions) == 3 else None,
        "four_bet_3way_oop_aggressor_flop": f"four_bet_3way_oop_aggr_{ordered_positions[0]}_{ordered_positions[1]}_{ordered_positions[2]}" if len(ordered_positions) == 3 else None,
        "four_bet_3way_middle_aggressor_flop": f"four_bet_3way_middle_aggr_{ordered_positions[0]}_{ordered_positions[1]}_{ordered_positions[2]}" if len(ordered_positions) == 3 else None,
        "four_bet_3way_ip_aggressor_flop": f"four_bet_3way_ip_aggr_{ordered_positions[0]}_{ordered_positions[1]}_{ordered_positions[2]}" if len(ordered_positions) == 3 else None,
    }
    candidate = prefix_map.get(family_id)
    if candidate and aggressor_position and candidate in library.get("matchup_instances", {}):
        return candidate
    return candidate if candidate in library.get("matchup_instances", {}) else None


def resolve_postflop_spec_components(hand: str, family_id: str, matchup_id: str) -> tuple[dict, dict, Optional[str], Optional[dict]]:
    library = build_flop_tree_spec_library()
    family = library["families"].get(family_id)
    matchup = library["matchup_instances"].get(matchup_id)
    if not family or not matchup:
        return {}, {}, None, None

    board_bucket = classify_flop_board_bucket(hand, family["board_bucket_set_ref"])
    if board_bucket:
        resolved = filtered_flop_specs(family=family_id, matchup=matchup_id, board_bucket=board_bucket)
        family = resolved["families"].get(family_id, family)
        matchup = resolved["matchup_instances"].get(matchup_id, matchup)
    return family, matchup, board_bucket, family.get("enforced_board_action_policy")


def identify_complex_postflop_path_tags(hand: str, hero_name: str) -> dict:
    scan = scan_preflop_path_basics(hand, hero_name)
    if not scan.get("available"):
        return scan

    flop_player_count = scan["flop_player_count"]
    raise_count = scan["raise_count"]
    has_unopened_callers = scan["has_unopened_callers"]
    family_id = None
    matchup_id = None
    aggressor_is_ip = scan.get("aggressor_is_ip")
    aggressor_flop_order = scan.get("aggressor_flop_order")

    if raise_count == 0 and flop_player_count == 2:
        family_id = "limped_pot_heads_up_flop"
        matchup_id = "limped_pot_2way"
    elif raise_count == 0 and has_unopened_callers:
        family_id = "limped_pot_multiway_flop"
        matchup_id = "limped_pot_3way" if flop_player_count == 3 else "limped_pot_4plus"
    elif raise_count == 1 and has_unopened_callers and flop_player_count == 2:
        family_id = "raised_after_limp_ip_aggressor_flop" if aggressor_is_ip else "raised_after_limp_oop_aggressor_flop"
        matchup_id = "iso_limped_pot_ip_aggressor" if aggressor_is_ip else "iso_limped_pot_oop_aggressor"
    elif raise_count == 1 and has_unopened_callers and flop_player_count >= 3:
        if flop_player_count == 3:
            if aggressor_flop_order == "first":
                family_id = "raised_after_limp_3way_oop_aggressor_flop"
                matchup_id = "raised_after_limp_3way_oop_aggressor"
            elif aggressor_flop_order == "middle":
                family_id = "raised_after_limp_3way_middle_aggressor_flop"
                matchup_id = "raised_after_limp_3way_middle_aggressor"
            else:
                family_id = "raised_after_limp_3way_ip_aggressor_flop"
                matchup_id = "raised_after_limp_3way_ip_aggressor"
        else:
            family_id = "raised_after_limp_multiway_flop"
            matchup_id = "overcalled_srp_4plus"
    elif has_unopened_callers and raise_count >= 2:
        if flop_player_count == 2:
            family_id = "raised_after_limp_ip_aggressor_flop" if aggressor_is_ip else "raised_after_limp_oop_aggressor_flop"
            matchup_id = "raised_after_limp_ip_aggressor" if aggressor_is_ip else "raised_after_limp_oop_aggressor"
        elif flop_player_count == 3:
            if aggressor_flop_order == "first":
                family_id = "raised_after_limp_3way_oop_aggressor_flop"
                matchup_id = "raised_after_limp_3way_oop_aggressor"
            elif aggressor_flop_order == "middle":
                family_id = "raised_after_limp_3way_middle_aggressor_flop"
                matchup_id = "raised_after_limp_3way_middle_aggressor"
            else:
                family_id = "raised_after_limp_3way_ip_aggressor_flop"
                matchup_id = "raised_after_limp_3way_ip_aggressor"
        else:
            family_id = "raised_after_limp_multiway_flop"
            matchup_id = "raised_after_limp_multiway"
    elif raise_count == 1 and flop_player_count >= 3:
        if flop_player_count == 3:
            if aggressor_flop_order == "first":
                family_id = "multiway_srp_3way_oop_aggressor_flop"
                matchup_id = "multiway_srp_3way_oop_aggressor"
            elif aggressor_flop_order == "middle":
                family_id = "multiway_srp_3way_middle_aggressor_flop"
                matchup_id = "multiway_srp_3way_middle_aggressor"
            else:
                family_id = "multiway_srp_3way_ip_aggressor_flop"
                matchup_id = "multiway_srp_3way_ip_aggressor"
        else:
            family_id = "multiway_srp_4plus_flop"
            matchup_id = "multiway_srp_4plus"
    elif raise_count == 2 and flop_player_count >= 3:
        if flop_player_count == 3:
            if aggressor_flop_order == "first":
                family_id = "multiway_3bp_3way_oop_aggressor_flop"
                matchup_id = "multiway_3bp_3way_oop_aggressor"
            elif aggressor_flop_order == "middle":
                family_id = "multiway_3bp_3way_middle_aggressor_flop"
                matchup_id = "multiway_3bp_3way_middle_aggressor"
            else:
                family_id = "multiway_3bp_3way_ip_aggressor_flop"
                matchup_id = "multiway_3bp_3way_ip_aggressor"
        else:
            family_id = "multiway_3bp_4plus_flop"
            matchup_id = "multiway_3bp_4plus"
    elif raise_count == 3:
        if flop_player_count == 2:
            family_id = "four_bet_ip_aggressor_flop" if aggressor_is_ip else "four_bet_oop_aggressor_flop"
            matchup_id = "four_bet_pot_ip_aggressor" if aggressor_is_ip else "four_bet_pot_oop_aggressor"
        elif flop_player_count == 3:
            if aggressor_flop_order == "first":
                family_id = "four_bet_3way_oop_aggressor_flop"
                matchup_id = "four_bet_3way_oop_aggressor"
            elif aggressor_flop_order == "middle":
                family_id = "four_bet_3way_middle_aggressor_flop"
                matchup_id = "four_bet_3way_middle_aggressor"
            else:
                family_id = "four_bet_3way_ip_aggressor_flop"
                matchup_id = "four_bet_3way_ip_aggressor"
        else:
            family_id = "four_bet_multiway_flop"
            matchup_id = "four_bet_pot_multiway"
    elif raise_count >= 4:
        if flop_player_count == 2:
            family_id = "five_bet_plus_ip_aggressor_flop" if aggressor_is_ip else "five_bet_plus_oop_aggressor_flop"
            matchup_id = "five_bet_plus_ip_aggressor" if aggressor_is_ip else "five_bet_plus_oop_aggressor"
        else:
            family_id = "four_bet_multiway_flop"
            matchup_id = "four_bet_pot_multiway"

    if not family_id or not matchup_id:
        return {"available": False, "reason": "No current complex preflop-path spec match.", "structure": scan}

    library = build_flop_tree_spec_library()
    exact_matchup = exact_complex_matchup_id(family_id, scan, library)
    if exact_matchup:
        matchup_id = exact_matchup
    family, matchup, board_bucket, enforced_board_action_policy = resolve_postflop_spec_components(hand, family_id, matchup_id)
    if not family or not matchup:
        return {"available": False, "reason": "Complex path family or matchup missing from spec registry.", "structure": scan}

    return {
        "available": True,
        "family_id": family_id,
        "matchup_id": matchup_id,
        "template_ref": family["template_ref"],
        "line_prefix": family["line_prefix"],
        "hero_role": "participant",
        "hero_group": "mixed",
        "pot_type": family["pot_type"],
        "preflop_path": matchup["preflop_path"],
        "positions": matchup["positions"],
        "priority_wave": matchup["priority_wave"],
        "board_bucket_biases": matchup["board_bucket_biases"],
        "range_profile_tags": matchup["range_profile_tags"],
        "grouped_path_shape": matchup_id,
        "board_bucket": board_bucket,
        "enforced_board_action_policy": enforced_board_action_policy,
        "structure": scan,
    }


def identify_postflop_spec_tags(hand: str, hero_name: str) -> dict:
    structure = extract_preflop_structure(hand, hero_name)
    if not structure.get("available"):
        complex_tag = identify_complex_postflop_path_tags(hand, hero_name)
        return complex_tag if complex_tag.get("available") else structure

    library = build_flop_tree_spec_library()
    family_id = None
    matchup_id = None
    opener_pos = structure["open_raiser_position"]
    caller_pos = structure["caller_position"]

    if structure["pot_type"] == "single_raised_pot":
        if opener_pos == "SB" and caller_pos == "BB":
            family_id = "bvb_flop_aggressive"
            matchup_id = "SB_open_vs_BB_defend"
        elif caller_pos == "BB" and opener_pos in {"UTG", "HJ", "CO", "BTN"}:
            family_id = "srp_ip_pfr_flop"
            matchup_id = f"{opener_pos}_open_vs_BB_defend"
        elif caller_pos == "SB" and opener_pos in {"UTG", "HJ", "CO", "BTN"}:
            family_id = "srp_oop_caller_flop"
            matchup_id = f"{opener_pos}_open_vs_SB_flat"
        elif opener_pos in {"UTG", "HJ", "CO"} and caller_pos in {"HJ", "CO", "BTN"}:
            family_id = "srp_oop_pfr_flop"
            matchup_id = f"{opener_pos}_open_vs_{caller_pos}_flat"
    elif structure["pot_type"] == "three_bet_pot":
        three_bettor_pos = structure.get("three_bettor_position")
        if three_bettor_pos == "CO" and opener_pos == "HJ":
            family_id = "three_bet_ip_3bettor_flop"
            matchup_id = "CO_3bets_vs_HJ_open"
        elif three_bettor_pos == "BTN" and opener_pos == "HJ":
            family_id = "three_bet_ip_3bettor_flop"
            matchup_id = "BTN_3bets_vs_HJ_open"
        elif three_bettor_pos == "BTN" and opener_pos == "CO":
            family_id = "three_bet_ip_3bettor_flop"
            matchup_id = "BTN_3bets_vs_CO_open"
        elif three_bettor_pos == "SB" and opener_pos == "BTN":
            family_id = "three_bet_oop_3bettor_flop"
            matchup_id = "SB_3bets_vs_BTN_open"
        elif three_bettor_pos == "BB" and opener_pos == "BTN":
            family_id = "three_bet_oop_3bettor_flop"
            matchup_id = "BB_3bets_vs_BTN_open"
        elif three_bettor_pos == "BB" and opener_pos == "SB":
            family_id = "three_bet_oop_3bettor_flop"
            matchup_id = "BB_3bets_vs_SB_open"

    if not family_id or not matchup_id:
        open_group = structure.get("open_raiser_group")
        caller_group = structure.get("caller_group")
        three_bettor_group = structure.get("three_bettor_group")

        if structure.get("grouped_path_shape") == "invalid_grouping":
            family_id = None
            matchup_id = None
        elif structure["pot_type"] == "single_raised_pot":
            if caller_group == "BB" and open_group in {"EP", "MP", "LP", "BTN"}:
                family_id = "srp_ip_pfr_flop"
                matchup_id = f"{open_group}_open_vs_BB_defend"
            elif caller_group == "SB" and open_group in {"EP", "MP", "LP", "BTN"}:
                family_id = "srp_oop_caller_flop"
                matchup_id = f"{open_group}_open_vs_SB_flat"
            elif (
                open_group in {"EP", "MP", "LP"}
                and caller_group in {"EP", "MP", "LP", "BTN"}
                and preflop_action_order_key(structure.get("caller_raw_position", "UNKNOWN"))
                > preflop_action_order_key(structure.get("open_raiser_raw_position", "UNKNOWN"))
            ):
                family_id = "srp_oop_pfr_flop"
                if open_group == "LP" and caller_group == "BTN":
                    matchup_id = "LP_open_vs_BTN_flat"
                elif caller_group == open_group:
                    matchup_id = f"{open_group}_open_vs_same_band_later_flat"
                else:
                    matchup_id = f"{open_group}_open_vs_later_band_flat"
        elif structure["pot_type"] == "three_bet_pot":
            if (
                three_bettor_group == open_group == "EP"
                and preflop_action_order_key(structure.get("three_bettor_raw_position", "UNKNOWN"))
                > preflop_action_order_key(structure.get("open_raiser_raw_position", "UNKNOWN"))
            ):
                family_id = "three_bet_ip_3bettor_flop"
                matchup_id = "EP_3bets_vs_same_band_open"
            elif three_bettor_group in {"MP", "LP", "BTN"} and open_group in {"EP", "MP"}:
                family_id = "three_bet_ip_3bettor_flop"
                matchup_id = f"{three_bettor_group}_3bets_vs_{open_group}_open"
            elif three_bettor_group in {"SB", "BB"} and open_group in {"EP", "MP", "LP", "BTN"}:
                family_id = "three_bet_oop_3bettor_flop"
                matchup_id = f"{three_bettor_group}_3bets_vs_{open_group}_open"

    if not family_id or not matchup_id:
        return {
            "available": False,
            "reason": "No current postflop spec match for this preflop path.",
            "structure": structure,
        }

    family, matchup, board_bucket, enforced_board_action_policy = resolve_postflop_spec_components(hand, family_id, matchup_id)
    if not family or not matchup:
        return {
            "available": False,
            "reason": "Resolved a path shape, but the spec registry is missing the family or matchup entry.",
            "structure": structure,
            "candidate_family": family_id,
            "candidate_matchup": matchup_id,
        }

    return {
        "available": True,
        "family_id": family_id,
        "matchup_id": matchup_id,
        "template_ref": family["template_ref"],
        "line_prefix": family["line_prefix"],
        "hero_role": structure["hero_role"],
        "hero_group": structure.get("hero_group"),
        "pot_type": structure["pot_type"],
        "preflop_path": matchup["preflop_path"],
        "positions": matchup["positions"],
        "priority_wave": matchup["priority_wave"],
        "board_bucket_biases": matchup["board_bucket_biases"],
        "range_profile_tags": matchup["range_profile_tags"],
        "grouped_path_shape": structure.get("grouped_path_shape"),
        "board_bucket": board_bucket,
        "enforced_board_action_policy": enforced_board_action_policy,
        "structure": structure,
    }


def build_postflop_spec_context(hand: str, hero_name: str) -> list[str]:
    tag = identify_postflop_spec_tags(hand, hero_name)
    if not tag.get("available"):
        reason = tag.get("reason", "unknown")
        structure = tag.get("structure") if isinstance(tag.get("structure"), dict) else {}
        grouped_path = structure.get("grouped_path_shape")
        if grouped_path:
            return [
                f"Postflop spec tag: unavailable ({reason})",
                f"Grouped path candidate: {grouped_path}",
            ]
        return [f"Postflop spec tag: unavailable ({reason})"]

    positions = tag["positions"]
    return [
        f"Postflop family: {tag['family_id']}",
        f"Postflop matchup: {tag['matchup_id']}",
        f"Postflop grouped path: {tag.get('grouped_path_shape', 'unknown')}",
        f"Postflop template: {tag['template_ref']}",
        f"Postflop line prefix: {tag['line_prefix']}",
        f"Flop board bucket: {tag.get('board_bucket', 'unknown')}",
        f"Hero structural role: {tag['hero_role']} | Hero group: {tag.get('hero_group', 'UNKNOWN')}",
        f"Preflop path: {' -> '.join(tag['preflop_path'])}",
        f"Positions: pfr={positions['pfr']}, caller={positions['caller']}, oop={positions['oop']}, ip={positions['ip']}",
        f"Spec wave: {tag['priority_wave']} | Range tags: {', '.join(tag['range_profile_tags'])}",
        f"Board biases: {', '.join(tag['board_bucket_biases'])}",
        f"Enforced lead pruning: {', '.join((tag.get('enforced_board_action_policy') or {}).get('removed_lead_branches', [])) or 'none'}",
        f"Enforced size pruning: {', '.join((tag.get('enforced_board_action_policy') or {}).get('removed_size_branches', [])) or 'none'}",
    ]


def extract_preflop_context(hand: str, hero_name: str) -> dict:
    preflop = extract_preflop_lines(hand)

    hero_idx = next((i for i, line in enumerate(preflop) if line.startswith(f"{hero_name}:")), None)
    hero_line = preflop[hero_idx] if hero_idx is not None else ""
    prior = preflop[:hero_idx] if hero_idx is not None else preflop
    prior_actions = [line for line in prior if ":" in line and not line.startswith(f"{hero_name}:")]

    hero_action = "unknown"
    lower_hero = hero_line.lower()
    if " folds" in lower_hero:
        hero_action = "fold"
    elif " calls" in lower_hero:
        hero_action = "call"
    elif " raises" in lower_hero and "all-in" in lower_hero:
        hero_action = "raise_all_in"
    elif " raises" in lower_hero:
        hero_action = "raise"
    elif " bets" in lower_hero:
        hero_action = "bet"

    facing_all_in = any("all-in" in line.lower() for line in prior_actions)
    prior_raises = sum("raises" in line.lower() for line in prior_actions)
    prior_calls = sum("calls" in line.lower() for line in prior_actions)
    unopened = prior_raises == 0 and prior_calls == 0 and not facing_all_in

    decision_type = "other"
    if facing_all_in and hero_action in {"call", "fold"}:
        decision_type = "call_or_fold_vs_shove"
    elif unopened and hero_action == "raise_all_in":
        decision_type = "open_shove"
    elif unopened and hero_action == "raise":
        decision_type = "open_raise"
    elif prior_raises >= 1 and hero_action == "raise_all_in":
        decision_type = "reshove"
    elif prior_raises >= 1 and hero_action == "fold":
        decision_type = "fold_to_raise"
    elif prior_raises >= 1 and hero_action == "call":
        decision_type = "flat_call_vs_raise"

    return {
        "hero_action": hero_action,
        "hero_line": hero_line,
        "hero_index": hero_idx,
        "prior_actions": prior_actions,
        "facing_all_in": facing_all_in,
        "prior_raises": prior_raises,
        "prior_calls": prior_calls,
        "unopened": unopened,
        "decision_type": decision_type,
    }


def extract_player_stacks(hand: str) -> dict:
    players = {}
    for line in hand.splitlines():
        match = re.match(r"Seat (\d+): (.+) \(([\d,]+) in chips\)", line)
        if match:
            seat = int(match.group(1))
            name = match.group(2)
            chips = int(match.group(3).replace(",", ""))
            players[name] = {"seat": seat, "chips": chips}
    return players


def format_bb(chips: Optional[int], bb: Optional[int]) -> str:
    if chips is None or not bb:
        return "unknown"
    return f"{round(chips / bb, 2)} BB"


def player_label(name: str, players: dict, position_map: dict) -> str:
    seat = players.get(name, {}).get("seat")
    return position_map.get(seat, name)


def simplify_action_line(action_line: str, players: dict, position_map: dict, bb: Optional[int]) -> Optional[str]:
    if not action_line or ":" not in action_line:
        return None
    actor = action_line.split(":", 1)[0]
    label = player_label(actor, players, position_map)
    lower = action_line.lower()
    if ": folds" in action_line:
        return None
    if ": calls " in action_line:
        amt = extract_amount_after_keyword(action_line, "calls")
        suffix = " and is all-in" if "all-in" in lower else ""
        return f"{label} calls {format_bb(amt, bb)}{suffix}"
    if ": raises " in action_line:
        to_amt = extract_to_amount(action_line)
        suffix = " and is all-in" if "all-in" in lower else ""
        return f"{label} raises to {format_bb(to_amt, bb)}{suffix}"
    if ": bets " in action_line:
        amt = extract_amount_after_keyword(action_line, "bets")
        suffix = " and is all-in" if "all-in" in lower else ""
        return f"{label} bets {format_bb(amt, bb)}{suffix}"
    if ": posts big blind " in action_line:
        amt = extract_amount_after_keyword(action_line, "posts big blind")
        return f"{label} posts big blind {format_bb(amt, bb)}"
    if ": posts small blind " in action_line:
        amt = extract_amount_after_keyword(action_line, "posts small blind")
        return f"{label} posts small blind {format_bb(amt, bb)}"
    return None


def parse_action_event(action_line: str, players: dict, position_map: dict, bb: Optional[int]) -> Optional[dict]:
    if not action_line or ":" not in action_line:
        return None
    actor = action_line.split(":", 1)[0]
    actor_label = player_label(actor, players, position_map)
    lower = action_line.lower()
    if ": folds" in action_line:
        return None
    if ": calls " in action_line:
        amt = extract_amount_after_keyword(action_line, "calls")
        return {
            "actor": actor_label,
            "type": "call",
            "bb": format_bb(amt, bb),
            "all_in": "all-in" in lower,
        }
    if ": raises " in action_line:
        to_amt = extract_to_amount(action_line)
        return {
            "actor": actor_label,
            "type": "raise",
            "bb": format_bb(to_amt, bb),
            "all_in": "all-in" in lower,
        }
    if ": bets " in action_line:
        amt = extract_amount_after_keyword(action_line, "bets")
        return {
            "actor": actor_label,
            "type": "bet",
            "bb": format_bb(amt, bb),
            "all_in": "all-in" in lower,
        }
    return None


def extract_to_amount(action_line: str) -> Optional[int]:
    match = re.search(r" to ([\d,]+)", action_line)
    if match:
        return int(match.group(1).replace(",", ""))
    return None


def extract_amount_after_keyword(action_line: str, keyword: str) -> Optional[int]:
    match = re.search(rf"{keyword} ([\d,]+)", action_line)
    if match:
        return int(match.group(1).replace(",", ""))
    return None


def extract_tournament_players_left(hand: str) -> Optional[int]:
    patterns = [
        r"(\d+) players remaining",
        r"(\d+) players left",
        r"(\d+) remaining",
    ]
    for pattern in patterns:
        match = re.search(pattern, hand, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def extract_level_number(hand: str) -> Optional[int]:
    match = re.search(r"Level\s*(\d+)", hand, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def extract_blind_ante_structure(hand: str) -> dict:
    match = re.search(r"Level\s*\d+\s*\(([\d,]+)/([\d,]+)\(([\d,]+)\)\)", hand, re.IGNORECASE)
    if match:
        sb = int(match.group(1).replace(",", ""))
        bb = int(match.group(2).replace(",", ""))
        ante = int(match.group(3).replace(",", ""))
        return {"sb": sb, "bb": bb, "ante": ante}

    bb = extract_bb_value(hand)
    return {"sb": None, "bb": bb, "ante": None}


def extract_buyin_amount(hand: str) -> Optional[int]:
    first_line = hand.splitlines()[0] if hand.splitlines() else ""
    match = re.search(r"[¥$€₹](\d+(?:,\d{3})*(?:\.\d+)?)", first_line)
    if match:
        return int(float(match.group(1).replace(",", "")))
    return None


def estimate_table_stack_texture(hand: str, bb: Optional[int]) -> dict:
    players = extract_player_stacks(hand)
    if not players or not bb:
        return {"short_count": 0, "median_bb": None}

    stack_bbs = sorted(player["chips"] / bb for player in players.values())
    mid = len(stack_bbs) // 2
    median_bb = stack_bbs[mid] if len(stack_bbs) % 2 == 1 else (stack_bbs[mid - 1] + stack_bbs[mid]) / 2
    short_count = sum(stack_bb <= 15 for stack_bb in stack_bbs)
    return {"short_count": short_count, "median_bb": round(median_bb, 2)}


def pressure_score(pressure_band: str) -> int:
    return {
        "low": 0,
        "low-medium": 1,
        "medium": 2,
        "medium-high": 3,
        "high": 4,
    }.get(pressure_band, 0)


def lower_pressure_band(pressure_band: str) -> str:
    pressure_bands = ["low", "low-medium", "medium", "medium-high", "high"]
    if pressure_band not in pressure_bands:
        return pressure_band
    return pressure_bands[max(0, pressure_bands.index(pressure_band) - 1)]


def extract_tournament_header_text(hand: str) -> str:
    lines = [line.strip() for line in hand.splitlines()[:6] if line.strip()]
    return " | ".join(lines)


def is_bounty_tournament(hand: str) -> bool:
    header_text = extract_tournament_header_text(hand)
    return bool(
        re.search(
            r"\b(bounty|hunters?|pko|progressive knockout|knockout|ko)\b",
            header_text,
            re.IGNORECASE,
        )
    )


def infer_tournament_archetype(hand: str, table_players: int, tournament_summary: Optional[dict] = None) -> dict:
    level = extract_level_number(hand)
    structure = extract_blind_ante_structure(hand)
    buyin = extract_buyin_amount(hand)
    bb = structure.get("bb")
    ante = structure.get("ante")
    ante_ratio = round(ante / bb, 2) if ante and bb else None
    summary_hint = build_summary_stage_hint(tournament_summary)
    field_size_band = summary_hint.get("field_size_band", "unknown")

    stage_band = "unknown"
    if level is not None:
        if field_size_band == "massive":
            if level <= 10:
                stage_band = "early"
            elif level <= 24:
                stage_band = "middle"
            elif level <= 36:
                stage_band = "late"
            else:
                stage_band = "very_late"
        elif field_size_band == "large":
            if level <= 9:
                stage_band = "early"
            elif level <= 21:
                stage_band = "middle"
            elif level <= 32:
                stage_band = "late"
            else:
                stage_band = "very_late"
        elif level <= 8:
            stage_band = "early"
        elif level <= 18:
            stage_band = "middle"
        elif level <= 27:
            stage_band = "late"
        else:
            stage_band = "very_late"

    buyin_band = "unknown"
    if buyin is not None:
        if buyin <= 25:
            buyin_band = "micro_low"
        elif buyin <= 150:
            buyin_band = "low_mid"
        else:
            buyin_band = "mid_plus"

    likely_field = "standard"
    if table_players == 8 and buyin_band in {"micro_low", "low_mid"}:
        likely_field = "broad_field_nightly"

    return {
        "level": level,
        "buyin": buyin,
        "buyin_band": buyin_band,
        "ante_ratio": ante_ratio,
        "stage_band": stage_band,
        "likely_field": likely_field,
        "is_bounty": is_bounty_tournament(hand),
        "summary_hint": summary_hint,
        "field_size_band": field_size_band,
    }


def build_stage_icm_profile(hand: str, info: dict, table_players: int, tournament_summary: Optional[dict] = None) -> dict:
    hero_bb = info.get("hero_bb")
    bb = info.get("bb")
    archetype = infer_tournament_archetype(hand, table_players, tournament_summary)
    stack_texture = estimate_table_stack_texture(hand, bb)
    level = archetype.get("level")
    stage_band = archetype.get("stage_band")
    ante_ratio = archetype.get("ante_ratio")
    buyin = archetype.get("buyin")
    is_bounty = archetype.get("is_bounty", False)
    summary_hint = archetype.get("summary_hint", {})

    if level is None or stage_band == "unknown":
        return {"available": False}

    stage_label_map = {
        "early": "early-field",
        "middle": "middle stages",
        "late": "late-field",
        "very_late": "very late",
    }
    stage_label = stage_label_map.get(stage_band, "late-field")
    uncertainty = "wide"
    pressure = "low"
    note = "chip EV still dominates"
    texture_pressure_push = False
    bounty_adjusted = False

    if stage_band == "middle":
        pressure = "low-medium"
        note = "some survival value exists, but this is usually not a hard ICM node"
        uncertainty = "wide"
    elif stage_band == "late":
        pressure = "medium"
        note = "survival starts to matter, so marginal call-offs should tighten somewhat"
        uncertainty = "medium"
    elif stage_band == "very_late":
        pressure = "medium-high"
        note = "this looks closer to final-table territory than generic chip-EV play"
        uncertainty = "medium"

    if ante_ratio is not None and ante_ratio >= 0.12 and stage_band in {"late", "very_late"}:
        note = "big-blind-ante pressure is on, so short-stack decisions carry more survival weight"

    if isinstance(hero_bb, (int, float)) and hero_bb <= 12 and pressure in {"medium", "medium-high"}:
        pressure = "high" if pressure == "medium-high" else "medium-high"
        note = "short-stack survival matters more than pure chip EV in close preflop spots"
        texture_pressure_push = True

    if table_players <= 6 and pressure in {"medium", "medium-high", "high"}:
        pressure = "high"
        note = "short-handed late play often means stronger survival pressure than the raw level alone suggests"
        uncertainty = "medium"
        texture_pressure_push = True

    if stack_texture.get("short_count", 0) >= max(2, table_players // 3) and pressure in {"medium", "medium-high"}:
        pressure = "high"
        note = "several short stacks are in play, which usually increases practical ICM pressure"
        texture_pressure_push = True

    if summary_hint.get("available"):
        field_size_band = summary_hint.get("field_size_band")
        if field_size_band == "massive" and stage_band in {"middle", "late"} and pressure_score(pressure) >= 2:
            pressure = lower_pressure_band(pressure)
            note = "massive-field context usually means this is still far from the sharpest payout pressure, so stay closer to chip EV unless other signals are strong"
            uncertainty = "wide"
        elif field_size_band == "large" and stage_band == "late" and pressure_score(pressure) >= 3:
            pressure = lower_pressure_band(pressure)
            note = "large-field context slightly softens survival pressure here because late levels do not always mean near-final-table conditions"

        min_players_remaining = summary_hint.get("min_players_remaining")
        if isinstance(min_players_remaining, int) and min_players_remaining > 500 and pressure_score(pressure) >= 2:
            pressure = lower_pressure_band(pressure)
            note = "the linked summary shows Hero later busted with a very large player pool still alive, so this hand is better treated as broad-field survival pressure rather than a sharp ICM node"
            uncertainty = "wide"

    if is_bounty and texture_pressure_push and pressure_score(pressure) >= 2:
        pressure = lower_pressure_band(pressure)
        note = "bounty format trims pure survival pressure a bit here, so close preflop spots stay closer to chip EV"
        uncertainty = "wide"
        bounty_adjusted = True

    if stage_band == "early" and not (isinstance(hero_bb, (int, float)) and hero_bb <= 10):
        if not summary_hint.get("available"):
            return {"available": False}
        pressure = "low"
        note = "the linked summary points to a broad-field spot, so this is mainly chip-EV poker rather than meaningful payout pressure"
        uncertainty = "wide"

    return {
        "available": True,
        "stage_band": stage_band,
        "stage_label": stage_label,
        "pressure_band": pressure,
        "pressure_score": pressure_score(pressure),
        "uncertainty": uncertainty,
        "note": note,
        "level": level,
        "ante_ratio": ante_ratio,
        "buyin": buyin,
        "is_bounty": is_bounty,
        "bounty_adjusted": bounty_adjusted,
        "summary_hint": summary_hint,
    }


def estimate_stage_icm_note(hand: str, info: dict, table_players: int, tournament_summary: Optional[dict] = None) -> str:
    profile = build_stage_icm_profile(hand, info, table_players, tournament_summary)
    if not profile.get("available"):
        return ""

    buyin = profile.get("buyin")
    buyin_tag = f"GG ¥{buyin}" if buyin is not None else "GG"
    summary_hint = profile.get("summary_hint", {})
    icm_cluster = summary_hint.get("icm_cluster")
    paid = summary_hint.get("estimated_paid_seats")
    itm = summary_hint.get("itm_pct")
    icm_str = ""
    if paid and itm:
        icm_str = f" [{paid} paid ({itm}% ITM)]"
    if icm_cluster and icm_cluster != "regular":
        icm_str += f" [{icm_cluster}]"
    note = (
        f"Approx stage/ICM: {profile['stage_label']}, {profile['pressure_band']} pressure "
        f"({buyin_tag} 8-max archetype, Level {profile['level']}, ante {profile['ante_ratio'] if profile['ante_ratio'] is not None else '?'} BB, "
        f"{profile['uncertainty']}-band estimate){icm_str}; {profile['note']}."
    )
    if summary_hint.get("available"):
        note += f" Linked summary: {summary_hint['note']}."
    return note


def build_stage_icm_nudge(stage_profile: dict, decision_type: str, stack_bucket: str, hand_class: str) -> dict:
    if not stage_profile.get("available"):
        return {"applies": False, "tighten_calls": False, "tighten_jams": False, "summary": ""}

    if stage_profile.get("stage_band") not in {"late", "very_late"}:
        return {"applies": False, "tighten_calls": False, "tighten_jams": False, "summary": ""}

    if stage_profile.get("pressure_score", 0) < 2:
        return {"applies": False, "tighten_calls": False, "tighten_jams": False, "summary": ""}

    thin_call_classes = {"small_pair", "suited_ace", "wheel_ace", "middling_broadway", "dominated_broadway"}
    thin_jam_classes = {
        "small_pair",
        "suited_ace",
        "wheel_ace",
        "middling_broadway",
        "dominated_broadway",
        "low_suited_connector",
        "low_suited_gapper",
    }

    tighten_calls = (
        decision_type == "call_or_fold_vs_shove"
        and stack_bucket in {"short", "shallow"}
        and hand_class in thin_call_classes
    )
    tighten_jams = (
        decision_type in {"open_shove", "reshove", "fold_to_raise"}
        and stack_bucket in {"short", "shallow"}
        and hand_class in thin_jam_classes
    )

    if not tighten_calls and not tighten_jams:
        return {"applies": False, "tighten_calls": False, "tighten_jams": False, "summary": ""}

    nudges = []
    if tighten_calls:
        nudges.append("thin call-offs should tighten a bit")
    if tighten_jams:
        nudges.append("marginal jams and reshoves should tighten a bit")

    return {
        "applies": True,
        "tighten_calls": tighten_calls,
        "tighten_jams": tighten_jams,
        "summary": (
            f"{stage_profile['stage_label']} / {stage_profile['pressure_band']} pressure band: "
            + " and ".join(nudges)
            + ", but never at the expense of obvious push-fold fundamentals."
        ),
    }


def build_decision_context(hand: str, info: dict, hero_name: str, tournament_summary: Optional[dict] = None) -> list[str]:
    bb = info.get("bb")
    hero_chips = info.get("hero_chips")
    hero_pos = info.get("position", "UNKNOWN")
    hero_bb = info.get("hero_bb", "unknown")
    context = extract_preflop_context(hand, hero_name)
    players = extract_player_stacks(hand)
    btn, hero_seat, seats = extract_positions(hand, hero_name)
    position_map = assign_positions(btn, seats) if btn is not None and hero_seat is not None else {}

    street_contrib = {name: 0 for name in players}
    pot = 0
    current_bet = 0
    last_aggressor = None
    last_aggressive_line = None

    preflop_lines = extract_preflop_lines(hand)
    hero_index = context.get("hero_index")
    upto_hero = preflop_lines[:hero_index] if hero_index is not None else preflop_lines

    for line in hand.splitlines():
        if line.startswith("*** HOLE CARDS ***"):
            break
        if ": posts the ante " in line:
            _, amount = line.split(": posts the ante ", 1)
            pot += int(amount.replace(",", ""))
        elif ": posts small blind " in line:
            name, amount = line.split(": posts small blind ", 1)
            amt = int(amount.replace(",", ""))
            pot += amt
            street_contrib[name] = street_contrib.get(name, 0) + amt
            current_bet = max(current_bet, street_contrib[name])
            last_aggressor = name
            last_aggressive_line = line
        elif ": posts big blind " in line:
            name, amount = line.split(": posts big blind ", 1)
            amt = int(amount.replace(",", ""))
            pot += amt
            street_contrib[name] = street_contrib.get(name, 0) + amt
            current_bet = max(current_bet, street_contrib[name])
            last_aggressor = name
            last_aggressive_line = line

    prior_events = []
    for line in upto_hero:
        if not ":" in line or line.startswith("Dealt to ") or line.startswith("***"):
            continue
        actor = line.split(":", 1)[0]
        event = parse_action_event(line, players, position_map, bb)
        if event:
            prior_events.append(event)
        if ": folds" in line:
            continue
        if ": calls " in line:
            amt = extract_amount_after_keyword(line, "calls")
            if amt is not None:
                pot += amt
                street_contrib[actor] = street_contrib.get(actor, 0) + amt
        elif ": raises " in line:
            to_amt = extract_to_amount(line)
            if to_amt is not None:
                add_amt = to_amt - street_contrib.get(actor, 0)
                pot += max(add_amt, 0)
                street_contrib[actor] = to_amt
                current_bet = max(current_bet, to_amt)
                last_aggressor = actor
                last_aggressive_line = line
        elif ": bets " in line:
            amt = extract_amount_after_keyword(line, "bets")
            if amt is not None:
                add_amt = amt - street_contrib.get(actor, 0)
                pot += max(add_amt, 0)
                street_contrib[actor] = amt
                current_bet = max(current_bet, amt)
                last_aggressor = actor
                last_aggressive_line = line

    aggressor_stack = players.get(last_aggressor, {}).get("chips") if last_aggressor else None
    effective_chips = min(hero_chips, aggressor_stack) if hero_chips is not None and aggressor_stack is not None else None

    summary = f"Hero in {hero_pos} with {hero_bb} BB"
    if not prior_events:
        summary += " in an unopened pot."
    else:
        action_bits = []
        raise_seen = False
        for event in prior_events:
            if event["type"] == "raise":
                if not raise_seen:
                    if event["all_in"]:
                        action_bits.append(f"a shove to {event['bb']} from {event['actor']}")
                    else:
                        action_bits.append(f"a {event['bb']} open raise from {event['actor']}")
                    raise_seen = True
                else:
                    if event["all_in"]:
                        action_bits.append(f"a reshove to {event['bb']} from {event['actor']}")
                    else:
                        action_bits.append(f"a 3-bet to {event['bb']} from {event['actor']}")
            elif event["type"] == "call":
                if raise_seen:
                    action_bits.append(f"cold call by {event['actor']}")
                else:
                    action_bits.append(f"limp by {event['actor']}")
            elif event["type"] == "bet":
                action_bits.append(f"a bet of {event['bb']} from {event['actor']}")
        if action_bits:
            summary += " facing " + " and ".join(action_bits) + "."
        else:
            summary += " in an unopened pot."

    if effective_chips is not None and prior_events:
        summary += f" Effective stack {format_bb(effective_chips, bb)}."

    lines = [summary]
    stage_note = estimate_stage_icm_note(hand, info, len(players), tournament_summary)
    if stage_note:
        lines.append(stage_note)
    return lines


def is_weak_blind_defense_hand(cards: str) -> bool:
    hand = describe_hole_cards(cards)
    if not hand or hand.get("pair") or "A" in hand.get("ranks", ()):
        return False
    high = hand["high"]
    low = hand["low"]
    if high in {"K", "Q", "J"} and rank_value(low) <= rank_value("6"):
        return True
    if hand["suited"] and hand["gap"] <= 2 and rank_value(high) <= rank_value("8"):
        return True
    return False


def is_weak_multiway_sb_hand(cards: str) -> bool:
    hand = describe_hole_cards(cards)
    if not hand or hand.get("pair") or "A" in hand.get("ranks", ()):
        return False
    return hand["suited"] and rank_value(hand["high"]) <= rank_value("8")


def classify_stack_bucket(hero_bb) -> str:
    if not isinstance(hero_bb, (int, float)):
        return "unknown"
    if hero_bb <= 1:
        return "ultra_short"
    if hero_bb <= 6:
        return "shove_critical"
    if hero_bb <= 10:
        return "short"
    if hero_bb <= 15:
        return "shallow"
    return "deeper"


def classify_position_group(position: str) -> str:
    if position in {"SB", "BB", "SB/BTN"}:
        return "blind"
    if position in {"UTG", "UTG+1", "UTG+2"}:
        return "early"
    if position in {"CO", "BTN"}:
        return "late"
    return "middle"


def classify_hand_class(cards: str) -> str:
    hand = describe_hole_cards(cards)
    if not hand:
        return "unknown"
    high = hand["high"]
    low = hand["low"]
    if hand["pair"]:
        if rank_value(high) >= rank_value("T"):
            return "premium_pair"
        if rank_value(high) >= rank_value("7"):
            return "medium_pair"
        return "small_pair"
    if "A" in hand["ranks"]:
        kicker = low if high == "A" else high
        if rank_value(kicker) >= rank_value("T"):
            return "strong_ace"
        if hand["suited"] and rank_value(kicker) <= rank_value("5"):
            return "wheel_ace"
        if hand["suited"]:
            return "suited_ace"
        return "weak_ace"
    if high in {"K", "Q", "J", "T"} and rank_value(low) >= rank_value("T"):
        return "strong_broadway"
    if high in {"K", "Q", "J"} and rank_value(low) >= rank_value("7"):
        return "middling_broadway"
    if high in {"K", "Q", "J"}:
        return "dominated_broadway"
    if hand["suited"] and hand["gap"] == 1 and rank_value(high) <= rank_value("9"):
        return "low_suited_connector"
    if hand["suited"] and hand["gap"] <= 2 and rank_value(high) <= rank_value("9"):
        return "low_suited_gapper"
    return "trash"


def ace_kicker_rank(cards: str) -> Optional[str]:
    hand = describe_hole_cards(cards)
    if not hand or hand.get("pair") or "A" not in hand.get("ranks", ()):
        return None
    return hand["low"] if hand["high"] == "A" else hand["high"]


def pair_rank(cards: str) -> Optional[str]:
    hand = describe_hole_cards(cards)
    if not hand or not hand.get("pair"):
        return None
    return hand["high"]


def is_clear_continue_vs_shove(cards: str, stack_bucket: str, nudge: dict) -> bool:
    hand_class = classify_hand_class(cards)

    if hand_class == "premium_pair":
        return True

    if hand_class == "medium_pair":
        rank = pair_rank(cards)
        if rank is None:
            return False
        if rank_value(rank) >= rank_value("9"):
            return True
        return not nudge.get("tighten_calls") and stack_bucket in {"shove_critical", "short"} and rank_value(rank) >= rank_value("7")

    if hand_class == "strong_ace":
        kicker = ace_kicker_rank(cards)
        if kicker is None:
            return False
        if rank_value(kicker) >= rank_value("Q"):
            return True
        return not nudge.get("tighten_calls") and stack_bucket in {"shove_critical", "short"} and rank_value(kicker) >= rank_value("J")

    return False


def is_marginal_jam_hand_class(hand_class: str) -> bool:
    return hand_class in {
        "small_pair",
        "suited_ace",
        "wheel_ace",
        "middling_broadway",
        "dominated_broadway",
        "low_suited_connector",
        "low_suited_gapper",
    }


def is_reasonable_open_shove(position_group: str, stack_bucket: str, hand_class: str) -> bool:
    any_short_stack = {"premium_pair", "medium_pair", "small_pair", "strong_ace", "suited_ace", "wheel_ace", "strong_broadway", "middling_broadway"}
    blind_short = any_short_stack | {"dominated_broadway", "low_suited_connector", "low_suited_gapper"}
    if stack_bucket in {"ultra_short", "shove_critical"}:
        return hand_class != "trash"
    if stack_bucket == "short":
        if position_group == "blind":
            return hand_class in blind_short
        if position_group == "late":
            return hand_class in any_short_stack | {"low_suited_connector"}
        return hand_class in any_short_stack
    if stack_bucket == "shallow" and position_group == "blind":
        return hand_class in any_short_stack
    return False


def is_reasonable_open_raise(position_group: str, stack_bucket: str, hand_class: str) -> bool:
    min_raise_hands = {"premium_pair", "medium_pair", "strong_ace", "strong_broadway", "suited_ace", "wheel_ace", "middling_broadway", "small_pair"}
    if stack_bucket == "deeper":
        return hand_class in min_raise_hands
    if stack_bucket == "shallow":
        return hand_class in min_raise_hands | {"low_suited_connector"}
    return True


def rule_based_analysis(
    hand: str,
    info: dict,
    hero_name: str,
    tournament_summary: Optional[dict] = None,
    input_path: Optional[Path] = None,
    raw_text: Optional[str] = None,
):
    context = extract_preflop_context(hand, hero_name)
    players = extract_player_stacks(hand)
    hero_bb = info.get("hero_bb")
    position = info.get("position")
    cards = info.get("hero_cards", "Unknown")
    stack_bucket = classify_stack_bucket(hero_bb)
    position_group = classify_position_group(position)
    hand_class = classify_hand_class(cards)
    stage_profile = build_stage_icm_profile(hand, info, len(players), tournament_summary)
    stage_nudge = build_stage_icm_nudge(stage_profile, context["decision_type"], stack_bucket, hand_class)
    context["stack_bucket"] = stack_bucket
    context["position_group"] = position_group
    context["hand_class"] = hand_class
    context["stage_icm_profile"] = stage_profile
    context["stage_icm_nudge"] = stage_nudge
    context["pko_bounty_profile"] = build_pko_bounty_profile(input_path, raw_text, hand, info, hero_name, context)

    if isinstance(hero_bb, (int, float)) and hero_bb <= 1 and context["hero_action"] == "fold":
        context["matched_rule"] = "under_1bb_no_fold"
        return (
            "Mistake: Folding\n"
            "Better play: Get the chips in or call off\n"
            "Reason: With 1 BB or less, preserving fold equity is no longer realistic and folding away that much equity is a mistake.\n"
            "Confidence: high",
            context,
        )

    if isinstance(hero_bb, (int, float)) and hero_bb <= 1 and context["hero_action"] in {"call", "raise_all_in"}:
        context["matched_rule"] = "under_1bb_correct_commit"
        return (
            "Mistake: No clear mistake.\n"
            "Better play: No better play.\n"
            "Reason: With 1 BB or less, getting the chips in with any remotely playable holding is standard because the stack is already in push-or-die mode.\n"
            "Confidence: high",
            context,
        )

    if (
        context["hero_action"] == "raise"
        and context["unopened"]
        and stack_bucket in {"ultra_short", "shove_critical"}
        and is_reasonable_open_shove(position_group, stack_bucket, hand_class)
    ):
        context["matched_rule"] = "raise_too_small_short_stack"
        return (
            "Mistake: Raising too small.\n"
            "Better play: Open shove all-in.\n"
            "Reason: At this stack depth, a small raise leaves awkward stack-to-pot ratios and gives away fold equity that a direct shove captures.\n"
            "Confidence: high",
            context,
        )

    if (
        context["hero_action"] == "raise_all_in"
        and context["unopened"]
        and is_reasonable_open_shove(position_group, stack_bucket, hand_class)
        and not (stage_nudge.get("tighten_jams") and is_marginal_jam_hand_class(hand_class))
    ):
        context["matched_rule"] = "reasonable_open_shove"
        return (
            "Mistake: No clear mistake.\n"
            "Better play: No better play than open-shove.\n"
            f"Reason: With a {stack_bucket.replace('_', ' ')} stack in {position}, this hand class ({hand_class.replace('_', ' ')}) is a reasonable open-shove candidate.\n"
            "Confidence: high",
            context,
        )

    if (
        context["decision_type"] == "open_raise"
        and is_reasonable_open_raise(position_group, stack_bucket, hand_class)
    ):
        context["matched_rule"] = "reasonable_open_raise"
        return (
            "Mistake: No clear mistake.\n"
            "Better play: No better play than min-raise.\n"
            f"Reason: With a {stack_bucket.replace('_', ' ')} stack in {position}, this hand class ({hand_class.replace('_', ' ')}) is a reasonable min-raise candidate.\n"
            "Confidence: high",
            context,
        )

    if (
        context["decision_type"] == "call_or_fold_vs_shove"
        and stack_bucket in {"shove_critical", "short", "shallow"}
        and context["hero_action"] == "call"
        and is_clear_continue_vs_shove(cards, stack_bucket, stage_nudge)
    ):
        context["matched_rule"] = "strong_hand_call_vs_shove"
        return (
            "Mistake: No clear mistake.\n"
            "Better play: No better play.\n"
            "Reason: In a call-versus-shove spot, strong aces and solid pairs are clear continue candidates at these stack depths.\n"
            "Confidence: high",
            context,
        )

    if (
        position_group == "blind"
        and context["decision_type"] == "call_or_fold_vs_shove"
        and isinstance(hero_bb, (int, float))
        and hero_bb <= 15
        and is_weak_blind_defense_hand(cards)
    ):
        if context["hero_action"] == "fold":
            context["matched_rule"] = "conservative_blind_fold_vs_shove"
            return (
                "Mistake: No clear mistake.\n"
                "Better play: No clear mistake.\n"
                "Reason: This is a blind-versus-shove spot with a weak dominated or marginal hand, so a conservative fold is completely reasonable with no reads.\n"
                "Confidence: high",
                context,
            )
        if context["hero_action"] == "call":
            context["matched_rule"] = "overdefend_blind_call_vs_shove"
            return (
                "Mistake: Calling too loose.\n"
                "Better play: Fold.\n"
                "Reason: In blind defense versus a shove, weak dominated hands and low suited connectors are usually over-defends without stronger range evidence.\n"
                "Confidence: medium",
                context,
            )

    if (
        position == "SB"
        and context["hero_action"] == "fold"
        and context["prior_raises"] >= 1
        and context["prior_calls"] >= 1
        and isinstance(hero_bb, (int, float))
        and hero_bb <= 12
        and is_weak_multiway_sb_hand(cards)
    ):
        context["matched_rule"] = "disciplined_multiway_sb_fold"
        return (
            "Mistake: No clear mistake.\n"
            "Better play: No clear mistake.\n"
            "Reason: Folding weak suited hands from the small blind in a short-stack multi-way pot is often the disciplined choice, not a missed shove.\n"
            "Confidence: high",
            context,
        )

    if (
        position == "SB"
        and context["hero_action"] == "fold"
        and context["prior_raises"] >= 1
        and context["prior_calls"] == 0
        and stack_bucket in {"shove_critical", "short"}
        and hand_class in {"strong_ace", "suited_ace", "wheel_ace", "medium_pair", "small_pair", "strong_broadway"}
        and not (stage_nudge.get("tighten_jams") and hand_class in {"suited_ace", "wheel_ace", "small_pair", "strong_broadway"})
    ):
        context["matched_rule"] = "sb_reshove_candidate"
        return (
            "Mistake: Folding too much.\n"
            "Better play: Consider a reshove.\n"
            "Reason: In the small blind with a short stack, hands in this class often perform better as aggressive jam candidates than as folds against a single raise.\n"
            "Confidence: medium",
            context,
        )

    return None, context


def analyze_hand(
    hand: str,
    info: dict,
    hero_name: str,
    client: OpenAI,
    tournament_summary: Optional[dict] = None,
    input_path: Optional[Path] = None,
    raw_text: Optional[str] = None,
):
    rule_result, context = rule_based_analysis(hand, info, hero_name, tournament_summary, input_path, raw_text)
    if rule_result:
        fields = parse_analysis_fields(rule_result)
        return format_analysis_output(
            fields=fields,
            verdict_source="rule",
            confidence_source="rule",
            rule_verdict=summarize_rule_verdict(context),
            ai_explanation="Not used. A deterministic rule handled this spot.",
        )

    rule_notes = [
        f"Decision type: {context['decision_type']}",
        f"Stack bucket: {context.get('stack_bucket', 'unknown')}",
        f"Position group: {context.get('position_group', 'unknown')}",
        f"Hand class: {context.get('hand_class', 'unknown')}",
    ]
    stage_profile = context.get("stage_icm_profile", {})
    if stage_profile.get("available"):
        rule_notes.append(
            f"Approx stage/ICM band: {stage_profile['stage_label']} with {stage_profile['pressure_band']} pressure. This is a bounded archetype estimate, not exact players-left data."
        )
    stage_nudge = context.get("stage_icm_nudge", {})
    if stage_nudge.get("applies"):
        rule_notes.append(f"ICM nudge: {stage_nudge['summary']}")
        rule_notes.append("If this note only nudges a close verdict rather than deciding it, say 'Close spot:' at the start of the Reason line.")
    pko_profile = context.get("pko_bounty_profile", {})
    if pko_profile.get("available"):
        rule_notes.append(pko_profile["note"])
        rule_notes.append(f"PKO pull strength: {pko_profile['pull']}")
        rule_notes.append("Use the PKO note only as a bounded tiebreaker in close call-vs-shove spots.")
    if context.get("hero_line"):
        rule_notes.append(f"Hero action line: {context['hero_line']}")
    if context.get("facing_all_in"):
        rule_notes.append("Hero is facing an all-in, so this should be evaluated as a call-or-fold spot unless the action history clearly says otherwise.")
    if context.get("prior_calls", 0) >= 1 and info.get("position") == "SB":
        rule_notes.append("There is already at least one caller, so multi-way equity realization matters more than raw push-fold aggression.")

    rule_notes_block = "\n".join(f"- {note}" for note in rule_notes)
    prompt = f"""
Elite MTT Coach Analysis.
Hero Name: {hero_name} | Position: {info['position']} | Stack: {info['hero_bb']} BB | Cards: {info['hero_cards']}

Rule Layer Notes:
{rule_notes_block}

Hand History:
{hand}

Focus on Hero's first meaningful preflop decision.
Be explicit about the actual decision type: open shove, reshove, call, or fold.
If Hero already took the strongest practical line, say so.
If the spot is range-dependent or unclear from the hand history, lower confidence instead of pretending certainty.

Return exactly these 4 lines, nothing else:
Mistake: ...
Better play: ...
Reason: ...
Confidence: low|medium|high
"""
    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": """You are an elite GTO MTT coach focused on tournament preflop decision quality.
Rules:
1. Be concise and practical.
2. Do not recommend impossible actions or contradict the hand history.
3. If Hero already made the best short-stack action, say 'No clear mistake'.
4. Under 1 BB, folding is the mistake unless Hero is already all-in.
5. From 1-12 BB, use push/fold logic heavily.
6. Distinguish open-shove spots from call-vs-fold spots. Never recommend 'push all-in' if Hero is clearly facing an all-in and the real choice is call or fold.
7. When Hero is facing a shove with no reads, default to sensible conservative MTT calling ranges rather than optimistic chip-EV hero calls.
8. Be especially careful with weak dominated Qx/Kx and marginal suited connectors from the blinds facing all-ins. If a call is close, prefer lower confidence or folding.
9. Do not auto-call weak hands from the blinds just because Hero is short. Consider opponent position, action, likely range, and tournament survival.
10. Respect the rule-layer notes from the parser. They are deterministic guardrails, not optional flavor.
11. Mention ICM only when it truly matters.
12. If the hand history does not provide enough context for a confident verdict, say so in the Reason and lower the confidence.
13. Use any stage/ICM band only as a light tiebreaker in close preflop spots. Tighten thin call-offs a bit in later higher-pressure bands, but do not override obvious push-fold fundamentals or clear strong continues.
14. When the stage/ICM band is only nudging a close verdict rather than deciding it, start the Reason line with 'Close spot:'.
15. Return exactly 4 labeled lines: Mistake, Better play, Reason, Confidence.""",
                },
                {"role": "user", "content": prompt},
            ],
        )
        fields = parse_analysis_fields(response.choices[0].message.content)
        stage_nudge = context.get("stage_icm_nudge", {})
        if stage_nudge.get("applies") and not fields["Reason"].lower().startswith("close spot:"):
            fields["Reason"] = f"Close spot: {fields['Reason']}"
        return format_analysis_output(
            fields=fields,
            verdict_source="hybrid",
            confidence_source="model",
            rule_verdict=summarize_rule_verdict(context),
            ai_explanation=fields["Reason"],
        )
    except Exception as exc:
        return f"Error: {exc}"


def find_default_input_file() -> Optional[Path]:
    if DEFAULT_INPUT_FILE.exists():
        return DEFAULT_INPUT_FILE
    candidates = [p for p in RAW_ROOT.rglob("*") if p.is_file() and p.suffix.lower() in {".txt", ".log"}]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def default_output_for(input_path: Path) -> Path:
    PARSED_ROOT.mkdir(parents=True, exist_ok=True)
    return PARSED_ROOT / f"{input_path.stem}_analysis.txt"


def build_report(input_path: Path, hands, important_hands, analyses, hero_name: str, tournament_summary: Optional[dict] = None):
    def analysis_value(analysis: str, label: str) -> str:
        prefix = f"{label}:"
        for line in analysis.splitlines():
            if line.startswith(prefix):
                return line.split(":", 1)[1].strip()
        return "unknown"

    def title_case_label(text: str) -> str:
        return text[:1].upper() + text[1:] if text else text

    def compact_spot_header(hand: str, info: dict) -> str:
        parts = [f"Hero {info['hero_bb']} BB"]
        profile = build_stage_icm_profile(hand, info, len(extract_player_stacks(hand)), tournament_summary)
        if profile.get("available"):
            parts.append(title_case_label(profile["stage_label"]))
            parts.append(f"{title_case_label(profile['pressure_band'])} pressure")
            summary_hint = profile.get("summary_hint", {})
            if summary_hint.get("available"):
                parts.append(f"Field {format_int(summary_hint.get('total_players'))}")
        return " | ".join(parts)

    verdict_counts = {}
    confidence_counts = {}
    postflop_tagged_count = 0
    for (hand, _), analysis in zip(important_hands, analyses):
        verdict = analysis_value(analysis, "Verdict source")
        confidence = analysis_value(analysis, "Confidence source")
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1
        if identify_postflop_spec_tags(hand, hero_name).get("available"):
            postflop_tagged_count += 1

    lines = []
    lines.append("Poker Hand Parser Report")
    lines.append("=" * 80)
    lines.append(f"Run time: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append("Summary")
    lines.append("-" * 80)
    lines.append(f"Input file: {input_path}")
    if tournament_summary:
        lines.append(f"Linked summary: {tournament_summary.get('path')}")
        lines.append(f"Tournament field size: {format_int(tournament_summary.get('total_players'))}")
    lines.append(f"Total hands parsed: {len(hands)}")
    lines.append(f"Actionable spots analyzed: {len(important_hands)}")
    lines.append(f"Rule-decided spots: {verdict_counts.get('rule', 0)}")
    lines.append(f"Hybrid spots: {verdict_counts.get('hybrid', 0)}")
    lines.append(f"Model-only spots: {verdict_counts.get('model', 0)}")
    lines.append(f"Rule confidence spots: {confidence_counts.get('rule', 0)}")
    lines.append(f"Model confidence spots: {confidence_counts.get('model', 0)}")
    lines.append(f"Postflop spec-tagged spots: {postflop_tagged_count}")
    lines.append("")
    lines.append("Hand Reviews")
    lines.append("-" * 80)
    lines.append("")
    for idx, ((hand, info), analysis) in enumerate(zip(important_hands, analyses), start=1):
        lines.append("=" * 80)
        lines.append(f"HAND {idx:02d}")
        lines.append(compact_spot_header(hand, info))
        lines.append(f"Spot: {info['position']} | {info['hero_cards']}")
        lines.append("Decision Context")
        lines.append("-" * 80)
        for context_line in build_decision_context(hand, info, hero_name, tournament_summary):
            lines.append(context_line)
        lines.append("Postflop Spec Tags")
        lines.append("-" * 80)
        for context_line in build_postflop_spec_context(hand, hero_name):
            lines.append(context_line)
        lines.append("Analysis")
        lines.append("-" * 80)
        lines.append(analysis)
        lines.append("")
    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(description="Parse poker hand-history files from the project raw folder and write analysis into parsed.")
    parser.add_argument("--input", help="Path to a specific raw hand-history file. Defaults to GG20260216-1224 - APL Series 110 Zodiac Evening Classic + Horse.txt if present, otherwise the newest .txt/.log file under data/hand_histories/raw/.")
    parser.add_argument("--output", help="Optional output path. Defaults to data/hand_histories/parsed/<input_stem>_analysis.txt")
    parser.add_argument("--summary", help="Optional tournament summary sidecar file. If omitted, the parser tries to auto-discover a matching summary by tournament ID under data/hand_histories/summaries/.")
    parser.add_argument("--hero", default=DEFAULT_HERO_NAME, help="Hero/player name used in the hand history.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum actionable hands to analyze.")
    return parser.parse_args()


def main():
    load_env_file(ENV_FILE)
    args = parse_args()

    input_path = Path(args.input).expanduser().resolve() if args.input else find_default_input_file()
    if not input_path or not input_path.exists():
        print(f"No input file found. Put a raw hand-history file in {RAW_ROOT} or pass --input.")
        return

    output_path = Path(args.output).expanduser().resolve() if args.output else default_output_for(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tournament_summary = discover_tournament_summary(input_path, args.summary)

    api_key = os.getenv("OPENAI_API_KEY", "ollama")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    client = OpenAI(api_key=api_key, base_url=base_url)
    text = read_file(input_path)
    hands = split_hands(text)
    important_hands = []

    for hand in hands:
        info = extract_info(hand, args.hero)
        if is_important(hand, info, args.hero):
            important_hands.append((hand, info))

    important_hands = important_hands[: args.limit]
    analyses = [
        analyze_hand(hand, info, args.hero, client, tournament_summary, input_path, text)
        for hand, info in important_hands
    ]
    report = build_report(input_path, hands, important_hands, analyses, args.hero, tournament_summary)
    output_path.write_text(report, encoding="utf-8")

    print(f"Input: {input_path}")
    if tournament_summary:
        print(f"Summary: {tournament_summary.get('path')}")
    print(f"Output: {output_path}")
    print(f"Parsed {len(hands)} hands. Wrote {len(important_hands)} analyzed spots.")


if __name__ == "__main__":
    main()
