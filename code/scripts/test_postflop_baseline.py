#!/usr/bin/env python3
from postflop_baseline import (
    get_cbet_baseline,
    get_donk_baseline, 
    get_probe_baseline,
    compare_frequency,
    CBET_BASELINES,
    DONK_LEAD_BASELINES,
    PROBE_BASELINES,
)


def test_cbet_lookup():
    baseline = get_cbet_baseline("srp_ip_pfr", "IP", "A_HIGH_DRY", "shallow")
    assert baseline is not None
    assert baseline.cbet_small_freq == 0.35
    assert baseline.cbet_big_freq == 0.20
    assert baseline.check_freq == 0.45
    print("✓ CBET lookup")


def test_donk_lookup():
    baseline = get_donk_baseline("srp_oop_caller", "OOP", "MID_CONNECTED", "shallow")
    assert baseline is not None
    assert baseline.donk_small_freq == 0.10
    assert baseline.donk_big_freq == 0.05
    print("✓ DONK lookup")


def test_probe_lookup():
    baseline = get_probe_baseline("srp_oop_pfr", "OOP", "MONOTONE", "shallow")
    assert baseline is not None
    assert baseline.probe_small_freq == 0.20
    assert baseline.probe_big_freq == 0.10
    print("✓ PROBE lookup")


def test_compare_frequency():
    baseline = get_cbet_baseline("srp_ip_pfr", "IP", "A_HIGH_DRY", "shallow")
    result = compare_frequency("small_bet", 0.50, baseline)
    assert result["actual_freq"] == 0.50
    assert result["expected_freq"] == 0.35
    assert result["deviation"] == 0.15
    print("✓ Compare frequency")


def test_spot_counts():
    assert len(CBET_BASELINES) >= 30, "CBET should have 30+ spots"
    assert len(DONK_LEAD_BASELINES) >= 5, "DONK should have 5+ spots"
    assert len(PROBE_BASELINES) >= 5, "PROBE should have 5+ spots"
    print(f"✓ Spot counts: CBET={len(CBET_BASELINES)}, DONK={len(DONK_LEAD_BASELINES)}, PROBE={len(PROBE_BASELINES)}")


if __name__ == "__main__":
    test_cbet_lookup()
    test_donk_lookup()
    test_probe_lookup()
    test_compare_frequency()
    test_spot_counts()
    print("\nAll tests passed!")