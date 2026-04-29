# TODO: Refine baseline ranges with larger HH corpus and solver data
# Current baseline: ~35 spots for v1, directional but needs more data for statistically significant leak ranking.
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

BOARD_TEXTURE_BUCKETS = [
    "A_HIGH_DRY",
    "BROADWAY_STATIC",
    "MID_CONNECTED",
    "PAIRED",
    "MONOTONE",
    "TWO_TONE",
]

STACK_DEPTH_BANDS = ["shallow", "deep"]


@dataclass
class CbetBaseline:
    spot_key: str
    position_group: str
    board_bucket: str
    stack_band: str
    cbet_small_freq: float
    cbet_big_freq: float
    check_freq: float
    description: str


CBET_BASELINES: dict[str, CbetBaseline] = {
    ("srp_ip_pfr", "IP", "A_HIGH_DRY", "shallow"): CbetBaseline(
        spot_key="srp_ip_pfr",
        position_group="IP",
        board_bucket="A_HIGH_DRY",
        stack_band="shallow",
        cbet_small_freq=0.35,
        cbet_big_freq=0.20,
        check_freq=0.45,
        description="SRP IP cbet: range advantage on dry ace-high",
    ),
    ("srp_ip_pfr", "IP", "BROADWAY_STATIC", "shallow"): CbetBaseline(
        spot_key="srp_ip_pfr",
        position_group="IP",
        board_bucket="BROADWAY_STATIC",
        stack_band="shallow",
        cbet_small_freq=0.30,
        cbet_big_freq=0.25,
        check_freq=0.45,
        description="SRP IP cbet: static broadway board",
    ),
    ("srp_ip_pfr", "IP", "MID_CONNECTED", "shallow"): CbetBaseline(
        spot_key="srp_ip_pfr",
        position_group="IP",
        board_bucket="MID_CONNECTED",
        stack_band="shallow",
        cbet_small_freq=0.35,
        cbet_big_freq=0.15,
        check_freq=0.50,
        description="SRP IP cbet: middling connected board",
    ),
    ("srp_ip_pfr", "IP", "PAIRED", "shallow"): CbetBaseline(
        spot_key="srp_ip_pfr",
        position_group="IP",
        board_bucket="PAIRED",
        stack_band="shallow",
        cbet_small_freq=0.30,
        cbet_big_freq=0.10,
        check_freq=0.60,
        description="SRP IP cbet: paired board, reduce betting",
    ),
    ("srp_ip_pfr", "IP", "MONOTONE", "shallow"): CbetBaseline(
        spot_key="srp_ip_pfr",
        position_group="IP",
        board_bucket="MONOTONE",
        stack_band="shallow",
        cbet_small_freq=0.25,
        cbet_big_freq=0.10,
        check_freq=0.65,
        description="SRP IP cbet: monotone, play conservative",
    ),
    ("srp_ip_pfr", "IP", "A_HIGH_DRY", "deep"): CbetBaseline(
        spot_key="srp_ip_pfr",
        position_group="IP",
        board_bucket="A_HIGH_DRY",
        stack_band="deep",
        cbet_small_freq=0.30,
        cbet_big_freq=0.25,
        check_freq=0.45,
        description="SRP IP cbet deep: more checking with initiative",
    ),
    ("srp_ip_pfr", "IP", "BROADWAY_STATIC", "deep"): CbetBaseline(
        spot_key="srp_ip_pfr",
        position_group="IP",
        board_bucket="BROADWAY_STATIC",
        stack_band="deep",
        cbet_small_freq=0.25,
        cbet_big_freq=0.25,
        check_freq=0.50,
        description="SRP IP cbet deep: balanced betting",
    ),
    ("srp_ip_pfr", "IP", "MID_CONNECTED", "deep"): CbetBaseline(
        spot_key="srp_ip_pfr",
        position_group="IP",
        board_bucket="MID_CONNECTED",
        stack_band="deep",
        cbet_small_freq=0.30,
        cbet_big_freq=0.15,
        check_freq=0.55,
        description="SRP IP cbet deep: more checking on dynamic",
    ),
    ("srp_oop_defender", "OOP", "A_HIGH_DRY", "shallow"): CbetBaseline(
        spot_key="srp_oop_defender",
        position_group="OOP",
        board_bucket="A_HIGH_DRY",
        stack_band="shallow",
        cbet_small_freq=0.00,
        cbet_big_freq=0.00,
        check_freq=1.00,
        description="SRP OOP: check back ace-high",
    ),
    ("srp_oop_defender", "OOP", "BROADWAY_STATIC", "shallow"): CbetBaseline(
        spot_key="srp_oop_defender",
        position_group="OOP",
        board_bucket="BROADWAY_STATIC",
        stack_band="shallow",
        cbet_small_freq=0.00,
        cbet_big_freq=0.00,
        check_freq=1.00,
        description="SRP OOP: check back static",
    ),
    ("srp_oop_defender", "OOP", "MID_CONNECTED", "shallow"): CbetBaseline(
        spot_key="srp_oop_defender",
        position_group="OOP",
        board_bucket="MID_CONNECTED",
        stack_band="shallow",
        cbet_small_freq=0.00,
        cbet_big_freq=0.00,
        check_freq=1.00,
        description="SRP OOP: check back dynamic",
    ),
    ("srp_oop_defender", "OOP", "PAIRED", "shallow"): CbetBaseline(
        spot_key="srp_oop_defender",
        position_group="OOP",
        board_bucket="PAIRED",
        stack_band="shallow",
        cbet_small_freq=0.00,
        cbet_big_freq=0.00,
        check_freq=1.00,
        description="SRP OOP: check back paired",
    ),
    ("srp_oop_defender", "OOP", "MONOTONE", "shallow"): CbetBaseline(
        spot_key="srp_oop_defender",
        position_group="OOP",
        board_bucket="MONOTONE",
        stack_band="shallow",
        cbet_small_freq=0.00,
        cbet_big_freq=0.00,
        check_freq=1.00,
        description="SRP OOP: check back monotone",
    ),
    ("srp_oop_defender", "OOP", "A_HIGH_DRY", "deep"): CbetBaseline(
        spot_key="srp_oop_defender",
        position_group="OOP",
        board_bucket="A_HIGH_DRY",
        stack_band="deep",
        cbet_small_freq=0.00,
        cbet_big_freq=0.00,
        check_freq=1.00,
        description="SRP OOP deep: check back ace-high",
    ),
    ("three_bet_ip_3bettor", "IP", "ACE_HIGH", "shallow"): CbetBaseline(
        spot_key="three_bet_ip_3bettor",
        position_group="IP",
        board_bucket="ACE_HIGH",
        stack_band="shallow",
        cbet_small_freq=0.40,
        cbet_big_freq=0.20,
        check_freq=0.40,
        description="3BP IP: aggressive cbet on ace-high",
    ),
    ("three_bet_ip_3bettor", "IP", "KING_HIGH", "shallow"): CbetBaseline(
        spot_key="three_bet_ip_3bettor",
        position_group="IP",
        board_bucket="KING_HIGH",
        stack_band="shallow",
        cbet_small_freq=0.35,
        cbet_big_freq=0.20,
        check_freq=0.45,
        description="3BP IP: cbet on king-high",
    ),
    ("three_bet_ip_3bettor", "IP", "LOW_STATIC", "shallow"): CbetBaseline(
        spot_key="three_bet_ip_3bettor",
        position_group="IP",
        board_bucket="LOW_STATIC",
        stack_band="shallow",
        cbet_small_freq=0.30,
        cbet_big_freq=0.15,
        check_freq=0.55,
        description="3BP IP: reduced cbet low static",
    ),
    ("three_bet_ip_3bettor", "IP", "MID_DYNAMIC", "shallow"): CbetBaseline(
        spot_key="three_bet_ip_3bettor",
        position_group="IP",
        board_bucket="MID_DYNAMIC",
        stack_band="shallow",
        cbet_small_freq=0.25,
        cbet_big_freq=0.10,
        check_freq=0.65,
        description="3BP IP: more checking on dynamic",
    ),
    ("three_bet_ip_3bettor", "IP", "PAIRED", "shallow"): CbetBaseline(
        spot_key="three_bet_ip_3bettor",
        position_group="IP",
        board_bucket="PAIRED",
        stack_band="shallow",
        cbet_small_freq=0.25,
        cbet_big_freq=0.10,
        check_freq=0.65,
        description="3BP IP: reduced cbet paired",
    ),
    ("three_bet_ip_3bettor", "IP", "MONOTONE", "shallow"): CbetBaseline(
        spot_key="three_bet_ip_3bettor",
        position_group="IP",
        board_bucket="MONOTONE",
        stack_band="shallow",
        cbet_small_freq=0.20,
        cbet_big_freq=0.05,
        check_freq=0.75,
        description="3BP IP: very conservative on monotone",
    ),
    ("three_bet_oop_3bettor", "OOP", "ACE_HIGH", "shallow"): CbetBaseline(
        spot_key="three_bet_oop_3bettor",
        position_group="OOP",
        board_bucket="ACE_HIGH",
        stack_band="shallow",
        cbet_small_freq=0.00,
        cbet_big_freq=0.00,
        check_freq=1.00,
        description="3BP OOP: check back ace-high",
    ),
    ("three_bet_oop_3bettor", "OOP", "KING_HIGH", "shallow"): CbetBaseline(
        spot_key="three_bet_oop_3bettor",
        position_group="OOP",
        board_bucket="KING_HIGH",
        stack_band="shallow",
        cbet_small_freq=0.00,
        cbet_big_freq=0.00,
        check_freq=1.00,
        description="3BP OOP: check back king-high",
    ),
    ("three_bet_oop_3bettor", "OOP", "MID_DYNAMIC", "shallow"): CbetBaseline(
        spot_key="three_bet_oop_3bettor",
        position_group="OOP",
        board_bucket="MID_DYNAMIC",
        stack_band="shallow",
        cbet_small_freq=0.00,
        cbet_big_freq=0.00,
        check_freq=1.00,
        description="3BP OOP: check back dynamic",
    ),
    ("bvb_ip_pfr", "IP", "HIGH_CARD_STATIC", "shallow"): CbetBaseline(
        spot_key="bvb_ip_pfr",
        position_group="IP",
        board_bucket="HIGH_CARD_STATIC",
        stack_band="shallow",
        cbet_small_freq=0.40,
        cbet_big_freq=0.20,
        check_freq=0.40,
        description="BVB IP: aggressive on high cards",
    ),
    ("bvb_ip_pfr", "IP", "LOW_DISCONNECTED", "shallow"): CbetBaseline(
        spot_key="bvb_ip_pfr",
        position_group="IP",
        board_bucket="LOW_DISCONNECTED",
        stack_band="shallow",
        cbet_small_freq=0.30,
        cbet_big_freq=0.25,
        check_freq=0.45,
        description="BVB IP: stab on low disconnected",
    ),
    ("bvb_ip_pfr", "IP", "LOW_CONNECTED", "shallow"): CbetBaseline(
        spot_key="bvb_ip_pfr",
        position_group="IP",
        board_bucket="LOW_CONNECTED",
        stack_band="shallow",
        cbet_small_freq=0.35,
        cbet_big_freq=0.15,
        check_freq=0.50,
        description="BVB IP: bet connected boards",
    ),
    ("bvb_ip_pfr", "IP", "PAIRED", "shallow"): CbetBaseline(
        spot_key="bvb_ip_pfr",
        position_group="IP",
        board_bucket="PAIRED",
        stack_band="shallow",
        cbet_small_freq=0.30,
        cbet_big_freq=0.10,
        check_freq=0.60,
        description="BVB IP: reduced on paired",
    ),
    ("bvb_ip_pfr", "IP", "MONOTONE", "shallow"): CbetBaseline(
        spot_key="bvb_ip_pfr",
        position_group="IP",
        board_bucket="MONOTONE",
        stack_band="shallow",
        cbet_small_freq=0.25,
        cbet_big_freq=0.10,
        check_freq=0.65,
        description="BVB IP: conservative on monotone",
    ),
    ("bvb_oop_defender", "OOP", "HIGH_CARD_STATIC", "shallow"): CbetBaseline(
        spot_key="bvb_oop_defender",
        position_group="OOP",
        board_bucket="HIGH_CARD_STATIC",
        stack_band="shallow",
        cbet_small_freq=0.00,
        cbet_big_freq=0.00,
        check_freq=1.00,
        description="BVB OOP: check back high cards",
    ),
    ("bvb_oop_defender", "OOP", "LOW_DISCONNECTED", "shallow"): CbetBaseline(
        spot_key="bvb_oop_defender",
        position_group="OOP",
        board_bucket="LOW_DISCONNECTED",
        stack_band="shallow",
        cbet_small_freq=0.00,
        cbet_big_freq=0.00,
        check_freq=1.00,
        description="BVB OOP: check back low disconnected",
    ),
    ("bvb_oop_defender", "OOP", "LOW_CONNECTED", "shallow"): CbetBaseline(
        spot_key="bvb_oop_defender",
        position_group="OOP",
        board_bucket="LOW_CONNECTED",
        stack_band="shallow",
        cbet_small_freq=0.00,
        cbet_big_freq=0.00,
        check_freq=1.00,
        description="BVB OOP: check back low connected",
    ),
}


@dataclass
class DonkLeadBaseline:
    spot_key: str
    position_group: str
    board_bucket: str
    stack_band: str
    donk_small_freq: float
    donk_big_freq: float
    check_freq: float
    description: str


DONK_LEAD_BASELINES: dict[str, DonkLeadBaseline] = {
    ("srp_oop_caller", "OOP", "A_HIGH_DRY", "shallow"): DonkLeadBaseline(
        spot_key="srp_oop_caller",
        position_group="OOP",
        board_bucket="A_HIGH_DRY",
        stack_band="shallow",
        donk_small_freq=0.05,
        donk_big_freq=0.00,
        check_freq=0.95,
        description="SRP OOP: rarely donk ace-high",
    ),
    ("srp_oop_caller", "OOP", "BROADWAY_STATIC", "shallow"): DonkLeadBaseline(
        spot_key="srp_oop_caller",
        position_group="OOP",
        board_bucket="BROADWAY_STATIC",
        stack_band="shallow",
        donk_small_freq=0.05,
        donk_big_freq=0.00,
        check_freq=0.95,
        description="SRP OOP: rarely donk static",
    ),
    ("srp_oop_caller", "OOP", "MID_CONNECTED", "shallow"): DonkLeadBaseline(
        spot_key="srp_oop_caller",
        position_group="OOP",
        board_bucket="MID_CONNECTED",
        stack_band="shallow",
        donk_small_freq=0.10,
        donk_big_freq=0.05,
        check_freq=0.85,
        description="SRP OOP: some donk on dynamic",
    ),
    ("srp_oop_caller", "OOP", "PAIRED", "shallow"): DonkLeadBaseline(
        spot_key="srp_oop_caller",
        position_group="OOP",
        board_bucket="PAIRED",
        stack_band="shallow",
        donk_small_freq=0.10,
        donk_big_freq=0.05,
        check_freq=0.85,
        description="SRP OOP: donk paired",
    ),
    ("srp_oop_caller", "OOP", "MONOTONE", "shallow"): DonkLeadBaseline(
        spot_key="srp_oop_caller",
        position_group="OOP",
        board_bucket="MONOTONE",
        stack_band="shallow",
        donk_small_freq=0.15,
        donk_big_freq=0.05,
        check_freq=0.80,
        description="SRP OOP: more donk monotone",
    ),
    ("bvb_oop_defender", "OOP", "HIGH_CARD_STATIC", "shallow"): DonkLeadBaseline(
        spot_key="bvb_oop_defender",
        position_group="OOP",
        board_bucket="HIGH_CARD_STATIC",
        stack_band="shallow",
        donk_small_freq=0.10,
        donk_big_freq=0.05,
        check_freq=0.85,
        description="BVB OOP: donk high cards",
    ),
}


@dataclass
class ProbeBaseline:
    spot_key: str
    position_group: str
    board_bucket: str
    stack_band: str
    probe_small_freq: float
    probe_big_freq: float
    check_freq: float
    description: str


PROBE_BASELINES: dict[str, ProbeBaseline] = {
    ("srp_oop_pfr", "OOP", "A_HIGH_DRY", "shallow"): ProbeBaseline(
        spot_key="srp_oop_pfr",
        position_group="OOP",
        board_bucket="A_HIGH_DRY",
        stack_band="shallow",
        probe_small_freq=0.10,
        probe_big_freq=0.05,
        check_freq=0.85,
        description="SRP OOP PFR: probe ace-high",
    ),
    ("srp_oop_pfr", "OOP", "BROADWAY_STATIC", "shallow"): ProbeBaseline(
        spot_key="srp_oop_pfr",
        position_group="OOP",
        board_bucket="BROADWAY_STATIC",
        stack_band="shallow",
        probe_small_freq=0.10,
        probe_big_freq=0.05,
        check_freq=0.85,
        description="SRP OOP PFR: probe static",
    ),
    ("srp_oop_pfr", "OOP", "MID_CONNECTED", "shallow"): ProbeBaseline(
        spot_key="srp_oop_pfr",
        position_group="OOP",
        board_bucket="MID_CONNECTED",
        stack_band="shallow",
        probe_small_freq=0.15,
        probe_big_freq=0.10,
        check_freq=0.75,
        description="SRP OOP PFR: probe dynamic more",
    ),
    ("srp_oop_pfr", "OOP", "PAIRED", "shallow"): ProbeBaseline(
        spot_key="srp_oop_pfr",
        position_group="OOP",
        board_bucket="PAIRED",
        stack_band="shallow",
        probe_small_freq=0.15,
        probe_big_freq=0.05,
        check_freq=0.80,
        description="SRP OOP PFR: probe paired",
    ),
    ("srp_oop_pfr", "OOP", "MONOTONE", "shallow"): ProbeBaseline(
        spot_key="srp_oop_pfr",
        position_group="OOP",
        board_bucket="MONOTONE",
        stack_band="shallow",
        probe_small_freq=0.20,
        probe_big_freq=0.10,
        check_freq=0.70,
        description="SRP OOP PFR: probe monotone most",
    ),
    ("three_bet_oop_pfr", "OOP", "ACE_HIGH", "shallow"): ProbeBaseline(
        spot_key="three_bet_oop_pfr",
        position_group="OOP",
        board_bucket="ACE_HIGH",
        stack_band="shallow",
        probe_small_freq=0.10,
        probe_big_freq=0.00,
        check_freq=0.90,
        description="3BP OOP PFR: probe ace-high rarely",
    ),
    ("three_bet_oop_pfr", "OOP", "KING_HIGH", "shallow"): ProbeBaseline(
        spot_key="three_bet_oop_pfr",
        position_group="OOP",
        board_bucket="KING_HIGH",
        stack_band="shallow",
        probe_small_freq=0.10,
        probe_big_freq=0.05,
        check_freq=0.85,
        description="3BP OOP PFR: probe king-high",
    ),
    ("three_bet_oop_pfr", "OOP", "MID_DYNAMIC", "shallow"): ProbeBaseline(
        spot_key="three_bet_oop_pfr",
        position_group="OOP",
        board_bucket="MID_DYNAMIC",
        stack_band="shallow",
        probe_small_freq=0.15,
        probe_big_freq=0.10,
        check_freq=0.75,
        description="3BP OOP PFR: probe dynamic more",
    ),
}


def bucket_stack_depth(stack_bb: float) -> str:
    if stack_bb <= 40:
        return "shallow"
    return "deep"


def get_cbet_baseline(
    spot_key: str,
    position_group: str,
    board_bucket: str,
    stack_band: str,
) -> Optional[CbetBaseline]:
    return CBET_BASELINES.get((spot_key, position_group, board_bucket, stack_band))


def get_donk_baseline(
    spot_key: str,
    position_group: str,
    board_bucket: str,
    stack_band: str,
) -> Optional[DonkLeadBaseline]:
    return DONK_LEAD_BASELINES.get((spot_key, position_group, board_bucket, stack_band))


def get_probe_baseline(
    spot_key: str,
    position_group: str,
    board_bucket: str,
    stack_band: str,
) -> Optional[ProbeBaseline]:
    return PROBE_BASELINES.get((spot_key, position_group, board_bucket, stack_band))


def compare_frequency(
    action_type: str,
    actual_freq: float,
    baseline: CbetBaseline | DonkLeadBaseline | ProbeBaseline,
) -> dict:
    if isinstance(baseline, CbetBaseline):
        expected_small = baseline.cbet_small_freq
        expected_big = baseline.cbet_big_freq
        expected_check = baseline.check_freq
    elif isinstance(baseline, DonkLeadBaseline):
        expected_small = baseline.donk_small_freq
        expected_big = baseline.donk_big_freq
        expected_check = baseline.check_freq
    else:
        expected_small = baseline.probe_small_freq
        expected_big = baseline.probe_big_freq
        expected_check = baseline.check_freq

    if action_type == "small_bet":
        expected = expected_small
    elif action_type == "big_bet":
        expected = baseline.cbet_big_freq if isinstance(baseline, CbetBaseline) else expected_big
    else:
        expected = expected_check

    deviation = actual_freq - expected
    is_leak = abs(deviation) > 0.15

    return {
        "status": "leak" if is_leak else "correct",
        "actual_freq": round(actual_freq, 2),
        "expected_freq": round(expected, 2),
        "deviation": round(deviation, 2),
    }


@dataclass
class TurnBarrelBaseline:
    spot_key: str
    position_group: str
    board_bucket: str
    stack_band: str
    barrel_freq: float
    check_back_freq: float
    description: str


TURN_BARREL_BASELINES: dict[str, TurnBarrelBaseline] = {
    ("srp_ip_pfr", "IP", "A_HIGH_DRY", "shallow"): TurnBarrelBaseline(
        spot_key="srp_ip_pfr",
        position_group="IP",
        board_bucket="A_HIGH_DRY",
        stack_band="shallow",
        barrel_freq=0.40,
        check_back_freq=0.50,
        description="SRP IP turn: barrel ace-high dry",
    ),
    ("srp_ip_pfr", "IP", "BROADWAY_STATIC", "shallow"): TurnBarrelBaseline(
        spot_key="srp_ip_pfr",
        position_group="IP",
        board_bucket="BROADWAY_STATIC",
        stack_band="shallow",
        barrel_freq=0.35,
        check_back_freq=0.55,
        description="SRP IP turn: barrel broadway static",
    ),
    ("srp_ip_pfr", "IP", "MID_CONNECTED", "shallow"): TurnBarrelBaseline(
        spot_key="srp_ip_pfr",
        position_group="IP",
        board_bucket="MID_CONNECTED",
        stack_band="shallow",
        barrel_freq=0.25,
        check_back_freq=0.60,
        description="SRP IP turn: less barrel on dynamic",
    ),
    ("srp_ip_pfr", "IP", "TWO_TONE", "shallow"): TurnBarrelBaseline(
        spot_key="srp_ip_pfr",
        position_group="IP",
        board_bucket="TWO_TONE",
        stack_band="shallow",
        barrel_freq=0.30,
        check_back_freq=0.55,
        description="SRP IP turn: two-tone",
    ),
    ("srp_ip_pfr", "IP", "PAIRED", "shallow"): TurnBarrelBaseline(
        spot_key="srp_ip_pfr",
        position_group="IP",
        board_bucket="PAIRED",
        stack_band="shallow",
        barrel_freq=0.20,
        check_back_freq=0.70,
        description="SRP IP turn: reduce on paired",
    ),
    ("srp_ip_pfr", "IP", "MONOTONE", "shallow"): TurnBarrelBaseline(
        spot_key="srp_ip_pfr",
        position_group="IP",
        board_bucket="MONOTONE",
        stack_band="shallow",
        barrel_freq=0.15,
        check_back_freq=0.75,
        description="SRP IP turn: very conservative on monotone",
    ),
    ("srp_oop_caller", "OOP", "A_HIGH_DRY", "shallow"): TurnBarrelBaseline(
        spot_key="srp_oop_caller",
        position_group="OOP",
        board_bucket="A_HIGH_DRY",
        stack_band="shallow",
        barrel_freq=0.15,
        check_back_freq=0.70,
        description="SRP OOP turn: probe ace-high",
    ),
    ("srp_oop_caller", "OOP", "MID_CONNECTED", "shallow"): TurnBarrelBaseline(
        spot_key="srp_oop_caller",
        position_group="OOP",
        board_bucket="MID_CONNECTED",
        stack_band="shallow",
        barrel_freq=0.25,
        check_back_freq=0.60,
        description="SRP OOP turn: probe connected",
    ),
    ("srp_oop_caller", "OOP", "TWO_TONE", "shallow"): TurnBarrelBaseline(
        spot_key="srp_oop_caller",
        position_group="OOP",
        board_bucket="TWO_TONE",
        stack_band="shallow",
        barrel_freq=0.20,
        check_back_freq=0.65,
        description="SRP OOP turn: probe two-tone",
    ),
    ("srp_oop_pfr", "OOP", "A_HIGH_DRY", "shallow"): TurnBarrelBaseline(
        spot_key="srp_oop_pfr",
        position_group="OOP",
        board_bucket="A_HIGH_DRY",
        stack_band="shallow",
        barrel_freq=0.45,
        check_back_freq=0.45,
        description="SRP OOP PFR turn: barrel ace-high",
    ),
    ("srp_oop_pfr", "OOP", "MID_CONNECTED", "shallow"): TurnBarrelBaseline(
        spot_key="srp_oop_pfr",
        position_group="OOP",
        board_bucket="MID_CONNECTED",
        stack_band="shallow",
        barrel_freq=0.35,
        check_back_freq=0.50,
        description="SRP OOP PFR turn: barrel connected",
    ),
    ("limped_pot_heads_up", "IP", "BROADWAY_STATIC", "shallow"): TurnBarrelBaseline(
        spot_key="limped_pot_heads_up",
        position_group="IP",
        board_bucket="BROADWAY_STATIC",
        stack_band="shallow",
        barrel_freq=0.40,
        check_back_freq=0.50,
        description="Limped pot IP turn: bet broadway",
    ),
    ("limped_pot_heads_up", "IP", "MID_CONNECTED", "shallow"): TurnBarrelBaseline(
        spot_key="limped_pot_heads_up",
        position_group="IP",
        board_bucket="MID_CONNECTED",
        stack_band="shallow",
        barrel_freq=0.30,
        check_back_freq=0.55,
        description="Limped pot IP turn: bet connected",
    ),
    ("multiway_srp_3way_ip_aggressor", "IP", "TWO_TONE", "shallow"): TurnBarrelBaseline(
        spot_key="multiway_srp_3way_ip_aggressor",
        position_group="IP",
        board_bucket="TWO_TONE",
        stack_band="shallow",
        barrel_freq=0.30,
        check_back_freq=0.55,
        description="3way SRP IP turn: bet two-tone",
    ),
    ("multiway_srp_3way_middle_aggressor", "IP", "TWO_TONE", "shallow"): TurnBarrelBaseline(
        spot_key="multiway_srp_3way_middle_aggressor",
        position_group="IP",
        board_bucket="TWO_TONE",
        stack_band="shallow",
        barrel_freq=0.25,
        check_back_freq=0.60,
        description="3way SRP middle turn: bet two-tone",
    ),
}


@dataclass
class RiverBetBaseline:
    spot_key: str
    position_group: str
    board_bucket: str
    stack_band: str
    bet_freq: float
    check_freq: float
    description: str


RIVER_BET_BASELINES: dict[str, RiverBetBaseline] = {
    ("srp_ip_pfr", "IP", "A_HIGH_DRY", "shallow"): RiverBetBaseline(
        spot_key="srp_ip_pfr",
        position_group="IP",
        board_bucket="A_HIGH_DRY",
        stack_band="shallow",
        bet_freq=0.45,
        check_freq=0.45,
        description="SRP IP river: value thin on ace-high",
    ),
    ("srp_ip_pfr", "IP", "BROADWAY_STATIC", "shallow"): RiverBetBaseline(
        spot_key="srp_ip_pfr",
        position_group="IP",
        board_bucket="BROADWAY_STATIC",
        stack_band="shallow",
        bet_freq=0.40,
        check_freq=0.50,
        description="SRP IP river: value broadway",
    ),
    ("srp_ip_pfr", "IP", "MID_CONNECTED", "shallow"): RiverBetBaseline(
        spot_key="srp_ip_pfr",
        position_group="IP",
        board_bucket="MID_CONNECTED",
        stack_band="shallow",
        bet_freq=0.30,
        check_freq=0.60,
        description="SRP IP river: less value on connected",
    ),
    ("srp_ip_pfr", "IP", "TWO_TONE", "shallow"): RiverBetBaseline(
        spot_key="srp_ip_pfr",
        position_group="IP",
        board_bucket="TWO_TONE",
        stack_band="shallow",
        bet_freq=0.35,
        check_freq=0.55,
        description="SRP IP river: value two-tone",
    ),
    ("srp_oop_caller", "OOP", "A_HIGH_DRY", "shallow"): RiverBetBaseline(
        spot_key="srp_oop_caller",
        position_group="OOP",
        board_bucket="A_HIGH_DRY",
        stack_band="shallow",
        bet_freq=0.25,
        check_freq=0.60,
        description="SRP OOP river: probe ace-high",
    ),
    ("srp_oop_caller", "OOP", "MID_CONNECTED", "shallow"): RiverBetBaseline(
        spot_key="srp_oop_caller",
        position_group="OOP",
        board_bucket="MID_CONNECTED",
        stack_band="shallow",
        bet_freq=0.20,
        check_freq=0.65,
        description="SRP OOP river: probe less on connected",
    ),
    ("srp_oop_pfr", "OOP", "A_HIGH_DRY", "shallow"): RiverBetBaseline(
        spot_key="srp_oop_pfr",
        position_group="OOP",
        board_bucket="A_HIGH_DRY",
        stack_band="shallow",
        bet_freq=0.50,
        check_freq=0.40,
        description="SRP OOP PFR river: bet ace-high",
    ),
    ("limped_pot_heads_up", "IP", "BROADWAY_STATIC", "shallow"): RiverBetBaseline(
        spot_key="limped_pot_heads_up",
        position_group="IP",
        board_bucket="BROADWAY_STATIC",
        stack_band="shallow",
        bet_freq=0.45,
        check_freq=0.45,
        description="Limped pot IP river: bet broadway",
    ),
}


def get_turn_barrel_baseline(
    spot_key: str,
    position_group: str,
    board_bucket: str,
    stack_band: str,
) -> Optional[TurnBarrelBaseline]:
    return TURN_BARREL_BASELINES.get((spot_key, position_group, board_bucket, stack_band))


def get_river_bet_baseline(
    spot_key: str,
    position_group: str,
    board_bucket: str,
    stack_band: str,
) -> Optional[RiverBetBaseline]:
    return RIVER_BET_BASELINES.get((spot_key, position_group, board_bucket, stack_band))


def get_all_spots() -> list[str]:
    spots = []
    for key in CBET_BASELINES:
        spots.append(f"cbet:{key[0]}|{key[1]}|{key[2]}|{key[3]}")
    for key in DONK_LEAD_BASELINES:
        spots.append(f"donk:{key[0]}|{key[1]}|{key[2]}|{key[3]}")
    for key in PROBE_BASELINES:
        spots.append(f"probe:{key[0]}|{key[1]}|{key[2]}|{key[3]}")
    return sorted(spots)