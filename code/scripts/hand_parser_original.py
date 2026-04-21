import os
import re
from openai import OpenAI

client = OpenAI()

HERO_NAME = "Hero"

# -------- READ FILE --------
def read_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

# -------- SPLIT HANDS --------
def split_hands(text):
    # Splits by GG Poker hand headers
    hands = re.split(r'(Hand #\w+:|Poker Hand #\w+:)', text)
    combined = []
    for i in range(1, len(hands), 2):
        combined.append(hands[i] + hands[i+1])
    return combined

# -------- POSITION FUNCTIONS --------
def extract_positions(hand):
    lines = hand.split("\n")
    button_seat = None
    hero_seat = None
    active_seats = []

    for line in lines:
        if "is the button" in line:
            match = re.search(r'Seat #(\d+)', line)
            if match: button_seat = int(match.group(1))

        # Only count seats that are actually in the hand with chips
        if line.strip().startswith("Seat") and "in chips" in line:
            match = re.search(r'Seat (\d+):', line)
            if match:
                seat = int(match.group(1))
                active_seats.append(seat)
                if f" {HERO_NAME} " in line or f": {HERO_NAME}" in line:
                    hero_seat = seat

    return button_seat, hero_seat, sorted(active_seats)

def assign_positions(button_seat, seats):
    if not seats: return {}
    if button_seat not in seats:
        potential_btns = [s for s in seats if s <= button_seat]
        button_seat = potential_btns[-1] if potential_btns else seats[-1]

    btn_index = seats.index(button_seat)
    # Order: SB, BB, UTG... BTN
    ordered = seats[btn_index+1:] + seats[:btn_index+1]
    num_players = len(ordered)

    if num_players == 2:
        positions_order = ["SB/BTN", "BB"]
    elif num_players == 3:
        positions_order = ["SB", "BB", "BTN"]
    else:
        # Dynamic mapping to prevent IndexError
        core = ["SB", "BB"]
        middle_count = num_players - 4
        middles = ["UTG"] + [f"UTG+{i}" for i in range(1, middle_count + 1)] if middle_count >= 0 else []
        positions_order = core + middles + ["CO", "BTN"]

    # Safety padding
    while len(positions_order) < len(ordered):
        positions_order.insert(2, "MP")

    return {seat: positions_order[i] for i, seat in enumerate(ordered)}

# -------- HELPER FUNCTIONS --------
def extract_bb_value(hand):
    # Search for the standard GG Level format: Level 15 (1,250/2,500)
    level_match = re.search(r'Level \d+ \([\d,]+/([\d,]+)\)', hand)
    if level_match:
        return int(level_match.group(1).replace(",", ""))

    # Search for header format often found in the first two lines: (250/500)
    # This looks for any (number/number) pattern and takes the second one
    header_match = re.search(r'\(([\d,]+)/([\d,]+)\)', hand)
    if header_match:
        return int(header_match.group(2).replace(",", ""))
        
    # Search for "Big Blind" literal string
    bb_literal = re.search(r'Big Blind ([\d,]+)', hand, re.IGNORECASE)
    if bb_literal:
        return int(bb_literal.group(1).replace(",", ""))

    return None

def extract_hero_chips(hand):
    # Matches: Seat X: Hero (123,456 in chips)
    match = re.search(rf'Seat \d+: {re.escape(HERO_NAME)} \((\d[\d,]*)\s+in chips\)', hand)
    if match:
        return int(match.group(1).replace(",", ""))
    return None

# -------- EXTRACT INFO --------
def extract_info(hand):
    bb = extract_bb_value(hand)
    chips = extract_hero_chips(hand)
    
    # If BB is still None, we check the first few lines of the hand specifically
    if not bb:
        first_line = hand.split('\n')[0]
        # Match "(100/200)" in "Table 'Zodiac' 6-max (100/200)"
        m = re.search(r'/([\d,]+)\)', first_line)
        if m: bb = int(m.group(1).replace(",", ""))

    info = {
        "hero_cards": "Unknown",
        "hero_chips": chips,
        "bb": bb,
        "hero_vpip": False,
        "hero_all_in": False,
        "position": "UNKNOWN"
    }

    # Rest of the logic remains the same...
    btn, hero_s, seats = extract_positions(hand)
    if btn is not None and hero_s is not None:
        pos_map = assign_positions(btn, seats)
        info["position"] = pos_map.get(hero_s, "UNKNOWN")

    if info["hero_chips"] is not None and info["bb"]:
        info["hero_bb"] = round(info["hero_chips"] / info["bb"], 2)
    else:
        info["hero_bb"] = "N/A"
        
    # Action parsing...
    lines = hand.split("\n")
    for line in lines:
        if f"Dealt to {HERO_NAME}" in line:
            info["hero_cards"] = line.split("[")[-1].split("]")[0] if "[" in line else "Unknown"
        if line.startswith(f"{HERO_NAME}:"):
            if any(x in line for x in ["calls", "raises", "bets"]):
                info["hero_vpip"] = True
            if "all-in" in line.lower():
                info["hero_all_in"] = True
    return info

def is_important(hand, info):
    if info["hero_vpip"] or info["hero_all_in"]: return True
    if info["position"] in ["BB", "SB"] and ("raises" in hand or "all-in" in hand.lower()):
        if f"{HERO_NAME}: folds" in hand: return True
    return False

# -------- AI ANALYSIS --------
def analyze_hand(hand, info):
    prompt = f"""
Elite MTT Coach Analysis.
Hero Name: {HERO_NAME} | Pos: {info['position']} | Stack: {info['hero_bb']} BB | Cards: {info['hero_cards']}

Hand History:
{hand}

Format:
- Mistake: [Briefly state the error]
- Better play: [GTO/ICM recommendation]
- Reason: [1-2 sentences on why]
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.2,
            messages=[
        {"role": "system", "content": """You are an elite GTO MTT Coach. 
        Follow these rules:
        1. Under 1 BB: Hero is 'auto-all-in'. Fold equity is zero. The only 'mistake' is folding.
        2. 1-12 BB: Use Push/Fold charts. Fold equity is the primary goal.
        3. 13-25 BB: Focus on 3-bet shoves and set-mining.
        4. Always consider ICM (stack preservation vs. field) in your 'Reason'."""},
        {"role": "user", "content": prompt}
    ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

# -------- MAIN --------
def main():
    file_path = os.path.expanduser("/Users/shubham/Downloads/GG20260216-1224 - APL Series 110 Zodiac Evening Classic + Horse.txt")
    
    if not os.path.exists(file_path):
        print("File not found.")
        return

    hands = split_hands(read_file(file_path))
    important_hands = []

    for hand in hands:
        info = extract_info(hand)
        if is_important(hand, info):
            important_hands.append((hand, info))

    print(f"Parsed {len(hands)} hands. Found {len(important_hands)} actionable spots.\n")

    for i, (hand, info) in enumerate(important_hands[:10]): # Process first 10
        print(f"{'='*50}\nHAND {i+1} | {info['position']} | {info['hero_bb']} BB\n{'-'*50}")
        print(analyze_hand(hand, info))

if __name__ == "__main__":
    main()
