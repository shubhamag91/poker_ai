# TODO: Refine baseline ranges with larger HH corpus
# Current baseline: 21 spots analyzed, ranges are directional but need more data
# for statistically significant leak ranking. Calibrate once more HH data is added.
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

@dataclass
class OpenJamBaseline:
    stack_bb: int
    position_group: str
    push_hands: set[str]
    min_raise_hands: set[str]
    pko_push_hands: set[str]
    description: str

OPEN_JAM_BASELINES = {
    (8, "early"): OpenJamBaseline(
        stack_bb=8,
        position_group="early",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway", 
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair",
        },
        min_raise_hands=set(),
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway", 
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair", "low_suited_connector",
        },
        description="8 BB EP: Push all, no min-raise",
    ),
    (8, "middle"): OpenJamBaseline(
        stack_bb=8,
        position_group="middle",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair", "low_suited_connector",
        },
        min_raise_hands=set(),
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair", "low_suited_connector", "low_suited_gapper",
        },
        description="8 BB MP: Push all, no min-raise",
    ),
    (8, "late"): OpenJamBaseline(
        stack_bb=8,
        position_group="late",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair", 
            "low_suited_connector", "low_suited_gapper",
        },
        min_raise_hands=set(),
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair", 
            "low_suited_connector", "low_suited_gapper", "weak_ace",
        },
        description="8 BB LP: Push all, no min-raise",
    ),
    (8, "blind"): OpenJamBaseline(
        stack_bb=8,
        position_group="blind",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair",
        },
        min_raise_hands=set(),
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair", "low_suited_connector",
        },
        description="8 BB SB/BB: Push all, no min-raise",
    ),
    (10, "early"): OpenJamBaseline(
        stack_bb=10,
        position_group="early",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
        },
        min_raise_hands={
            "middling_broadway", "small_pair",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair",
        },
        description="10 BB EP: Push top, min-raise mid",
    ),
    (10, "middle"): OpenJamBaseline(
        stack_bb=10,
        position_group="middle",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair",
        },
        min_raise_hands={
            "low_suited_connector",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair", "low_suited_connector",
        },
        description="10 BB MP: Push most, min-raise connectors",
    ),
    (10, "late"): OpenJamBaseline(
        stack_bb=10,
        position_group="late",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair", "low_suited_connector",
        },
        min_raise_hands={
            "low_suited_gapper",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair", "low_suited_connector", "low_suited_gapper",
        },
        description="10 BB LP: Push wide, min-raise gappers",
    ),
    (10, "blind"): OpenJamBaseline(
        stack_bb=10,
        position_group="blind",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair", "low_suited_connector",
        },
        min_raise_hands=set(),
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair", "low_suited_connector", "low_suited_gapper",
        },
        description="10 BB SB/BB: Push all",
    ),
    (12, "early"): OpenJamBaseline(
        stack_bb=12,
        position_group="early",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
        },
        min_raise_hands={
            "middling_broadway", "small_pair",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace", "middling_broadway",
        },
        description="12 BB EP: Push top, min-raise mid",
    ),
    (12, "middle"): OpenJamBaseline(
        stack_bb=12,
        position_group="middle",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway",
        },
        min_raise_hands={
            "small_pair", "low_suited_connector",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair",
        },
        description="12 BB MP: Push strong, min-raise mid",
    ),
    (12, "late"): OpenJamBaseline(
        stack_bb=12,
        position_group="late",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair",
        },
        min_raise_hands={
            "low_suited_connector", "low_suited_gapper",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair", "low_suited_connector",
        },
        description="12 BB LP: Push most, min-raise suited",
    ),
    (12, "blind"): OpenJamBaseline(
        stack_bb=12,
        position_group="blind",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair",
        },
        min_raise_hands={
            "low_suited_connector",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair", "low_suited_connector",
        },
        description="12 BB SB/BB: Push strong, min-raise mid",
    ),
    (15, "early"): OpenJamBaseline(
        stack_bb=15,
        position_group="early",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
        },
        min_raise_hands={
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
        },
        description="15 BB EP: Push premium, min-raise mid",
    ),
    (15, "middle"): OpenJamBaseline(
        stack_bb=15,
        position_group="middle",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
        },
        min_raise_hands={
            "middling_broadway", "small_pair",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway",
        },
        description="15 BB MP: Push strong, min-raise mid",
    ),
    (15, "late"): OpenJamBaseline(
        stack_bb=15,
        position_group="late",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway",
        },
        min_raise_hands={
            "small_pair", "low_suited_connector",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair",
        },
        description="15 BB LP: Push strong+, min-raise mid",
    ),
    (15, "blind"): OpenJamBaseline(
        stack_bb=15,
        position_group="blind",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair",
        },
        min_raise_hands={
            "low_suited_connector",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair", "low_suited_connector",
        },
        description="15 BB SB/BB: Push wide, min-raise suited",
    ),
    (18, "early"): OpenJamBaseline(
        stack_bb=18,
        position_group="early",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
        },
        min_raise_hands={
            "medium_pair", "suited_ace",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
        },
        description="18 BB EP: Push premium, min-raise medium",
    ),
    (18, "middle"): OpenJamBaseline(
        stack_bb=18,
        position_group="middle",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace",
        },
        min_raise_hands={
            "wheel_ace", "middling_broadway",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
        },
        description="18 BB MP: Push strong, min-raise mid",
    ),
    (18, "late"): OpenJamBaseline(
        stack_bb=18,
        position_group="late",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
        },
        min_raise_hands={
            "middling_broadway", "small_pair",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway",
        },
        description="18 BB LP: Push premium+, min-raise mid",
    ),
    (18, "blind"): OpenJamBaseline(
        stack_bb=18,
        position_group="blind",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway",
        },
        min_raise_hands={
            "small_pair", "low_suited_connector",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair",
        },
        description="18 BB SB/BB: Push strong, min-raise mid",
    ),
    (20, "early"): OpenJamBaseline(
        stack_bb=20,
        position_group="early",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
        },
        min_raise_hands={
            "medium_pair", "suited_ace",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace",
        },
        description="20 BB EP: Push premium, min-raise medium",
    ),
    (20, "middle"): OpenJamBaseline(
        stack_bb=20,
        position_group="middle",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair",
        },
        min_raise_hands={
            "suited_ace", "wheel_ace", "middling_broadway",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
        },
        description="20 BB MP: Push strong, min-raise mid",
    ),
    (20, "late"): OpenJamBaseline(
        stack_bb=20,
        position_group="late",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace",
        },
        min_raise_hands={
            "wheel_ace", "middling_broadway", "small_pair",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
        },
        description="20 BB LP: Push premium+, min-raise mid",
    ),
    (20, "blind"): OpenJamBaseline(
        stack_bb=20,
        position_group="blind",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
        },
        min_raise_hands={
            "middling_broadway", "small_pair",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway",
        },
        description="20 BB SB/BB: Push strong, min-raise mid",
    ),
    (25, "early"): OpenJamBaseline(
        stack_bb=25,
        position_group="early",
        push_hands={
            "premium_pair",
        },
        min_raise_hands={
            "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace",
        },
        pko_push_hands={
            "premium_pair", "strong_ace",
        },
        description="25 BB EP: Push AA-QQ, min-raise rest",
    ),
    (25, "middle"): OpenJamBaseline(
        stack_bb=25,
        position_group="middle",
        push_hands={
            "premium_pair", "strong_ace",
        },
        min_raise_hands={
            "strong_broadway", "medium_pair", "suited_ace",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
        },
        description="25 BB MP: Push premium+, min-raise strong",
    ),
    (25, "late"): OpenJamBaseline(
        stack_bb=25,
        position_group="late",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
        },
        min_raise_hands={
            "medium_pair", "suited_ace", "wheel_ace",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace",
        },
        description="25 BB LP: Push premium, min-raise mid+",
    ),
    (25, "blind"): OpenJamBaseline(
        stack_bb=25,
        position_group="blind",
        push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
        },
        min_raise_hands={
            "medium_pair", "suited_ace", "wheel_ace",
        },
        pko_push_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
        },
        description="25 BB SB/BB: Push premium, min-raise mid+",
    ),
}

def bucket_stack_depth(bb: float) -> int:
    if bb <= 8:
        return 8
    elif bb <= 10:
        return 10
    elif bb <= 12:
        return 12
    elif bb <= 15:
        return 15
    elif bb <= 18:
        return 18
    elif bb <= 20:
        return 20
    else:
        return 25

def get_baseline(stack_bb: int, position_group: str) -> Optional[OpenJamBaseline]:
    return OPEN_JAM_BASELINES.get((stack_bb, position_group))

def classify_action(hand_class: str, baseline: OpenJamBaseline) -> str:
    if hand_class in baseline.push_hands:
        return "push"
    elif hand_class in baseline.min_raise_hands:
        return "min_raise"
    else:
        return "fold"

def compare_decision(hand_class: str, actual_action: str, baseline: OpenJamBaseline) -> dict:
    expected = classify_action(hand_class, baseline)
    
    if actual_action == expected:
        return {"status": "correct", "hand": hand_class, "expected": expected, "actual": actual_action}
    
    return {"status": "leak", "hand": hand_class, "expected": expected, "actual": actual_action}

def get_all_buckets() -> list[tuple[int, str]]:
    buckets = []
    for depth in [8, 10, 12, 15, 18, 20, 25]:
        for pos in ["early", "middle", "late", "blind"]:
            if (depth, pos) in OPEN_JAM_BASELINES:
                buckets.append((depth, pos))
    return buckets


@dataclass
class CallOffBaseline:
    stack_bucket: str
    position_group: str
    call_hands: set[str]
    fold_hands: set[str]
    description: str


CALL_OFF_BASELINES = {
    ("shallow", "early"): CallOffBaseline(
        stack_bucket="shallow",
        position_group="early",
        call_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace",
        },
        fold_hands={
            "wheel_ace", "middling_broadway", "small_pair",
            "low_suited_connector", "low_suited_gapper",
            "trash", "dominated_broadway", "weak_ace",
        },
        description="8-12 BB EP: Call premium+, fold rest",
    ),
    ("shallow", "middle"): CallOffBaseline(
        stack_bucket="shallow",
        position_group="middle",
        call_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
        },
        fold_hands={
            "middling_broadway", "small_pair",
            "low_suited_connector", "low_suited_gapper",
            "trash", "dominated_broadway", "weak_ace",
        },
        description="8-12 BB MP: Call strong+, fold marginal",
    ),
    ("shallow", "late"): CallOffBaseline(
        stack_bucket="shallow",
        position_group="late",
        call_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway",
        },
        fold_hands={
            "small_pair", "low_suited_connector", "low_suited_gapper",
            "trash", "dominated_broadway", "weak_ace",
        },
        description="8-12 BB LP: Call wide, fold trash",
    ),
    ("shallow", "blind"): CallOffBaseline(
        stack_bucket="shallow",
        position_group="blind",
        call_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway",
        },
        fold_hands={
            "small_pair", "low_suited_connector", "low_suited_gapper",
            "trash", "dominated_broadway", "weak_ace",
        },
        description="8-12 BB SB/BB: Call strong, fold rest",
    ),
    ("shove_critical", "early"): CallOffBaseline(
        stack_bucket="shove_critical",
        position_group="early",
        call_hands={
            "premium_pair", "strong_ace", "strong_broadway",
        },
        fold_hands={
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair",
            "low_suited_connector", "low_suited_gapper",
            "trash", "dominated_broadway", "weak_ace",
        },
        description="<8 BB EP: Only premium call",
    ),
    ("shove_critical", "middle"): CallOffBaseline(
        stack_bucket="shove_critical",
        position_group="middle",
        call_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair",
        },
        fold_hands={
            "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair",
            "low_suited_connector", "low_suited_gapper",
            "trash", "dominated_broadway", "weak_ace",
        },
        description="<8 BB MP: Call premium+pair",
    ),
    ("shove_critical", "late"): CallOffBaseline(
        stack_bucket="shove_critical",
        position_group="late",
        call_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace",
        },
        fold_hands={
            "wheel_ace", "middling_broadway", "small_pair",
            "low_suited_connector", "low_suited_gapper",
            "trash", "dominated_broadway", "weak_ace",
        },
        description="<8 BB LP: Call premium+, fold marginal",
    ),
    ("shove_critical", "blind"): CallOffBaseline(
        stack_bucket="shove_critical",
        position_group="blind",
        call_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
        },
        fold_hands={
            "middling_broadway", "small_pair",
            "low_suited_connector", "low_suited_gapper",
            "trash", "dominated_broadway", "weak_ace",
        },
        description="<8 BB SB/BB: Call wider in blinds",
    ),
    ("deeper", "early"): CallOffBaseline(
        stack_bucket="deeper",
        position_group="early",
        call_hands={
            "premium_pair", "strong_ace", "strong_broadway",
        },
        fold_hands={
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair",
            "low_suited_connector", "low_suited_gapper",
            "trash", "dominated_broadway", "weak_ace",
        },
        description="15-25 BB EP: Call premium only",
    ),
    ("deeper", "middle"): CallOffBaseline(
        stack_bucket="deeper",
        position_group="middle",
        call_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair",
        },
        fold_hands={
            "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair",
            "low_suited_connector", "low_suited_gapper",
            "trash", "dominated_broadway", "weak_ace",
        },
        description="15-25 BB MP: Call premium+pair",
    ),
    ("deeper", "late"): CallOffBaseline(
        stack_bucket="deeper",
        position_group="late",
        call_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace",
        },
        fold_hands={
            "wheel_ace", "middling_broadway", "small_pair",
            "low_suited_connector", "low_suited_gapper",
            "trash", "dominated_broadway", "weak_ace",
        },
        description="15-25 BB LP: Call strong+",
    ),
    ("deeper", "blind"): CallOffBaseline(
        stack_bucket="deeper",
        position_group="blind",
        call_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
        },
        fold_hands={
            "middling_broadway", "small_pair",
            "low_suited_connector", "low_suited_gapper",
            "trash", "dominated_broadway", "weak_ace",
        },
        description="15-25 BB SB/BB: Call wider in blinds",
    ),
}


@dataclass
class ReshoveBaseline:
    stack_bucket: str
    position_group: str
    reshove_hands: set[str]
    description: str


RESHOVE_BASELINES = {
    ("shallow", "early"): ReshoveBaseline(
        stack_bucket="shallow",
        position_group="early",
        reshove_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace",
        },
        description="8-12 BB EP: Shove premium+",
    ),
    ("shallow", "middle"): ReshoveBaseline(
        stack_bucket="shallow",
        position_group="middle",
        reshove_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
        },
        description="8-12 BB MP: Shove strong+",
    ),
    ("shallow", "late"): ReshoveBaseline(
        stack_bucket="shallow",
        position_group="late",
        reshove_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway",
        },
        description="8-12 BB LP: Shove wide",
    ),
    ("shallow", "blind"): ReshoveBaseline(
        stack_bucket="shallow",
        position_group="blind",
        reshove_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway", "small_pair",
        },
        description="8-12 BB SB/BB: Shove widest",
    ),
    ("shove_critical", "early"): ReshoveBaseline(
        stack_bucket="shove_critical",
        position_group="early",
        reshove_hands={
            "premium_pair", "strong_ace", "strong_broadway",
        },
        description="<8 BB EP: Shove premium only",
    ),
    ("shove_critical", "middle"): ReshoveBaseline(
        stack_bucket="shove_critical",
        position_group="middle",
        reshove_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair",
        },
        description="<8 BB MP: Shove premium+",
    ),
    ("shove_critical", "late"): ReshoveBaseline(
        stack_bucket="shove_critical",
        position_group="late",
        reshove_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace",
        },
        description="<8 BB LP: Shove strong+",
    ),
    ("shove_critical", "blind"): ReshoveBaseline(
        stack_bucket="shove_critical",
        position_group="blind",
        reshove_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
        },
        description="<8 BB SB/BB: Shove premium+",
    ),
    ("deeper", "early"): ReshoveBaseline(
        stack_bucket="deeper",
        position_group="early",
        reshove_hands={
            "premium_pair", "strong_ace", "strong_broadway",
        },
        description="15-25 BB EP: Shove premium only",
    ),
    ("deeper", "middle"): ReshoveBaseline(
        stack_bucket="deeper",
        position_group="middle",
        reshove_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair",
        },
        description="15-25 BB MP: Shove premium+",
    ),
    ("deeper", "late"): ReshoveBaseline(
        stack_bucket="deeper",
        position_group="late",
        reshove_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace",
        },
        description="15-25 BB LP: Shove strong+",
    ),
    ("deeper", "blind"): ReshoveBaseline(
        stack_bucket="deeper",
        position_group="blind",
        reshove_hands={
            "premium_pair", "strong_ace", "strong_broadway",
            "medium_pair", "suited_ace", "wheel_ace",
            "middling_broadway",
        },
        description="15-25 BB SB/BB: Shove wide",
    ),
}


def get_call_off_baseline(stack_bucket: str, position_group: str) -> Optional[CallOffBaseline]:
    return CALL_OFF_BASELINES.get((stack_bucket, position_group))


def get_reshove_baseline(stack_bucket: str, position_group: str) -> Optional[ReshoveBaseline]:
    return RESHOVE_BASELINES.get((stack_bucket, position_group))