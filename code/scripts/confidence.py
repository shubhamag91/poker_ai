"""Shared confidence utilities for leak reports.

Wilson 95% confidence interval + n-tier confidence damping.
"""
from math import sqrt
from typing import Tuple


def wilson_confidence_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Calculate Wilson score confidence interval."""
    if total == 0:
        return 0.0, 1.0
    
    z = 1.96 if confidence == 0.95 else 1.645
    p = successes / total
    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    spread = z * sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denominator
    return max(0.0, center - spread), min(1.0, center + spread)


def confidence_tier(n: int) -> str:
    """Determine confidence tier based on sample size."""
    if n >= 20:
        return "high"
    elif n >= 8:
        return "medium"
    else:
        return "low"


def confidence_multiplier(n: int) -> float:
    """Apply n-tier confidence damping."""
    tier = confidence_tier(n)
    if tier == "high":
        return 1.0
    elif tier == "medium":
        return 0.7
    else:
        return 0.15


def augment_with_confidence(entry: dict, k: int, n: int) -> dict:
    """Add confidence fields to a leak report entry."""
    lo, hi = wilson_confidence_interval(k, n)
    tier = confidence_tier(n)
    entry.update({
        "n": n,
        "k": k,
        "freq": round(k / n, 3) if n > 0 else 0.0,
        "wilson_lower_ci": round(lo, 3),
        "wilson_upper_ci": round(hi, 3),
        "tier": tier,
    })
    return entry