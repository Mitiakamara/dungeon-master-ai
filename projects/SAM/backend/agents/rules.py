from .dice import DiceRoller

# D&D 5e XP thresholds for leveling
XP_THRESHOLDS = {
    1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500,
    6: 14000, 7: 23000, 8: 34000, 9: 48000, 10: 64000,
    11: 85000, 12: 100000, 13: 120000, 14: 140000, 15: 165000,
    16: 195000, 17: 225000, 18: 265000, 19: 305000, 20: 355000
}


def get_level_for_xp(xp: int) -> int:
    """Determine character level based on total XP."""
    level = 1
    for lvl, threshold in sorted(XP_THRESHOLDS.items()):
        if xp >= threshold:
            level = lvl
        else:
            break
    return level


def xp_to_next_level(current_xp: int, current_level: int) -> int:
    """Calculate XP needed for next level."""
    next_level = current_level + 1
    if next_level > 20:
        return 0
    return max(0, XP_THRESHOLDS.get(next_level, 0) - current_xp)


def calculate_hp_change(current_hp: int, amount: int, hp_max: int, is_damage: bool = True) -> dict:
    """Calculate HP change. Returns new HP and actual change."""
    if is_damage:
        new_hp = max(0, current_hp - amount)
        actual = current_hp - new_hp
    else:
        new_hp = min(hp_max, current_hp + amount)
        actual = new_hp - current_hp
    return {"new_hp": new_hp, "actual_change": actual, "is_unconscious": new_hp == 0}


def check_hit(attack_roll: int, modifier: int, target_ac: int) -> dict:
    """Determine if an attack hits."""
    is_nat20 = attack_roll == 20
    is_nat1 = attack_roll == 1
    total = attack_roll + modifier
    hit = is_nat20 or (not is_nat1 and total >= target_ac)
    return {
        "roll": attack_roll,
        "modifier": modifier,
        "total": total,
        "target_ac": target_ac,
        "hit": hit,
        "critical": is_nat20,
        "fumble": is_nat1
    }


def check_save(roll: int, modifier: int, dc: int) -> dict:
    """Determine if a saving throw succeeds."""
    total = roll + modifier
    return {
        "roll": roll,
        "modifier": modifier,
        "total": total,
        "dc": dc,
        "success": total >= dc
    }


# ─────────────────────────────────────────────
# Encounter balancing (D&D 5e CR + party XP)
# ─────────────────────────────────────────────

CR_XP_VALUES = {
    0: 10, 0.125: 25, 0.25: 50, 0.5: 100,
    1: 200, 2: 450, 3: 700, 4: 1100, 5: 1800,
    6: 2300, 7: 2900, 8: 3900, 9: 5000, 10: 5900,
    11: 7200, 12: 8400, 13: 10000, 14: 11500, 15: 13000,
    16: 15000, 17: 18000, 18: 20000, 19: 22000, 20: 25000,
    21: 33000, 22: 41000, 23: 50000, 24: 62000, 25: 75000,
    26: 90000, 27: 105000, 28: 120000, 29: 135000, 30: 155000,
}

# Average HP gained per level by class (5e fixed average, before CON mod)
HP_AVG_PER_LEVEL = {
    "barbarian": 7,
    "fighter": 6, "paladin": 6, "ranger": 6,
    "rogue": 5, "cleric": 5, "bard": 5, "monk": 5, "druid": 5, "warlock": 5,
    "wizard": 4, "sorcerer": 4,
}


def _normalize_cr(cr):
    """CR as float, or None if unparseable. Accepts int, float, '3', '0.5', '1/2'."""
    try:
        if isinstance(cr, str):
            cr = cr.strip()
            if "/" in cr:
                num, den = cr.split("/", 1)
                return float(num) / float(den)
        return float(cr)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def get_xp_for_cr(cr) -> int:
    """XP value for a CR. Accepts int, float, or str ('3', '0.5', '1/2')."""
    value = _normalize_cr(cr)
    if value is None:
        return 0
    # float(1) == 1 hashes equal to the int key, so .get(1.0) finds CR 1
    return CR_XP_VALUES.get(value, 0)


# Loot budget per CR band (5e-ish individual treasure, simplified — SAM-021 f2).
# Python decides gold and item slots; the LLM only NAMES flavor items.
# Bands: (max_cr inclusive | None = open end, dice_count, dice_sides,
#         multiplier, item_slots, item_rarity)
LOOT_BUDGET = [
    (0.25, 2, 6, 1, 0, None),
    (1,    3, 6, 1, 1, "trinket"),
    (4,    4, 6, 2, 1, "common"),
    (8,    6, 6, 5, 1, "uncommon"),
    (None, 8, 6, 10, 2, "uncommon"),  # CR 9+
]


def get_loot_budget(cr) -> dict:
    """
    Loot budget for a slain creature: gold (already rolled) + item slots and
    rarity. Unknown/unparseable CR falls to the CR 0 band (some gold, no items).
    """
    value = _normalize_cr(cr)
    if value is None:
        value = 0
    for max_cr, count, sides, mult, slots, rarity in LOOT_BUDGET:
        if max_cr is None or value <= max_cr:
            rolled = DiceRoller.roll_with_modifier(count, sides, 0)["total"] * mult
            return {
                "gold": rolled,
                "gold_spec": f"{count}d{sides}" + (f"x{mult}" if mult > 1 else ""),
                "item_slots": slots,
                "item_rarity": rarity,
            }


# [Easy, Medium, Hard, Deadly]
ENCOUNTER_THRESHOLDS = {
    1: [25, 50, 75, 100],
    2: [50, 100, 150, 200],
    3: [75, 150, 225, 400],
    4: [125, 250, 375, 500],
    5: [250, 500, 750, 1100],
    6: [300, 600, 900, 1400],
    7: [350, 750, 1100, 1700],
    8: [450, 900, 1400, 2100],
    9: [550, 1100, 1600, 2400],
    10: [600, 1200, 1900, 2800],
    11: [800, 1600, 2400, 3600],
    12: [1000, 2000, 3000, 4500],
    13: [1100, 2200, 3400, 5100],
    14: [1250, 2500, 3800, 5700],
    15: [1400, 2800, 4300, 6400],
    16: [1600, 3200, 4800, 7200],
    17: [2000, 3900, 5900, 8800],
    18: [2100, 4200, 6300, 9500],
    19: [2400, 4900, 7300, 10900],
    20: [2800, 5700, 8500, 12700],
}


def calculate_encounter_difficulty(monster_crs: list, party_levels: list) -> dict:
    """
    Calculate encounter difficulty based on monster CRs and party levels.
    Returns difficulty rating and recommendation.
    """
    total_monster_xp = sum(CR_XP_VALUES.get(cr, 0) for cr in monster_crs)

    num_monsters = len(monster_crs)
    if num_monsters == 1:
        multiplier = 1.0
    elif num_monsters == 2:
        multiplier = 1.5
    elif num_monsters <= 6:
        multiplier = 2.0
    elif num_monsters <= 10:
        multiplier = 2.5
    elif num_monsters <= 14:
        multiplier = 3.0
    else:
        multiplier = 4.0

    adjusted_xp = total_monster_xp * multiplier

    party_easy = sum(ENCOUNTER_THRESHOLDS.get(lvl, [25, 50, 75, 100])[0] for lvl in party_levels)
    party_medium = sum(ENCOUNTER_THRESHOLDS.get(lvl, [25, 50, 75, 100])[1] for lvl in party_levels)
    party_hard = sum(ENCOUNTER_THRESHOLDS.get(lvl, [25, 50, 75, 100])[2] for lvl in party_levels)
    party_deadly = sum(ENCOUNTER_THRESHOLDS.get(lvl, [25, 50, 75, 100])[3] for lvl in party_levels)

    if adjusted_xp >= party_deadly:
        difficulty = "DEADLY"
        recommendation = "This encounter will likely kill one or more party members. Consider using fewer or weaker monsters."
    elif adjusted_xp >= party_hard:
        difficulty = "HARD"
        recommendation = "Challenging but fair. The party will need to use resources wisely."
    elif adjusted_xp >= party_medium:
        difficulty = "MEDIUM"
        recommendation = "A balanced encounter. Some risk but manageable."
    elif adjusted_xp >= party_easy:
        difficulty = "EASY"
        recommendation = "Low risk. Good for warm-up or resource conservation."
    else:
        difficulty = "TRIVIAL"
        recommendation = "No real challenge. Consider adding more monsters or using stronger ones."

    return {
        "total_monster_xp": total_monster_xp,
        "adjusted_xp": adjusted_xp,
        "multiplier": multiplier,
        "difficulty": difficulty,
        "recommendation": recommendation,
        "thresholds": {
            "easy": party_easy,
            "medium": party_medium,
            "hard": party_hard,
            "deadly": party_deadly,
        },
    }


def get_recommended_cr_range(party_levels: list) -> dict:
    """Get recommended CR range for a party."""
    if not party_levels:
        return {
            "single_monster_cr": 1,
            "pair_cr": 0.5,
            "group_4_cr": 0.25,
            "boss_cr": 3,
            "avg_party_level": 1,
            "party_size": 0,
        }

    avg_level = sum(party_levels) / len(party_levels)
    party_size = len(party_levels)

    return {
        "single_monster_cr": round(avg_level),
        "pair_cr": max(0.5, round(avg_level * 0.6, 1)),
        "group_4_cr": max(0.25, round(avg_level * 0.3, 1)),
        "boss_cr": round(avg_level + 2),
        "avg_party_level": avg_level,
        "party_size": party_size,
    }
