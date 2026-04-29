#!/usr/bin/env python3
"""V2 EV prior replacer with measured data.

Swaps hand-coded EV priors with measured deltas from showdown data.
Only for leak classes with n ≥ 30.
"""
import json
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEAK_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "leak_prioritization"
SHOWDOWN_ROOT = PROJECT_ROOT / "data" / "hand_histories" / "showdown_ev"
EV_COST_PRIORS = {
    "preflop": {
        "open_jam_leak": 0.8,
        "min_raise_leak": 0.5,
        "limped_pot_raise_leak": 0.6,
        "3bet_leak": 0.7,
        "call_3bet_leak": 0.6,
        "reshove_wrong": 0.9,
        "call_off_fold": 0.85,
        "blind_def_light": 0.75,
    },
    "postflop": {
        "flop_cbet_miss": 0.4,
        "turn_barrel_miss": 0.5,
        "river_bet_miss": 0.55,
        "donk_lead_miss": 0.45,
        "probe_miss": 0.5,
    },
}


def load_measured_ev() -> dict:
    """Load measured EV from showdown data."""
    showdown_file = SHOWDOWN_ROOT / "latest.json"
    if not showdown_file.exists():
        return {}
    
    try:
        data = json.loads(showdown_file.read_text())
        return data.get("by_leak_class", {})
    except:
        return {}


def get_ev_cost(leak_type: str, street: str = "preflop") -> dict:
    """Get EV cost for a leak type, preferring measured when available."""
    measured = load_measured_ev()
    
    if leak_type in measured:
        m_data = measured[leak_type]
        n = m_data.get("n", 0)
        if n >= 30:
            return {
                "ev_cost": m_data.get("avg_ev_delta", 0),
                "prior_source": "measured",
                "n": n,
                "confidence": "high" if n >= 50 else "medium",
            }
    
    priors = EV_COST_PRIORS.get(street, EV_COST_PRIORS["preflop"])
    return {
        "ev_cost": priors.get(leak_type, 0.5),
        "prior_source": "heuristic",
        "n": 0,
        "confidence": "low",
    }


def main():
    print("EV Cost Lookup")
    print("=" * 50)
    
    test_types = ["3bet_leak", "reshove_wrong", "open_jam_leak", "flop_cbet_miss"]
    for lt in test_types:
        street = "preflop" if "jam" in lt or "3bet" in lt or "reshove" in lt else "postflop"
        ev = get_ev_cost(lt, street)
        print(f"{lt}: ${ev['ev_cost']:.2f} (source={ev['prior_source']}, n={ev['n']})")


if __name__ == "__main__":
    main()