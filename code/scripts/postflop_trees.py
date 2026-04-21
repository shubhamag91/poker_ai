#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from typing import Any, Optional


POSTFLOP_EXPANSION_PLAN: dict[str, Any] = {
    "meta": {
        "name": "postflop-expansion-plan",
        "version": 2,
        "recommendation": "Build breadth on flop first, then add turn follow-through, then river resolution last.",
        "principles": [
            "Start with heads-up single-raised pots before 3-bet pots or multi-way branches.",
            "Stabilize common sizing families before adding niche or exploit-heavy lines.",
            "Add future streets only after the previous street has clean buckets and repeatable heuristics.",
            "Keep one source of truth for postflop trees so the hand parser can import it later without copy-paste.",
            "Use structural templates first, then expand the concrete matchup matrix.",
        ],
    },
    "stages": [
        {
            "id": "flop",
            "label": "Flop-only foundation",
            "order": 1,
            "goal": "Build the base decision tree without later-street branching noise.",
            "why_now": "Flop is where range-vs-range structure, texture buckets, and baseline sizing logic get defined.",
            "focus": [
                "Single-raised pots first",
                "Heads-up before multi-way",
                "Common in-position and out-of-position c-bet trees",
                "Check-back, stab, and check-raise responses",
            ],
            "build_order": [
                {
                    "step": 1,
                    "id": "srp_btn_bb_ip_pfr",
                    "label": "BTN vs BB, single-raised pot, Hero as in-position preflop raiser",
                    "tree_family": "srp_ip_pfr_flop",
                    "core_sizes": ["25% pot", "66% pot", "check"],
                    "board_buckets": ["A-high dry", "broadway static", "middling connected", "paired", "monotone"],
                    "why_first": "Highest-frequency baseline c-bet tree. This should anchor the naming scheme and default texture buckets.",
                },
                {
                    "step": 2,
                    "id": "srp_btn_bb_oop_caller",
                    "label": "BTN vs BB, single-raised pot, Hero as out-of-position big blind defender",
                    "tree_family": "srp_oop_caller_flop",
                    "core_sizes": ["check", "check-raise to small", "check-raise to big"],
                    "board_buckets": ["low disconnected", "middling dynamic", "paired", "monotone", "range-favored high card"],
                    "why_first": "Pairs directly with the BTN vs BB c-bet tree and forces clean check-call versus check-raise splits.",
                },
                {
                    "step": 3,
                    "id": "srp_co_bb_ip_pfr",
                    "label": "CO vs BB, single-raised pot, Hero as in-position preflop raiser",
                    "tree_family": "srp_ip_pfr_flop",
                    "core_sizes": ["25% pot", "75% pot", "check"],
                    "board_buckets": ["ace-high", "queen-high", "middling dynamic", "paired", "two-tone"],
                    "why_first": "Same family as BTN vs BB, but with a more condensed opening range and different middling-board interaction.",
                },
                {
                    "step": 4,
                    "id": "srp_sb_bb_bvb_pfr",
                    "label": "SB vs BB, single-raised pot, Hero as small blind opener",
                    "tree_family": "bvb_flop_aggressive",
                    "core_sizes": ["20% pot", "50% pot", "check"],
                    "board_buckets": ["high-card static", "low disconnected", "paired", "monotone", "dynamic straight boards"],
                    "why_first": "Blind-versus-blind needs its own family because wider ranges create more aggression, more stabbing, and more mixed low-board behavior.",
                },
                {
                    "step": 5,
                    "id": "srp_sb_bb_bvb_defender",
                    "label": "SB vs BB, single-raised pot, Hero as big blind defender",
                    "tree_family": "bvb_defender_flop",
                    "core_sizes": ["check", "check-raise small", "check-raise jam-pressure branches"],
                    "board_buckets": ["range-neutral middling", "low connected", "paired", "monotone", "turn-sensitive two-tone"],
                    "why_first": "Completes the blind-versus-blind pair and sets up later turn probe logic in the highest-volatility SRP family.",
                },
                {
                    "step": 6,
                    "id": "three_bet_btn_blind_core",
                    "label": "BTN versus blind 3-bet pots, split into IP-3bettor and OOP-3bettor specs",
                    "tree_family": "three_bet_core_group",
                    "core_sizes": ["25% pot", "75% pot", "check"],
                    "board_buckets": ["ace-high", "king-high", "low disconnected", "paired", "monotone"],
                    "why_first": "The old umbrella bucket was too vague for a real spec. Machine-readable trees need separate IP-3bettor and OOP-3bettor variants.",
                },
            ],
            "node_families": [
                {
                    "id": "srp_ip_pfr_flop",
                    "use_for": ["BTN vs BB SRP as opener", "CO vs BB SRP as opener"],
                    "root_actions": ["bet_small", "bet_big", "check"],
                    "response_branches": ["fold_vs_bet", "call_vs_bet", "raise_vs_bet", "stab_after_check"],
                    "include_now": [
                        "single flop raise only",
                        "standard c-bet size family",
                        "check-back and versus-turn-probe seed tagging",
                    ],
                    "exclude_now": ["donk branches outside blind-versus-blind", "multiple raise loops", "exploit-only sizings"],
                },
                {
                    "id": "srp_oop_caller_flop",
                    "use_for": ["BB vs BTN SRP as defender"],
                    "root_actions": ["check"],
                    "response_branches": ["check_fold", "check_call", "check_raise_small", "check_raise_big"],
                    "include_now": ["check-raise construction", "versus-check-back tagging", "board coverage notes"],
                    "exclude_now": ["donk-lead trees", "turn branching beyond seed labels"],
                },
                {
                    "id": "srp_oop_pfr_flop",
                    "use_for": ["UTG vs BTN SRP as opener", "UTG vs CO SRP as opener", "HJ vs BTN SRP as opener", "CO vs BTN SRP as opener"],
                    "root_actions": ["bet_small", "bet_big", "check"],
                    "response_branches": ["fold_vs_bet", "call_vs_bet", "raise_vs_bet", "probe_after_check"],
                    "include_now": ["non-blind OOP preflop raiser structure", "delayed c-bet seeds", "probe defense after check"],
                    "exclude_now": ["multi-raise loops", "turn-overbet branches", "exploit-only sizings"],
                },
                {
                    "id": "bvb_flop_aggressive",
                    "use_for": ["SB vs BB SRP as opener"],
                    "root_actions": ["bet_tiny", "bet_medium", "check"],
                    "response_branches": ["fold_vs_bet", "call_vs_bet", "raise_vs_bet", "stab_after_check"],
                    "include_now": ["wider-range low-board strategy", "aggressive stab frequencies", "paired-board split behavior"],
                    "exclude_now": ["turn-overbet branches", "river planning inside the flop tree"],
                },
                {
                    "id": "bvb_defender_flop",
                    "use_for": ["BB vs SB SRP as defender"],
                    "root_actions": ["check"],
                    "response_branches": ["check_fold", "check_call", "check_raise_small", "check_raise_pressure"],
                    "include_now": ["high-volatility check-raise nodes", "probe seeds after flop checks through"],
                    "exclude_now": ["donk trees", "multi-way adaptations"],
                },
                {
                    "id": "three_bet_core_group",
                    "use_for": ["BTN versus blind 3-bet pots, both IP-3bettor and OOP-3bettor branches"],
                    "root_actions": ["bet_small", "bet_big", "check"],
                    "response_branches": ["fold_vs_bet", "call_vs_bet", "raise_vs_bet"],
                    "include_now": ["split machine-readable specs by who owns the preflop aggression and who acts first"],
                    "exclude_now": ["4-bet pots", "multi-way 3-bet pots", "deep node simplification work"],
                },
            ],
            "naming_scheme_examples": [
                "flop.srp.btn-bb.ip-pfr.cbet-small",
                "flop.srp.btn-bb.oop-caller.check-raise-small",
                "flop.srp.sb-bb.bvb.stab-after-check",
                "flop.srp.utg-btn.oop-pfr.cbet-small",
                "flop.3bp.btn-blind.ip-3bettor.bet-big",
                "flop.3bp.btn-blind.oop-3bettor.check-call",
            ],
            "spots": [
                {
                    "spot": "BTN vs BB single-raised pot",
                    "priority": "highest",
                    "nodes": [
                        "IP c-bet small / big / check",
                        "OOP check / check-call / check-raise / fold",
                        "Texture buckets: high-card, paired, disconnected, monotone, dynamic",
                    ],
                },
                {
                    "spot": "BB vs BTN single-raised pot",
                    "priority": "highest",
                    "nodes": [
                        "OOP defend strategy",
                        "Check-raise construction",
                        "Probe sensitivity after flop checks through",
                    ],
                },
                {
                    "spot": "CO vs BB single-raised pot",
                    "priority": "high",
                    "nodes": [
                        "Broader opening-range effects on flop betting",
                        "More middling-board interaction than BTN vs BB",
                    ],
                },
                {
                    "spot": "UTG/HJ/CO vs BTN/CO single-raised pots",
                    "priority": "high",
                    "nodes": [
                        "Non-blind OOP preflop raiser trees",
                        "Delayed c-bet and probe-defense structure after checks",
                        "Tighter-range board-bias handling than blind-defense families",
                    ],
                },
                {
                    "spot": "SB vs BB single-raised pot",
                    "priority": "high",
                    "nodes": [
                        "Wider ranges and higher aggression frequency",
                        "Lead, raise, and stab branches that appear more often blind-vs-blind",
                    ],
                },
                {
                    "spot": "3-bet pots",
                    "priority": "later within flop stage",
                    "nodes": [
                        "Split IP-3bettor and OOP-3bettor trees instead of one vague umbrella branch",
                        "Keep to core bet / check / raise branches before deeper simplification work",
                    ],
                },
            ],
            "deliverables": [
                "Texture bucket definitions",
                "Baseline sizing families",
                "Simple study trees for c-bet, check-back, stab, and check-raise branches",
                "A repeatable naming scheme the parser can reference later",
                "Machine-readable flop family specs that can scale into the full matchup matrix",
            ],
            "defer_until_later": [
                "Detailed turn runout classes",
                "River bluff-catcher thresholds",
                "Rare multi-way side branches unless they are explicitly important",
            ],
        },
        {
            "id": "turn",
            "label": "Turn follow-through",
            "order": 2,
            "goal": "Add the next decision layer only after flop branches are stable.",
            "why_now": "Turn strategy depends on flop range construction, so adding it earlier usually creates messy trees and duplicated logic.",
            "focus": [
                "Barrel versus check after flop c-bet branches",
                "Delayed c-bet trees after flop checks through",
                "Turn probes and probe defense",
                "Runout bucketing by equity shift and nut advantage change",
            ],
            "spots": [
                {
                    "spot": "Flop c-bet called -> turn decision",
                    "priority": "highest",
                    "nodes": [
                        "Brick turns",
                        "Overcard turns",
                        "Pairing turns",
                        "Flush-completing and straight-completing turns",
                    ],
                },
                {
                    "spot": "Flop checks through -> turn delayed aggression",
                    "priority": "highest",
                    "nodes": [
                        "Delayed c-bet",
                        "Turn stab after missed flop c-bet",
                        "Response tree versus turn probe or raise",
                    ],
                },
                {
                    "spot": "Flop check-raise called -> turn follow-up",
                    "priority": "medium",
                    "nodes": [
                        "Low-SPR pressure branches",
                        "Polar barrel versus give-up patterns",
                    ],
                },
            ],
            "deliverables": [
                "Turn runout class map",
                "Barrel / check / probe heuristics per flop branch",
                "Clear inheritance from flop node names so the parser can compose tree paths cleanly",
            ],
            "defer_until_later": [
                "River jam thresholds",
                "Detailed blocker-led triple barrel trees",
            ],
        },
        {
            "id": "river",
            "label": "River resolution",
            "order": 3,
            "goal": "Add terminal-street logic after flop and turn pathing is already clean.",
            "why_now": "River heuristics are easiest to misbuild when earlier streets are still unstable.",
            "focus": [
                "Polarization and value-to-bluff structure",
                "Blocker-aware bluff selection",
                "Bluff-catching thresholds",
                "Overbet and jam branches only after baseline river sizing is stable",
            ],
            "spots": [
                {
                    "spot": "Turn barrel called -> river strategy",
                    "priority": "highest",
                    "nodes": [
                        "Thin value versus polar value",
                        "Missed-draw bluffs",
                        "Blocker-driven give-ups",
                    ],
                },
                {
                    "spot": "Flop check-back -> turn bet called -> river",
                    "priority": "high",
                    "nodes": [
                        "Delayed-line river value/bluff split",
                        "Capped-range bluff-catching",
                    ],
                },
                {
                    "spot": "Turn checks through -> river probe or bluff-catch",
                    "priority": "high",
                    "nodes": [
                        "Probe sizing",
                        "Merged versus polar betting",
                        "Showdown-heavy node simplification",
                    ],
                },
            ],
            "deliverables": [
                "River node families tied back to turn path IDs",
                "Value/bluff guardrails",
                "Blocker notes that can later feed parser-side explanation text",
            ],
            "defer_until_later": [
                "Exploit-specific deviations by pool",
                "Population-report overlays",
            ],
        },
    ],
}


FLOP_TREE_SPEC_LIBRARY: dict[str, Any] = {
    "meta": {
        "name": "flop-tree-spec-library",
        "schema_version": 1,
        "street": "flop",
        "notes": [
            "These are machine-readable templates for the first-wave flop families.",
            "They are intentionally capped at a single flop raise cycle and seed turn follow-through instead of fully expanding later streets.",
            "Concrete matchup coverage expands by attaching more preflop range matchups to these families, not by inventing a fresh architecture each time.",
        ],
    },
    "board_bucket_sets": {
        "core_flop_textures_v1": [
            {"id": "A_HIGH_DRY", "tags": ["high_card", "static", "range_advantage_ip"]},
            {"id": "BROADWAY_STATIC", "tags": ["broadway", "semi_static", "high_card"]},
            {"id": "MID_CONNECTED", "tags": ["middling", "dynamic", "straight_heavy"]},
            {"id": "PAIRED", "tags": ["paired", "static", "range_interaction_sensitive"]},
            {"id": "MONOTONE", "tags": ["flush_heavy", "compression", "showdown_shift"]},
            {"id": "TWO_TONE", "tags": ["draw_heavy", "turn_sensitive"]},
        ],
        "blind_battle_textures_v1": [
            {"id": "HIGH_CARD_STATIC", "tags": ["high_card", "static", "wide_ranges"]},
            {"id": "LOW_DISCONNECTED", "tags": ["low_card", "static", "range_neutral"]},
            {"id": "LOW_CONNECTED", "tags": ["low_card", "dynamic", "straight_heavy"]},
            {"id": "PAIRED", "tags": ["paired", "range_swing"]},
            {"id": "MONOTONE", "tags": ["flush_heavy", "aggression_sensitive"]},
        ],
        "three_bet_textures_v1": [
            {"id": "ACE_HIGH", "tags": ["high_card", "static", "range_advantage_3bettor"]},
            {"id": "KING_HIGH", "tags": ["high_card", "semi_static", "range_advantage_3bettor"]},
            {"id": "LOW_STATIC", "tags": ["low_or_middling", "static", "nut_advantage_sensitive"]},
            {"id": "MID_DYNAMIC", "tags": ["middling", "connected_or_draw_heavy", "realization_sensitive"]},
            {"id": "PAIRED", "tags": ["paired", "static"]},
            {"id": "MONOTONE", "tags": ["flush_heavy", "compression"]},
        ],
    },
    "size_profiles": {
        "srp_checked_to_ip_v1": {
            "bet_small": {"unit": "pct_pot", "values": [0.25]},
            "bet_big": {"unit": "pct_pot", "values": [0.66, 0.75]},
            "raise_small": {"unit": "x_bet", "values": [3.0]},
            "raise_big": {"unit": "x_bet", "values": [4.5]},
        },
        "srp_oop_pfr_v1": {
            "bet_small": {"unit": "pct_pot", "values": [0.25, 0.33]},
            "bet_big": {"unit": "pct_pot", "values": [0.66, 0.75]},
            "probe_small": {"unit": "pct_pot", "values": [0.33]},
            "probe_big": {"unit": "pct_pot", "values": [0.66]},
            "raise_small": {"unit": "x_bet", "values": [3.0]},
            "raise_big": {"unit": "x_bet", "values": [4.5]},
        },
        "bvb_oop_pfr_v1": {
            "bet_small": {"unit": "pct_pot", "values": [0.2, 0.25]},
            "bet_big": {"unit": "pct_pot", "values": [0.5]},
            "probe_small": {"unit": "pct_pot", "values": [0.33]},
            "probe_big": {"unit": "pct_pot", "values": [0.66]},
            "raise_small": {"unit": "x_bet", "values": [3.0]},
            "raise_big": {"unit": "x_bet", "values": [4.5]},
        },
        "three_bet_checked_to_ip_v1": {
            "bet_small": {"unit": "pct_pot", "values": [0.25]},
            "bet_big": {"unit": "pct_pot", "values": [0.75]},
            "raise_small": {"unit": "x_bet", "values": [2.8]},
            "raise_big": {"unit": "x_bet", "values": [4.0]},
        },
        "three_bet_oop_pfr_v1": {
            "bet_small": {"unit": "pct_pot", "values": [0.25]},
            "bet_big": {"unit": "pct_pot", "values": [0.75]},
            "probe_small": {"unit": "pct_pot", "values": [0.33]},
            "probe_big": {"unit": "pct_pot", "values": [0.66]},
            "raise_small": {"unit": "x_bet", "values": [2.8]},
            "raise_big": {"unit": "x_bet", "values": [4.0]},
        },
        "multiway_srp_v1": {
            "bet_small": {"unit": "pct_pot", "values": [0.25, 0.33]},
            "bet_big": {"unit": "pct_pot", "values": [0.5, 0.66]},
            "probe_small": {"unit": "pct_pot", "values": [0.33]},
            "probe_big": {"unit": "pct_pot", "values": [0.66]},
            "raise_small": {"unit": "x_bet", "values": [3.0]},
        },
        "multiway_3bp_v1": {
            "bet_small": {"unit": "pct_pot", "values": [0.2, 0.25]},
            "bet_big": {"unit": "pct_pot", "values": [0.5, 0.66]},
            "probe_small": {"unit": "pct_pot", "values": [0.25, 0.33]},
            "probe_big": {"unit": "pct_pot", "values": [0.5]},
            "raise_small": {"unit": "x_bet", "values": [2.8]},
        },
        "limped_heads_up_v1": {
            "bet_small": {"unit": "pct_pot", "values": [0.25, 0.33]},
            "bet_big": {"unit": "pct_pot", "values": [0.5, 0.66]},
            "raise_small": {"unit": "x_bet", "values": [3.0]},
            "probe_small": {"unit": "pct_pot", "values": [0.33]},
            "probe_big": {"unit": "pct_pot", "values": [0.66]},
        },
        "four_bet_heads_up_v1": {
            "bet_small": {"unit": "pct_pot", "values": [0.2, 0.25]},
            "bet_big": {"unit": "pct_pot", "values": [0.5, 0.66]},
            "raise_small": {"unit": "x_bet", "values": [2.5]},
            "probe_small": {"unit": "pct_pot", "values": [0.25, 0.33]},
            "probe_big": {"unit": "pct_pot", "values": [0.5]},
        },
    },
    "templates": {
        "checked_to_ip_aggressor_v1": {
            "description": "OOP player does not lead. The street starts with a forced check, then IP chooses between small bet, big bet, or check.",
            "actors": {
                "oop_player": "out_of_position_caller_or_defender",
                "ip_player": "in_position_aggressor",
            },
            "nodes": [
                {
                    "id": "root",
                    "actor": "oop_player",
                    "kind": "forced",
                    "options": [{"action": "check", "next": "ip_decision"}],
                },
                {
                    "id": "ip_decision",
                    "actor": "ip_player",
                    "kind": "decision",
                    "options": [
                        {"action": "bet", "size_ref": "bet_small", "next": "oop_vs_small"},
                        {"action": "bet", "size_ref": "bet_big", "next": "oop_vs_big"},
                        {"action": "check", "next": "turn_seed_checkback"},
                    ],
                },
                {
                    "id": "oop_vs_small",
                    "actor": "oop_player",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_small_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "ip_vs_small_raise_small"},
                        {"action": "raise", "size_ref": "raise_big", "next": "ip_vs_small_raise_big"},
                    ],
                },
                {
                    "id": "oop_vs_big",
                    "actor": "oop_player",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_big_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "ip_vs_big_raise_small"},
                        {"action": "raise", "size_ref": "raise_big", "next": "ip_vs_big_raise_big"},
                    ],
                },
                {
                    "id": "ip_vs_small_raise_small",
                    "actor": "ip_player",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_small_raise_small_called"},
                    ],
                },
                {
                    "id": "ip_vs_small_raise_big",
                    "actor": "ip_player",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_small_raise_big_called"},
                    ],
                },
                {
                    "id": "ip_vs_big_raise_small",
                    "actor": "ip_player",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_big_raise_small_called"},
                    ],
                },
                {
                    "id": "ip_vs_big_raise_big",
                    "actor": "ip_player",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_big_raise_big_called"},
                    ],
                },
            ],
            "turn_seeds": [
                {"id": "turn_seed_checkback", "line": ["check", "check"], "tag": "flop_checked_through"},
                {"id": "turn_seed_small_called", "line": ["check", "bet_small", "call"], "tag": "cbet_small_called"},
                {"id": "turn_seed_big_called", "line": ["check", "bet_big", "call"], "tag": "cbet_big_called"},
                {
                    "id": "turn_seed_small_raise_small_called",
                    "line": ["check", "bet_small", "raise_small", "call"],
                    "tag": "bet_small_raise_small_called",
                },
                {
                    "id": "turn_seed_small_raise_big_called",
                    "line": ["check", "bet_small", "raise_big", "call"],
                    "tag": "bet_small_raise_big_called",
                },
                {
                    "id": "turn_seed_big_raise_small_called",
                    "line": ["check", "bet_big", "raise_small", "call"],
                    "tag": "bet_big_raise_small_called",
                },
                {
                    "id": "turn_seed_big_raise_big_called",
                    "line": ["check", "bet_big", "raise_big", "call"],
                    "tag": "bet_big_raise_big_called",
                },
            ],
            "terminal_nodes": ["terminal_fold"],
            "deferred_features": ["donk leads", "flop 3-bets", "turn and river expansion"],
        },
        "oop_pfr_open_action_v1": {
            "description": "OOP preflop raiser acts first on the flop. This covers c-bet or check branches, then a simple response tree.",
            "actors": {
                "oop_player": "out_of_position_preflop_raiser",
                "ip_player": "in_position_caller",
            },
            "nodes": [
                {
                    "id": "root",
                    "actor": "oop_player",
                    "kind": "decision",
                    "options": [
                        {"action": "bet", "size_ref": "bet_small", "next": "ip_vs_small"},
                        {"action": "bet", "size_ref": "bet_big", "next": "ip_vs_big"},
                        {"action": "check", "next": "ip_vs_check"},
                    ],
                },
                {
                    "id": "ip_vs_small",
                    "actor": "ip_player",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_small_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "oop_vs_small_raise_small"},
                        {"action": "raise", "size_ref": "raise_big", "next": "oop_vs_small_raise_big"},
                    ],
                },
                {
                    "id": "ip_vs_big",
                    "actor": "ip_player",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_big_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "oop_vs_big_raise_small"},
                        {"action": "raise", "size_ref": "raise_big", "next": "oop_vs_big_raise_big"},
                    ],
                },
                {
                    "id": "ip_vs_check",
                    "actor": "ip_player",
                    "kind": "decision",
                    "options": [
                        {"action": "check", "next": "turn_seed_checked_through"},
                        {"action": "bet", "size_ref": "probe_small", "next": "oop_vs_probe_small"},
                        {"action": "bet", "size_ref": "probe_big", "next": "oop_vs_probe_big"},
                    ],
                },
                {
                    "id": "oop_vs_probe_small",
                    "actor": "oop_player",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_probe_small_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "terminal_raised_after_probe_small"},
                    ],
                },
                {
                    "id": "oop_vs_probe_big",
                    "actor": "oop_player",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_probe_big_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "terminal_raised_after_probe_big"},
                    ],
                },
                {
                    "id": "oop_vs_small_raise_small",
                    "actor": "oop_player",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_small_raise_small_called"},
                    ],
                },
                {
                    "id": "oop_vs_small_raise_big",
                    "actor": "oop_player",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_small_raise_big_called"},
                    ],
                },
                {
                    "id": "oop_vs_big_raise_small",
                    "actor": "oop_player",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_big_raise_small_called"},
                    ],
                },
                {
                    "id": "oop_vs_big_raise_big",
                    "actor": "oop_player",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_big_raise_big_called"},
                    ],
                },
            ],
            "turn_seeds": [
                {"id": "turn_seed_checked_through", "line": ["check", "check"], "tag": "flop_checked_through"},
                {"id": "turn_seed_small_called", "line": ["bet_small", "call"], "tag": "cbet_small_called"},
                {"id": "turn_seed_big_called", "line": ["bet_big", "call"], "tag": "cbet_big_called"},
                {"id": "turn_seed_probe_small_called", "line": ["check", "probe_small", "call"], "tag": "probe_small_called"},
                {"id": "turn_seed_probe_big_called", "line": ["check", "probe_big", "call"], "tag": "probe_big_called"},
                {
                    "id": "turn_seed_small_raise_small_called",
                    "line": ["bet_small", "raise_small", "call"],
                    "tag": "bet_small_raise_small_called",
                },
                {
                    "id": "turn_seed_small_raise_big_called",
                    "line": ["bet_small", "raise_big", "call"],
                    "tag": "bet_small_raise_big_called",
                },
                {
                    "id": "turn_seed_big_raise_small_called",
                    "line": ["bet_big", "raise_small", "call"],
                    "tag": "bet_big_raise_small_called",
                },
                {
                    "id": "turn_seed_big_raise_big_called",
                    "line": ["bet_big", "raise_big", "call"],
                    "tag": "bet_big_raise_big_called",
                },
            ],
            "terminal_nodes": ["terminal_fold", "terminal_raised_after_probe_small", "terminal_raised_after_probe_big"],
            "deferred_features": ["flop 3-bets", "turn and river expansion"],
        },
        "bucket_only_v1": {
            "description": "Structural bucket for complex preflop path types that are intentionally tagged before detailed flop-node expansion exists.",
            "actors": {"bucket": "structural_bucket_only"},
            "nodes": [{"id": "root", "actor": "bucket", "kind": "bucket", "options": []}],
            "turn_seeds": [],
            "terminal_nodes": [],
            "deferred_features": ["detailed flop tree", "turn and river expansion"],
        },
        "multiway_checked_to_pfr_v1": {
            "description": "First-pass multiway SRP flop tree for spots where action checks to the preflop raiser. This compresses the field response while preserving the main c-bet, check-back, stab, and raise branches.",
            "actors": {
                "first_field_player": "first_player_to_act_in_field",
                "preflop_raiser": "preflop_raiser",
                "field": "remaining_multiway_field",
            },
            "nodes": [
                {
                    "id": "root",
                    "actor": "first_field_player",
                    "kind": "forced",
                    "options": [{"action": "check", "next": "pfr_decision"}],
                },
                {
                    "id": "pfr_decision",
                    "actor": "preflop_raiser",
                    "kind": "decision",
                    "options": [
                        {"action": "bet", "size_ref": "bet_small", "next": "field_vs_small"},
                        {"action": "bet", "size_ref": "bet_big", "next": "field_vs_big"},
                        {"action": "check", "next": "field_after_check"},
                    ],
                },
                {
                    "id": "field_vs_small",
                    "actor": "field",
                    "kind": "compressed_multiway_decision",
                    "options": [
                        {"action": "fold_all", "next": "terminal_field_folds"},
                        {"action": "one_or_more_calls", "next": "turn_seed_multiway_small_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "pfr_vs_small_raise"},
                    ],
                },
                {
                    "id": "field_vs_big",
                    "actor": "field",
                    "kind": "compressed_multiway_decision",
                    "options": [
                        {"action": "fold_all", "next": "terminal_field_folds"},
                        {"action": "one_or_more_calls", "next": "turn_seed_multiway_big_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "pfr_vs_big_raise"},
                    ],
                },
                {
                    "id": "field_after_check",
                    "actor": "field",
                    "kind": "compressed_multiway_decision",
                    "options": [
                        {"action": "check_through", "next": "turn_seed_multiway_checked_through"},
                        {"action": "bet", "size_ref": "probe_small", "next": "pfr_vs_field_probe_small"},
                        {"action": "bet", "size_ref": "probe_big", "next": "pfr_vs_field_probe_big"},
                    ],
                },
                {
                    "id": "pfr_vs_small_raise",
                    "actor": "preflop_raiser",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_multiway_small_raise_called"},
                    ],
                },
                {
                    "id": "pfr_vs_big_raise",
                    "actor": "preflop_raiser",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_multiway_big_raise_called"},
                    ],
                },
                {
                    "id": "pfr_vs_field_probe_small",
                    "actor": "preflop_raiser",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_multiway_probe_small_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "terminal_probe_small_raised"},
                    ],
                },
                {
                    "id": "pfr_vs_field_probe_big",
                    "actor": "preflop_raiser",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_multiway_probe_big_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "terminal_probe_big_raised"},
                    ],
                },
            ],
            "turn_seeds": [
                {"id": "turn_seed_multiway_checked_through", "line": ["check", "check_through"], "tag": "multiway_checked_through"},
                {"id": "turn_seed_multiway_small_called", "line": ["bet_small", "one_or_more_calls"], "tag": "multiway_small_cbet_called"},
                {"id": "turn_seed_multiway_big_called", "line": ["bet_big", "one_or_more_calls"], "tag": "multiway_big_cbet_called"},
                {"id": "turn_seed_multiway_small_raise_called", "line": ["bet_small", "raise_small", "call"], "tag": "multiway_small_bet_raise_called"},
                {"id": "turn_seed_multiway_big_raise_called", "line": ["bet_big", "raise_small", "call"], "tag": "multiway_big_bet_raise_called"},
                {"id": "turn_seed_multiway_probe_small_called", "line": ["check", "probe_small", "call"], "tag": "multiway_probe_small_called"},
                {"id": "turn_seed_multiway_probe_big_called", "line": ["check", "probe_big", "call"], "tag": "multiway_probe_big_called"},
            ],
            "terminal_nodes": ["terminal_fold", "terminal_field_folds", "terminal_probe_small_raised", "terminal_probe_big_raised"],
            "deferred_features": ["exact non-PFR actor ordering", "multiple continue branches separated by caller count", "turn and river expansion"],
        },
        "multiway_checked_to_3bettor_v1": {
            "description": "First-pass multiway 3-bet pot flop tree for spots where action checks to the 3-bettor. This is the 3-bet analogue of the multiway SRP template, with tighter sizing and higher-SPR compression assumptions.",
            "actors": {
                "first_field_player": "first_player_to_act_in_field",
                "three_bettor": "preflop_3bettor",
                "field": "remaining_multiway_field",
            },
            "nodes": [
                {
                    "id": "root",
                    "actor": "first_field_player",
                    "kind": "forced",
                    "options": [{"action": "check", "next": "three_bettor_decision"}],
                },
                {
                    "id": "three_bettor_decision",
                    "actor": "three_bettor",
                    "kind": "decision",
                    "options": [
                        {"action": "bet", "size_ref": "bet_small", "next": "field_vs_small"},
                        {"action": "bet", "size_ref": "bet_big", "next": "field_vs_big"},
                        {"action": "check", "next": "field_after_check"},
                    ],
                },
                {
                    "id": "field_vs_small",
                    "actor": "field",
                    "kind": "compressed_multiway_decision",
                    "options": [
                        {"action": "fold_all", "next": "terminal_field_folds"},
                        {"action": "one_or_more_calls", "next": "turn_seed_multiway_3bp_small_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "three_bettor_vs_small_raise"},
                    ],
                },
                {
                    "id": "field_vs_big",
                    "actor": "field",
                    "kind": "compressed_multiway_decision",
                    "options": [
                        {"action": "fold_all", "next": "terminal_field_folds"},
                        {"action": "one_or_more_calls", "next": "turn_seed_multiway_3bp_big_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "three_bettor_vs_big_raise"},
                    ],
                },
                {
                    "id": "field_after_check",
                    "actor": "field",
                    "kind": "compressed_multiway_decision",
                    "options": [
                        {"action": "check_through", "next": "turn_seed_multiway_3bp_checked_through"},
                        {"action": "bet", "size_ref": "probe_small", "next": "three_bettor_vs_probe_small"},
                        {"action": "bet", "size_ref": "probe_big", "next": "three_bettor_vs_probe_big"},
                    ],
                },
                {
                    "id": "three_bettor_vs_small_raise",
                    "actor": "three_bettor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_multiway_3bp_small_raise_called"},
                    ],
                },
                {
                    "id": "three_bettor_vs_big_raise",
                    "actor": "three_bettor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_multiway_3bp_big_raise_called"},
                    ],
                },
                {
                    "id": "three_bettor_vs_probe_small",
                    "actor": "three_bettor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_multiway_3bp_probe_small_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "terminal_probe_small_raised"},
                    ],
                },
                {
                    "id": "three_bettor_vs_probe_big",
                    "actor": "three_bettor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_multiway_3bp_probe_big_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "terminal_probe_big_raised"},
                    ],
                },
            ],
            "turn_seeds": [
                {"id": "turn_seed_multiway_3bp_checked_through", "line": ["check", "check_through"], "tag": "multiway_3bp_checked_through"},
                {"id": "turn_seed_multiway_3bp_small_called", "line": ["bet_small", "one_or_more_calls"], "tag": "multiway_3bp_small_bet_called"},
                {"id": "turn_seed_multiway_3bp_big_called", "line": ["bet_big", "one_or_more_calls"], "tag": "multiway_3bp_big_bet_called"},
                {"id": "turn_seed_multiway_3bp_small_raise_called", "line": ["bet_small", "raise_small", "call"], "tag": "multiway_3bp_small_bet_raise_called"},
                {"id": "turn_seed_multiway_3bp_big_raise_called", "line": ["bet_big", "raise_small", "call"], "tag": "multiway_3bp_big_bet_raise_called"},
                {"id": "turn_seed_multiway_3bp_probe_small_called", "line": ["check", "probe_small", "call"], "tag": "multiway_3bp_probe_small_called"},
                {"id": "turn_seed_multiway_3bp_probe_big_called", "line": ["check", "probe_big", "call"], "tag": "multiway_3bp_probe_big_called"},
            ],
            "terminal_nodes": ["terminal_fold", "terminal_field_folds", "terminal_probe_small_raised", "terminal_probe_big_raised"],
            "deferred_features": ["exact non-3bettor actor ordering", "multiple continue branches separated by caller count", "turn and river expansion"],
        },
        "limped_heads_up_neutral_v1": {
            "description": "First-pass heads-up limped-pot flop tree. This starts from a neutral checked-to node and captures the common check, stab, raise, and check-through branches without assigning a forced preflop aggressor.",
            "actors": {
                "first_actor": "first_player_to_act",
                "second_actor": "second_player_to_act",
            },
            "nodes": [
                {
                    "id": "root",
                    "actor": "first_actor",
                    "kind": "decision",
                    "options": [
                        {"action": "check", "next": "second_actor_after_check"},
                        {"action": "bet", "size_ref": "bet_small", "next": "second_actor_vs_small"},
                        {"action": "bet", "size_ref": "bet_big", "next": "second_actor_vs_big"},
                    ],
                },
                {
                    "id": "second_actor_after_check",
                    "actor": "second_actor",
                    "kind": "decision",
                    "options": [
                        {"action": "check", "next": "turn_seed_limped_checked_through"},
                        {"action": "bet", "size_ref": "probe_small", "next": "first_actor_vs_probe_small"},
                        {"action": "bet", "size_ref": "probe_big", "next": "first_actor_vs_probe_big"},
                    ],
                },
                {
                    "id": "second_actor_vs_small",
                    "actor": "second_actor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_limped_small_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "first_actor_vs_small_raise"},
                    ],
                },
                {
                    "id": "second_actor_vs_big",
                    "actor": "second_actor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_limped_big_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "first_actor_vs_big_raise"},
                    ],
                },
                {
                    "id": "first_actor_vs_small_raise",
                    "actor": "first_actor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_limped_small_raise_called"},
                    ],
                },
                {
                    "id": "first_actor_vs_big_raise",
                    "actor": "first_actor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_limped_big_raise_called"},
                    ],
                },
                {
                    "id": "first_actor_vs_probe_small",
                    "actor": "first_actor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_limped_probe_small_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "terminal_probe_small_raised"},
                    ],
                },
                {
                    "id": "first_actor_vs_probe_big",
                    "actor": "first_actor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_limped_probe_big_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "terminal_probe_big_raised"},
                    ],
                },
            ],
            "turn_seeds": [
                {"id": "turn_seed_limped_checked_through", "line": ["check", "check"], "tag": "limped_checked_through"},
                {"id": "turn_seed_limped_small_called", "line": ["bet_small", "call"], "tag": "limped_small_bet_called"},
                {"id": "turn_seed_limped_big_called", "line": ["bet_big", "call"], "tag": "limped_big_bet_called"},
                {"id": "turn_seed_limped_small_raise_called", "line": ["bet_small", "raise_small", "call"], "tag": "limped_small_bet_raise_called"},
                {"id": "turn_seed_limped_big_raise_called", "line": ["bet_big", "raise_small", "call"], "tag": "limped_big_bet_raise_called"},
                {"id": "turn_seed_limped_probe_small_called", "line": ["check", "probe_small", "call"], "tag": "limped_probe_small_called"},
                {"id": "turn_seed_limped_probe_big_called", "line": ["check", "probe_big", "call"], "tag": "limped_probe_big_called"},
            ],
            "terminal_nodes": ["terminal_fold", "terminal_probe_small_raised", "terminal_probe_big_raised"],
            "deferred_features": ["limped blind-vs-blind exact actor roles", "turn and river expansion"],
        },
        "heads_up_checked_to_last_aggressor_v1": {
            "description": "First-pass heads-up high-aggression tree for 4-bet and 5-bet-plus pots when action checks to the last aggressor.",
            "actors": {
                "oop_player": "out_of_position_non_aggressor",
                "last_aggressor": "last_preflop_aggressor",
            },
            "nodes": [
                {
                    "id": "root",
                    "actor": "oop_player",
                    "kind": "forced",
                    "options": [{"action": "check", "next": "aggressor_decision"}],
                },
                {
                    "id": "aggressor_decision",
                    "actor": "last_aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "bet", "size_ref": "bet_small", "next": "oop_vs_small"},
                        {"action": "bet", "size_ref": "bet_big", "next": "oop_vs_big"},
                        {"action": "check", "next": "turn_seed_4bp_checkback"},
                    ],
                },
                {
                    "id": "oop_vs_small",
                    "actor": "oop_player",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_4bp_small_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "aggressor_vs_small_raise"},
                    ],
                },
                {
                    "id": "oop_vs_big",
                    "actor": "oop_player",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_4bp_big_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "aggressor_vs_big_raise"},
                    ],
                },
                {
                    "id": "aggressor_vs_small_raise",
                    "actor": "last_aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_4bp_small_raise_called"},
                    ],
                },
                {
                    "id": "aggressor_vs_big_raise",
                    "actor": "last_aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_4bp_big_raise_called"},
                    ],
                },
            ],
            "turn_seeds": [
                {"id": "turn_seed_4bp_checkback", "line": ["check", "check"], "tag": "4bp_checked_through"},
                {"id": "turn_seed_4bp_small_called", "line": ["check", "bet_small", "call"], "tag": "4bp_small_bet_called"},
                {"id": "turn_seed_4bp_big_called", "line": ["check", "bet_big", "call"], "tag": "4bp_big_bet_called"},
                {"id": "turn_seed_4bp_small_raise_called", "line": ["check", "bet_small", "raise_small", "call"], "tag": "4bp_small_bet_raise_called"},
                {"id": "turn_seed_4bp_big_raise_called", "line": ["check", "bet_big", "raise_small", "call"], "tag": "4bp_big_bet_raise_called"},
            ],
            "terminal_nodes": ["terminal_fold"],
            "deferred_features": ["exact IP/OOP ownership by specific 4-bet line", "turn and river expansion"],
        },
        "oop_lead_or_check_to_ip_aggressor_v1": {
            "description": "First-pass heads-up template for IP-aggressor spots where the OOP player can either check to the aggressor or lead into them.",
            "actors": {
                "oop_player": "out_of_position_caller",
                "ip_aggressor": "in_position_aggressor",
            },
            "nodes": [
                {
                    "id": "root",
                    "actor": "oop_player",
                    "kind": "decision",
                    "options": [
                        {"action": "check", "next": "ip_decision_after_check"},
                        {"action": "bet", "size_ref": "probe_small", "next": "ip_vs_lead_small"},
                        {"action": "bet", "size_ref": "probe_big", "next": "ip_vs_lead_big"},
                    ],
                },
                {
                    "id": "ip_decision_after_check",
                    "actor": "ip_aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "bet", "size_ref": "bet_small", "next": "oop_vs_small"},
                        {"action": "bet", "size_ref": "bet_big", "next": "oop_vs_big"},
                        {"action": "check", "next": "turn_seed_ip_checkback"},
                    ],
                },
                {
                    "id": "oop_vs_small",
                    "actor": "oop_player",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_ip_small_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "ip_vs_small_raise"},
                    ],
                },
                {
                    "id": "oop_vs_big",
                    "actor": "oop_player",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_ip_big_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "ip_vs_big_raise"},
                    ],
                },
                {
                    "id": "ip_vs_small_raise",
                    "actor": "ip_aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_ip_small_raise_called"},
                    ],
                },
                {
                    "id": "ip_vs_big_raise",
                    "actor": "ip_aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_ip_big_raise_called"},
                    ],
                },
                {
                    "id": "ip_vs_lead_small",
                    "actor": "ip_aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_oop_lead_small_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "terminal_oop_small_lead_raised"},
                    ],
                },
                {
                    "id": "ip_vs_lead_big",
                    "actor": "ip_aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_oop_lead_big_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "terminal_oop_big_lead_raised"},
                    ],
                },
            ],
            "turn_seeds": [
                {"id": "turn_seed_ip_checkback", "line": ["check", "check"], "tag": "ip_aggressor_checked_back"},
                {"id": "turn_seed_ip_small_called", "line": ["check", "bet_small", "call"], "tag": "ip_aggressor_small_bet_called"},
                {"id": "turn_seed_ip_big_called", "line": ["check", "bet_big", "call"], "tag": "ip_aggressor_big_bet_called"},
                {"id": "turn_seed_ip_small_raise_called", "line": ["check", "bet_small", "raise_small", "call"], "tag": "ip_aggressor_small_bet_raise_called"},
                {"id": "turn_seed_ip_big_raise_called", "line": ["check", "bet_big", "raise_small", "call"], "tag": "ip_aggressor_big_bet_raise_called"},
                {"id": "turn_seed_oop_lead_small_called", "line": ["probe_small", "call"], "tag": "oop_small_lead_called"},
                {"id": "turn_seed_oop_lead_big_called", "line": ["probe_big", "call"], "tag": "oop_big_lead_called"},
            ],
            "terminal_nodes": ["terminal_fold", "terminal_oop_small_lead_raised", "terminal_oop_big_lead_raised"],
            "deferred_features": ["exact donk frequency by board family", "turn and river expansion"],
        },
        "multiway_field_lead_or_check_to_aggressor_v1": {
            "description": "First-pass 3-way template where the first field player can either check to the aggressor or lead into the field before the aggressor acts.",
            "actors": {
                "first_field_player": "first_player_to_act_in_field",
                "aggressor": "preflop_aggressor",
                "field": "remaining_field",
            },
            "nodes": [
                {
                    "id": "root",
                    "actor": "first_field_player",
                    "kind": "decision",
                    "options": [
                        {"action": "check", "next": "aggressor_after_check"},
                        {"action": "bet", "size_ref": "probe_small", "next": "aggressor_vs_field_lead_small"},
                        {"action": "bet", "size_ref": "probe_big", "next": "aggressor_vs_field_lead_big"},
                    ],
                },
                {
                    "id": "aggressor_after_check",
                    "actor": "aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "bet", "size_ref": "bet_small", "next": "field_vs_small"},
                        {"action": "bet", "size_ref": "bet_big", "next": "field_vs_big"},
                        {"action": "check", "next": "turn_seed_multiway_checkback"},
                    ],
                },
                {
                    "id": "field_vs_small",
                    "actor": "field",
                    "kind": "compressed_multiway_decision",
                    "options": [
                        {"action": "fold_all", "next": "terminal_field_folds"},
                        {"action": "one_or_more_calls", "next": "turn_seed_multiway_small_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "aggressor_vs_small_raise"},
                    ],
                },
                {
                    "id": "field_vs_big",
                    "actor": "field",
                    "kind": "compressed_multiway_decision",
                    "options": [
                        {"action": "fold_all", "next": "terminal_field_folds"},
                        {"action": "one_or_more_calls", "next": "turn_seed_multiway_big_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "aggressor_vs_big_raise"},
                    ],
                },
                {
                    "id": "aggressor_vs_small_raise",
                    "actor": "aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_multiway_small_raise_called"},
                    ],
                },
                {
                    "id": "aggressor_vs_big_raise",
                    "actor": "aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_multiway_big_raise_called"},
                    ],
                },
                {
                    "id": "aggressor_vs_field_lead_small",
                    "actor": "aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_multiway_field_lead_small_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "terminal_field_lead_small_raised"},
                    ],
                },
                {
                    "id": "aggressor_vs_field_lead_big",
                    "actor": "aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_multiway_field_lead_big_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "terminal_field_lead_big_raised"},
                    ],
                },
            ],
            "turn_seeds": [
                {"id": "turn_seed_multiway_checkback", "line": ["check", "check"], "tag": "multiway_aggressor_checked_back"},
                {"id": "turn_seed_multiway_small_called", "line": ["check", "bet_small", "one_or_more_calls"], "tag": "multiway_aggressor_small_bet_called"},
                {"id": "turn_seed_multiway_big_called", "line": ["check", "bet_big", "one_or_more_calls"], "tag": "multiway_aggressor_big_bet_called"},
                {"id": "turn_seed_multiway_small_raise_called", "line": ["check", "bet_small", "raise_small", "call"], "tag": "multiway_aggressor_small_bet_raise_called"},
                {"id": "turn_seed_multiway_big_raise_called", "line": ["check", "bet_big", "raise_small", "call"], "tag": "multiway_aggressor_big_bet_raise_called"},
                {"id": "turn_seed_multiway_field_lead_small_called", "line": ["probe_small", "call"], "tag": "multiway_field_small_lead_called"},
                {"id": "turn_seed_multiway_field_lead_big_called", "line": ["probe_big", "call"], "tag": "multiway_field_big_lead_called"},
            ],
            "terminal_nodes": ["terminal_fold", "terminal_field_folds", "terminal_field_lead_small_raised", "terminal_field_lead_big_raised"],
            "deferred_features": ["exact multiway lead frequency by board family", "turn and river expansion"],
        },
        "multiway_oop_aggressor_open_action_v1": {
            "description": "First-pass 3-way template for cases where the preflop aggressor is first to act on the flop.",
            "actors": {
                "aggressor": "out_of_position_preflop_aggressor",
                "field": "two_remaining_players",
            },
            "nodes": [
                {
                    "id": "root",
                    "actor": "aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "bet", "size_ref": "bet_small", "next": "field_vs_small"},
                        {"action": "bet", "size_ref": "bet_big", "next": "field_vs_big"},
                        {"action": "check", "next": "field_after_check"},
                    ],
                },
                {
                    "id": "field_vs_small",
                    "actor": "field",
                    "kind": "compressed_multiway_decision",
                    "options": [
                        {"action": "fold_all", "next": "terminal_field_folds"},
                        {"action": "one_or_more_calls", "next": "turn_seed_oop_aggressor_small_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "aggressor_vs_small_raise"},
                    ],
                },
                {
                    "id": "field_vs_big",
                    "actor": "field",
                    "kind": "compressed_multiway_decision",
                    "options": [
                        {"action": "fold_all", "next": "terminal_field_folds"},
                        {"action": "one_or_more_calls", "next": "turn_seed_oop_aggressor_big_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "aggressor_vs_big_raise"},
                    ],
                },
                {
                    "id": "aggressor_vs_small_raise",
                    "actor": "aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_oop_aggressor_small_raise_called"},
                    ],
                },
                {
                    "id": "aggressor_vs_big_raise",
                    "actor": "aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_oop_aggressor_big_raise_called"},
                    ],
                },
                {
                    "id": "field_after_check",
                    "actor": "field",
                    "kind": "compressed_multiway_decision",
                    "options": [
                        {"action": "check_through", "next": "turn_seed_oop_aggressor_check_through"},
                        {"action": "stab_small", "next": "aggressor_vs_field_stab_small"},
                        {"action": "stab_big", "next": "aggressor_vs_field_stab_big"},
                    ],
                },
                {
                    "id": "aggressor_vs_field_stab_small",
                    "actor": "aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_field_stab_small_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "terminal_field_stab_small_raised"},
                    ],
                },
                {
                    "id": "aggressor_vs_field_stab_big",
                    "actor": "aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_field_stab_big_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "terminal_field_stab_big_raised"},
                    ],
                },
            ],
            "turn_seeds": [
                {"id": "turn_seed_oop_aggressor_small_called", "line": ["bet_small", "one_or_more_calls"], "tag": "multiway_oop_aggressor_small_bet_called"},
                {"id": "turn_seed_oop_aggressor_big_called", "line": ["bet_big", "one_or_more_calls"], "tag": "multiway_oop_aggressor_big_bet_called"},
                {"id": "turn_seed_oop_aggressor_small_raise_called", "line": ["bet_small", "raise_small", "call"], "tag": "multiway_oop_aggressor_small_bet_raise_called"},
                {"id": "turn_seed_oop_aggressor_big_raise_called", "line": ["bet_big", "raise_small", "call"], "tag": "multiway_oop_aggressor_big_bet_raise_called"},
                {"id": "turn_seed_oop_aggressor_check_through", "line": ["check", "check_through"], "tag": "multiway_oop_aggressor_checked_through"},
                {"id": "turn_seed_field_stab_small_called", "line": ["check", "stab_small", "call"], "tag": "multiway_field_small_stab_called"},
                {"id": "turn_seed_field_stab_big_called", "line": ["check", "stab_big", "call"], "tag": "multiway_field_big_stab_called"},
            ],
            "terminal_nodes": ["terminal_fold", "terminal_field_folds", "terminal_field_stab_small_raised", "terminal_field_stab_big_raised"],
            "deferred_features": ["exact stab ownership inside compressed field", "turn and river expansion"],
        },
        "multiway_two_fields_before_ip_aggressor_v1": {
            "description": "First-pass 3-way template for cases where two field players act before the in-position aggressor.",
            "actors": {
                "first_field_player": "first_player_to_act",
                "second_field_player": "second_player_to_act",
                "aggressor": "in_position_preflop_aggressor",
                "field": "combined_field_after_aggressor_bet",
            },
            "nodes": [
                {
                    "id": "root",
                    "actor": "first_field_player",
                    "kind": "decision",
                    "options": [
                        {"action": "bet", "size_ref": "probe_small", "next": "aggressor_vs_first_field_small"},
                        {"action": "bet", "size_ref": "probe_big", "next": "aggressor_vs_first_field_big"},
                        {"action": "check", "next": "second_field_after_first_check"},
                    ],
                },
                {
                    "id": "second_field_after_first_check",
                    "actor": "second_field_player",
                    "kind": "decision",
                    "options": [
                        {"action": "bet", "size_ref": "probe_small", "next": "aggressor_vs_second_field_small"},
                        {"action": "bet", "size_ref": "probe_big", "next": "aggressor_vs_second_field_big"},
                        {"action": "check", "next": "aggressor_after_double_check"},
                    ],
                },
                {
                    "id": "aggressor_after_double_check",
                    "actor": "aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "bet", "size_ref": "bet_small", "next": "field_vs_small"},
                        {"action": "bet", "size_ref": "bet_big", "next": "field_vs_big"},
                        {"action": "check", "next": "turn_seed_ip_aggressor_checkback"},
                    ],
                },
                {
                    "id": "field_vs_small",
                    "actor": "field",
                    "kind": "compressed_multiway_decision",
                    "options": [
                        {"action": "fold_all", "next": "terminal_field_folds"},
                        {"action": "one_or_more_calls", "next": "turn_seed_ip_aggressor_small_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "aggressor_vs_small_raise"},
                    ],
                },
                {
                    "id": "field_vs_big",
                    "actor": "field",
                    "kind": "compressed_multiway_decision",
                    "options": [
                        {"action": "fold_all", "next": "terminal_field_folds"},
                        {"action": "one_or_more_calls", "next": "turn_seed_ip_aggressor_big_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "aggressor_vs_big_raise"},
                    ],
                },
                {
                    "id": "aggressor_vs_small_raise",
                    "actor": "aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_ip_aggressor_small_raise_called"},
                    ],
                },
                {
                    "id": "aggressor_vs_big_raise",
                    "actor": "aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_ip_aggressor_big_raise_called"},
                    ],
                },
                {
                    "id": "aggressor_vs_first_field_small",
                    "actor": "aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_first_field_small_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "terminal_first_field_small_raised"},
                    ],
                },
                {
                    "id": "aggressor_vs_first_field_big",
                    "actor": "aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_first_field_big_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "terminal_first_field_big_raised"},
                    ],
                },
                {
                    "id": "aggressor_vs_second_field_small",
                    "actor": "aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_second_field_small_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "terminal_second_field_small_raised"},
                    ],
                },
                {
                    "id": "aggressor_vs_second_field_big",
                    "actor": "aggressor",
                    "kind": "decision",
                    "options": [
                        {"action": "fold", "next": "terminal_fold"},
                        {"action": "call", "next": "turn_seed_second_field_big_called"},
                        {"action": "raise", "size_ref": "raise_small", "next": "terminal_second_field_big_raised"},
                    ],
                },
            ],
            "turn_seeds": [
                {"id": "turn_seed_ip_aggressor_checkback", "line": ["check", "check", "check"], "tag": "multiway_ip_aggressor_checked_back"},
                {"id": "turn_seed_ip_aggressor_small_called", "line": ["check", "check", "bet_small", "one_or_more_calls"], "tag": "multiway_ip_aggressor_small_bet_called"},
                {"id": "turn_seed_ip_aggressor_big_called", "line": ["check", "check", "bet_big", "one_or_more_calls"], "tag": "multiway_ip_aggressor_big_bet_called"},
                {"id": "turn_seed_ip_aggressor_small_raise_called", "line": ["check", "check", "bet_small", "raise_small", "call"], "tag": "multiway_ip_aggressor_small_bet_raise_called"},
                {"id": "turn_seed_ip_aggressor_big_raise_called", "line": ["check", "check", "bet_big", "raise_small", "call"], "tag": "multiway_ip_aggressor_big_bet_raise_called"},
                {"id": "turn_seed_first_field_small_called", "line": ["probe_small", "call"], "tag": "multiway_first_field_small_lead_called"},
                {"id": "turn_seed_first_field_big_called", "line": ["probe_big", "call"], "tag": "multiway_first_field_big_lead_called"},
                {"id": "turn_seed_second_field_small_called", "line": ["check", "probe_small", "call"], "tag": "multiway_second_field_small_lead_called"},
                {"id": "turn_seed_second_field_big_called", "line": ["check", "probe_big", "call"], "tag": "multiway_second_field_big_lead_called"},
            ],
            "terminal_nodes": ["terminal_fold", "terminal_field_folds", "terminal_first_field_small_raised", "terminal_first_field_big_raised", "terminal_second_field_small_raised", "terminal_second_field_big_raised"],
            "deferred_features": ["exact field ownership after ip checkback or bet", "turn and river expansion"],
        },
    },
    "families": {
        "srp_ip_pfr_flop": {
            "template_ref": "checked_to_ip_aggressor_v1",
            "hero_role": "ip_pfr",
            "villain_role": "oop_caller",
            "street": "flop",
            "pot_type": "single_raised_pot",
            "board_bucket_set_ref": "core_flop_textures_v1",
            "size_profile_ref": "srp_checked_to_ip_v1",
            "applies_to_matchups": ["UTG_vs_BB", "HJ_vs_BB", "CO_vs_BB", "BTN_vs_BB"],
            "planned_expansion_matchups": ["CO_vs_SB_if_modelled", "HJ_vs_SB_if_modelled", "UTG_vs_SB_if_modelled"],
            "line_prefix": "flop.srp.ip-pfr",
            "board_size_policy": {
                "A_HIGH_DRY": {"remove_size_refs": ["bet_big"]},
                "BROADWAY_STATIC": {"remove_size_refs": ["bet_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big"]}
            },
            "board_turn_seed_policy": {
                "A_HIGH_DRY": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "BROADWAY_STATIC": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]}
            },
        },
        "srp_oop_caller_flop": {
            "template_ref": "checked_to_ip_aggressor_v1",
            "hero_role": "oop_caller",
            "villain_role": "ip_pfr",
            "street": "flop",
            "pot_type": "single_raised_pot",
            "board_bucket_set_ref": "core_flop_textures_v1",
            "size_profile_ref": "srp_checked_to_ip_v1",
            "applies_to_matchups": ["BB_vs_UTG", "BB_vs_HJ", "BB_vs_CO", "BB_vs_BTN", "SB_vs_UTG", "SB_vs_HJ", "SB_vs_CO", "SB_vs_BTN"],
            "planned_expansion_matchups": ["SB_vs_LJ_if_modelled", "BB_vs_LJ_if_modelled"],
            "line_prefix": "flop.srp.oop-caller",
            "board_size_policy": {
                "A_HIGH_DRY": {"remove_size_refs": ["bet_big"]},
                "BROADWAY_STATIC": {"remove_size_refs": ["bet_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big"]}
            },
            "board_turn_seed_policy": {
                "A_HIGH_DRY": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "BROADWAY_STATIC": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]}
            },
        },
        "srp_oop_pfr_flop": {
            "template_ref": "oop_pfr_open_action_v1",
            "hero_role": "oop_pfr",
            "villain_role": "ip_caller",
            "street": "flop",
            "pot_type": "single_raised_pot",
            "board_bucket_set_ref": "core_flop_textures_v1",
            "size_profile_ref": "srp_oop_pfr_v1",
            "applies_to_matchups": ["UTG_vs_HJ", "UTG_vs_CO", "UTG_vs_BTN", "HJ_vs_CO", "HJ_vs_BTN", "CO_vs_BTN"],
            "planned_expansion_matchups": ["LJ_vs_CO_if_modelled", "LJ_vs_BTN_if_modelled"],
            "line_prefix": "flop.srp.oop-pfr",
            "board_size_policy": {
                "A_HIGH_DRY": {"remove_size_refs": ["bet_big", "probe_big"]},
                "BROADWAY_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]}
            },
            "board_turn_seed_policy": {
                "A_HIGH_DRY": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "BROADWAY_STATIC": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]}
            },
        },
        "bvb_flop_aggressive": {
            "template_ref": "oop_pfr_open_action_v1",
            "hero_role": "sb_pfr",
            "villain_role": "bb_caller",
            "street": "flop",
            "pot_type": "single_raised_pot",
            "board_bucket_set_ref": "blind_battle_textures_v1",
            "size_profile_ref": "bvb_oop_pfr_v1",
            "applies_to_matchups": ["SB_vs_BB"],
            "planned_expansion_matchups": ["SB_vs_BB_limped_branches_later"],
            "line_prefix": "flop.srp.bvb.sb-pfr",
            "board_size_policy": {
                "HIGH_CARD_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]}
            },
            "board_turn_seed_policy": {
                "HIGH_CARD_STATIC": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]}
            },
        },
        "bvb_defender_flop": {
            "template_ref": "oop_pfr_open_action_v1",
            "hero_role": "bb_caller",
            "villain_role": "sb_pfr",
            "street": "flop",
            "pot_type": "single_raised_pot",
            "board_bucket_set_ref": "blind_battle_textures_v1",
            "size_profile_ref": "bvb_oop_pfr_v1",
            "applies_to_matchups": ["BB_vs_SB"],
            "planned_expansion_matchups": ["BB_vs_SB_limped_branches_later"],
            "line_prefix": "flop.srp.bvb.bb-defender",
            "board_size_policy": {
                "HIGH_CARD_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]}
            },
            "board_turn_seed_policy": {
                "HIGH_CARD_STATIC": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]}
            },
        },
        "three_bet_ip_3bettor_flop": {
            "template_ref": "checked_to_ip_aggressor_v1",
            "hero_role": "ip_3bettor",
            "villain_role": "oop_caller",
            "street": "flop",
            "pot_type": "three_bet_pot",
            "board_bucket_set_ref": "three_bet_textures_v1",
            "size_profile_ref": "three_bet_checked_to_ip_v1",
            "applies_to_matchups": ["CO_3bets_vs_HJ", "BTN_3bets_vs_CO", "BTN_3bets_vs_HJ"],
            "planned_expansion_matchups": ["BTN_3bets_vs_UTG", "CO_3bets_vs_UTG"],
            "line_prefix": "flop.3bp.ip-3bettor",
            "board_size_policy": {
                "ACE_HIGH": {"remove_size_refs": ["bet_big"]},
                "KING_HIGH": {"remove_size_refs": ["bet_big"]},
                "LOW_STATIC": {"remove_size_refs": ["bet_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big"]}
            },
            "board_turn_seed_policy": {
                "ACE_HIGH": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "KING_HIGH": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "LOW_STATIC": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]}
            },
        },
        "three_bet_oop_3bettor_flop": {
            "template_ref": "oop_pfr_open_action_v1",
            "hero_role": "oop_3bettor",
            "villain_role": "ip_caller",
            "street": "flop",
            "pot_type": "three_bet_pot",
            "board_bucket_set_ref": "three_bet_textures_v1",
            "size_profile_ref": "three_bet_oop_pfr_v1",
            "applies_to_matchups": ["SB_3bets_vs_BTN", "BB_3bets_vs_BTN"],
            "planned_expansion_matchups": ["SB_3bets_vs_CO", "BB_3bets_vs_CO", "SB_3bets_vs_HJ"],
            "line_prefix": "flop.3bp.oop-3bettor",
            "board_size_policy": {
                "ACE_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "KING_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "LOW_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]}
            },
            "board_turn_seed_policy": {
                "ACE_HIGH": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "KING_HIGH": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "LOW_STATIC": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]}
            },
        },
        "multiway_srp_3way_oop_aggressor_flop": {
            "template_ref": "multiway_oop_aggressor_open_action_v1",
            "hero_role": "participant",
            "villain_role": "multiway_field",
            "street": "flop",
            "pot_type": "single_raised_pot_multiway",
            "board_bucket_set_ref": "core_flop_textures_v1",
            "size_profile_ref": "multiway_srp_v1",
            "applies_to_matchups": ["multiway_srp_3way_oop_aggressor"],
            "planned_expansion_matchups": ["multiway_pfr_oop_3way"],
            "line_prefix": "flop.multiway.srp.3way.oop-aggressor",
            "board_size_policy": {
                "A_HIGH_DRY": {"remove_size_refs": ["bet_big"]},
                "BROADWAY_STATIC": {"remove_size_refs": ["bet_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big"]}
            },
            "board_turn_seed_policy": {
                "A_HIGH_DRY": {"remove_turn_seed_ids": ["turn_seed_oop_aggressor_big_called", "turn_seed_oop_aggressor_big_raise_called", "turn_seed_field_stab_big_called"]},
                "BROADWAY_STATIC": {"remove_turn_seed_ids": ["turn_seed_oop_aggressor_big_called", "turn_seed_oop_aggressor_big_raise_called", "turn_seed_field_stab_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_oop_aggressor_big_called", "turn_seed_oop_aggressor_big_raise_called", "turn_seed_field_stab_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_oop_aggressor_big_called", "turn_seed_oop_aggressor_big_raise_called", "turn_seed_field_stab_big_called"]}
            },
        },
        "multiway_srp_3way_middle_aggressor_flop": {
            "template_ref": "multiway_field_lead_or_check_to_aggressor_v1",
            "hero_role": "participant",
            "villain_role": "multiway_field",
            "street": "flop",
            "pot_type": "single_raised_pot_multiway",
            "board_bucket_set_ref": "core_flop_textures_v1",
            "size_profile_ref": "multiway_srp_v1",
            "applies_to_matchups": ["multiway_srp_3way_middle_aggressor"],
            "planned_expansion_matchups": ["multiway_caller_first_action_3way"],
            "line_prefix": "flop.multiway.srp.3way.middle-aggressor",
            "board_action_policy": {
                "oop_lead_enabled_on": ["MID_CONNECTED", "MONOTONE", "TWO_TONE"],
                "oop_lead_discouraged_on": ["A_HIGH_DRY", "BROADWAY_STATIC", "PAIRED"],
                "notes": ["3-way SRP middle-position aggressor spots can support selective field leads on dynamic boards."]
            },
            "board_size_policy": {
                "A_HIGH_DRY": {"remove_size_refs": ["bet_big", "probe_big"]},
                "BROADWAY_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]}
            },
            "board_turn_seed_policy": {
                "A_HIGH_DRY": {"remove_turn_seed_ids": ["turn_seed_multiway_big_called", "turn_seed_multiway_big_raise_called", "turn_seed_multiway_field_lead_big_called"]},
                "BROADWAY_STATIC": {"remove_turn_seed_ids": ["turn_seed_multiway_big_called", "turn_seed_multiway_big_raise_called", "turn_seed_multiway_field_lead_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_multiway_big_called", "turn_seed_multiway_big_raise_called", "turn_seed_multiway_field_lead_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_multiway_big_called", "turn_seed_multiway_big_raise_called", "turn_seed_multiway_field_lead_big_called"]}
            },
        },
        "multiway_srp_3way_ip_aggressor_flop": {
            "template_ref": "multiway_two_fields_before_ip_aggressor_v1",
            "hero_role": "participant",
            "villain_role": "multiway_field",
            "street": "flop",
            "pot_type": "single_raised_pot_multiway",
            "board_bucket_set_ref": "core_flop_textures_v1",
            "size_profile_ref": "multiway_srp_v1",
            "applies_to_matchups": ["multiway_srp_3way_ip_aggressor"],
            "planned_expansion_matchups": ["multiway_ip_pfr_last_to_act_3way"],
            "line_prefix": "flop.multiway.srp.3way.ip-aggressor",
            "board_action_policy": {
                "oop_lead_enabled_on": ["MID_CONNECTED", "MONOTONE", "TWO_TONE"],
                "oop_lead_discouraged_on": ["A_HIGH_DRY", "BROADWAY_STATIC", "PAIRED"],
                "notes": ["3-way SRP IP-aggressor spots should allow selective first-field and second-field lead branches before the aggressor acts."]
            },
            "board_size_policy": {
                "A_HIGH_DRY": {"remove_size_refs": ["bet_big", "probe_big"]},
                "BROADWAY_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]}
            },
            "board_turn_seed_policy": {
                "A_HIGH_DRY": {"remove_turn_seed_ids": ["turn_seed_ip_aggressor_big_called", "turn_seed_ip_aggressor_big_raise_called", "turn_seed_first_field_big_called", "turn_seed_second_field_big_called"]},
                "BROADWAY_STATIC": {"remove_turn_seed_ids": ["turn_seed_ip_aggressor_big_called", "turn_seed_ip_aggressor_big_raise_called", "turn_seed_first_field_big_called", "turn_seed_second_field_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_ip_aggressor_big_called", "turn_seed_ip_aggressor_big_raise_called", "turn_seed_first_field_big_called", "turn_seed_second_field_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_ip_aggressor_big_called", "turn_seed_ip_aggressor_big_raise_called", "turn_seed_first_field_big_called", "turn_seed_second_field_big_called"]}
            },
        },
        "multiway_srp_4plus_flop": {
            "template_ref": "bucket_only_v1",
            "hero_role": "participant",
            "villain_role": "multiway_field",
            "street": "flop",
            "pot_type": "single_raised_pot_multiway",
            "board_bucket_set_ref": "core_flop_textures_v1",
            "size_profile_ref": "bucket_only",
            "applies_to_matchups": ["multiway_srp_4plus"],
            "planned_expansion_matchups": ["multiway_caller_first_action_4plus", "multiway_iso_raised_later"],
            "line_prefix": "flop.multiway.srp.4plus",
        },
        "multiway_3bp_3way_oop_aggressor_flop": {
            "template_ref": "multiway_oop_aggressor_open_action_v1",
            "hero_role": "participant",
            "villain_role": "multiway_field",
            "street": "flop",
            "pot_type": "three_bet_pot_multiway",
            "board_bucket_set_ref": "three_bet_textures_v1",
            "size_profile_ref": "multiway_3bp_v1",
            "applies_to_matchups": ["multiway_3bp_3way_oop_aggressor"],
            "planned_expansion_matchups": ["multiway_squeezed_3way"],
            "line_prefix": "flop.multiway.3bp.3way.oop-aggressor",
            "board_size_policy": {
                "ACE_HIGH": {"remove_size_refs": ["bet_big"]},
                "KING_HIGH": {"remove_size_refs": ["bet_big"]},
                "LOW_STATIC": {"remove_size_refs": ["bet_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big"]}
            },
            "board_turn_seed_policy": {
                "ACE_HIGH": {"remove_turn_seed_ids": ["turn_seed_oop_aggressor_big_called", "turn_seed_oop_aggressor_big_raise_called", "turn_seed_field_stab_big_called"]},
                "KING_HIGH": {"remove_turn_seed_ids": ["turn_seed_oop_aggressor_big_called", "turn_seed_oop_aggressor_big_raise_called", "turn_seed_field_stab_big_called"]},
                "LOW_STATIC": {"remove_turn_seed_ids": ["turn_seed_oop_aggressor_big_called", "turn_seed_oop_aggressor_big_raise_called", "turn_seed_field_stab_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_oop_aggressor_big_called", "turn_seed_oop_aggressor_big_raise_called", "turn_seed_field_stab_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_oop_aggressor_big_called", "turn_seed_oop_aggressor_big_raise_called", "turn_seed_field_stab_big_called"]}
            },
        },
        "multiway_3bp_3way_middle_aggressor_flop": {
            "template_ref": "multiway_field_lead_or_check_to_aggressor_v1",
            "hero_role": "participant",
            "villain_role": "multiway_field",
            "street": "flop",
            "pot_type": "three_bet_pot_multiway",
            "board_bucket_set_ref": "three_bet_textures_v1",
            "size_profile_ref": "multiway_3bp_v1",
            "applies_to_matchups": ["multiway_3bp_3way_middle_aggressor"],
            "planned_expansion_matchups": ["multiway_squeezed_3way"],
            "line_prefix": "flop.multiway.3bp.3way.middle-aggressor",
            "board_action_policy": {
                "oop_lead_enabled_on": ["MID_DYNAMIC", "MONOTONE"],
                "oop_lead_discouraged_on": ["ACE_HIGH", "KING_HIGH", "LOW_STATIC", "PAIRED"],
                "notes": ["3-way 3-bet-pot middle-position aggressor spots should keep lead branches narrow and texture-dependent."]
            },
            "board_size_policy": {
                "ACE_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "KING_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "LOW_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]}
            },
            "board_turn_seed_policy": {
                "ACE_HIGH": {"remove_turn_seed_ids": ["turn_seed_multiway_big_called", "turn_seed_multiway_big_raise_called", "turn_seed_multiway_field_lead_big_called"]},
                "KING_HIGH": {"remove_turn_seed_ids": ["turn_seed_multiway_big_called", "turn_seed_multiway_big_raise_called", "turn_seed_multiway_field_lead_big_called"]},
                "LOW_STATIC": {"remove_turn_seed_ids": ["turn_seed_multiway_big_called", "turn_seed_multiway_big_raise_called", "turn_seed_multiway_field_lead_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_multiway_big_called", "turn_seed_multiway_big_raise_called", "turn_seed_multiway_field_lead_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_multiway_big_called", "turn_seed_multiway_big_raise_called", "turn_seed_multiway_field_lead_big_called"]}
            },
        },
        "multiway_3bp_3way_ip_aggressor_flop": {
            "template_ref": "multiway_two_fields_before_ip_aggressor_v1",
            "hero_role": "participant",
            "villain_role": "multiway_field",
            "street": "flop",
            "pot_type": "three_bet_pot_multiway",
            "board_bucket_set_ref": "three_bet_textures_v1",
            "size_profile_ref": "multiway_3bp_v1",
            "applies_to_matchups": ["multiway_3bp_3way_ip_aggressor"],
            "planned_expansion_matchups": ["multiway_squeezed_3way"],
            "line_prefix": "flop.multiway.3bp.3way.ip-aggressor",
            "board_action_policy": {
                "oop_lead_enabled_on": ["MID_DYNAMIC", "MONOTONE"],
                "oop_lead_discouraged_on": ["ACE_HIGH", "KING_HIGH", "LOW_STATIC", "PAIRED"],
                "notes": ["3-way 3-bet-pot IP-aggressor spots should allow only narrow field lead branches before the aggressor acts."]
            },
            "board_size_policy": {
                "ACE_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "KING_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "LOW_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]}
            },
            "board_turn_seed_policy": {
                "ACE_HIGH": {"remove_turn_seed_ids": ["turn_seed_ip_aggressor_big_called", "turn_seed_ip_aggressor_big_raise_called", "turn_seed_first_field_big_called", "turn_seed_second_field_big_called"]},
                "KING_HIGH": {"remove_turn_seed_ids": ["turn_seed_ip_aggressor_big_called", "turn_seed_ip_aggressor_big_raise_called", "turn_seed_first_field_big_called", "turn_seed_second_field_big_called"]},
                "LOW_STATIC": {"remove_turn_seed_ids": ["turn_seed_ip_aggressor_big_called", "turn_seed_ip_aggressor_big_raise_called", "turn_seed_first_field_big_called", "turn_seed_second_field_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_ip_aggressor_big_called", "turn_seed_ip_aggressor_big_raise_called", "turn_seed_first_field_big_called", "turn_seed_second_field_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_ip_aggressor_big_called", "turn_seed_ip_aggressor_big_raise_called", "turn_seed_first_field_big_called", "turn_seed_second_field_big_called"]}
            },
        },
        "multiway_3bp_4plus_flop": {
            "template_ref": "bucket_only_v1",
            "hero_role": "participant",
            "villain_role": "multiway_field",
            "street": "flop",
            "pot_type": "three_bet_pot_multiway",
            "board_bucket_set_ref": "three_bet_textures_v1",
            "size_profile_ref": "bucket_only",
            "applies_to_matchups": ["multiway_3bp_4plus"],
            "planned_expansion_matchups": ["squeezed_multiway_3bp"],
            "line_prefix": "flop.multiway.3bp.4plus",
        },
        "limped_pot_heads_up_flop": {
            "template_ref": "limped_heads_up_neutral_v1",
            "hero_role": "participant",
            "villain_role": "limped_field",
            "street": "flop",
            "pot_type": "limped_pot_heads_up",
            "board_bucket_set_ref": "core_flop_textures_v1",
            "size_profile_ref": "limped_heads_up_v1",
            "applies_to_matchups": ["limped_pot_2way"],
            "planned_expansion_matchups": ["limped_bvb_heads_up_exact_roles"],
            "line_prefix": "flop.limped.heads-up",
            "board_size_policy": {
                "A_HIGH_DRY": {"remove_size_refs": ["bet_big", "probe_big"]},
                "BROADWAY_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]}
            },
            "board_turn_seed_policy": {
                "A_HIGH_DRY": {"remove_turn_seed_ids": ["turn_seed_limped_big_called", "turn_seed_limped_big_raise_called", "turn_seed_limped_probe_big_called"]},
                "BROADWAY_STATIC": {"remove_turn_seed_ids": ["turn_seed_limped_big_called", "turn_seed_limped_big_raise_called", "turn_seed_limped_probe_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_limped_big_called", "turn_seed_limped_big_raise_called", "turn_seed_limped_probe_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_limped_big_called", "turn_seed_limped_big_raise_called", "turn_seed_limped_probe_big_called"]}
            },
        },
        "limped_pot_multiway_flop": {
            "template_ref": "bucket_only_v1",
            "hero_role": "participant",
            "villain_role": "limped_field",
            "street": "flop",
            "pot_type": "limped_pot_multiway",
            "board_bucket_set_ref": "core_flop_textures_v1",
            "size_profile_ref": "bucket_only",
            "applies_to_matchups": ["limped_pot_3way", "limped_pot_4plus"],
            "planned_expansion_matchups": ["limped_pot_3way_exact_roles", "limped_pot_4plus_exact_roles"],
            "line_prefix": "flop.limped.multiway",
        },
        "raised_after_limp_ip_aggressor_flop": {
            "template_ref": "oop_lead_or_check_to_ip_aggressor_v1",
            "hero_role": "participant",
            "villain_role": "raised_after_limp_field",
            "street": "flop",
            "pot_type": "raised_after_limp_heads_up",
            "board_bucket_set_ref": "core_flop_textures_v1",
            "size_profile_ref": "multiway_srp_v1",
            "applies_to_matchups": ["iso_limped_pot_ip_aggressor", "raised_after_limp_ip_aggressor"],
            "planned_expansion_matchups": ["heads_up_raised_after_limp_exact_ip_roles"],
            "line_prefix": "flop.limped.raised.ip-aggressor",
            "board_action_policy": {
                "oop_lead_enabled_on": ["MID_CONNECTED", "MONOTONE", "TWO_TONE"],
                "oop_lead_discouraged_on": ["A_HIGH_DRY", "PAIRED"],
                "notes": ["Limped-then-raised heads-up donk branches are more credible on dynamic boards than on static high-card boards."]
            },
            "board_size_policy": {
                "A_HIGH_DRY": {"remove_size_refs": ["bet_big", "probe_big"]},
                "BROADWAY_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]}
            },
            "board_turn_seed_policy": {
                "A_HIGH_DRY": {"remove_turn_seed_ids": ["turn_seed_ip_big_called", "turn_seed_ip_big_raise_called", "turn_seed_oop_lead_big_called"]},
                "BROADWAY_STATIC": {"remove_turn_seed_ids": ["turn_seed_ip_big_called", "turn_seed_ip_big_raise_called", "turn_seed_oop_lead_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_ip_big_called", "turn_seed_ip_big_raise_called", "turn_seed_oop_lead_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_ip_big_called", "turn_seed_ip_big_raise_called", "turn_seed_oop_lead_big_called"]}
            },
        },
        "raised_after_limp_oop_aggressor_flop": {
            "template_ref": "oop_pfr_open_action_v1",
            "hero_role": "participant",
            "villain_role": "raised_after_limp_field",
            "street": "flop",
            "pot_type": "raised_after_limp_heads_up",
            "board_bucket_set_ref": "core_flop_textures_v1",
            "size_profile_ref": "multiway_srp_v1",
            "applies_to_matchups": ["iso_limped_pot_oop_aggressor", "raised_after_limp_oop_aggressor"],
            "planned_expansion_matchups": ["heads_up_raised_after_limp_exact_oop_roles"],
            "line_prefix": "flop.limped.raised.oop-aggressor",
            "board_size_policy": {
                "A_HIGH_DRY": {"remove_size_refs": ["bet_big", "probe_big"]},
                "BROADWAY_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]}
            },
            "board_turn_seed_policy": {
                "A_HIGH_DRY": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "BROADWAY_STATIC": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]}
            },
        },
        "raised_after_limp_3way_oop_aggressor_flop": {
            "template_ref": "multiway_oop_aggressor_open_action_v1",
            "hero_role": "participant",
            "villain_role": "raised_after_limp_field",
            "street": "flop",
            "pot_type": "raised_after_limp_multiway",
            "board_bucket_set_ref": "core_flop_textures_v1",
            "size_profile_ref": "multiway_srp_v1",
            "applies_to_matchups": ["raised_after_limp_3way_oop_aggressor"],
            "planned_expansion_matchups": ["raised_after_limp_3way_exact_roles"],
            "line_prefix": "flop.limped.raised.3way.oop-aggressor",
            "board_size_policy": {
                "A_HIGH_DRY": {"remove_size_refs": ["bet_big"]},
                "BROADWAY_STATIC": {"remove_size_refs": ["bet_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big"]}
            },
            "board_turn_seed_policy": {
                "A_HIGH_DRY": {"remove_turn_seed_ids": ["turn_seed_oop_aggressor_big_called", "turn_seed_oop_aggressor_big_raise_called", "turn_seed_field_stab_big_called"]},
                "BROADWAY_STATIC": {"remove_turn_seed_ids": ["turn_seed_oop_aggressor_big_called", "turn_seed_oop_aggressor_big_raise_called", "turn_seed_field_stab_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_oop_aggressor_big_called", "turn_seed_oop_aggressor_big_raise_called", "turn_seed_field_stab_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_oop_aggressor_big_called", "turn_seed_oop_aggressor_big_raise_called", "turn_seed_field_stab_big_called"]}
            },
        },
        "raised_after_limp_3way_middle_aggressor_flop": {
            "template_ref": "multiway_field_lead_or_check_to_aggressor_v1",
            "hero_role": "participant",
            "villain_role": "raised_after_limp_field",
            "street": "flop",
            "pot_type": "raised_after_limp_multiway",
            "board_bucket_set_ref": "core_flop_textures_v1",
            "size_profile_ref": "multiway_srp_v1",
            "applies_to_matchups": ["raised_after_limp_3way_middle_aggressor"],
            "planned_expansion_matchups": ["raised_after_limp_3way_exact_roles"],
            "line_prefix": "flop.limped.raised.3way.middle-aggressor",
            "board_action_policy": {
                "oop_lead_enabled_on": ["MID_CONNECTED", "MONOTONE", "TWO_TONE"],
                "oop_lead_discouraged_on": ["A_HIGH_DRY", "PAIRED"],
                "notes": ["3-way raised-after-limp middle-aggressor spots should allow selective field leads, not universal donks."]
            },
            "board_size_policy": {
                "A_HIGH_DRY": {"remove_size_refs": ["bet_big", "probe_big"]},
                "BROADWAY_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]}
            },
            "board_turn_seed_policy": {
                "A_HIGH_DRY": {"remove_turn_seed_ids": ["turn_seed_multiway_big_called", "turn_seed_multiway_big_raise_called", "turn_seed_multiway_field_lead_big_called"]},
                "BROADWAY_STATIC": {"remove_turn_seed_ids": ["turn_seed_multiway_big_called", "turn_seed_multiway_big_raise_called", "turn_seed_multiway_field_lead_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_multiway_big_called", "turn_seed_multiway_big_raise_called", "turn_seed_multiway_field_lead_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_multiway_big_called", "turn_seed_multiway_big_raise_called", "turn_seed_multiway_field_lead_big_called"]}
            },
        },
        "raised_after_limp_3way_ip_aggressor_flop": {
            "template_ref": "multiway_two_fields_before_ip_aggressor_v1",
            "hero_role": "participant",
            "villain_role": "raised_after_limp_field",
            "street": "flop",
            "pot_type": "raised_after_limp_multiway",
            "board_bucket_set_ref": "core_flop_textures_v1",
            "size_profile_ref": "multiway_srp_v1",
            "applies_to_matchups": ["raised_after_limp_3way_ip_aggressor"],
            "planned_expansion_matchups": ["raised_after_limp_3way_exact_roles"],
            "line_prefix": "flop.limped.raised.3way.ip-aggressor",
            "board_action_policy": {
                "oop_lead_enabled_on": ["MID_CONNECTED", "MONOTONE", "TWO_TONE"],
                "oop_lead_discouraged_on": ["A_HIGH_DRY", "PAIRED"],
                "notes": ["3-way raised-after-limp IP-aggressor spots should permit early-field leads only on dynamic textures."]
            },
            "board_size_policy": {
                "A_HIGH_DRY": {"remove_size_refs": ["bet_big", "probe_big"]},
                "BROADWAY_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]}
            },
            "board_turn_seed_policy": {
                "A_HIGH_DRY": {"remove_turn_seed_ids": ["turn_seed_ip_aggressor_big_called", "turn_seed_ip_aggressor_big_raise_called", "turn_seed_first_field_big_called", "turn_seed_second_field_big_called"]},
                "BROADWAY_STATIC": {"remove_turn_seed_ids": ["turn_seed_ip_aggressor_big_called", "turn_seed_ip_aggressor_big_raise_called", "turn_seed_first_field_big_called", "turn_seed_second_field_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_ip_aggressor_big_called", "turn_seed_ip_aggressor_big_raise_called", "turn_seed_first_field_big_called", "turn_seed_second_field_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_ip_aggressor_big_called", "turn_seed_ip_aggressor_big_raise_called", "turn_seed_first_field_big_called", "turn_seed_second_field_big_called"]}
            },
        },
        "raised_after_limp_multiway_flop": {
            "template_ref": "bucket_only_v1",
            "hero_role": "participant",
            "villain_role": "raised_after_limp_field",
            "street": "flop",
            "pot_type": "raised_after_limp_multiway",
            "board_bucket_set_ref": "core_flop_textures_v1",
            "size_profile_ref": "bucket_only",
            "applies_to_matchups": ["overcalled_srp_4plus", "raised_after_limp_multiway"],
            "planned_expansion_matchups": ["overcalled_srp_exact_roles", "raised_after_limp_multiway_exact_roles"],
            "line_prefix": "flop.limped.raised.multiway",
        },
        "four_bet_ip_aggressor_flop": {
            "template_ref": "oop_lead_or_check_to_ip_aggressor_v1",
            "hero_role": "participant",
            "villain_role": "four_bet_field",
            "street": "flop",
            "pot_type": "four_bet_pot_heads_up",
            "board_bucket_set_ref": "three_bet_textures_v1",
            "size_profile_ref": "four_bet_heads_up_v1",
            "applies_to_matchups": ["four_bet_pot_ip_aggressor"],
            "planned_expansion_matchups": ["four_bet_exact_ip_roles"],
            "line_prefix": "flop.4bp.ip-aggressor",
            "board_action_policy": {
                "oop_lead_enabled_on": ["MID_DYNAMIC", "MONOTONE"],
                "oop_lead_discouraged_on": ["ACE_HIGH", "KING_HIGH", "LOW_STATIC", "PAIRED"],
                "notes": ["4-bet-pot OOP leads should be rare and concentrated on low or flush-compressed textures."]
            },
            "board_size_policy": {
                "ACE_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "KING_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "LOW_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]}
            },
            "board_turn_seed_policy": {
                "ACE_HIGH": {"remove_turn_seed_ids": ["turn_seed_ip_big_called", "turn_seed_ip_big_raise_called", "turn_seed_oop_lead_big_called"]},
                "KING_HIGH": {"remove_turn_seed_ids": ["turn_seed_ip_big_called", "turn_seed_ip_big_raise_called", "turn_seed_oop_lead_big_called"]},
                "LOW_STATIC": {"remove_turn_seed_ids": ["turn_seed_ip_big_called", "turn_seed_ip_big_raise_called", "turn_seed_oop_lead_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_ip_big_called", "turn_seed_ip_big_raise_called", "turn_seed_oop_lead_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_ip_big_called", "turn_seed_ip_big_raise_called", "turn_seed_oop_lead_big_called"]}
            },
        },
        "four_bet_oop_aggressor_flop": {
            "template_ref": "oop_pfr_open_action_v1",
            "hero_role": "participant",
            "villain_role": "four_bet_field",
            "street": "flop",
            "pot_type": "four_bet_pot_heads_up",
            "board_bucket_set_ref": "three_bet_textures_v1",
            "size_profile_ref": "four_bet_heads_up_v1",
            "applies_to_matchups": ["four_bet_pot_oop_aggressor"],
            "planned_expansion_matchups": ["four_bet_exact_oop_roles"],
            "line_prefix": "flop.4bp.oop-aggressor",
            "board_size_policy": {
                "ACE_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "KING_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "LOW_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]}
            },
            "board_turn_seed_policy": {
                "ACE_HIGH": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "KING_HIGH": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "LOW_STATIC": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]}
            },
        },
        "four_bet_3way_oop_aggressor_flop": {
            "template_ref": "multiway_oop_aggressor_open_action_v1",
            "hero_role": "participant",
            "villain_role": "four_bet_field",
            "street": "flop",
            "pot_type": "four_bet_pot_multiway",
            "board_bucket_set_ref": "three_bet_textures_v1",
            "size_profile_ref": "four_bet_heads_up_v1",
            "applies_to_matchups": ["four_bet_3way_oop_aggressor"],
            "planned_expansion_matchups": ["four_bet_multiway_exact_roles"],
            "line_prefix": "flop.4bp.3way.oop-aggressor",
            "board_size_policy": {
                "ACE_HIGH": {"remove_size_refs": ["bet_big"]},
                "KING_HIGH": {"remove_size_refs": ["bet_big"]},
                "LOW_STATIC": {"remove_size_refs": ["bet_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big"]}
            },
            "board_turn_seed_policy": {
                "ACE_HIGH": {"remove_turn_seed_ids": ["turn_seed_oop_aggressor_big_called", "turn_seed_oop_aggressor_big_raise_called", "turn_seed_field_stab_big_called"]},
                "KING_HIGH": {"remove_turn_seed_ids": ["turn_seed_oop_aggressor_big_called", "turn_seed_oop_aggressor_big_raise_called", "turn_seed_field_stab_big_called"]},
                "LOW_STATIC": {"remove_turn_seed_ids": ["turn_seed_oop_aggressor_big_called", "turn_seed_oop_aggressor_big_raise_called", "turn_seed_field_stab_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_oop_aggressor_big_called", "turn_seed_oop_aggressor_big_raise_called", "turn_seed_field_stab_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_oop_aggressor_big_called", "turn_seed_oop_aggressor_big_raise_called", "turn_seed_field_stab_big_called"]}
            },
        },
        "four_bet_3way_middle_aggressor_flop": {
            "template_ref": "multiway_field_lead_or_check_to_aggressor_v1",
            "hero_role": "participant",
            "villain_role": "four_bet_field",
            "street": "flop",
            "pot_type": "four_bet_pot_multiway",
            "board_bucket_set_ref": "three_bet_textures_v1",
            "size_profile_ref": "four_bet_heads_up_v1",
            "applies_to_matchups": ["four_bet_3way_middle_aggressor"],
            "planned_expansion_matchups": ["four_bet_multiway_exact_roles"],
            "line_prefix": "flop.4bp.3way.middle-aggressor",
            "board_action_policy": {
                "oop_lead_enabled_on": ["MID_DYNAMIC", "MONOTONE"],
                "oop_lead_discouraged_on": ["ACE_HIGH", "KING_HIGH", "LOW_STATIC", "PAIRED"],
                "notes": ["3-way 4-bet-pot middle-aggressor field leads should stay rare and texture-selective."]
            },
            "board_size_policy": {
                "ACE_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "KING_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "LOW_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]}
            },
            "board_turn_seed_policy": {
                "ACE_HIGH": {"remove_turn_seed_ids": ["turn_seed_multiway_big_called", "turn_seed_multiway_big_raise_called", "turn_seed_multiway_field_lead_big_called"]},
                "KING_HIGH": {"remove_turn_seed_ids": ["turn_seed_multiway_big_called", "turn_seed_multiway_big_raise_called", "turn_seed_multiway_field_lead_big_called"]},
                "LOW_STATIC": {"remove_turn_seed_ids": ["turn_seed_multiway_big_called", "turn_seed_multiway_big_raise_called", "turn_seed_multiway_field_lead_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_multiway_big_called", "turn_seed_multiway_big_raise_called", "turn_seed_multiway_field_lead_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_multiway_big_called", "turn_seed_multiway_big_raise_called", "turn_seed_multiway_field_lead_big_called"]}
            },
        },
        "four_bet_3way_ip_aggressor_flop": {
            "template_ref": "multiway_two_fields_before_ip_aggressor_v1",
            "hero_role": "participant",
            "villain_role": "four_bet_field",
            "street": "flop",
            "pot_type": "four_bet_pot_multiway",
            "board_bucket_set_ref": "three_bet_textures_v1",
            "size_profile_ref": "four_bet_heads_up_v1",
            "applies_to_matchups": ["four_bet_3way_ip_aggressor"],
            "planned_expansion_matchups": ["four_bet_multiway_exact_roles"],
            "line_prefix": "flop.4bp.3way.ip-aggressor",
            "board_action_policy": {
                "oop_lead_enabled_on": ["MID_DYNAMIC", "MONOTONE"],
                "oop_lead_discouraged_on": ["ACE_HIGH", "KING_HIGH", "LOW_STATIC", "PAIRED"],
                "notes": ["3-way 4-bet-pot IP-aggressor spots should only keep narrow early-field lead branches."]
            },
            "board_size_policy": {
                "ACE_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "KING_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "LOW_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]}
            },
            "board_turn_seed_policy": {
                "ACE_HIGH": {"remove_turn_seed_ids": ["turn_seed_ip_aggressor_big_called", "turn_seed_ip_aggressor_big_raise_called", "turn_seed_first_field_big_called", "turn_seed_second_field_big_called"]},
                "KING_HIGH": {"remove_turn_seed_ids": ["turn_seed_ip_aggressor_big_called", "turn_seed_ip_aggressor_big_raise_called", "turn_seed_first_field_big_called", "turn_seed_second_field_big_called"]},
                "LOW_STATIC": {"remove_turn_seed_ids": ["turn_seed_ip_aggressor_big_called", "turn_seed_ip_aggressor_big_raise_called", "turn_seed_first_field_big_called", "turn_seed_second_field_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_ip_aggressor_big_called", "turn_seed_ip_aggressor_big_raise_called", "turn_seed_first_field_big_called", "turn_seed_second_field_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_ip_aggressor_big_called", "turn_seed_ip_aggressor_big_raise_called", "turn_seed_first_field_big_called", "turn_seed_second_field_big_called"]}
            },
        },
        "four_bet_multiway_flop": {
            "template_ref": "bucket_only_v1",
            "hero_role": "participant",
            "villain_role": "four_bet_field",
            "street": "flop",
            "pot_type": "four_bet_pot_multiway",
            "board_bucket_set_ref": "three_bet_textures_v1",
            "size_profile_ref": "bucket_only",
            "applies_to_matchups": ["four_bet_pot_multiway"],
            "planned_expansion_matchups": ["four_bet_multiway_exact_roles"],
            "line_prefix": "flop.4bp.multiway",
        },
        "five_bet_plus_ip_aggressor_flop": {
            "template_ref": "oop_lead_or_check_to_ip_aggressor_v1",
            "hero_role": "participant",
            "villain_role": "five_bet_plus_field",
            "street": "flop",
            "pot_type": "five_bet_plus_heads_up",
            "board_bucket_set_ref": "three_bet_textures_v1",
            "size_profile_ref": "four_bet_heads_up_v1",
            "applies_to_matchups": ["five_bet_plus_ip_aggressor"],
            "planned_expansion_matchups": ["five_bet_plus_multiway"],
            "line_prefix": "flop.5bpplus.ip-aggressor",
            "board_action_policy": {
                "oop_lead_enabled_on": ["MID_DYNAMIC", "MONOTONE"],
                "oop_lead_discouraged_on": ["ACE_HIGH", "KING_HIGH", "LOW_STATIC", "PAIRED"],
                "notes": ["5-bet-plus OOP leads should be the narrowest donk subset in the current library."]
            },
            "board_size_policy": {
                "ACE_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "KING_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "LOW_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]}
            },
            "board_turn_seed_policy": {
                "ACE_HIGH": {"remove_turn_seed_ids": ["turn_seed_ip_big_called", "turn_seed_ip_big_raise_called", "turn_seed_oop_lead_big_called"]},
                "KING_HIGH": {"remove_turn_seed_ids": ["turn_seed_ip_big_called", "turn_seed_ip_big_raise_called", "turn_seed_oop_lead_big_called"]},
                "LOW_STATIC": {"remove_turn_seed_ids": ["turn_seed_ip_big_called", "turn_seed_ip_big_raise_called", "turn_seed_oop_lead_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_ip_big_called", "turn_seed_ip_big_raise_called", "turn_seed_oop_lead_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_ip_big_called", "turn_seed_ip_big_raise_called", "turn_seed_oop_lead_big_called"]}
            },
        },
        "five_bet_plus_oop_aggressor_flop": {
            "template_ref": "oop_pfr_open_action_v1",
            "hero_role": "participant",
            "villain_role": "five_bet_plus_field",
            "street": "flop",
            "pot_type": "five_bet_plus_heads_up",
            "board_bucket_set_ref": "three_bet_textures_v1",
            "size_profile_ref": "four_bet_heads_up_v1",
            "applies_to_matchups": ["five_bet_plus_oop_aggressor"],
            "planned_expansion_matchups": ["five_bet_plus_multiway"],
            "line_prefix": "flop.5bpplus.oop-aggressor",
            "board_size_policy": {
                "ACE_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "KING_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "LOW_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]}
            },
            "board_turn_seed_policy": {
                "ACE_HIGH": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "KING_HIGH": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "LOW_STATIC": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "PAIRED": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]},
                "MONOTONE": {"remove_turn_seed_ids": ["turn_seed_big_called", "turn_seed_probe_big_called", "turn_seed_small_raise_big_called", "turn_seed_big_raise_small_called", "turn_seed_big_raise_big_called"]}
            },
        },
    },
    "matchup_instances": {
        "EP_open_vs_BB_defend": {
            "family_ref": "srp_ip_pfr_flop",
            "preflop_path": ["EP opens", "BB calls"],
            "positions": {"pfr": "EP", "caller": "BB", "oop": "BB", "ip": "EP"},
            "priority_wave": 2,
            "range_profile_tags": ["grouped_srp", "ep_open", "bb_defend"],
            "board_bucket_biases": ["ace_high", "broadway_static", "paired"],
        },
        "MP_open_vs_BB_defend": {
            "family_ref": "srp_ip_pfr_flop",
            "preflop_path": ["MP opens", "BB calls"],
            "positions": {"pfr": "MP", "caller": "BB", "oop": "BB", "ip": "MP"},
            "priority_wave": 2,
            "range_profile_tags": ["grouped_srp", "mp_open", "bb_defend"],
            "board_bucket_biases": ["queen_high", "middling_connected", "paired"],
        },
        "LP_open_vs_BB_defend": {
            "family_ref": "srp_ip_pfr_flop",
            "preflop_path": ["LP opens", "BB calls"],
            "positions": {"pfr": "LP", "caller": "BB", "oop": "BB", "ip": "LP"},
            "priority_wave": 2,
            "range_profile_tags": ["grouped_srp", "lp_open", "bb_defend"],
            "board_bucket_biases": ["middling_connected", "two_tone", "monotone"],
        },
        "BTN_open_vs_BB_defend": {
            "family_ref": "srp_ip_pfr_flop",
            "preflop_path": ["BTN opens", "BB calls"],
            "positions": {"pfr": "BTN", "caller": "BB", "oop": "BB", "ip": "BTN"},
            "priority_wave": 1,
            "range_profile_tags": ["wide_open", "wide_defend", "high_frequency_anchor"],
            "board_bucket_biases": ["middling_connected", "paired", "monotone"],
        },
        "UTG_open_vs_BB_defend": {
            "family_ref": "srp_ip_pfr_flop",
            "preflop_path": ["UTG opens", "BB calls"],
            "positions": {"pfr": "UTG", "caller": "BB", "oop": "BB", "ip": "UTG"},
            "priority_wave": 1,
            "range_profile_tags": ["tight_open", "wide_defend", "high_card_anchor"],
            "board_bucket_biases": ["ace_high", "broadway_static", "paired"],
        },
        "HJ_open_vs_BB_defend": {
            "family_ref": "srp_ip_pfr_flop",
            "preflop_path": ["HJ opens", "BB calls"],
            "positions": {"pfr": "HJ", "caller": "BB", "oop": "BB", "ip": "HJ"},
            "priority_wave": 1,
            "range_profile_tags": ["medium_tight_open", "wide_defend", "high_frequency_core"],
            "board_bucket_biases": ["queen_high", "middling_connected", "paired"],
        },
        "CO_open_vs_BB_defend": {
            "family_ref": "srp_ip_pfr_flop",
            "preflop_path": ["CO opens", "BB calls"],
            "positions": {"pfr": "CO", "caller": "BB", "oop": "BB", "ip": "CO"},
            "priority_wave": 1,
            "range_profile_tags": ["medium_open", "wide_defend", "anchor_extension"],
            "board_bucket_biases": ["ace_high", "queen_high", "two_tone"],
        },
        "EP_open_vs_SB_flat": {
            "family_ref": "srp_oop_caller_flop",
            "preflop_path": ["EP opens", "SB flats", "BB folds"],
            "positions": {"pfr": "EP", "caller": "SB", "oop": "SB", "ip": "EP"},
            "priority_wave": 2,
            "range_profile_tags": ["grouped_srp", "ep_open", "sb_flat"],
            "board_bucket_biases": ["ace_high", "broadway_static", "paired"],
        },
        "MP_open_vs_SB_flat": {
            "family_ref": "srp_oop_caller_flop",
            "preflop_path": ["MP opens", "SB flats", "BB folds"],
            "positions": {"pfr": "MP", "caller": "SB", "oop": "SB", "ip": "MP"},
            "priority_wave": 2,
            "range_profile_tags": ["grouped_srp", "mp_open", "sb_flat"],
            "board_bucket_biases": ["queen_high", "middling_connected", "paired"],
        },
        "LP_open_vs_SB_flat": {
            "family_ref": "srp_oop_caller_flop",
            "preflop_path": ["LP opens", "SB flats", "BB folds"],
            "positions": {"pfr": "LP", "caller": "SB", "oop": "SB", "ip": "LP"},
            "priority_wave": 2,
            "range_profile_tags": ["grouped_srp", "lp_open", "sb_flat"],
            "board_bucket_biases": ["high_card", "two_tone", "monotone"],
        },
        "BTN_open_vs_SB_flat": {
            "family_ref": "srp_oop_caller_flop",
            "preflop_path": ["BTN opens", "SB flats", "BB folds"],
            "positions": {"pfr": "BTN", "caller": "SB", "oop": "SB", "ip": "BTN"},
            "priority_wave": 2,
            "range_profile_tags": ["late_position_open", "blind_flat", "higher_rake_sensitivity_if_cash"],
            "board_bucket_biases": ["high_card", "monotone", "paired"],
        },
        "UTG_open_vs_SB_flat": {
            "family_ref": "srp_oop_caller_flop",
            "preflop_path": ["UTG opens", "SB flats", "BB folds"],
            "positions": {"pfr": "UTG", "caller": "SB", "oop": "SB", "ip": "UTG"},
            "priority_wave": 2,
            "range_profile_tags": ["tight_open", "tight_blind_flat", "domination_risk"],
            "board_bucket_biases": ["ace_high", "broadway_static", "paired"],
        },
        "HJ_open_vs_SB_flat": {
            "family_ref": "srp_oop_caller_flop",
            "preflop_path": ["HJ opens", "SB flats", "BB folds"],
            "positions": {"pfr": "HJ", "caller": "SB", "oop": "SB", "ip": "HJ"},
            "priority_wave": 2,
            "range_profile_tags": ["medium_tight_open", "blind_flat", "domination_risk"],
            "board_bucket_biases": ["queen_high", "middling_connected", "paired"],
        },
        "CO_open_vs_SB_flat": {
            "family_ref": "srp_oop_caller_flop",
            "preflop_path": ["CO opens", "SB flats", "BB folds"],
            "positions": {"pfr": "CO", "caller": "SB", "oop": "SB", "ip": "CO"},
            "priority_wave": 2,
            "range_profile_tags": ["medium_open", "blind_flat", "late_position_pressure"],
            "board_bucket_biases": ["high_card", "two_tone", "monotone"],
        },
        "EP_open_vs_same_band_later_flat": {
            "family_ref": "srp_oop_pfr_flop",
            "preflop_path": ["EP opens", "later same-band caller flats"],
            "positions": {"pfr": "EP", "caller": "EP_later", "oop": "EP", "ip": "EP_later"},
            "priority_wave": 2,
            "range_profile_tags": ["grouped_srp", "ep_open", "same_band_later_flat"],
            "board_bucket_biases": ["ace_high", "paired", "broadway_static"],
        },
        "EP_open_vs_later_band_flat": {
            "family_ref": "srp_oop_pfr_flop",
            "preflop_path": ["EP opens", "later-band caller flats"],
            "positions": {"pfr": "EP", "caller": "later_band", "oop": "EP", "ip": "later_band"},
            "priority_wave": 2,
            "range_profile_tags": ["grouped_srp", "ep_open", "later_band_flat"],
            "board_bucket_biases": ["ace_high", "broadway_static", "paired"],
        },
        "EP_open_vs_MP_flat": {
            "family_ref": "srp_oop_pfr_flop",
            "preflop_path": ["EP opens", "MP flats"],
            "positions": {"pfr": "EP", "caller": "MP", "oop": "EP", "ip": "MP"},
            "priority_wave": 2,
            "range_profile_tags": ["grouped_srp", "ep_open", "mp_flat"],
            "board_bucket_biases": ["ace_high", "middling_connected", "two_tone"],
        },
        "EP_open_vs_LP_flat": {
            "family_ref": "srp_oop_pfr_flop",
            "preflop_path": ["EP opens", "LP flats"],
            "positions": {"pfr": "EP", "caller": "LP", "oop": "EP", "ip": "LP"},
            "priority_wave": 2,
            "range_profile_tags": ["grouped_srp", "ep_open", "lp_flat"],
            "board_bucket_biases": ["ace_high", "broadway_static", "paired"],
        },
        "EP_open_vs_BTN_flat": {
            "family_ref": "srp_oop_pfr_flop",
            "preflop_path": ["EP opens", "BTN flats"],
            "positions": {"pfr": "EP", "caller": "BTN", "oop": "EP", "ip": "BTN"},
            "priority_wave": 2,
            "range_profile_tags": ["grouped_srp", "ep_open", "btn_flat"],
            "board_bucket_biases": ["ace_high", "king_high", "paired"],
        },
        "MP_open_vs_same_band_later_flat": {
            "family_ref": "srp_oop_pfr_flop",
            "preflop_path": ["MP opens", "later same-band caller flats"],
            "positions": {"pfr": "MP", "caller": "MP_later", "oop": "MP", "ip": "MP_later"},
            "priority_wave": 2,
            "range_profile_tags": ["grouped_srp", "mp_open", "same_band_later_flat"],
            "board_bucket_biases": ["queen_high", "middling_connected", "paired"],
        },
        "MP_open_vs_later_band_flat": {
            "family_ref": "srp_oop_pfr_flop",
            "preflop_path": ["MP opens", "later-band caller flats"],
            "positions": {"pfr": "MP", "caller": "later_band", "oop": "MP", "ip": "later_band"},
            "priority_wave": 2,
            "range_profile_tags": ["grouped_srp", "mp_open", "later_band_flat"],
            "board_bucket_biases": ["queen_high", "two_tone", "monotone"],
        },
        "MP_open_vs_LP_flat": {
            "family_ref": "srp_oop_pfr_flop",
            "preflop_path": ["MP opens", "LP flats"],
            "positions": {"pfr": "MP", "caller": "LP", "oop": "MP", "ip": "LP"},
            "priority_wave": 2,
            "range_profile_tags": ["grouped_srp", "mp_open", "lp_flat"],
            "board_bucket_biases": ["queen_high", "two_tone", "monotone"],
        },
        "MP_open_vs_BTN_flat": {
            "family_ref": "srp_oop_pfr_flop",
            "preflop_path": ["MP opens", "BTN flats"],
            "positions": {"pfr": "MP", "caller": "BTN", "oop": "MP", "ip": "BTN"},
            "priority_wave": 2,
            "range_profile_tags": ["grouped_srp", "mp_open", "btn_flat"],
            "board_bucket_biases": ["queen_high", "middling_connected", "two_tone"],
        },
        "LP_open_vs_BTN_flat": {
            "family_ref": "srp_oop_pfr_flop",
            "preflop_path": ["LP opens", "BTN flats"],
            "positions": {"pfr": "LP", "caller": "BTN", "oop": "LP", "ip": "BTN"},
            "priority_wave": 2,
            "range_profile_tags": ["grouped_srp", "lp_open", "btn_flat"],
            "board_bucket_biases": ["middling_connected", "two_tone", "monotone"],
        },
        "UTG_open_vs_HJ_flat": {
            "family_ref": "srp_oop_pfr_flop",
            "preflop_path": ["UTG opens", "HJ calls"],
            "positions": {"pfr": "UTG", "caller": "HJ", "oop": "UTG", "ip": "HJ"},
            "priority_wave": 2,
            "range_profile_tags": ["tight_vs_tight", "condensed_ip_flat", "ooppfr_core"],
            "board_bucket_biases": ["ace_high", "paired", "broadway_static"],
        },
        "UTG_open_vs_CO_flat": {
            "family_ref": "srp_oop_pfr_flop",
            "preflop_path": ["UTG opens", "CO calls"],
            "positions": {"pfr": "UTG", "caller": "CO", "oop": "UTG", "ip": "CO"},
            "priority_wave": 2,
            "range_profile_tags": ["tight_vs_condensed", "high_card_heavy", "ooppfr_core"],
            "board_bucket_biases": ["ace_high", "broadway_static", "paired"],
        },
        "UTG_open_vs_BTN_flat": {
            "family_ref": "srp_oop_pfr_flop",
            "preflop_path": ["UTG opens", "BTN calls"],
            "positions": {"pfr": "UTG", "caller": "BTN", "oop": "UTG", "ip": "BTN"},
            "priority_wave": 2,
            "range_profile_tags": ["tight_vs_wider_ip_flat", "high_card_heavy", "ooppfr_core"],
            "board_bucket_biases": ["ace_high", "king_high", "paired"],
        },
        "HJ_open_vs_CO_flat": {
            "family_ref": "srp_oop_pfr_flop",
            "preflop_path": ["HJ opens", "CO calls"],
            "positions": {"pfr": "HJ", "caller": "CO", "oop": "HJ", "ip": "CO"},
            "priority_wave": 2,
            "range_profile_tags": ["medium_tight_vs_condensed", "middle_position_collision", "ooppfr_core"],
            "board_bucket_biases": ["queen_high", "paired", "two_tone"],
        },
        "HJ_open_vs_BTN_flat": {
            "family_ref": "srp_oop_pfr_flop",
            "preflop_path": ["HJ opens", "BTN calls"],
            "positions": {"pfr": "HJ", "caller": "BTN", "oop": "HJ", "ip": "BTN"},
            "priority_wave": 2,
            "range_profile_tags": ["medium_tight_vs_wide_ip", "dynamic_middle_boards", "ooppfr_core"],
            "board_bucket_biases": ["queen_high", "middling_connected", "two_tone"],
        },
        "CO_open_vs_BTN_flat": {
            "family_ref": "srp_oop_pfr_flop",
            "preflop_path": ["CO opens", "BTN calls"],
            "positions": {"pfr": "CO", "caller": "BTN", "oop": "CO", "ip": "BTN"},
            "priority_wave": 2,
            "range_profile_tags": ["late_vs_late", "range_overlap_high", "ooppfr_core"],
            "board_bucket_biases": ["middling_connected", "two_tone", "monotone"],
        },
        "SB_open_vs_BB_defend": {
            "family_ref": "bvb_flop_aggressive",
            "preflop_path": ["SB opens", "BB calls"],
            "positions": {"pfr": "SB", "caller": "BB", "oop": "SB", "ip": "BB"},
            "priority_wave": 1,
            "range_profile_tags": ["blind_vs_blind", "wide_vs_wide", "high_volatility"],
            "board_bucket_biases": ["low_disconnected", "low_connected", "paired"],
        },
        "BB_vs_SB_open_defend": {
            "family_ref": "bvb_defender_flop",
            "preflop_path": ["SB opens", "BB calls"],
            "positions": {"pfr": "SB", "caller": "BB", "oop": "SB", "ip": "BB"},
            "priority_wave": 1,
            "range_profile_tags": ["blind_vs_blind", "defender_view", "high_volatility"],
            "board_bucket_biases": ["low_connected", "paired", "monotone"],
        },
        "EP_3bets_vs_same_band_open": {
            "family_ref": "three_bet_ip_3bettor_flop",
            "preflop_path": ["EP opens", "later EP 3-bets", "EP calls"],
            "positions": {"pfr": "EP_3bettor", "caller": "EP", "oop": "EP", "ip": "EP_3bettor"},
            "priority_wave": 3,
            "range_profile_tags": ["grouped_3bp", "ep_3bet", "same_band_open"],
            "board_bucket_biases": ["ace_high", "king_high", "paired"],
        },
        "MP_3bets_vs_EP_open": {
            "family_ref": "three_bet_ip_3bettor_flop",
            "preflop_path": ["EP opens", "MP 3-bets", "EP calls"],
            "positions": {"pfr": "MP_3bettor", "caller": "EP", "oop": "EP", "ip": "MP"},
            "priority_wave": 3,
            "range_profile_tags": ["grouped_3bp", "mp_3bet", "vs_ep_open"],
            "board_bucket_biases": ["ace_high", "king_high", "paired"],
        },
        "LP_3bets_vs_EP_open": {
            "family_ref": "three_bet_ip_3bettor_flop",
            "preflop_path": ["EP opens", "LP 3-bets", "EP calls"],
            "positions": {"pfr": "LP_3bettor", "caller": "EP", "oop": "EP", "ip": "LP"},
            "priority_wave": 3,
            "range_profile_tags": ["grouped_3bp", "lp_3bet", "vs_ep_open"],
            "board_bucket_biases": ["ace_high", "king_high", "paired"],
        },
        "MP_3bets_vs_MP_open": {
            "family_ref": "three_bet_ip_3bettor_flop",
            "preflop_path": ["MP opens", "later MP 3-bets", "MP calls"],
            "positions": {"pfr": "MP_3bettor", "caller": "MP", "oop": "MP", "ip": "MP"},
            "priority_wave": 3,
            "range_profile_tags": ["grouped_3bp", "mp_3bet", "same_band_open"],
            "board_bucket_biases": ["ace_high", "king_high", "paired"],
        },
        "LP_3bets_vs_MP_open": {
            "family_ref": "three_bet_ip_3bettor_flop",
            "preflop_path": ["MP opens", "LP 3-bets", "MP calls"],
            "positions": {"pfr": "LP_3bettor", "caller": "MP", "oop": "MP", "ip": "LP"},
            "priority_wave": 3,
            "range_profile_tags": ["grouped_3bp", "lp_3bet", "vs_mp_open"],
            "board_bucket_biases": ["ace_high", "king_high", "paired"],
        },
        "BTN_3bets_vs_EP_open": {
            "family_ref": "three_bet_ip_3bettor_flop",
            "preflop_path": ["EP opens", "BTN 3-bets", "EP calls"],
            "positions": {"pfr": "BTN_3bettor", "caller": "EP", "oop": "EP", "ip": "BTN"},
            "priority_wave": 3,
            "range_profile_tags": ["grouped_3bp", "btn_3bet", "vs_ep_open"],
            "board_bucket_biases": ["ace_high", "king_high", "paired"],
        },
        "BTN_3bets_vs_MP_open": {
            "family_ref": "three_bet_ip_3bettor_flop",
            "preflop_path": ["MP opens", "BTN 3-bets", "MP calls"],
            "positions": {"pfr": "BTN_3bettor", "caller": "MP", "oop": "MP", "ip": "BTN"},
            "priority_wave": 3,
            "range_profile_tags": ["grouped_3bp", "btn_3bet", "vs_mp_open"],
            "board_bucket_biases": ["ace_high", "king_high", "paired"],
        },
        "SB_3bets_vs_EP_open": {
            "family_ref": "three_bet_oop_3bettor_flop",
            "preflop_path": ["EP opens", "SB 3-bets", "EP calls"],
            "positions": {"pfr": "SB_3bettor", "caller": "EP", "oop": "SB", "ip": "EP"},
            "priority_wave": 3,
            "range_profile_tags": ["grouped_3bp", "sb_3bet", "vs_ep_open"],
            "board_bucket_biases": ["ace_high", "low_disconnected", "paired"],
        },
        "SB_3bets_vs_MP_open": {
            "family_ref": "three_bet_oop_3bettor_flop",
            "preflop_path": ["MP opens", "SB 3-bets", "MP calls"],
            "positions": {"pfr": "SB_3bettor", "caller": "MP", "oop": "SB", "ip": "MP"},
            "priority_wave": 3,
            "range_profile_tags": ["grouped_3bp", "sb_3bet", "vs_mp_open"],
            "board_bucket_biases": ["ace_high", "low_disconnected", "paired"],
        },
        "SB_3bets_vs_LP_open": {
            "family_ref": "three_bet_oop_3bettor_flop",
            "preflop_path": ["LP opens", "SB 3-bets", "LP calls"],
            "positions": {"pfr": "SB_3bettor", "caller": "LP", "oop": "SB", "ip": "LP"},
            "priority_wave": 3,
            "range_profile_tags": ["grouped_3bp", "sb_3bet", "vs_lp_open"],
            "board_bucket_biases": ["ace_high", "low_disconnected", "paired"],
        },
        "BB_3bets_vs_EP_open": {
            "family_ref": "three_bet_oop_3bettor_flop",
            "preflop_path": ["EP opens", "BB 3-bets", "EP calls"],
            "positions": {"pfr": "BB_3bettor", "caller": "EP", "oop": "BB", "ip": "EP"},
            "priority_wave": 3,
            "range_profile_tags": ["grouped_3bp", "bb_3bet", "vs_ep_open"],
            "board_bucket_biases": ["ace_high", "low_disconnected", "paired"],
        },
        "BB_3bets_vs_MP_open": {
            "family_ref": "three_bet_oop_3bettor_flop",
            "preflop_path": ["MP opens", "BB 3-bets", "MP calls"],
            "positions": {"pfr": "BB_3bettor", "caller": "MP", "oop": "BB", "ip": "MP"},
            "priority_wave": 3,
            "range_profile_tags": ["grouped_3bp", "bb_3bet", "vs_mp_open"],
            "board_bucket_biases": ["ace_high", "low_disconnected", "paired"],
        },
        "BB_3bets_vs_LP_open": {
            "family_ref": "three_bet_oop_3bettor_flop",
            "preflop_path": ["LP opens", "BB 3-bets", "LP calls"],
            "positions": {"pfr": "BB_3bettor", "caller": "LP", "oop": "BB", "ip": "LP"},
            "priority_wave": 3,
            "range_profile_tags": ["grouped_3bp", "bb_3bet", "vs_lp_open"],
            "board_bucket_biases": ["ace_high", "low_disconnected", "paired"],
        },
        "CO_3bets_vs_HJ_open": {
            "family_ref": "three_bet_ip_3bettor_flop",
            "preflop_path": ["HJ opens", "CO 3-bets", "HJ calls"],
            "positions": {"pfr": "CO_3bettor", "caller": "HJ", "oop": "HJ", "ip": "CO"},
            "priority_wave": 3,
            "range_profile_tags": ["three_bet_pot", "ip_3bettor", "range_advantage_heavy"],
            "board_bucket_biases": ["ace_high", "king_high", "paired"],
        },
        "BTN_3bets_vs_HJ_open": {
            "family_ref": "three_bet_ip_3bettor_flop",
            "preflop_path": ["HJ opens", "BTN 3-bets", "HJ calls"],
            "positions": {"pfr": "BTN_3bettor", "caller": "HJ", "oop": "HJ", "ip": "BTN"},
            "priority_wave": 3,
            "range_profile_tags": ["three_bet_pot", "ip_3bettor", "range_advantage_heavy"],
            "board_bucket_biases": ["ace_high", "king_high", "paired"],
        },
        "BTN_3bets_vs_CO_open": {
            "family_ref": "three_bet_ip_3bettor_flop",
            "preflop_path": ["CO opens", "BTN 3-bets", "CO calls"],
            "positions": {"pfr": "BTN_3bettor", "caller": "CO", "oop": "CO", "ip": "BTN"},
            "priority_wave": 3,
            "range_profile_tags": ["three_bet_pot", "ip_3bettor", "range_advantage_heavy"],
            "board_bucket_biases": ["ace_high", "king_high", "paired"],
        },
        "SB_3bets_vs_BTN_open": {
            "family_ref": "three_bet_oop_3bettor_flop",
            "preflop_path": ["BTN opens", "SB 3-bets", "BTN calls"],
            "positions": {"pfr": "SB_3bettor", "caller": "BTN", "oop": "SB", "ip": "BTN"},
            "priority_wave": 3,
            "range_profile_tags": ["three_bet_pot", "oop_3bettor", "range_advantage_heavy"],
            "board_bucket_biases": ["ace_high", "low_disconnected", "paired"],
        },
        "BB_3bets_vs_BTN_open": {
            "family_ref": "three_bet_oop_3bettor_flop",
            "preflop_path": ["BTN opens", "BB 3-bets", "BTN calls"],
            "positions": {"pfr": "BB_3bettor", "caller": "BTN", "oop": "BB", "ip": "BTN"},
            "priority_wave": 3,
            "range_profile_tags": ["three_bet_pot", "oop_3bettor", "range_advantage_heavy"],
            "board_bucket_biases": ["ace_high", "low_disconnected", "paired"],
        },
        "BB_3bets_vs_SB_open": {
            "family_ref": "three_bet_oop_3bettor_flop",
            "preflop_path": ["SB opens", "BB 3-bets", "SB calls"],
            "positions": {"pfr": "BB_3bettor", "caller": "SB", "oop": "BB", "ip": "SB"},
            "priority_wave": 3,
            "range_profile_tags": ["three_bet_pot", "oop_3bettor", "blind_vs_blind"],
            "board_bucket_biases": ["ace_high", "low_disconnected", "paired"],
        },
        "multiway_srp_3way_oop_aggressor": {
            "family_ref": "multiway_srp_3way_oop_aggressor_flop",
            "preflop_path": ["single raise preflop", "3 players see flop", "aggressor first to act"],
            "positions": {"pfr": "mixed", "caller": "mixed+mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["multiway", "single_raised_pot", "3way", "oop_aggressor"],
            "board_bucket_biases": ["range_compression", "realization_sensitive", "draw_heavy"],
        },
        "multiway_srp_3way_middle_aggressor": {
            "family_ref": "multiway_srp_3way_middle_aggressor_flop",
            "preflop_path": ["single raise preflop", "3 players see flop", "aggressor acts second"],
            "positions": {"pfr": "mixed", "caller": "mixed+mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["multiway", "single_raised_pot", "3way", "middle_aggressor"],
            "board_bucket_biases": ["range_compression", "realization_sensitive", "draw_heavy"],
        },
        "multiway_srp_3way_ip_aggressor": {
            "family_ref": "multiway_srp_3way_ip_aggressor_flop",
            "preflop_path": ["single raise preflop", "3 players see flop", "aggressor last to act"],
            "positions": {"pfr": "mixed", "caller": "mixed+mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["multiway", "single_raised_pot", "3way", "ip_aggressor"],
            "board_bucket_biases": ["range_compression", "realization_sensitive", "draw_heavy"],
        },
        "multiway_3bp_3way_oop_aggressor": {
            "family_ref": "multiway_3bp_3way_oop_aggressor_flop",
            "preflop_path": ["3-bet preflop", "3 players see flop", "aggressor first to act"],
            "positions": {"pfr": "mixed", "caller": "mixed+mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["multiway", "three_bet_pot", "3way", "oop_aggressor"],
            "board_bucket_biases": ["range_compression", "spr_sensitive", "high_card"],
        },
        "multiway_3bp_3way_middle_aggressor": {
            "family_ref": "multiway_3bp_3way_middle_aggressor_flop",
            "preflop_path": ["3-bet preflop", "3 players see flop", "aggressor acts second"],
            "positions": {"pfr": "mixed", "caller": "mixed+mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["multiway", "three_bet_pot", "3way", "middle_aggressor"],
            "board_bucket_biases": ["range_compression", "spr_sensitive", "high_card"],
        },
        "multiway_3bp_3way_ip_aggressor": {
            "family_ref": "multiway_3bp_3way_ip_aggressor_flop",
            "preflop_path": ["3-bet preflop", "3 players see flop", "aggressor last to act"],
            "positions": {"pfr": "mixed", "caller": "mixed+mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["multiway", "three_bet_pot", "3way", "ip_aggressor"],
            "board_bucket_biases": ["range_compression", "spr_sensitive", "high_card"],
        },
        "multiway_3bp_4plus": {
            "family_ref": "multiway_3bp_4plus_flop",
            "preflop_path": ["3-bet preflop", "4 or more players see flop"],
            "positions": {"pfr": "mixed", "caller": "mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["multiway", "three_bet_pot", "4plus"],
            "board_bucket_biases": ["range_compression", "spr_sensitive", "high_card"],
        },
        "multiway_srp_4plus": {
            "family_ref": "multiway_srp_4plus_flop",
            "preflop_path": ["single raise preflop", "4 or more players see flop"],
            "positions": {"pfr": "mixed", "caller": "mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["multiway", "single_raised_pot", "4plus"],
            "board_bucket_biases": ["range_compression", "realization_sensitive", "draw_heavy"],
        },
        "limped_pot_2way": {
            "family_ref": "limped_pot_heads_up_flop",
            "preflop_path": ["unraised preflop", "2 players see flop"],
            "positions": {"pfr": "none", "caller": "none", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["limped_pot", "heads_up"],
            "board_bucket_biases": ["range_neutral", "low_board_swing", "showdown_heavy"],
        },
        "limped_pot_3way": {
            "family_ref": "limped_pot_multiway_flop",
            "preflop_path": ["unraised preflop", "3 players see flop"],
            "positions": {"pfr": "none", "caller": "none", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["limped_pot", "3way"],
            "board_bucket_biases": ["range_neutral", "multiway", "showdown_heavy"],
        },
        "iso_limped_pot_ip_aggressor": {
            "family_ref": "raised_after_limp_ip_aggressor_flop",
            "preflop_path": ["limp preflop", "isolation raise", "limper calls", "heads-up flop", "aggressor in position"],
            "positions": {"pfr": "isolator", "caller": "limper", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["limp_raise_call", "heads_up", "isolated_pot", "ip_aggressor"],
            "board_bucket_biases": ["range_compression", "realization_sensitive", "draw_heavy"],
        },
        "iso_limped_pot_oop_aggressor": {
            "family_ref": "raised_after_limp_oop_aggressor_flop",
            "preflop_path": ["limp preflop", "isolation raise", "limper calls", "heads-up flop", "aggressor out of position"],
            "positions": {"pfr": "isolator", "caller": "limper", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["limp_raise_call", "heads_up", "isolated_pot", "oop_aggressor"],
            "board_bucket_biases": ["range_compression", "realization_sensitive", "draw_heavy"],
        },
        "limped_pot_4plus": {
            "family_ref": "limped_pot_multiway_flop",
            "preflop_path": ["unraised preflop", "4 or more players see flop"],
            "positions": {"pfr": "none", "caller": "none", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["limped_pot", "4plus"],
            "board_bucket_biases": ["range_neutral", "multiway", "showdown_heavy"],
        },
        "raised_after_limp_3way_oop_aggressor": {
            "family_ref": "raised_after_limp_3way_oop_aggressor_flop",
            "preflop_path": ["single raise or raised-after-limp preflop", "3 players see flop", "aggressor first to act"],
            "positions": {"pfr": "mixed", "caller": "mixed+mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["overcall_or_limp_raise", "multiway", "3way", "oop_aggressor"],
            "board_bucket_biases": ["range_compression", "realization_sensitive", "draw_heavy"],
        },
        "raised_after_limp_3way_middle_aggressor": {
            "family_ref": "raised_after_limp_3way_middle_aggressor_flop",
            "preflop_path": ["single raise or raised-after-limp preflop", "3 players see flop", "aggressor acts second"],
            "positions": {"pfr": "mixed", "caller": "mixed+mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["overcall_or_limp_raise", "multiway", "3way", "middle_aggressor"],
            "board_bucket_biases": ["range_compression", "realization_sensitive", "draw_heavy"],
        },
        "raised_after_limp_3way_ip_aggressor": {
            "family_ref": "raised_after_limp_3way_ip_aggressor_flop",
            "preflop_path": ["single raise or raised-after-limp preflop", "3 players see flop", "aggressor last to act"],
            "positions": {"pfr": "mixed", "caller": "mixed+mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["overcall_or_limp_raise", "multiway", "3way", "ip_aggressor"],
            "board_bucket_biases": ["range_compression", "realization_sensitive", "draw_heavy"],
        },
        "raised_after_limp_ip_aggressor": {
            "family_ref": "raised_after_limp_ip_aggressor_flop",
            "preflop_path": ["one or more limps", "raise and re-raise sequence", "heads-up flop", "aggressor in position"],
            "positions": {"pfr": "mixed", "caller": "mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["limped_then_raised", "heads_up", "complex_preflop", "ip_aggressor"],
            "board_bucket_biases": ["range_compression", "spr_sensitive", "draw_heavy"],
        },
        "raised_after_limp_oop_aggressor": {
            "family_ref": "raised_after_limp_oop_aggressor_flop",
            "preflop_path": ["one or more limps", "raise and re-raise sequence", "heads-up flop", "aggressor out of position"],
            "positions": {"pfr": "mixed", "caller": "mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["limped_then_raised", "heads_up", "complex_preflop", "oop_aggressor"],
            "board_bucket_biases": ["range_compression", "spr_sensitive", "draw_heavy"],
        },
        "raised_after_limp_multiway": {
            "family_ref": "raised_after_limp_multiway_flop",
            "preflop_path": ["one or more limps", "raise and re-raise sequence", "multiway flop"],
            "positions": {"pfr": "mixed", "caller": "mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["limped_then_raised", "multiway", "complex_preflop"],
            "board_bucket_biases": ["range_compression", "spr_sensitive", "draw_heavy"],
        },
        "overcalled_srp_4plus": {
            "family_ref": "raised_after_limp_multiway_flop",
            "preflop_path": ["single raise preflop", "at least one overcall", "4 or more players see flop"],
            "positions": {"pfr": "mixed", "caller": "mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["overcall", "single_raised_pot", "4plus"],
            "board_bucket_biases": ["range_compression", "realization_sensitive", "draw_heavy"],
        },
        "four_bet_pot_ip_aggressor": {
            "family_ref": "four_bet_ip_aggressor_flop",
            "preflop_path": ["4-bet preflop", "heads-up flop", "last aggressor in position"],
            "positions": {"pfr": "mixed", "caller": "mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["four_bet_pot", "heads_up", "ip_aggressor"],
            "board_bucket_biases": ["high_card", "spr_sensitive", "range_advantage_heavy"],
        },
        "four_bet_pot_oop_aggressor": {
            "family_ref": "four_bet_oop_aggressor_flop",
            "preflop_path": ["4-bet preflop", "heads-up flop", "last aggressor out of position"],
            "positions": {"pfr": "mixed", "caller": "mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["four_bet_pot", "heads_up", "oop_aggressor"],
            "board_bucket_biases": ["high_card", "spr_sensitive", "range_advantage_heavy"],
        },
        "four_bet_3way_oop_aggressor": {
            "family_ref": "four_bet_3way_oop_aggressor_flop",
            "preflop_path": ["4-bet preflop", "3 players see flop", "aggressor first to act"],
            "positions": {"pfr": "mixed", "caller": "mixed+mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["four_bet_pot", "multiway", "3way", "oop_aggressor"],
            "board_bucket_biases": ["high_card", "spr_sensitive", "range_advantage_heavy"],
        },
        "four_bet_3way_middle_aggressor": {
            "family_ref": "four_bet_3way_middle_aggressor_flop",
            "preflop_path": ["4-bet preflop", "3 players see flop", "aggressor acts second"],
            "positions": {"pfr": "mixed", "caller": "mixed+mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["four_bet_pot", "multiway", "3way", "middle_aggressor"],
            "board_bucket_biases": ["high_card", "spr_sensitive", "range_advantage_heavy"],
        },
        "four_bet_3way_ip_aggressor": {
            "family_ref": "four_bet_3way_ip_aggressor_flop",
            "preflop_path": ["4-bet preflop", "3 players see flop", "aggressor last to act"],
            "positions": {"pfr": "mixed", "caller": "mixed+mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["four_bet_pot", "multiway", "3way", "ip_aggressor"],
            "board_bucket_biases": ["high_card", "spr_sensitive", "range_advantage_heavy"],
        },
        "four_bet_pot_multiway": {
            "family_ref": "four_bet_multiway_flop",
            "preflop_path": ["4-bet preflop", "4 or more players see flop"],
            "positions": {"pfr": "mixed", "caller": "mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["four_bet_pot", "multiway", "4plus"],
            "board_bucket_biases": ["high_card", "spr_sensitive", "range_advantage_heavy"],
        },
        "five_bet_plus_ip_aggressor": {
            "family_ref": "five_bet_plus_ip_aggressor_flop",
            "preflop_path": ["5-bet or more preflop", "heads-up flop", "last aggressor in position"],
            "positions": {"pfr": "mixed", "caller": "mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["five_bet_plus", "heads_up", "ip_aggressor"],
            "board_bucket_biases": ["high_card", "spr_sensitive", "range_advantage_heavy"],
        },
        "five_bet_plus_oop_aggressor": {
            "family_ref": "five_bet_plus_oop_aggressor_flop",
            "preflop_path": ["5-bet or more preflop", "heads-up flop", "last aggressor out of position"],
            "positions": {"pfr": "mixed", "caller": "mixed", "oop": "mixed", "ip": "mixed"},
            "priority_wave": 4,
            "range_profile_tags": ["five_bet_plus", "heads_up", "oop_aggressor"],
            "board_bucket_biases": ["high_card", "spr_sensitive", "range_advantage_heavy"],
        },
    },
}


def build_postflop_expansion_plan() -> dict[str, Any]:
    return deepcopy(POSTFLOP_EXPANSION_PLAN)


EXACT_COMPLEX_POSITION_LABELS = ["UTG", "MP", "LJ", "HJ", "CO", "BTN", "SB", "BB"]


def _complex_position_order_key(position: str) -> int:
    order = {
        "SB": 0,
        "BB": 1,
        "UTG": 2,
        "MP": 30,
        "LJ": 40,
        "HJ": 50,
        "CO": 60,
        "BTN": 70,
    }
    return order.get(position, 20)


def _generate_exact_complex_heads_up_matchups(library: dict[str, Any]) -> None:
    configs = [
        {
            "family_ref": "raised_after_limp_ip_aggressor_flop",
            "prefix": "raised_after_limp_ip_aggr",
            "aggressor_role": "ip",
            "preflop_path": ["one or more limps", "raise sequence", "heads-up flop", "aggressor in position"],
            "range_profile_tags": ["limped_then_raised", "heads_up", "ip_aggressor"],
            "board_bucket_biases": ["range_compression", "spr_sensitive", "draw_heavy"],
        },
        {
            "family_ref": "raised_after_limp_oop_aggressor_flop",
            "prefix": "raised_after_limp_oop_aggr",
            "aggressor_role": "oop",
            "preflop_path": ["one or more limps", "raise sequence", "heads-up flop", "aggressor out of position"],
            "range_profile_tags": ["limped_then_raised", "heads_up", "oop_aggressor"],
            "board_bucket_biases": ["range_compression", "spr_sensitive", "draw_heavy"],
        },
        {
            "family_ref": "four_bet_ip_aggressor_flop",
            "prefix": "four_bet_ip_aggr",
            "aggressor_role": "ip",
            "preflop_path": ["4-bet preflop", "heads-up flop", "aggressor in position"],
            "range_profile_tags": ["four_bet_pot", "heads_up", "ip_aggressor"],
            "board_bucket_biases": ["high_card", "spr_sensitive", "range_advantage_heavy"],
        },
        {
            "family_ref": "four_bet_oop_aggressor_flop",
            "prefix": "four_bet_oop_aggr",
            "aggressor_role": "oop",
            "preflop_path": ["4-bet preflop", "heads-up flop", "aggressor out of position"],
            "range_profile_tags": ["four_bet_pot", "heads_up", "oop_aggressor"],
            "board_bucket_biases": ["high_card", "spr_sensitive", "range_advantage_heavy"],
        },
        {
            "family_ref": "five_bet_plus_ip_aggressor_flop",
            "prefix": "five_bet_plus_ip_aggr",
            "aggressor_role": "ip",
            "preflop_path": ["5-bet or more preflop", "heads-up flop", "aggressor in position"],
            "range_profile_tags": ["five_bet_plus", "heads_up", "ip_aggressor"],
            "board_bucket_biases": ["high_card", "spr_sensitive", "range_advantage_heavy"],
        },
        {
            "family_ref": "five_bet_plus_oop_aggressor_flop",
            "prefix": "five_bet_plus_oop_aggr",
            "aggressor_role": "oop",
            "preflop_path": ["5-bet or more preflop", "heads-up flop", "aggressor out of position"],
            "range_profile_tags": ["five_bet_plus", "heads_up", "oop_aggressor"],
            "board_bucket_biases": ["high_card", "spr_sensitive", "range_advantage_heavy"],
        },
    ]

    generated = {}
    for config in configs:
        for oop in EXACT_COMPLEX_POSITION_LABELS:
            for ip in EXACT_COMPLEX_POSITION_LABELS:
                if _complex_position_order_key(ip) <= _complex_position_order_key(oop):
                    continue
                if config["aggressor_role"] == "ip":
                    aggressor = ip
                    caller = oop
                    matchup_id = f"{config['prefix']}_{ip}_vs_{oop}"
                else:
                    aggressor = oop
                    caller = ip
                    matchup_id = f"{config['prefix']}_{oop}_vs_{ip}"
                generated[matchup_id] = {
                    "family_ref": config["family_ref"],
                    "preflop_path": config["preflop_path"],
                    "positions": {"pfr": aggressor, "caller": caller, "oop": oop, "ip": ip},
                    "priority_wave": 5,
                    "range_profile_tags": config["range_profile_tags"] + [f"oop_{oop.lower()}", f"ip_{ip.lower()}"],
                    "board_bucket_biases": config["board_bucket_biases"],
                }
    library["matchup_instances"].update(generated)


def _generate_exact_complex_multiway_3way_matchups(library: dict[str, Any]) -> None:
    ordered_positions = sorted(EXACT_COMPLEX_POSITION_LABELS, key=_complex_position_order_key)
    configs = [
        {
            "family_ref": "multiway_srp_3way_oop_aggressor_flop",
            "prefix": "multiway_srp_3way_oop_aggr",
            "aggressor_slot": "first",
            "preflop_path": ["single raise preflop", "3 players see flop", "aggressor first to act"],
            "range_profile_tags": ["multiway", "single_raised_pot", "3way", "oop_aggressor"],
            "board_bucket_biases": ["range_compression", "realization_sensitive", "draw_heavy"],
        },
        {
            "family_ref": "multiway_srp_3way_middle_aggressor_flop",
            "prefix": "multiway_srp_3way_middle_aggr",
            "aggressor_slot": "middle",
            "preflop_path": ["single raise preflop", "3 players see flop", "aggressor acts second"],
            "range_profile_tags": ["multiway", "single_raised_pot", "3way", "middle_aggressor"],
            "board_bucket_biases": ["range_compression", "realization_sensitive", "draw_heavy"],
        },
        {
            "family_ref": "multiway_srp_3way_ip_aggressor_flop",
            "prefix": "multiway_srp_3way_ip_aggr",
            "aggressor_slot": "last",
            "preflop_path": ["single raise preflop", "3 players see flop", "aggressor last to act"],
            "range_profile_tags": ["multiway", "single_raised_pot", "3way", "ip_aggressor"],
            "board_bucket_biases": ["range_compression", "realization_sensitive", "draw_heavy"],
        },
        {
            "family_ref": "multiway_3bp_3way_oop_aggressor_flop",
            "prefix": "multiway_3bp_3way_oop_aggr",
            "aggressor_slot": "first",
            "preflop_path": ["3-bet preflop", "3 players see flop", "aggressor first to act"],
            "range_profile_tags": ["multiway", "three_bet_pot", "3way", "oop_aggressor"],
            "board_bucket_biases": ["range_compression", "spr_sensitive", "high_card"],
        },
        {
            "family_ref": "multiway_3bp_3way_middle_aggressor_flop",
            "prefix": "multiway_3bp_3way_middle_aggr",
            "aggressor_slot": "middle",
            "preflop_path": ["3-bet preflop", "3 players see flop", "aggressor acts second"],
            "range_profile_tags": ["multiway", "three_bet_pot", "3way", "middle_aggressor"],
            "board_bucket_biases": ["range_compression", "spr_sensitive", "high_card"],
        },
        {
            "family_ref": "multiway_3bp_3way_ip_aggressor_flop",
            "prefix": "multiway_3bp_3way_ip_aggr",
            "aggressor_slot": "last",
            "preflop_path": ["3-bet preflop", "3 players see flop", "aggressor last to act"],
            "range_profile_tags": ["multiway", "three_bet_pot", "3way", "ip_aggressor"],
            "board_bucket_biases": ["range_compression", "spr_sensitive", "high_card"],
        },
        {
            "family_ref": "raised_after_limp_3way_oop_aggressor_flop",
            "prefix": "raised_after_limp_3way_oop_aggr",
            "aggressor_slot": "first",
            "preflop_path": ["single raise or raised-after-limp preflop", "3 players see flop", "aggressor first to act"],
            "range_profile_tags": ["overcall_or_limp_raise", "multiway", "3way", "oop_aggressor"],
            "board_bucket_biases": ["range_compression", "realization_sensitive", "draw_heavy"],
        },
        {
            "family_ref": "raised_after_limp_3way_middle_aggressor_flop",
            "prefix": "raised_after_limp_3way_middle_aggr",
            "aggressor_slot": "middle",
            "preflop_path": ["single raise or raised-after-limp preflop", "3 players see flop", "aggressor acts second"],
            "range_profile_tags": ["overcall_or_limp_raise", "multiway", "3way", "middle_aggressor"],
            "board_bucket_biases": ["range_compression", "realization_sensitive", "draw_heavy"],
        },
        {
            "family_ref": "raised_after_limp_3way_ip_aggressor_flop",
            "prefix": "raised_after_limp_3way_ip_aggr",
            "aggressor_slot": "last",
            "preflop_path": ["single raise or raised-after-limp preflop", "3 players see flop", "aggressor last to act"],
            "range_profile_tags": ["overcall_or_limp_raise", "multiway", "3way", "ip_aggressor"],
            "board_bucket_biases": ["range_compression", "realization_sensitive", "draw_heavy"],
        },
        {
            "family_ref": "four_bet_3way_oop_aggressor_flop",
            "prefix": "four_bet_3way_oop_aggr",
            "aggressor_slot": "first",
            "preflop_path": ["4-bet preflop", "3 players see flop", "aggressor first to act"],
            "range_profile_tags": ["four_bet_pot", "multiway", "3way", "oop_aggressor"],
            "board_bucket_biases": ["high_card", "spr_sensitive", "range_advantage_heavy"],
        },
        {
            "family_ref": "four_bet_3way_middle_aggressor_flop",
            "prefix": "four_bet_3way_middle_aggr",
            "aggressor_slot": "middle",
            "preflop_path": ["4-bet preflop", "3 players see flop", "aggressor acts second"],
            "range_profile_tags": ["four_bet_pot", "multiway", "3way", "middle_aggressor"],
            "board_bucket_biases": ["high_card", "spr_sensitive", "range_advantage_heavy"],
        },
        {
            "family_ref": "four_bet_3way_ip_aggressor_flop",
            "prefix": "four_bet_3way_ip_aggr",
            "aggressor_slot": "last",
            "preflop_path": ["4-bet preflop", "3 players see flop", "aggressor last to act"],
            "range_profile_tags": ["four_bet_pot", "multiway", "3way", "ip_aggressor"],
            "board_bucket_biases": ["high_card", "spr_sensitive", "range_advantage_heavy"],
        },
    ]

    generated = {}
    for i in range(len(ordered_positions)):
        for j in range(i + 1, len(ordered_positions)):
            for k in range(j + 1, len(ordered_positions)):
                first_pos, middle_pos, last_pos = ordered_positions[i], ordered_positions[j], ordered_positions[k]
                for config in configs:
                    if config["aggressor_slot"] == "first":
                        aggressor = first_pos
                        callers = f"{middle_pos}+{last_pos}"
                    elif config["aggressor_slot"] == "middle":
                        aggressor = middle_pos
                        callers = f"{first_pos}+{last_pos}"
                    else:
                        aggressor = last_pos
                        callers = f"{first_pos}+{middle_pos}"
                    matchup_id = f"{config['prefix']}_{first_pos}_{middle_pos}_{last_pos}"
                    generated[matchup_id] = {
                        "family_ref": config["family_ref"],
                        "preflop_path": config["preflop_path"],
                        "positions": {
                            "pfr": aggressor,
                            "caller": callers,
                            "oop": first_pos,
                            "ip": last_pos,
                            "middle": middle_pos,
                            "first_to_act": first_pos,
                            "last_to_act": last_pos,
                        },
                        "priority_wave": 5,
                        "range_profile_tags": config["range_profile_tags"] + [f"triple_{first_pos.lower()}_{middle_pos.lower()}_{last_pos.lower()}"],
                        "board_bucket_biases": config["board_bucket_biases"],
                    }
    library["matchup_instances"].update(generated)


def build_flop_tree_spec_library() -> dict[str, Any]:
    library = deepcopy(FLOP_TREE_SPEC_LIBRARY)
    _generate_exact_complex_heads_up_matchups(library)
    _generate_exact_complex_multiway_3way_matchups(library)
    return library


TURN_TREE_SPEC_LIBRARY: dict[str, Any] = {
    "size_profiles": {
        "turn_heads_up_ip_last_v1": {
            "bet_small": "50% pot",
            "bet_big": "90% pot",
            "probe_small": "50% pot",
            "probe_big": "90% pot",
            "raise_small": "2.7x",
        },
        "turn_heads_up_oop_aggressor_v1": {
            "bet_small": "50% pot",
            "bet_big": "90% pot",
            "probe_small": "50% pot",
            "probe_big": "90% pot",
            "raise_small": "2.7x",
        },
        "turn_multiway_v1": {
            "bet_small": "50% pot",
            "bet_big": "90% pot",
            "probe_small": "50% pot",
            "probe_big": "90% pot",
            "raise_small": "2.7x",
        },
    },
    "templates": {
        "turn_oop_can_lead_or_check_to_ip_v1": {
            "description": "Controlled first turn template for heads-up spots where the OOP player acts first and the IP player can respond after a check.",
            "actors": {"oop_player": "out_of_position_player", "ip_player": "in_position_player"},
            "nodes": [
                {"id": "root", "actor": "oop_player", "kind": "decision", "options": [
                    {"action": "check", "next": "ip_after_check"},
                    {"action": "bet", "size_ref": "probe_small", "next": "ip_vs_probe_small"},
                    {"action": "bet", "size_ref": "probe_big", "next": "ip_vs_probe_big"},
                ]},
                {"id": "ip_after_check", "actor": "ip_player", "kind": "decision", "options": [
                    {"action": "check", "next": "river_seed_checked_through"},
                    {"action": "bet", "size_ref": "bet_small", "next": "oop_vs_small"},
                    {"action": "bet", "size_ref": "bet_big", "next": "oop_vs_big"},
                ]},
                {"id": "oop_vs_small", "actor": "oop_player", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_ip_small_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "ip_vs_small_raise"},
                ]},
                {"id": "oop_vs_big", "actor": "oop_player", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_ip_big_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "ip_vs_big_raise"},
                ]},
                {"id": "ip_vs_small_raise", "actor": "ip_player", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_ip_small_raise_called"},
                ]},
                {"id": "ip_vs_big_raise", "actor": "ip_player", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_ip_big_raise_called"},
                ]},
                {"id": "ip_vs_probe_small", "actor": "ip_player", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_oop_probe_small_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "terminal_probe_small_raised"},
                ]},
                {"id": "ip_vs_probe_big", "actor": "ip_player", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_oop_probe_big_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "terminal_probe_big_raised"},
                ]},
            ],
            "river_seeds": [
                {"id": "river_seed_checked_through", "tag": "turn_checked_through"},
                {"id": "river_seed_ip_small_called", "tag": "turn_ip_small_bet_called"},
                {"id": "river_seed_ip_big_called", "tag": "turn_ip_big_bet_called"},
                {"id": "river_seed_ip_small_raise_called", "tag": "turn_ip_small_bet_raise_called"},
                {"id": "river_seed_ip_big_raise_called", "tag": "turn_ip_big_bet_raise_called"},
                {"id": "river_seed_oop_probe_small_called", "tag": "turn_oop_small_probe_called"},
                {"id": "river_seed_oop_probe_big_called", "tag": "turn_oop_big_probe_called"},
            ],
        },
        "turn_oop_aggressor_open_action_v1": {
            "description": "Controlled first turn template for heads-up spots where the OOP player is the likely aggressor node owner at turn start.",
            "actors": {"oop_aggressor": "out_of_position_aggressor", "ip_player": "in_position_player"},
            "nodes": [
                {"id": "root", "actor": "oop_aggressor", "kind": "decision", "options": [
                    {"action": "check", "next": "ip_after_check"},
                    {"action": "bet", "size_ref": "bet_small", "next": "ip_vs_small"},
                    {"action": "bet", "size_ref": "bet_big", "next": "ip_vs_big"},
                ]},
                {"id": "ip_after_check", "actor": "ip_player", "kind": "decision", "options": [
                    {"action": "check", "next": "river_seed_checked_through"},
                    {"action": "bet", "size_ref": "probe_small", "next": "oop_vs_probe_small"},
                    {"action": "bet", "size_ref": "probe_big", "next": "oop_vs_probe_big"},
                ]},
                {"id": "ip_vs_small", "actor": "ip_player", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_small_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "oop_vs_small_raise"},
                ]},
                {"id": "ip_vs_big", "actor": "ip_player", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_big_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "oop_vs_big_raise"},
                ]},
                {"id": "oop_vs_small_raise", "actor": "oop_aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_small_raise_called"},
                ]},
                {"id": "oop_vs_big_raise", "actor": "oop_aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_big_raise_called"},
                ]},
                {"id": "oop_vs_probe_small", "actor": "oop_aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_probe_small_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "terminal_probe_small_raised"},
                ]},
                {"id": "oop_vs_probe_big", "actor": "oop_aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_probe_big_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "terminal_probe_big_raised"},
                ]},
            ],
            "river_seeds": [
                {"id": "river_seed_checked_through", "tag": "turn_checked_through"},
                {"id": "river_seed_small_called", "tag": "turn_oop_small_bet_called"},
                {"id": "river_seed_big_called", "tag": "turn_oop_big_bet_called"},
                {"id": "river_seed_small_raise_called", "tag": "turn_oop_small_bet_raise_called"},
                {"id": "river_seed_big_raise_called", "tag": "turn_oop_big_bet_raise_called"},
                {"id": "river_seed_probe_small_called", "tag": "turn_ip_small_probe_called"},
                {"id": "river_seed_probe_big_called", "tag": "turn_ip_big_probe_called"},
            ],
        },
        "turn_multiway_field_lead_or_check_to_aggressor_v1": {
            "description": "Controlled first turn template for 3-way spots where the first field player acts before the aggressor.",
            "actors": {"first_field_player": "first_player_to_act", "aggressor": "middle_aggressor", "field": "remaining_field"},
            "nodes": [
                {"id": "root", "actor": "first_field_player", "kind": "decision", "options": [
                    {"action": "check", "next": "aggressor_after_check"},
                    {"action": "bet", "size_ref": "probe_small", "next": "aggressor_vs_field_lead_small"},
                    {"action": "bet", "size_ref": "probe_big", "next": "aggressor_vs_field_lead_big"},
                ]},
                {"id": "aggressor_after_check", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "bet", "size_ref": "bet_small", "next": "field_vs_small"},
                    {"action": "bet", "size_ref": "bet_big", "next": "field_vs_big"},
                    {"action": "check", "next": "river_seed_multiway_checkback"},
                ]},
                {"id": "field_vs_small", "actor": "field", "kind": "compressed_multiway_decision", "options": [
                    {"action": "fold_all", "next": "terminal_field_folds"},
                    {"action": "one_or_more_calls", "next": "river_seed_multiway_small_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "aggressor_vs_small_raise"},
                ]},
                {"id": "field_vs_big", "actor": "field", "kind": "compressed_multiway_decision", "options": [
                    {"action": "fold_all", "next": "terminal_field_folds"},
                    {"action": "one_or_more_calls", "next": "river_seed_multiway_big_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "aggressor_vs_big_raise"},
                ]},
                {"id": "aggressor_vs_small_raise", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_multiway_small_raise_called"},
                ]},
                {"id": "aggressor_vs_big_raise", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_multiway_big_raise_called"},
                ]},
                {"id": "aggressor_vs_field_lead_small", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_multiway_field_lead_small_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "terminal_field_lead_small_raised"},
                ]},
                {"id": "aggressor_vs_field_lead_big", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_multiway_field_lead_big_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "terminal_field_lead_big_raised"},
                ]},
            ],
            "river_seeds": [
                {"id": "river_seed_multiway_checkback", "tag": "turn_multiway_checkback"},
                {"id": "river_seed_multiway_small_called", "tag": "turn_multiway_small_called"},
                {"id": "river_seed_multiway_big_called", "tag": "turn_multiway_big_called"},
                {"id": "river_seed_multiway_small_raise_called", "tag": "turn_multiway_small_raise_called"},
                {"id": "river_seed_multiway_big_raise_called", "tag": "turn_multiway_big_raise_called"},
                {"id": "river_seed_multiway_field_lead_small_called", "tag": "turn_multiway_field_lead_small_called"},
                {"id": "river_seed_multiway_field_lead_big_called", "tag": "turn_multiway_field_lead_big_called"},
            ],
        },
        "turn_multiway_two_fields_before_ip_aggressor_v1": {
            "description": "Controlled first turn template for 3-way spots where two field players act before the IP aggressor.",
            "actors": {"first_field_player": "first_player_to_act", "second_field_player": "second_player_to_act", "aggressor": "ip_aggressor", "field": "combined_field"},
            "nodes": [
                {"id": "root", "actor": "first_field_player", "kind": "decision", "options": [
                    {"action": "bet", "size_ref": "probe_small", "next": "aggressor_vs_first_field_small"},
                    {"action": "bet", "size_ref": "probe_big", "next": "aggressor_vs_first_field_big"},
                    {"action": "check", "next": "second_field_after_first_check"},
                ]},
                {"id": "second_field_after_first_check", "actor": "second_field_player", "kind": "decision", "options": [
                    {"action": "bet", "size_ref": "probe_small", "next": "aggressor_vs_second_field_small"},
                    {"action": "bet", "size_ref": "probe_big", "next": "aggressor_vs_second_field_big"},
                    {"action": "check", "next": "aggressor_after_double_check"},
                ]},
                {"id": "aggressor_after_double_check", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "bet", "size_ref": "bet_small", "next": "field_vs_small"},
                    {"action": "bet", "size_ref": "bet_big", "next": "field_vs_big"},
                    {"action": "check", "next": "river_seed_ip_aggressor_checkback"},
                ]},
                {"id": "field_vs_small", "actor": "field", "kind": "compressed_multiway_decision", "options": [
                    {"action": "fold_all", "next": "terminal_field_folds"},
                    {"action": "one_or_more_calls", "next": "river_seed_ip_aggressor_small_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "aggressor_vs_small_raise"},
                ]},
                {"id": "field_vs_big", "actor": "field", "kind": "compressed_multiway_decision", "options": [
                    {"action": "fold_all", "next": "terminal_field_folds"},
                    {"action": "one_or_more_calls", "next": "river_seed_ip_aggressor_big_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "aggressor_vs_big_raise"},
                ]},
                {"id": "aggressor_vs_small_raise", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_ip_aggressor_small_raise_called"},
                ]},
                {"id": "aggressor_vs_big_raise", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_ip_aggressor_big_raise_called"},
                ]},
                {"id": "aggressor_vs_first_field_small", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_first_field_small_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "terminal_first_field_small_raised"},
                ]},
                {"id": "aggressor_vs_first_field_big", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_first_field_big_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "terminal_first_field_big_raised"},
                ]},
                {"id": "aggressor_vs_second_field_small", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_second_field_small_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "terminal_second_field_small_raised"},
                ]},
                {"id": "aggressor_vs_second_field_big", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_second_field_big_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "terminal_second_field_big_raised"},
                ]},
            ],
            "river_seeds": [
                {"id": "river_seed_ip_aggressor_checkback", "tag": "turn_ip_aggressor_checkback"},
                {"id": "river_seed_ip_aggressor_small_called", "tag": "turn_ip_aggressor_small_called"},
                {"id": "river_seed_ip_aggressor_big_called", "tag": "turn_ip_aggressor_big_called"},
                {"id": "river_seed_ip_aggressor_small_raise_called", "tag": "turn_ip_aggressor_small_raise_called"},
                {"id": "river_seed_ip_aggressor_big_raise_called", "tag": "turn_ip_aggressor_big_raise_called"},
                {"id": "river_seed_first_field_small_called", "tag": "turn_first_field_small_called"},
                {"id": "river_seed_first_field_big_called", "tag": "turn_first_field_big_called"},
                {"id": "river_seed_second_field_small_called", "tag": "turn_second_field_small_called"},
                {"id": "river_seed_second_field_big_called", "tag": "turn_second_field_big_called"},
            ],
        },
        "turn_multiway_oop_aggressor_open_action_v1": {
            "description": "Controlled first turn template for 3-way spots where the aggressor is first to act.",
            "actors": {"aggressor": "out_of_position_aggressor", "field": "two_remaining_players"},
            "nodes": [
                {"id": "root", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "bet", "size_ref": "bet_small", "next": "field_vs_small"},
                    {"action": "bet", "size_ref": "bet_big", "next": "field_vs_big"},
                    {"action": "check", "next": "field_after_check"},
                ]},
                {"id": "field_vs_small", "actor": "field", "kind": "compressed_multiway_decision", "options": [
                    {"action": "fold_all", "next": "terminal_field_folds"},
                    {"action": "one_or_more_calls", "next": "river_seed_oop_aggressor_small_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "aggressor_vs_small_raise"},
                ]},
                {"id": "field_vs_big", "actor": "field", "kind": "compressed_multiway_decision", "options": [
                    {"action": "fold_all", "next": "terminal_field_folds"},
                    {"action": "one_or_more_calls", "next": "river_seed_oop_aggressor_big_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "aggressor_vs_big_raise"},
                ]},
                {"id": "aggressor_vs_small_raise", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_oop_aggressor_small_raise_called"},
                ]},
                {"id": "aggressor_vs_big_raise", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_oop_aggressor_big_raise_called"},
                ]},
                {"id": "field_after_check", "actor": "field", "kind": "compressed_multiway_decision", "options": [
                    {"action": "check_through", "next": "river_seed_oop_aggressor_check_through"},
                    {"action": "stab_small", "next": "aggressor_vs_field_stab_small"},
                    {"action": "stab_big", "next": "aggressor_vs_field_stab_big"},
                ]},
                {"id": "aggressor_vs_field_stab_small", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_field_stab_small_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "terminal_field_stab_small_raised"},
                ]},
                {"id": "aggressor_vs_field_stab_big", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_field_stab_big_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "terminal_field_stab_big_raised"},
                ]},
            ],
            "river_seeds": [
                {"id": "river_seed_oop_aggressor_small_called", "tag": "turn_oop_aggressor_small_called"},
                {"id": "river_seed_oop_aggressor_big_called", "tag": "turn_oop_aggressor_big_called"},
                {"id": "river_seed_oop_aggressor_small_raise_called", "tag": "turn_oop_aggressor_small_raise_called"},
                {"id": "river_seed_oop_aggressor_big_raise_called", "tag": "turn_oop_aggressor_big_raise_called"},
                {"id": "river_seed_oop_aggressor_check_through", "tag": "turn_oop_aggressor_checked_through"},
                {"id": "river_seed_field_stab_small_called", "tag": "turn_field_stab_small_called"},
                {"id": "river_seed_field_stab_big_called", "tag": "turn_field_stab_big_called"},
            ],
        },
        "turn_multiway_field_as_aggressor_v1": {
            "description": "Controlled first turn template for 3-way spots where a field player became the aggressor on the flop — by leading into the preflop aggressor or by raising the aggressor's bet and being called. The field player now holds initiative on the turn; the original aggressor and any remaining players respond compressed.",
            "actors": {
                "field_aggressor": "field_player_who_became_aggressor_on_flop",
                "remaining_players": "compressed_original_aggressor_and_other_field",
            },
            "nodes": [
                {"id": "root", "actor": "field_aggressor", "kind": "decision", "options": [
                    {"action": "bet", "size_ref": "bet_small", "next": "remaining_vs_small"},
                    {"action": "bet", "size_ref": "bet_big", "next": "remaining_vs_big"},
                    {"action": "check", "next": "remaining_after_check"},
                ]},
                {"id": "remaining_vs_small", "actor": "remaining_players", "kind": "compressed_multiway_decision", "options": [
                    {"action": "fold_all", "next": "terminal_folds"},
                    {"action": "one_or_more_calls", "next": "river_seed_field_aggressor_small_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "field_aggressor_vs_small_raise"},
                ]},
                {"id": "remaining_vs_big", "actor": "remaining_players", "kind": "compressed_multiway_decision", "options": [
                    {"action": "fold_all", "next": "terminal_folds"},
                    {"action": "one_or_more_calls", "next": "river_seed_field_aggressor_big_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "field_aggressor_vs_big_raise"},
                ]},
                {"id": "field_aggressor_vs_small_raise", "actor": "field_aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_field_aggressor_small_raise_called"},
                ]},
                {"id": "field_aggressor_vs_big_raise", "actor": "field_aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_field_aggressor_big_raise_called"},
                ]},
                {"id": "remaining_after_check", "actor": "remaining_players", "kind": "compressed_multiway_decision", "options": [
                    {"action": "check_through", "next": "river_seed_field_aggressor_checked_through"},
                    {"action": "stab_small", "next": "field_aggressor_vs_stab_small"},
                    {"action": "stab_big", "next": "field_aggressor_vs_stab_big"},
                ]},
                {"id": "field_aggressor_vs_stab_small", "actor": "field_aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_field_aggressor_vs_stab_small_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "terminal_stab_small_raised"},
                ]},
                {"id": "field_aggressor_vs_stab_big", "actor": "field_aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "river_seed_field_aggressor_vs_stab_big_called"},
                    {"action": "raise", "size_ref": "raise_small", "next": "terminal_stab_big_raised"},
                ]},
            ],
            "river_seeds": [
                {"id": "river_seed_field_aggressor_small_called", "tag": "turn_field_aggressor_small_called"},
                {"id": "river_seed_field_aggressor_big_called", "tag": "turn_field_aggressor_big_called"},
                {"id": "river_seed_field_aggressor_small_raise_called", "tag": "turn_field_aggressor_small_raise_called"},
                {"id": "river_seed_field_aggressor_big_raise_called", "tag": "turn_field_aggressor_big_raise_called"},
                {"id": "river_seed_field_aggressor_checked_through", "tag": "turn_field_aggressor_checked_through"},
                {"id": "river_seed_field_aggressor_vs_stab_small_called", "tag": "turn_field_aggressor_vs_stab_small_called"},
                {"id": "river_seed_field_aggressor_vs_stab_big_called", "tag": "turn_field_aggressor_vs_stab_big_called"},
            ],
            "terminal_nodes": ["terminal_fold", "terminal_folds", "terminal_stab_small_raised", "terminal_stab_big_raised"],
            "deferred_features": ["probe ownership inside compressed remaining players", "river expansion"],
        },
    },
    "families": {
        "turn_heads_up_ip_last_after_checkback": {
            "template_ref": "turn_oop_can_lead_or_check_to_ip_v1",
            "street": "turn",
            "line_prefix": "turn.hup.after-checkback.ip-last",
            "size_profile_ref": "turn_heads_up_ip_last_v1",
            "source_flop_families": [
                "srp_ip_pfr_flop",
                "srp_oop_caller_flop",
                "srp_oop_pfr_flop",
                "three_bet_ip_3bettor_flop",
                "three_bet_oop_3bettor_flop",
                "bvb_flop_aggressive",
                "bvb_defender_flop",
                "raised_after_limp_ip_aggressor_flop",
                "raised_after_limp_oop_aggressor_flop",
                "four_bet_ip_aggressor_flop",
                "four_bet_oop_aggressor_flop",
                "five_bet_plus_ip_aggressor_flop",
                "five_bet_plus_oop_aggressor_flop",
            ],
        },
        "turn_heads_up_ip_aggressor_after_flop_bet_called": {
            "template_ref": "turn_oop_can_lead_or_check_to_ip_v1",
            "street": "turn",
            "line_prefix": "turn.hup.ip-aggressor.after-flop-bet-called",
            "size_profile_ref": "turn_heads_up_ip_last_v1",
            "source_flop_families": ["srp_ip_pfr_flop", "srp_oop_caller_flop", "three_bet_ip_3bettor_flop", "raised_after_limp_ip_aggressor_flop", "four_bet_ip_aggressor_flop", "five_bet_plus_ip_aggressor_flop"],
        },
        "turn_heads_up_oop_aggressor_after_flop_bet_called": {
            "template_ref": "turn_oop_aggressor_open_action_v1",
            "street": "turn",
            "line_prefix": "turn.hup.oop-aggressor.after-flop-bet-called",
            "size_profile_ref": "turn_heads_up_oop_aggressor_v1",
            "source_flop_families": ["srp_oop_pfr_flop", "three_bet_oop_3bettor_flop", "bvb_flop_aggressive", "bvb_defender_flop", "raised_after_limp_oop_aggressor_flop", "four_bet_oop_aggressor_flop", "five_bet_plus_oop_aggressor_flop"],
        },
        "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called": {
            "template_ref": "turn_oop_aggressor_open_action_v1",
            "street": "turn",
            "line_prefix": "turn.hup.oop-aggressor.after-flop-raise-or-lead-called",
            "size_profile_ref": "turn_heads_up_oop_aggressor_v1",
            "source_flop_families": ["srp_ip_pfr_flop", "srp_oop_caller_flop", "three_bet_ip_3bettor_flop", "raised_after_limp_ip_aggressor_flop", "four_bet_ip_aggressor_flop", "five_bet_plus_ip_aggressor_flop"],
        },
        "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called": {
            "template_ref": "turn_oop_can_lead_or_check_to_ip_v1",
            "street": "turn",
            "line_prefix": "turn.hup.ip-aggressor.after-flop-probe-or-raise-called",
            "size_profile_ref": "turn_heads_up_ip_last_v1",
            "source_flop_families": ["srp_oop_pfr_flop", "three_bet_oop_3bettor_flop", "bvb_flop_aggressive", "bvb_defender_flop", "raised_after_limp_oop_aggressor_flop", "four_bet_oop_aggressor_flop", "five_bet_plus_oop_aggressor_flop"],
        },
        "turn_3way_middle_aggressor_continuation": {
            "template_ref": "turn_multiway_field_lead_or_check_to_aggressor_v1",
            "street": "turn",
            "line_prefix": "turn.3way.middle-aggressor.continuation",
            "size_profile_ref": "turn_multiway_v1",
            "source_flop_families": ["multiway_srp_3way_middle_aggressor_flop", "multiway_3bp_3way_middle_aggressor_flop", "four_bet_3way_middle_aggressor_flop", "raised_after_limp_3way_middle_aggressor_flop"],
        },
        "turn_3way_ip_aggressor_continuation": {
            "template_ref": "turn_multiway_two_fields_before_ip_aggressor_v1",
            "street": "turn",
            "line_prefix": "turn.3way.ip-aggressor.continuation",
            "size_profile_ref": "turn_multiway_v1",
            "source_flop_families": ["multiway_srp_3way_ip_aggressor_flop", "multiway_3bp_3way_ip_aggressor_flop", "four_bet_3way_ip_aggressor_flop", "raised_after_limp_3way_ip_aggressor_flop"],
        },
        "turn_3way_oop_aggressor_continuation": {
            "template_ref": "turn_multiway_oop_aggressor_open_action_v1",
            "street": "turn",
            "line_prefix": "turn.3way.oop-aggressor.continuation",
            "size_profile_ref": "turn_multiway_v1",
            "source_flop_families": ["multiway_srp_3way_oop_aggressor_flop", "multiway_3bp_3way_oop_aggressor_flop", "four_bet_3way_oop_aggressor_flop", "raised_after_limp_3way_oop_aggressor_flop"],
        },
        "turn_3way_field_aggressor_continuation": {
            "template_ref": "turn_multiway_field_as_aggressor_v1",
            "street": "turn",
            "line_prefix": "turn.3way.field-aggressor.continuation",
            "size_profile_ref": "turn_multiway_v1",
            "source_flop_families": [
                "multiway_srp_3way_ip_aggressor_flop",
                "multiway_3bp_3way_ip_aggressor_flop",
                "four_bet_3way_ip_aggressor_flop",
                "raised_after_limp_3way_ip_aggressor_flop",
                "multiway_srp_3way_middle_aggressor_flop",
                "multiway_3bp_3way_middle_aggressor_flop",
                "four_bet_3way_middle_aggressor_flop",
                "raised_after_limp_3way_middle_aggressor_flop",
                "multiway_srp_3way_oop_aggressor_flop",
                "multiway_3bp_3way_oop_aggressor_flop",
                "four_bet_3way_oop_aggressor_flop",
                "raised_after_limp_3way_oop_aggressor_flop",
            ],
        },
    },
    "seed_family_map": {
        "srp_ip_pfr_flop": {
            "turn_seed_checkback": "turn_heads_up_ip_last_after_checkback",
            "turn_seed_small_called": "turn_heads_up_ip_aggressor_after_flop_bet_called",
            "turn_seed_big_called": "turn_heads_up_ip_aggressor_after_flop_bet_called",
            "turn_seed_small_raise_small_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
            "turn_seed_small_raise_big_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
            "turn_seed_big_raise_small_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
            "turn_seed_big_raise_big_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
        },
        "srp_oop_caller_flop": {
            "turn_seed_checkback": "turn_heads_up_ip_last_after_checkback",
            "turn_seed_small_called": "turn_heads_up_ip_aggressor_after_flop_bet_called",
            "turn_seed_big_called": "turn_heads_up_ip_aggressor_after_flop_bet_called",
            "turn_seed_small_raise_small_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
            "turn_seed_small_raise_big_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
            "turn_seed_big_raise_small_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
            "turn_seed_big_raise_big_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
        },
        "srp_oop_pfr_flop": {
            "turn_seed_checked_through": "turn_heads_up_ip_last_after_checkback",
            "turn_seed_small_called": "turn_heads_up_oop_aggressor_after_flop_bet_called",
            "turn_seed_big_called": "turn_heads_up_oop_aggressor_after_flop_bet_called",
            "turn_seed_probe_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_probe_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_small_raise_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_small_raise_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_big_raise_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_big_raise_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
        },
        "three_bet_ip_3bettor_flop": {
            "turn_seed_checkback": "turn_heads_up_ip_last_after_checkback",
            "turn_seed_small_called": "turn_heads_up_ip_aggressor_after_flop_bet_called",
            "turn_seed_big_called": "turn_heads_up_ip_aggressor_after_flop_bet_called",
            "turn_seed_small_raise_small_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
            "turn_seed_small_raise_big_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
            "turn_seed_big_raise_small_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
            "turn_seed_big_raise_big_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
        },
        "raised_after_limp_ip_aggressor_flop": {
            "turn_seed_ip_checkback": "turn_heads_up_ip_last_after_checkback",
            "turn_seed_ip_small_called": "turn_heads_up_ip_aggressor_after_flop_bet_called",
            "turn_seed_ip_big_called": "turn_heads_up_ip_aggressor_after_flop_bet_called",
            "turn_seed_ip_small_raise_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
            "turn_seed_ip_big_raise_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
            "turn_seed_oop_lead_small_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
            "turn_seed_oop_lead_big_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
        },
        "four_bet_ip_aggressor_flop": {
            "turn_seed_ip_checkback": "turn_heads_up_ip_last_after_checkback",
            "turn_seed_ip_small_called": "turn_heads_up_ip_aggressor_after_flop_bet_called",
            "turn_seed_ip_big_called": "turn_heads_up_ip_aggressor_after_flop_bet_called",
            "turn_seed_ip_small_raise_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
            "turn_seed_ip_big_raise_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
            "turn_seed_oop_lead_small_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
            "turn_seed_oop_lead_big_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
        },
        "five_bet_plus_ip_aggressor_flop": {
            "turn_seed_ip_checkback": "turn_heads_up_ip_last_after_checkback",
            "turn_seed_ip_small_called": "turn_heads_up_ip_aggressor_after_flop_bet_called",
            "turn_seed_ip_big_called": "turn_heads_up_ip_aggressor_after_flop_bet_called",
            "turn_seed_ip_small_raise_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
            "turn_seed_ip_big_raise_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
            "turn_seed_oop_lead_small_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
            "turn_seed_oop_lead_big_called": "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
        },
        "three_bet_oop_3bettor_flop": {
            "turn_seed_checked_through": "turn_heads_up_ip_last_after_checkback",
            "turn_seed_small_called": "turn_heads_up_oop_aggressor_after_flop_bet_called",
            "turn_seed_big_called": "turn_heads_up_oop_aggressor_after_flop_bet_called",
            "turn_seed_probe_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_probe_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_small_raise_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_small_raise_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_big_raise_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_big_raise_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
        },
        "bvb_flop_aggressive": {
            "turn_seed_checked_through": "turn_heads_up_ip_last_after_checkback",
            "turn_seed_small_called": "turn_heads_up_oop_aggressor_after_flop_bet_called",
            "turn_seed_big_called": "turn_heads_up_oop_aggressor_after_flop_bet_called",
            "turn_seed_probe_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_probe_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_small_raise_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_small_raise_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_big_raise_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_big_raise_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
        },
        "bvb_defender_flop": {
            "turn_seed_checked_through": "turn_heads_up_ip_last_after_checkback",
            "turn_seed_small_called": "turn_heads_up_oop_aggressor_after_flop_bet_called",
            "turn_seed_big_called": "turn_heads_up_oop_aggressor_after_flop_bet_called",
            "turn_seed_probe_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_probe_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_small_raise_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_small_raise_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_big_raise_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_big_raise_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
        },
        "raised_after_limp_oop_aggressor_flop": {
            "turn_seed_checked_through": "turn_heads_up_ip_last_after_checkback",
            "turn_seed_small_called": "turn_heads_up_oop_aggressor_after_flop_bet_called",
            "turn_seed_big_called": "turn_heads_up_oop_aggressor_after_flop_bet_called",
            "turn_seed_probe_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_probe_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_small_raise_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_small_raise_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_big_raise_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_big_raise_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
        },
        "four_bet_oop_aggressor_flop": {
            "turn_seed_checked_through": "turn_heads_up_ip_last_after_checkback",
            "turn_seed_small_called": "turn_heads_up_oop_aggressor_after_flop_bet_called",
            "turn_seed_big_called": "turn_heads_up_oop_aggressor_after_flop_bet_called",
            "turn_seed_probe_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_probe_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_small_raise_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_small_raise_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_big_raise_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_big_raise_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
        },
        "five_bet_plus_oop_aggressor_flop": {
            "turn_seed_checked_through": "turn_heads_up_ip_last_after_checkback",
            "turn_seed_small_called": "turn_heads_up_oop_aggressor_after_flop_bet_called",
            "turn_seed_big_called": "turn_heads_up_oop_aggressor_after_flop_bet_called",
            "turn_seed_probe_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_probe_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_small_raise_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_small_raise_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_big_raise_small_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            "turn_seed_big_raise_big_called": "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
        },
        "multiway_srp_3way_middle_aggressor_flop": {
            "turn_seed_multiway_checkback": "turn_3way_middle_aggressor_continuation",
            "turn_seed_multiway_small_called": "turn_3way_middle_aggressor_continuation",
            "turn_seed_multiway_big_called": "turn_3way_middle_aggressor_continuation",
            "turn_seed_multiway_small_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_multiway_big_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_multiway_field_lead_small_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_multiway_field_lead_big_called": "turn_3way_field_aggressor_continuation",
        },
        "multiway_3bp_3way_middle_aggressor_flop": {
            "turn_seed_multiway_checkback": "turn_3way_middle_aggressor_continuation",
            "turn_seed_multiway_small_called": "turn_3way_middle_aggressor_continuation",
            "turn_seed_multiway_big_called": "turn_3way_middle_aggressor_continuation",
            "turn_seed_multiway_small_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_multiway_big_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_multiway_field_lead_small_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_multiway_field_lead_big_called": "turn_3way_field_aggressor_continuation",
        },
        "four_bet_3way_middle_aggressor_flop": {
            "turn_seed_multiway_checkback": "turn_3way_middle_aggressor_continuation",
            "turn_seed_multiway_small_called": "turn_3way_middle_aggressor_continuation",
            "turn_seed_multiway_big_called": "turn_3way_middle_aggressor_continuation",
            "turn_seed_multiway_small_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_multiway_big_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_multiway_field_lead_small_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_multiway_field_lead_big_called": "turn_3way_field_aggressor_continuation",
        },
        "raised_after_limp_3way_middle_aggressor_flop": {
            "turn_seed_multiway_checkback": "turn_3way_middle_aggressor_continuation",
            "turn_seed_multiway_small_called": "turn_3way_middle_aggressor_continuation",
            "turn_seed_multiway_big_called": "turn_3way_middle_aggressor_continuation",
            "turn_seed_multiway_small_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_multiway_big_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_multiway_field_lead_small_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_multiway_field_lead_big_called": "turn_3way_field_aggressor_continuation",
        },
        "multiway_srp_3way_ip_aggressor_flop": {
            "turn_seed_ip_aggressor_checkback": "turn_3way_ip_aggressor_continuation",
            "turn_seed_ip_aggressor_small_called": "turn_3way_ip_aggressor_continuation",
            "turn_seed_ip_aggressor_big_called": "turn_3way_ip_aggressor_continuation",
            "turn_seed_ip_aggressor_small_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_ip_aggressor_big_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_first_field_small_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_first_field_big_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_second_field_small_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_second_field_big_called": "turn_3way_field_aggressor_continuation",
        },
        "multiway_3bp_3way_ip_aggressor_flop": {
            "turn_seed_ip_aggressor_checkback": "turn_3way_ip_aggressor_continuation",
            "turn_seed_ip_aggressor_small_called": "turn_3way_ip_aggressor_continuation",
            "turn_seed_ip_aggressor_big_called": "turn_3way_ip_aggressor_continuation",
            "turn_seed_ip_aggressor_small_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_ip_aggressor_big_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_first_field_small_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_first_field_big_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_second_field_small_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_second_field_big_called": "turn_3way_field_aggressor_continuation",
        },
        "four_bet_3way_ip_aggressor_flop": {
            "turn_seed_ip_aggressor_checkback": "turn_3way_ip_aggressor_continuation",
            "turn_seed_ip_aggressor_small_called": "turn_3way_ip_aggressor_continuation",
            "turn_seed_ip_aggressor_big_called": "turn_3way_ip_aggressor_continuation",
            "turn_seed_ip_aggressor_small_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_ip_aggressor_big_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_first_field_small_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_first_field_big_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_second_field_small_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_second_field_big_called": "turn_3way_field_aggressor_continuation",
        },
        "raised_after_limp_3way_ip_aggressor_flop": {
            "turn_seed_ip_aggressor_checkback": "turn_3way_ip_aggressor_continuation",
            "turn_seed_ip_aggressor_small_called": "turn_3way_ip_aggressor_continuation",
            "turn_seed_ip_aggressor_big_called": "turn_3way_ip_aggressor_continuation",
            "turn_seed_ip_aggressor_small_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_ip_aggressor_big_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_first_field_small_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_first_field_big_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_second_field_small_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_second_field_big_called": "turn_3way_field_aggressor_continuation",
        },
        "multiway_srp_3way_oop_aggressor_flop": {
            "turn_seed_oop_aggressor_check_through": "turn_3way_oop_aggressor_continuation",
            "turn_seed_oop_aggressor_small_called": "turn_3way_oop_aggressor_continuation",
            "turn_seed_oop_aggressor_big_called": "turn_3way_oop_aggressor_continuation",
            "turn_seed_oop_aggressor_small_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_oop_aggressor_big_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_field_stab_small_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_field_stab_big_called": "turn_3way_field_aggressor_continuation",
        },
        "multiway_3bp_3way_oop_aggressor_flop": {
            "turn_seed_oop_aggressor_check_through": "turn_3way_oop_aggressor_continuation",
            "turn_seed_oop_aggressor_small_called": "turn_3way_oop_aggressor_continuation",
            "turn_seed_oop_aggressor_big_called": "turn_3way_oop_aggressor_continuation",
            "turn_seed_oop_aggressor_small_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_oop_aggressor_big_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_field_stab_small_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_field_stab_big_called": "turn_3way_field_aggressor_continuation",
        },
        "four_bet_3way_oop_aggressor_flop": {
            "turn_seed_oop_aggressor_check_through": "turn_3way_oop_aggressor_continuation",
            "turn_seed_oop_aggressor_small_called": "turn_3way_oop_aggressor_continuation",
            "turn_seed_oop_aggressor_big_called": "turn_3way_oop_aggressor_continuation",
            "turn_seed_oop_aggressor_small_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_oop_aggressor_big_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_field_stab_small_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_field_stab_big_called": "turn_3way_field_aggressor_continuation",
        },
        "raised_after_limp_3way_oop_aggressor_flop": {
            "turn_seed_oop_aggressor_check_through": "turn_3way_oop_aggressor_continuation",
            "turn_seed_oop_aggressor_small_called": "turn_3way_oop_aggressor_continuation",
            "turn_seed_oop_aggressor_big_called": "turn_3way_oop_aggressor_continuation",
            "turn_seed_oop_aggressor_small_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_oop_aggressor_big_raise_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_field_stab_small_called": "turn_3way_field_aggressor_continuation",
            "turn_seed_field_stab_big_called": "turn_3way_field_aggressor_continuation",
        },
    },
}


RIVER_TREE_SPEC_LIBRARY: dict[str, Any] = {
    "meta": {
        "name": "river-tree-spec-library",
        "schema_version": 1,
        "street": "river",
        "notes": [
            "These are controlled river-side placeholders built only off stabilized turn families.",
            "They intentionally stop at a shallow terminal layer and do not claim full river-tree coverage.",
            "Turn families remain the bridge into river placeholders via explicit river seed mappings.",
        ],
    },
    "size_profiles": {
        "river_heads_up_oop_first_v1": {
            "bet_small": "66% pot",
            "bet_big": "100% pot",
            "probe_small": "66% pot",
            "probe_big": "100% pot",
        },
        "river_multiway_v1": {
            "bet_small": "66% pot",
            "bet_big": "100% pot",
            "probe_small": "66% pot",
            "probe_big": "100% pot",
        },
    },
    "templates": {
        "river_oop_first_closed_resolution_v1": {
            "description": "Controlled first river placeholder for heads-up spots where the OOP player acts first and the branch closes without a further raise layer.",
            "actors": {"oop_player": "out_of_position_player", "ip_player": "in_position_player"},
            "nodes": [
                {"id": "root", "actor": "oop_player", "kind": "decision", "options": [
                    {"action": "check", "next": "ip_after_check"},
                    {"action": "bet", "size_ref": "probe_small", "next": "ip_vs_probe_small"},
                    {"action": "bet", "size_ref": "probe_big", "next": "ip_vs_probe_big"},
                ]},
                {"id": "ip_after_check", "actor": "ip_player", "kind": "decision", "options": [
                    {"action": "check", "next": "terminal_showdown"},
                    {"action": "bet", "size_ref": "bet_small", "next": "oop_vs_small"},
                    {"action": "bet", "size_ref": "bet_big", "next": "oop_vs_big"},
                ]},
                {"id": "oop_vs_small", "actor": "oop_player", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "terminal_showdown"},
                ]},
                {"id": "oop_vs_big", "actor": "oop_player", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "terminal_showdown"},
                ]},
                {"id": "ip_vs_probe_small", "actor": "ip_player", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "terminal_showdown"},
                ]},
                {"id": "ip_vs_probe_big", "actor": "ip_player", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "terminal_showdown"},
                ]},
            ],
            "terminal_nodes": ["terminal_fold", "terminal_showdown"],
            "deferred_features": ["river raises", "overbet and jam branches", "blocker-led strategy detail"],
        },
        "river_multiway_first_field_resolution_v1": {
            "description": "Controlled first river placeholder for 3-way spots where a field player acts before the aggressor.",
            "actors": {"first_field_player": "first_player_to_act", "aggressor": "middle_aggressor", "field": "remaining_field"},
            "nodes": [
                {"id": "root", "actor": "first_field_player", "kind": "decision", "options": [
                    {"action": "check", "next": "aggressor_after_check"},
                    {"action": "bet", "size_ref": "probe_small", "next": "aggressor_vs_field_lead_small"},
                    {"action": "bet", "size_ref": "probe_big", "next": "aggressor_vs_field_lead_big"},
                ]},
                {"id": "aggressor_after_check", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "bet", "size_ref": "bet_small", "next": "field_vs_small"},
                    {"action": "bet", "size_ref": "bet_big", "next": "field_vs_big"},
                    {"action": "check", "next": "terminal_showdown"},
                ]},
                {"id": "field_vs_small", "actor": "field", "kind": "compressed_multiway_decision", "options": [
                    {"action": "fold_all", "next": "terminal_field_folds"},
                    {"action": "one_or_more_calls", "next": "terminal_showdown"},
                ]},
                {"id": "field_vs_big", "actor": "field", "kind": "compressed_multiway_decision", "options": [
                    {"action": "fold_all", "next": "terminal_field_folds"},
                    {"action": "one_or_more_calls", "next": "terminal_showdown"},
                ]},
                {"id": "aggressor_vs_field_lead_small", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "terminal_showdown"},
                ]},
                {"id": "aggressor_vs_field_lead_big", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "terminal_showdown"},
                ]},
            ],
            "terminal_nodes": ["terminal_fold", "terminal_field_folds", "terminal_showdown"],
            "deferred_features": ["multiway river raises", "exact downstream caller ownership", "overbet and jam branches"],
        },
        "river_multiway_two_fields_before_ip_resolution_v1": {
            "description": "Controlled first river placeholder for 3-way spots where two field players act before the IP aggressor.",
            "actors": {"first_field_player": "first_player_to_act", "second_field_player": "second_player_to_act", "aggressor": "ip_aggressor", "field": "combined_field"},
            "nodes": [
                {"id": "root", "actor": "first_field_player", "kind": "decision", "options": [
                    {"action": "bet", "size_ref": "probe_small", "next": "aggressor_vs_first_field_small"},
                    {"action": "bet", "size_ref": "probe_big", "next": "aggressor_vs_first_field_big"},
                    {"action": "check", "next": "second_field_after_first_check"},
                ]},
                {"id": "second_field_after_first_check", "actor": "second_field_player", "kind": "decision", "options": [
                    {"action": "bet", "size_ref": "probe_small", "next": "aggressor_vs_second_field_small"},
                    {"action": "bet", "size_ref": "probe_big", "next": "aggressor_vs_second_field_big"},
                    {"action": "check", "next": "aggressor_after_double_check"},
                ]},
                {"id": "aggressor_after_double_check", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "bet", "size_ref": "bet_small", "next": "field_vs_small"},
                    {"action": "bet", "size_ref": "bet_big", "next": "field_vs_big"},
                    {"action": "check", "next": "terminal_showdown"},
                ]},
                {"id": "field_vs_small", "actor": "field", "kind": "compressed_multiway_decision", "options": [
                    {"action": "fold_all", "next": "terminal_field_folds"},
                    {"action": "one_or_more_calls", "next": "terminal_showdown"},
                ]},
                {"id": "field_vs_big", "actor": "field", "kind": "compressed_multiway_decision", "options": [
                    {"action": "fold_all", "next": "terminal_field_folds"},
                    {"action": "one_or_more_calls", "next": "terminal_showdown"},
                ]},
                {"id": "aggressor_vs_first_field_small", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "terminal_showdown"},
                ]},
                {"id": "aggressor_vs_first_field_big", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "terminal_showdown"},
                ]},
                {"id": "aggressor_vs_second_field_small", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "terminal_showdown"},
                ]},
                {"id": "aggressor_vs_second_field_big", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "terminal_showdown"},
                ]},
            ],
            "terminal_nodes": ["terminal_fold", "terminal_field_folds", "terminal_showdown"],
            "deferred_features": ["multiway river raises", "exact field ownership after checks", "overbet and jam branches"],
        },
        "river_multiway_oop_aggressor_resolution_v1": {
            "description": "Controlled first river placeholder for 3-way spots where the aggressor is first to act.",
            "actors": {"aggressor": "out_of_position_aggressor", "field": "two_remaining_players"},
            "nodes": [
                {"id": "root", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "bet", "size_ref": "bet_small", "next": "field_vs_small"},
                    {"action": "bet", "size_ref": "bet_big", "next": "field_vs_big"},
                    {"action": "check", "next": "field_after_check"},
                ]},
                {"id": "field_vs_small", "actor": "field", "kind": "compressed_multiway_decision", "options": [
                    {"action": "fold_all", "next": "terminal_field_folds"},
                    {"action": "one_or_more_calls", "next": "terminal_showdown"},
                ]},
                {"id": "field_vs_big", "actor": "field", "kind": "compressed_multiway_decision", "options": [
                    {"action": "fold_all", "next": "terminal_field_folds"},
                    {"action": "one_or_more_calls", "next": "terminal_showdown"},
                ]},
                {"id": "field_after_check", "actor": "field", "kind": "compressed_multiway_decision", "options": [
                    {"action": "check_through", "next": "terminal_showdown"},
                    {"action": "stab_small", "next": "aggressor_vs_field_stab_small"},
                    {"action": "stab_big", "next": "aggressor_vs_field_stab_big"},
                ]},
                {"id": "aggressor_vs_field_stab_small", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "terminal_showdown"},
                ]},
                {"id": "aggressor_vs_field_stab_big", "actor": "aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "terminal_showdown"},
                ]},
            ],
            "terminal_nodes": ["terminal_fold", "terminal_field_folds", "terminal_showdown"],
            "deferred_features": ["multiway river raises", "exact stab ownership inside compressed field", "overbet and jam branches"],
        },
        "river_multiway_field_aggressor_resolution_v1": {
            "description": "Controlled first river placeholder for 3-way spots where a field player reached river as the aggressor.",
            "actors": {
                "field_aggressor": "field_player_who_became_aggressor_before_river",
                "remaining_players": "compressed_original_aggressor_and_other_field",
            },
            "nodes": [
                {"id": "root", "actor": "field_aggressor", "kind": "decision", "options": [
                    {"action": "bet", "size_ref": "bet_small", "next": "remaining_vs_small"},
                    {"action": "bet", "size_ref": "bet_big", "next": "remaining_vs_big"},
                    {"action": "check", "next": "remaining_after_check"},
                ]},
                {"id": "remaining_vs_small", "actor": "remaining_players", "kind": "compressed_multiway_decision", "options": [
                    {"action": "fold_all", "next": "terminal_field_folds"},
                    {"action": "one_or_more_calls", "next": "terminal_showdown"},
                ]},
                {"id": "remaining_vs_big", "actor": "remaining_players", "kind": "compressed_multiway_decision", "options": [
                    {"action": "fold_all", "next": "terminal_field_folds"},
                    {"action": "one_or_more_calls", "next": "terminal_showdown"},
                ]},
                {"id": "remaining_after_check", "actor": "remaining_players", "kind": "compressed_multiway_decision", "options": [
                    {"action": "check_through", "next": "terminal_showdown"},
                    {"action": "stab_small", "next": "field_aggressor_vs_stab_small"},
                    {"action": "stab_big", "next": "field_aggressor_vs_stab_big"},
                ]},
                {"id": "field_aggressor_vs_stab_small", "actor": "field_aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "terminal_showdown"},
                ]},
                {"id": "field_aggressor_vs_stab_big", "actor": "field_aggressor", "kind": "decision", "options": [
                    {"action": "fold", "next": "terminal_fold"},
                    {"action": "call", "next": "terminal_showdown"},
                ]},
            ],
            "terminal_nodes": ["terminal_fold", "terminal_field_folds", "terminal_showdown"],
            "deferred_features": ["multiway river raises", "probe ownership inside compressed remaining players", "overbet and jam branches"],
        },
    },
    "families": {
        "river_heads_up_oop_first_resolution": {
            "template_ref": "river_oop_first_closed_resolution_v1",
            "street": "river",
            "line_prefix": "river.hup.oop-first.resolution",
            "size_profile_ref": "river_heads_up_oop_first_v1",
            "board_size_policy": {
                "A_HIGH_DRY": {"remove_size_refs": ["bet_big", "probe_big"]},
                "BROADWAY_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]},
                "ACE_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "KING_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "LOW_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "HIGH_CARD_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "LOW_DISCONNECTED": {"remove_size_refs": ["bet_big", "probe_big"]},
            },
            "source_turn_families": [
                "turn_heads_up_ip_last_after_checkback",
                "turn_heads_up_ip_aggressor_after_flop_bet_called",
                "turn_heads_up_oop_aggressor_after_flop_bet_called",
                "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called",
                "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called",
            ],
        },
        "river_3way_middle_aggressor_resolution": {
            "template_ref": "river_multiway_first_field_resolution_v1",
            "street": "river",
            "line_prefix": "river.3way.middle-aggressor.resolution",
            "size_profile_ref": "river_multiway_v1",
            "board_size_policy": {
                "A_HIGH_DRY": {"remove_size_refs": ["bet_big", "probe_big"]},
                "BROADWAY_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]},
                "ACE_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "KING_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "LOW_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
            },
            "source_turn_families": ["turn_3way_middle_aggressor_continuation"],
        },
        "river_3way_ip_aggressor_resolution": {
            "template_ref": "river_multiway_two_fields_before_ip_resolution_v1",
            "street": "river",
            "line_prefix": "river.3way.ip-aggressor.resolution",
            "size_profile_ref": "river_multiway_v1",
            "board_size_policy": {
                "A_HIGH_DRY": {"remove_size_refs": ["bet_big", "probe_big"]},
                "BROADWAY_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big", "probe_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big", "probe_big"]},
                "ACE_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "KING_HIGH": {"remove_size_refs": ["bet_big", "probe_big"]},
                "LOW_STATIC": {"remove_size_refs": ["bet_big", "probe_big"]},
            },
            "source_turn_families": ["turn_3way_ip_aggressor_continuation"],
        },
        "river_3way_oop_aggressor_resolution": {
            "template_ref": "river_multiway_oop_aggressor_resolution_v1",
            "street": "river",
            "line_prefix": "river.3way.oop-aggressor.resolution",
            "size_profile_ref": "river_multiway_v1",
            "board_size_policy": {
                "A_HIGH_DRY": {"remove_size_refs": ["bet_big"], "remove_actions": ["stab_big"]},
                "BROADWAY_STATIC": {"remove_size_refs": ["bet_big"], "remove_actions": ["stab_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big"], "remove_actions": ["stab_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big"], "remove_actions": ["stab_big"]},
                "ACE_HIGH": {"remove_size_refs": ["bet_big"], "remove_actions": ["stab_big"]},
                "KING_HIGH": {"remove_size_refs": ["bet_big"], "remove_actions": ["stab_big"]},
                "LOW_STATIC": {"remove_size_refs": ["bet_big"], "remove_actions": ["stab_big"]},
            },
            "source_turn_families": ["turn_3way_oop_aggressor_continuation"],
        },
        "river_3way_field_aggressor_resolution": {
            "template_ref": "river_multiway_field_aggressor_resolution_v1",
            "street": "river",
            "line_prefix": "river.3way.field-aggressor.resolution",
            "size_profile_ref": "river_multiway_v1",
            "board_size_policy": {
                "A_HIGH_DRY": {"remove_size_refs": ["bet_big"], "remove_actions": ["stab_big"]},
                "BROADWAY_STATIC": {"remove_size_refs": ["bet_big"], "remove_actions": ["stab_big"]},
                "PAIRED": {"remove_size_refs": ["bet_big"], "remove_actions": ["stab_big"]},
                "MONOTONE": {"remove_size_refs": ["bet_big"], "remove_actions": ["stab_big"]},
                "ACE_HIGH": {"remove_size_refs": ["bet_big"], "remove_actions": ["stab_big"]},
                "KING_HIGH": {"remove_size_refs": ["bet_big"], "remove_actions": ["stab_big"]},
                "LOW_STATIC": {"remove_size_refs": ["bet_big"], "remove_actions": ["stab_big"]},
            },
            "source_turn_families": ["turn_3way_field_aggressor_continuation"],
        },
    },
    "seed_family_map": {
        "turn_heads_up_ip_last_after_checkback": {
            "river_seed_checked_through": "river_heads_up_oop_first_resolution",
            "river_seed_ip_small_called": "river_heads_up_oop_first_resolution",
            "river_seed_ip_big_called": "river_heads_up_oop_first_resolution",
            "river_seed_ip_small_raise_called": "river_heads_up_oop_first_resolution",
            "river_seed_ip_big_raise_called": "river_heads_up_oop_first_resolution",
            "river_seed_oop_probe_small_called": "river_heads_up_oop_first_resolution",
            "river_seed_oop_probe_big_called": "river_heads_up_oop_first_resolution",
        },
        "turn_heads_up_ip_aggressor_after_flop_bet_called": {
            "river_seed_checked_through": "river_heads_up_oop_first_resolution",
            "river_seed_ip_small_called": "river_heads_up_oop_first_resolution",
            "river_seed_ip_big_called": "river_heads_up_oop_first_resolution",
            "river_seed_ip_small_raise_called": "river_heads_up_oop_first_resolution",
            "river_seed_ip_big_raise_called": "river_heads_up_oop_first_resolution",
            "river_seed_oop_probe_small_called": "river_heads_up_oop_first_resolution",
            "river_seed_oop_probe_big_called": "river_heads_up_oop_first_resolution",
        },
        "turn_heads_up_oop_aggressor_after_flop_bet_called": {
            "river_seed_checked_through": "river_heads_up_oop_first_resolution",
            "river_seed_small_called": "river_heads_up_oop_first_resolution",
            "river_seed_big_called": "river_heads_up_oop_first_resolution",
            "river_seed_small_raise_called": "river_heads_up_oop_first_resolution",
            "river_seed_big_raise_called": "river_heads_up_oop_first_resolution",
            "river_seed_probe_small_called": "river_heads_up_oop_first_resolution",
            "river_seed_probe_big_called": "river_heads_up_oop_first_resolution",
        },
        "turn_heads_up_oop_aggressor_after_flop_raise_or_lead_called": {
            "river_seed_checked_through": "river_heads_up_oop_first_resolution",
            "river_seed_small_called": "river_heads_up_oop_first_resolution",
            "river_seed_big_called": "river_heads_up_oop_first_resolution",
            "river_seed_small_raise_called": "river_heads_up_oop_first_resolution",
            "river_seed_big_raise_called": "river_heads_up_oop_first_resolution",
            "river_seed_probe_small_called": "river_heads_up_oop_first_resolution",
            "river_seed_probe_big_called": "river_heads_up_oop_first_resolution",
        },
        "turn_heads_up_ip_aggressor_after_flop_probe_or_raise_called": {
            "river_seed_checked_through": "river_heads_up_oop_first_resolution",
            "river_seed_ip_small_called": "river_heads_up_oop_first_resolution",
            "river_seed_ip_big_called": "river_heads_up_oop_first_resolution",
            "river_seed_ip_small_raise_called": "river_heads_up_oop_first_resolution",
            "river_seed_ip_big_raise_called": "river_heads_up_oop_first_resolution",
            "river_seed_oop_probe_small_called": "river_heads_up_oop_first_resolution",
            "river_seed_oop_probe_big_called": "river_heads_up_oop_first_resolution",
        },
        "turn_3way_middle_aggressor_continuation": {
            "river_seed_multiway_checkback": "river_3way_middle_aggressor_resolution",
            "river_seed_multiway_small_called": "river_3way_middle_aggressor_resolution",
            "river_seed_multiway_big_called": "river_3way_middle_aggressor_resolution",
            "river_seed_multiway_small_raise_called": "river_3way_middle_aggressor_resolution",
            "river_seed_multiway_big_raise_called": "river_3way_middle_aggressor_resolution",
            "river_seed_multiway_field_lead_small_called": "river_3way_middle_aggressor_resolution",
            "river_seed_multiway_field_lead_big_called": "river_3way_middle_aggressor_resolution",
        },
        "turn_3way_ip_aggressor_continuation": {
            "river_seed_ip_aggressor_checkback": "river_3way_ip_aggressor_resolution",
            "river_seed_ip_aggressor_small_called": "river_3way_ip_aggressor_resolution",
            "river_seed_ip_aggressor_big_called": "river_3way_ip_aggressor_resolution",
            "river_seed_ip_aggressor_small_raise_called": "river_3way_ip_aggressor_resolution",
            "river_seed_ip_aggressor_big_raise_called": "river_3way_ip_aggressor_resolution",
            "river_seed_first_field_small_called": "river_3way_ip_aggressor_resolution",
            "river_seed_first_field_big_called": "river_3way_ip_aggressor_resolution",
            "river_seed_second_field_small_called": "river_3way_ip_aggressor_resolution",
            "river_seed_second_field_big_called": "river_3way_ip_aggressor_resolution",
        },
        "turn_3way_oop_aggressor_continuation": {
            "river_seed_oop_aggressor_small_called": "river_3way_oop_aggressor_resolution",
            "river_seed_oop_aggressor_big_called": "river_3way_oop_aggressor_resolution",
            "river_seed_oop_aggressor_small_raise_called": "river_3way_oop_aggressor_resolution",
            "river_seed_oop_aggressor_big_raise_called": "river_3way_oop_aggressor_resolution",
            "river_seed_oop_aggressor_check_through": "river_3way_oop_aggressor_resolution",
            "river_seed_field_stab_small_called": "river_3way_oop_aggressor_resolution",
            "river_seed_field_stab_big_called": "river_3way_oop_aggressor_resolution",
        },
        "turn_3way_field_aggressor_continuation": {
            "river_seed_field_aggressor_small_called": "river_3way_field_aggressor_resolution",
            "river_seed_field_aggressor_big_called": "river_3way_field_aggressor_resolution",
            "river_seed_field_aggressor_small_raise_called": "river_3way_field_aggressor_resolution",
            "river_seed_field_aggressor_big_raise_called": "river_3way_field_aggressor_resolution",
            "river_seed_field_aggressor_checked_through": "river_3way_field_aggressor_resolution",
            "river_seed_field_aggressor_vs_stab_small_called": "river_3way_field_aggressor_resolution",
            "river_seed_field_aggressor_vs_stab_big_called": "river_3way_field_aggressor_resolution",
        },
    },
}


def build_turn_tree_spec_library() -> dict[str, Any]:
    return deepcopy(TURN_TREE_SPEC_LIBRARY)


def _validate_turn_template_structure(
    template_id: str,
    template: dict[str, Any],
    size_profile: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    node_ids = {node["id"] for node in template.get("nodes", [])}
    river_seed_ids = {seed["id"] for seed in template.get("river_seeds", [])}

    for node in template.get("nodes", []):
        for option in node.get("options", []):
            next_id = option.get("next")
            if next_id and next_id not in node_ids and next_id not in river_seed_ids and not next_id.startswith("terminal_"):
                issues.append(f"Template {template_id} option points to unknown next id '{next_id}'.")
            size_ref = option.get("size_ref")
            if size_ref and size_ref not in size_profile:
                issues.append(f"Template {template_id} option references missing size_ref '{size_ref}'.")

    return issues


def build_turn_validation_report() -> dict[str, Any]:
    library = build_turn_tree_spec_library()
    flop_families = build_flop_tree_spec_library()["families"]
    issues: list[str] = []

    families = library["families"]
    templates = library["templates"]
    size_profiles = library["size_profiles"]
    seed_family_map = library["seed_family_map"]

    for family_id, family in families.items():
        template_id = family["template_ref"]
        size_profile_id = family["size_profile_ref"]
        template = templates.get(template_id)
        size_profile = size_profiles.get(size_profile_id)

        if template is None:
            issues.append(f"Family {family_id} references missing template '{template_id}'.")
            continue
        if size_profile is None:
            issues.append(f"Family {family_id} references missing size profile '{size_profile_id}'.")
            continue

        issues.extend(_validate_turn_template_structure(template_id, template, size_profile))

        for source_family_id in family.get("source_flop_families", []):
            if source_family_id not in flop_families:
                issues.append(f"Family {family_id} lists unknown source flop family '{source_family_id}'.")
                continue
            mapped_targets = set(seed_family_map.get(source_family_id, {}).values())
            if family_id not in mapped_targets:
                issues.append(
                    f"Family {family_id} lists source flop family '{source_family_id}' but seed_family_map has no path into it."
                )

    for source_family_id, seed_map in seed_family_map.items():
        if source_family_id not in flop_families:
            issues.append(f"seed_family_map references unknown flop family '{source_family_id}'.")
            continue
        for seed_id, target_family_id in seed_map.items():
            if target_family_id not in families:
                issues.append(
                    f"seed_family_map {source_family_id}.{seed_id} points to unknown turn family '{target_family_id}'."
                )
                continue
            if source_family_id not in families[target_family_id].get("source_flop_families", []):
                issues.append(
                    f"seed_family_map {source_family_id}.{seed_id} -> {target_family_id} is not reciprocated in source_flop_families."
                )

    total_seed_links = sum(len(seed_map) for seed_map in seed_family_map.values())
    return {
        "valid": not issues,
        "family_count": len(families),
        "template_count": len(templates),
        "size_profile_count": len(size_profiles),
        "mapped_source_flop_family_count": len(seed_family_map),
        "total_seed_links": total_seed_links,
        "issues": issues,
    }


def build_river_tree_spec_library() -> dict[str, Any]:
    return deepcopy(RIVER_TREE_SPEC_LIBRARY)


def _validate_river_template_structure(
    template_id: str,
    template: dict[str, Any],
    size_profile: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    node_ids = {node["id"] for node in template.get("nodes", [])}
    terminal_nodes = set(template.get("terminal_nodes", []))

    for node in template.get("nodes", []):
        for option in node.get("options", []):
            next_id = option.get("next")
            if next_id and next_id not in node_ids and next_id not in terminal_nodes and not next_id.startswith("terminal_"):
                issues.append(f"Template {template_id} option points to unknown next id '{next_id}'.")
            size_ref = option.get("size_ref")
            if size_ref and size_ref not in size_profile:
                issues.append(f"Template {template_id} option references missing size_ref '{size_ref}'.")

    return issues


def build_river_validation_report() -> dict[str, Any]:
    library = build_river_tree_spec_library()
    turn_families = build_turn_tree_spec_library()["families"]
    turn_templates = build_turn_tree_spec_library()["templates"]
    issues: list[str] = []

    families = library["families"]
    templates = library["templates"]
    size_profiles = library["size_profiles"]
    seed_family_map = library["seed_family_map"]

    for family_id, family in families.items():
        template_id = family["template_ref"]
        size_profile_id = family["size_profile_ref"]
        template = templates.get(template_id)
        size_profile = size_profiles.get(size_profile_id)

        if template is None:
            issues.append(f"Family {family_id} references missing template '{template_id}'.")
            continue
        if size_profile is None:
            issues.append(f"Family {family_id} references missing size profile '{size_profile_id}'.")
            continue

        issues.extend(_validate_river_template_structure(template_id, template, size_profile))

        for source_family_id in family.get("source_turn_families", []):
            if source_family_id not in turn_families:
                issues.append(f"Family {family_id} lists unknown source turn family '{source_family_id}'.")
                continue
            mapped_targets = set(seed_family_map.get(source_family_id, {}).values())
            if family_id not in mapped_targets:
                issues.append(
                    f"Family {family_id} lists source turn family '{source_family_id}' but seed_family_map has no path into it."
                )

    for source_family_id, seed_map in seed_family_map.items():
        if source_family_id not in turn_families:
            issues.append(f"seed_family_map references unknown turn family '{source_family_id}'.")
            continue

        available_seed_ids = {seed["id"] for seed in turn_templates[turn_families[source_family_id]["template_ref"]].get("river_seeds", [])}
        for seed_id, target_family_id in seed_map.items():
            if seed_id not in available_seed_ids:
                issues.append(f"seed_family_map {source_family_id}.{seed_id} references a missing river seed on the source turn template.")
            if target_family_id not in families:
                issues.append(
                    f"seed_family_map {source_family_id}.{seed_id} points to unknown river family '{target_family_id}'."
                )
                continue
            if source_family_id not in families[target_family_id].get("source_turn_families", []):
                issues.append(
                    f"seed_family_map {source_family_id}.{seed_id} -> {target_family_id} is not reciprocated in source_turn_families."
                )

    total_seed_links = sum(len(seed_map) for seed_map in seed_family_map.values())
    return {
        "valid": not issues,
        "family_count": len(families),
        "template_count": len(templates),
        "size_profile_count": len(size_profiles),
        "mapped_source_turn_family_count": len(seed_family_map),
        "total_seed_links": total_seed_links,
        "issues": issues,
    }


def filtered_turn_specs(family: Optional[str] = None) -> dict[str, Any]:
    library = build_turn_tree_spec_library()
    if family:
        canonical_family = normalize_turn_family_id(family)
        library["families"] = {canonical_family: library["families"][canonical_family]}
    return library


def enforce_river_board_policies(library: dict[str, Any], board_bucket: str) -> dict[str, Any]:
    canonical_bucket = normalize_board_bucket_id(library, board_bucket)
    for family_id, family in library["families"].items():
        size_policy = family.get("board_size_policy")
        if not size_policy:
            continue

        family["resolved_board_bucket"] = canonical_bucket
        template_id = family["template_ref"]
        template = deepcopy(library["templates"][template_id])
        removed_sizes = []

        bucket_rule = size_policy.get(canonical_bucket, {})
        remove_size_refs = set(bucket_rule.get("remove_size_refs", []))
        remove_actions = set(bucket_rule.get("remove_actions", []))
        if remove_size_refs or remove_actions:
            removed_sizes = _remove_options_by_rule(
                template,
                lambda option: option.get("size_ref") in remove_size_refs or option.get("action") in remove_actions,
            )

        if not removed_sizes:
            family["enforced_board_policy"] = {"removed_size_branches": []}
            continue

        template["resolved_for_board_bucket"] = canonical_bucket
        template["removed_policy_options"] = {"size": removed_sizes}
        resolved_template_id = f"{template_id}__{canonical_bucket.lower()}__{family_id}"
        library["templates"][resolved_template_id] = template
        family["template_ref"] = resolved_template_id
        family["enforced_board_policy"] = {"removed_size_branches": removed_sizes}
    return library


def filtered_river_specs(family: Optional[str] = None, board_bucket: Optional[str] = None) -> dict[str, Any]:
    library = build_river_tree_spec_library()
    if family:
        canonical_family = normalize_river_family_id(family)
        library["families"] = {canonical_family: library["families"][canonical_family]}
    if board_bucket:
        library = enforce_river_board_policies(library, board_bucket)
    return library


def render_turn_specs_text(artifact: dict[str, Any]) -> str:
    lines = ["Turn tree specs", "===============", ""]
    for family_id, family in artifact["families"].items():
        template = artifact["templates"][family["template_ref"]]
        lines.append(f"- {family_id}")
        lines.append(f"  - template: {family['template_ref']}")
        lines.append(f"  - line prefix: {family['line_prefix']}")
        lines.append(f"  - source flop families: {', '.join(family.get('source_flop_families', []))}")
        lines.append(f"  - root actor: {template['nodes'][0]['actor']}")
        lines.append("")
    return "\n".join(lines)


def render_turn_validation_text(report: dict[str, Any]) -> str:
    lines = ["Turn tree validation", "====================", ""]
    lines.append(f"- valid: {report['valid']}")
    lines.append(f"- turn families: {report['family_count']}")
    lines.append(f"- templates: {report['template_count']}")
    lines.append(f"- size profiles: {report['size_profile_count']}")
    lines.append(f"- mapped source flop families: {report['mapped_source_flop_family_count']}")
    lines.append(f"- total seed links: {report['total_seed_links']}")
    if report["issues"]:
        lines.append("- issues:")
        for issue in report["issues"]:
            lines.append(f"  - {issue}")
    else:
        lines.append("- issues: none")
    return "\n".join(lines)


def render_river_specs_text(artifact: dict[str, Any]) -> str:
    lines = ["River tree specs", "================", ""]
    meta = artifact["meta"]
    lines.append(f"- schema version: {meta['schema_version']}")
    lines.append(f"- street: {meta['street']}")
    lines.append(f"- notes: {' | '.join(meta['notes'])}")
    lines.append("")
    for family_id, family in artifact["families"].items():
        template = artifact["templates"][family["template_ref"]]
        lines.append(f"- {family_id}")
        lines.append(f"  - template: {family['template_ref']}")
        lines.append(f"  - line prefix: {family['line_prefix']}")
        lines.append(f"  - source turn families: {', '.join(family.get('source_turn_families', []))}")
        if family.get("resolved_board_bucket"):
            lines.append(f"  - resolved board bucket: {family['resolved_board_bucket']}")
        if family.get("enforced_board_policy") is not None:
            removed_sizes = family["enforced_board_policy"].get("removed_size_branches", [])
            lines.append(f"  - enforced size branches removed: {', '.join(removed_sizes) if removed_sizes else 'none'}")
        lines.append(f"  - root actor: {template['nodes'][0]['actor']}")
        lines.append(f"  - terminal nodes: {', '.join(template.get('terminal_nodes', []))}")
        lines.append("")
    return "\n".join(lines)


def render_river_validation_text(report: dict[str, Any]) -> str:
    lines = ["River tree validation", "=====================", ""]
    lines.append(f"- valid: {report['valid']}")
    lines.append(f"- river families: {report['family_count']}")
    lines.append(f"- templates: {report['template_count']}")
    lines.append(f"- size profiles: {report['size_profile_count']}")
    lines.append(f"- mapped source turn families: {report['mapped_source_turn_family_count']}")
    lines.append(f"- total seed links: {report['total_seed_links']}")
    if report["issues"]:
        lines.append("- issues:")
        for issue in report["issues"]:
            lines.append(f"  - {issue}")
    else:
        lines.append("- issues: none")
    return "\n".join(lines)


def normalize_stage_id(stage_id: str) -> str:
    raw = stage_id.strip().lower().replace("_", "-")
    aliases = {
        "all": "all",
        "flop": "flop",
        "flop-only": "flop",
        "flop_only": "flop",
        "turn": "turn",
        "turn-follow-through": "turn",
        "turn_follow_through": "turn",
        "river": "river",
        "river-last": "river",
        "river_last": "river",
    }
    if raw not in aliases:
        valid = ", ".join(sorted(aliases))
        raise ValueError(f"Unknown stage '{stage_id}'. Expected one of: {valid}")
    return aliases[raw]


def get_stage_plan(stage_id: str) -> dict[str, Any]:
    plan = build_postflop_expansion_plan()
    normalized = normalize_stage_id(stage_id)
    for stage in plan["stages"]:
        if stage["id"] == normalized:
            return stage
    valid = ", ".join(stage["id"] for stage in plan["stages"])
    raise ValueError(f"Unknown stage '{stage_id}'. Expected one of: {valid}")


def filtered_plan(stage: str) -> dict[str, Any]:
    plan = build_postflop_expansion_plan()
    normalized = normalize_stage_id(stage)
    if normalized == "all":
        return plan
    plan["stages"] = [get_stage_plan(normalized)]
    return plan


def normalize_family_id(family_id: str) -> str:
    raw = family_id.strip().lower().replace("-", "_")
    families = build_flop_tree_spec_library()["families"]
    normalized_map = {name.lower().replace("-", "_"): name for name in families}
    if raw not in normalized_map:
        valid = ", ".join(sorted(families))
        raise ValueError(f"Unknown family '{family_id}'. Expected one of: {valid}")
    return normalized_map[raw]


def normalize_turn_family_id(family_id: str) -> str:
    raw = family_id.strip().lower().replace("-", "_")
    families = build_turn_tree_spec_library()["families"]
    normalized_map = {name.lower().replace("-", "_"): name for name in families}
    if raw not in normalized_map:
        valid = ", ".join(sorted(families))
        raise ValueError(f"Unknown turn family '{family_id}'. Expected one of: {valid}")
    return normalized_map[raw]


def normalize_river_family_id(family_id: str) -> str:
    raw = family_id.strip().lower().replace("-", "_")
    families = build_river_tree_spec_library()["families"]
    normalized_map = {name.lower().replace("-", "_"): name for name in families}
    if raw not in normalized_map:
        valid = ", ".join(sorted(families))
        raise ValueError(f"Unknown river family '{family_id}'. Expected one of: {valid}")
    return normalized_map[raw]


def normalize_matchup_id(matchup_id: str) -> str:
    raw = matchup_id.strip().lower().replace("-", "_")
    matchups = build_flop_tree_spec_library()["matchup_instances"]
    normalized_map = {name.lower().replace("-", "_"): name for name in matchups}
    if raw not in normalized_map:
        valid = ", ".join(sorted(matchups))
        raise ValueError(f"Unknown matchup '{matchup_id}'. Expected one of: {valid}")
    return normalized_map[raw]


def normalize_board_bucket_id(library: dict[str, Any], board_bucket: str) -> str:
    raw = board_bucket.strip().upper().replace("-", "_")
    valid = {}
    for bucket_set in library.get("board_bucket_sets", {}).values():
        for bucket in bucket_set:
            valid[bucket["id"].upper()] = bucket["id"]

    if library.get("meta", {}).get("street") in {"turn", "river"}:
        for bucket_set in build_flop_tree_spec_library().get("board_bucket_sets", {}).values():
            for bucket in bucket_set:
                valid[bucket["id"].upper()] = bucket["id"]

    for family in library.get("families", {}).values():
        lead_policy = family.get("board_action_policy") or {}
        for bucket in lead_policy.get("oop_lead_enabled_on", []):
            valid[bucket.upper()] = bucket
        for field in ("board_size_policy", "board_turn_seed_policy"):
            for bucket in (family.get(field) or {}).keys():
                valid[bucket.upper()] = bucket

    if raw not in valid:
        choices = ", ".join(sorted(valid.values()))
        raise ValueError(f"Unknown board bucket '{board_bucket}'. Expected one of: {choices}")
    return valid[raw]


def _is_lead_probe_option(option: dict[str, Any]) -> bool:
    return option.get("action") == "bet" and option.get("size_ref") in {"probe_small", "probe_big"}


def _remove_options_by_rule(template: dict[str, Any], predicate) -> list[str]:
    removed = []
    for node in template["nodes"]:
        kept_options = []
        for option in node.get("options", []):
            if predicate(option):
                removed.append(f"{node['id']}:{option.get('size_ref', option.get('action', 'unknown'))}")
                continue
            kept_options.append(option)
        node["options"] = kept_options
    return removed


def enforce_board_action_policies(library: dict[str, Any], board_bucket: str) -> dict[str, Any]:
    canonical_bucket = normalize_board_bucket_id(library, board_bucket)
    for family_id, family in library["families"].items():
        lead_policy = family.get("board_action_policy")
        size_policy = family.get("board_size_policy")
        turn_seed_policy = family.get("board_turn_seed_policy")
        if not lead_policy and not size_policy and not turn_seed_policy:
            continue

        family["resolved_board_bucket"] = canonical_bucket
        template_id = family["template_ref"]
        template = deepcopy(library["templates"][template_id])
        removed_leads = []
        removed_sizes = []
        removed_turn_seeds = []

        if lead_policy:
            allowed = set(lead_policy.get("oop_lead_enabled_on", []))
            if canonical_bucket not in allowed:
                removed_leads = _remove_options_by_rule(template, _is_lead_probe_option)

        if size_policy:
            bucket_rule = size_policy.get(canonical_bucket, {})
            remove_size_refs = set(bucket_rule.get("remove_size_refs", []))
            if remove_size_refs:
                removed_sizes = _remove_options_by_rule(
                    template,
                    lambda option: option.get("size_ref") in remove_size_refs,
                )

        if turn_seed_policy:
            bucket_rule = turn_seed_policy.get(canonical_bucket, {})
            remove_turn_seed_ids = set(bucket_rule.get("remove_turn_seed_ids", []))
            if remove_turn_seed_ids:
                template["turn_seeds"] = [seed for seed in template["turn_seeds"] if seed["id"] not in remove_turn_seed_ids]
                removed_turn_seeds = sorted(remove_turn_seed_ids)
                _remove_options_by_rule(
                    template,
                    lambda option: option.get("next") in remove_turn_seed_ids,
                )

        if not removed_leads and not removed_sizes and not removed_turn_seeds:
            family["enforced_board_action_policy"] = {
                "removed_lead_branches": [],
                "removed_size_branches": [],
                "removed_turn_seeds": [],
            }
            continue

        template["resolved_for_board_bucket"] = canonical_bucket
        template["removed_policy_options"] = {
            "lead": removed_leads,
            "size": removed_sizes,
            "turn_seeds": removed_turn_seeds,
        }
        resolved_template_id = f"{template_id}__{canonical_bucket.lower()}__{family_id}"
        library["templates"][resolved_template_id] = template
        family["template_ref"] = resolved_template_id
        family["enforced_board_action_policy"] = {
            "removed_lead_branches": removed_leads,
            "removed_size_branches": removed_sizes,
            "removed_turn_seeds": removed_turn_seeds,
        }
    return library


def filtered_flop_specs(
    family: Optional[str] = None,
    matchup: Optional[str] = None,
    board_bucket: Optional[str] = None,
) -> dict[str, Any]:
    library = build_flop_tree_spec_library()
    if family:
        canonical_family = normalize_family_id(family)
        library["families"] = {canonical_family: library["families"][canonical_family]}
        library["matchup_instances"] = {
            matchup_id: spec
            for matchup_id, spec in library["matchup_instances"].items()
            if spec["family_ref"] == canonical_family
        }
    if matchup:
        canonical_matchup = normalize_matchup_id(matchup)
        family_ref = library["matchup_instances"][canonical_matchup]["family_ref"]
        library["families"] = {family_ref: library["families"][family_ref]}
        library["matchup_instances"] = {canonical_matchup: library["matchup_instances"][canonical_matchup]}
    if board_bucket:
        library = enforce_board_action_policies(library, board_bucket)
    return library


def render_plan_text(plan: dict[str, Any]) -> str:
    meta = plan["meta"]
    lines = [
        meta["name"],
        "=" * len(meta["name"]),
        meta["recommendation"],
        "",
        "Principles",
        "-" * len("Principles"),
    ]

    for principle in meta["principles"]:
        lines.append(f"- {principle}")

    for stage in plan["stages"]:
        lines.extend(
            [
                "",
                f"{stage['order']}. {stage['label']}",
                f"Goal: {stage['goal']}",
                f"Why now: {stage['why_now']}",
                "Focus:",
            ]
        )
        for item in stage["focus"]:
            lines.append(f"  - {item}")

        if stage.get("build_order"):
            lines.append("Concrete build order:")
            for item in stage["build_order"]:
                lines.append(f"  {item['step']}. {item['label']}")
                lines.append(f"    - family: {item['tree_family']}")
                lines.append(f"    - sizes: {', '.join(item['core_sizes'])}")
                lines.append(f"    - boards: {', '.join(item['board_buckets'])}")
                lines.append(f"    - why: {item['why_first']}")

        if stage.get("node_families"):
            lines.append("Node families:")
            for family in stage["node_families"]:
                lines.append(f"  - {family['id']}")
                lines.append(f"    - use for: {', '.join(family['use_for'])}")
                lines.append(f"    - root actions: {', '.join(family['root_actions'])}")
                lines.append(f"    - responses: {', '.join(family['response_branches'])}")
                lines.append(f"    - include now: {', '.join(family['include_now'])}")
                lines.append(f"    - exclude now: {', '.join(family['exclude_now'])}")

        if stage.get("naming_scheme_examples"):
            lines.append("Naming examples:")
            for item in stage["naming_scheme_examples"]:
                lines.append(f"  - {item}")

        lines.append("Priority spots:")
        for spot in stage["spots"]:
            lines.append(f"  - {spot['spot']} ({spot['priority']})")
            for node in spot["nodes"]:
                lines.append(f"    - {node}")

        lines.append("Deliverables:")
        for item in stage["deliverables"]:
            lines.append(f"  - {item}")

        lines.append("Defer until later:")
        for item in stage["defer_until_later"]:
            lines.append(f"  - {item}")

    return "\n".join(lines)


def render_specs_text(library: dict[str, Any]) -> str:
    meta = library["meta"]
    lines = [
        meta["name"],
        "=" * len(meta["name"]),
        f"Street: {meta['street']}",
        f"Schema version: {meta['schema_version']}",
        "",
        "Notes",
        "-" * len("Notes"),
    ]
    for note in meta["notes"]:
        lines.append(f"- {note}")

    lines.extend(["", "Templates", "-" * len("Templates")])
    for template_id, template in library["templates"].items():
        lines.append(f"- {template_id}")
        lines.append(f"  - description: {template['description']}")
        lines.append(f"  - node count: {len(template['nodes'])}")
        lines.append(f"  - turn seeds: {', '.join(seed['id'] for seed in template['turn_seeds'])}")
        lines.append(f"  - deferred: {', '.join(template['deferred_features'])}")

    lines.extend(["", "Families", "-" * len("Families")])
    for family_id, family in library["families"].items():
        template = library["templates"][family["template_ref"]]
        lines.append(f"- {family_id}")
        lines.append(f"  - template: {family['template_ref']}")
        lines.append(f"  - hero role: {family['hero_role']}")
        lines.append(f"  - villain role: {family['villain_role']}")
        lines.append(f"  - pot type: {family['pot_type']}")
        lines.append(f"  - size profile: {family['size_profile_ref']}")
        lines.append(f"  - board buckets: {family['board_bucket_set_ref']}")
        lines.append(f"  - matchups now: {', '.join(family['applies_to_matchups'])}")
        lines.append(f"  - matchups later: {', '.join(family['planned_expansion_matchups'])}")
        lines.append(f"  - line prefix: {family['line_prefix']}")
        if family.get("resolved_board_bucket"):
            lines.append(f"  - resolved board bucket: {family['resolved_board_bucket']}")
        if family.get("enforced_board_action_policy") is not None:
            removed_leads = family["enforced_board_action_policy"].get("removed_lead_branches", [])
            removed_sizes = family["enforced_board_action_policy"].get("removed_size_branches", [])
            removed_turns = family["enforced_board_action_policy"].get("removed_turn_seeds", [])
            lines.append(f"  - enforced lead branches removed: {', '.join(removed_leads) if removed_leads else 'none'}")
            lines.append(f"  - enforced size branches removed: {', '.join(removed_sizes) if removed_sizes else 'none'}")
            lines.append(f"  - enforced turn seeds removed: {', '.join(removed_turns) if removed_turns else 'none'}")
        root = template['nodes'][0]
        root_actions = ", ".join(
            f"{option['action']}:{option['size_ref']}" if option.get('size_ref') else option['action']
            for option in root['options']
        )
        lines.append(f"  - root actor: {root['actor']} ({root_actions})")

    lines.extend(["", "Matchup instances", "-" * len("Matchup instances")])
    for matchup_id, matchup in library["matchup_instances"].items():
        positions = matchup["positions"]
        lines.append(f"- {matchup_id}")
        lines.append(f"  - family: {matchup['family_ref']}")
        lines.append(f"  - preflop path: {' -> '.join(matchup['preflop_path'])}")
        lines.append(
            f"  - positions: pfr={positions['pfr']}, caller={positions['caller']}, oop={positions['oop']}, ip={positions['ip']}"
        )
        lines.append(f"  - priority wave: {matchup['priority_wave']}")
        lines.append(f"  - range tags: {', '.join(matchup['range_profile_tags'])}")
        lines.append(f"  - board biases: {', '.join(matchup['board_bucket_biases'])}")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Emit the staged postflop roadmap or the machine-readable flop tree specs kept outside hand_parser.py."
    )
    parser.add_argument(
        "--artifact",
        choices=["plan", "specs", "turn_specs", "turn_validation", "river_specs", "river_validation"],
        default="plan",
        help="Whether to emit the staged roadmap, the machine-readable flop specs, the controlled first-turn specs, the first river placeholder specs, or a validation report for the staged later-street libraries.",
    )
    parser.add_argument(
        "--stage",
        default="all",
        help="Stage to emit for roadmap mode: all, flop, turn, or river.",
    )
    parser.add_argument(
        "--family",
        help="Optional family id for specs mode, for example srp_ip_pfr_flop.",
    )
    parser.add_argument(
        "--matchup",
        help="Optional matchup id for specs mode, for example UTG_open_vs_BTN_flat.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--board-bucket",
        help="Optional board bucket id to enforce board_action_policy pruning, for example MONOTONE or A_HIGH_DRY.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.artifact == "plan":
        artifact = filtered_plan(args.stage)
        if args.format == "json":
            print(json.dumps(artifact, indent=2))
            return
        print(render_plan_text(artifact))
        return

    if args.artifact == "turn_specs":
        artifact = filtered_turn_specs(args.family)
        if args.format == "json":
            print(json.dumps(artifact, indent=2))
            return
        print(render_turn_specs_text(artifact))
        return

    if args.artifact == "turn_validation":
        artifact = build_turn_validation_report()
        if args.format == "json":
            print(json.dumps(artifact, indent=2))
            return
        print(render_turn_validation_text(artifact))
        return

    if args.artifact == "river_specs":
        artifact = filtered_river_specs(args.family, args.board_bucket)
        if args.format == "json":
            print(json.dumps(artifact, indent=2))
            return
        print(render_river_specs_text(artifact))
        return

    if args.artifact == "river_validation":
        artifact = build_river_validation_report()
        if args.format == "json":
            print(json.dumps(artifact, indent=2))
            return
        print(render_river_validation_text(artifact))
        return

    normalized_stage = normalize_stage_id(args.stage)
    if normalized_stage not in {"all", "flop"}:
        raise ValueError("Specs mode currently supports only flop or all.")

    artifact = filtered_flop_specs(args.family, args.matchup, args.board_bucket)
    if args.format == "json":
        print(json.dumps(artifact, indent=2))
        return
    print(render_specs_text(artifact))


if __name__ == "__main__":
    main()
