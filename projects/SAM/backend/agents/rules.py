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
