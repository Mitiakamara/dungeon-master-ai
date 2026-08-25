"""
Mechanic Agent — Pure Python game engine.
Receives structured intents, executes mechanics, returns facts.
Zero LLM calls. Zero XML. Zero guessing.
"""

from .dice import DiceRoller
from .rules import (
    calculate_hp_change, check_hit, check_save,
    get_level_for_xp, xp_to_next_level, XP_THRESHOLDS,
    HP_AVG_PER_LEVEL
)
from .combat_state import CombatState
from typing import Optional
import json
import re


def parse_dice_notation(notation):
    """Parse 'NdM[+X]' (optional damage-type suffix) → (count, sides).
    Returns (None, None) when there's no dice expression (e.g. a bare number)."""
    if not notation:
        return None, None
    tokens = str(notation).strip().split()
    token = tokens[0] if tokens else ""
    token = re.split(r"[+\-]", token)[0]  # drop the modifier
    m = re.match(r"(\d*)d(\d+)$", token.lower())
    if not m:
        return None, None
    count = int(m.group(1)) if m.group(1) else 1
    return count, int(m.group(2))


def clean_dice_spec(notation):
    """Return just the dice expression 'NdM[+X]' (strip any damage-type suffix)."""
    if not notation:
        return ""
    tokens = str(notation).strip().split()
    return tokens[0] if tokens else ""


# D&D 5e skill → ability mapping
SKILL_ABILITY_MAP = {
    "acrobatics": "dex", "animal_handling": "wis", "arcana": "int",
    "athletics": "str", "deception": "cha", "history": "int",
    "insight": "wis", "intimidation": "cha", "investigation": "int",
    "medicine": "wis", "nature": "int", "perception": "wis",
    "performance": "cha", "persuasion": "cha", "religion": "int",
    "sleight_of_hand": "dex", "stealth": "dex", "survival": "wis",
}

# SAM-053: the interpreter is told to emit canonical English skill names, but it
# is an LLM — a Spanish name that slips through used to fall silently to the
# "wis" default with proficiency "none" (a Stealth check resolved as a bare WIS
# roll). Python normalizes here so the degradation can't happen. Keys are
# accent-stripped and space→underscore, matching _calculate_skill_modifier.
SKILL_ALIASES = {
    "percepcion": "perception", "sigilo": "stealth", "historia": "history",
    "intimidacion": "intimidation", "investigacion": "investigation",
    "engano": "deception", "enganio": "deception", "atletismo": "athletics",
    "acrobacias": "acrobatics", "perspicacia": "insight", "intuicion": "insight",
    "naturaleza": "nature", "medicina": "medicine", "supervivencia": "survival",
    "interpretacion": "performance", "actuacion": "performance",
    "juego_de_manos": "sleight_of_hand", "trato_con_animales": "animal_handling",
    "arcano": "arcana", "conocimiento_arcano": "arcana",
    # persuasion / religion / arcana are spelled identically once de-accented.
}


def _strip_accents(text: str) -> str:
    """lower + drop diacritics, so 'Percepción' and 'percepcion' compare equal."""
    import unicodedata
    s = unicodedata.normalize("NFKD", str(text or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


class MechanicEngine:
    """Executes D&D 5e mechanics deterministically."""

    def __init__(self, combat_state: CombatState = None):
        self.combat = combat_state or CombatState()
        self.results = []  # Accumulates mechanical results for the narrator
        self.state_updates = []  # DB updates to apply (HP, XP, inventory, etc.)
        self.pending_player_roll = None  # What we're waiting for the player to roll

    def reset_turn(self):
        """Clear results for a new turn."""
        self.results = []
        self.state_updates = []

    # ─────────────────────────────────────
    # PLAYER ACTIONS
    # ─────────────────────────────────────

    def process_spell(self, caster: dict, spell: dict, target: dict) -> dict:
        """
        Process a spell cast.
        caster: character context (name, stats, level, etc.)
        spell: spell data (name, save_atk, damage, range, etc.)
        target: target data (name, ac, hp, hp_max, saves, is_npc, etc.)
        """
        result = {
            "action": "spell",
            "caster": caster["name"],
            "spell": spell["name"],
            "target": target["name"]
        }

        save_atk = spell.get("save_atk", "")

        # Spell requires a saving throw (e.g., Sacred Flame: DEX 13)
        if save_atk and any(s in save_atk.upper() for s in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]):
            # Parse DC from save_atk (e.g., "DEX 13" or "WIS 13")
            parts = save_atk.strip().split()
            ability = parts[0].upper() if parts else ""
            dc = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 13

            if target.get("is_npc", False):
                # NPC save — we roll for them
                save_mod = target.get("saves", {}).get(ability.lower(), 0)
                roll = DiceRoller.roll(20)
                save_result = check_save(roll, save_mod, dc)
                result["save"] = {
                    "ability": ability,
                    "roll": roll,
                    "modifier": save_mod,
                    "total": save_result["total"],
                    "dc": dc,
                    "success": save_result["success"]
                }

                if not save_result["success"]:
                    # Save failed — need damage from player
                    result["needs_player_roll"] = True
                    result["damage_dice"] = self._get_spell_damage_dice(spell, caster)
                    result["prompt_player"] = f"¡{target['name']} falla la salvación! Tira {result['damage_dice']} de daño."
                    self.pending_player_roll = {
                        "type": "spell_damage",
                        "spell": spell["name"],
                        "target": target["name"],
                        "target_data": target,
                        "damage_spec": clean_dice_spec(result["damage_dice"]),  # SAM-042
                        "character_name": caster.get("name"),  # SAM-049: owner
                    }
                else:
                    result["needs_player_roll"] = False
                    result["prompt_player"] = f"¡{target['name']} resiste el hechizo!"
            else:
                # Player target — player rolls their own save
                result["needs_player_roll"] = True
                result["prompt_player"] = f"Haz una tirada de salvación de {ability} (DC {dc})."

        # Spell requires attack roll (e.g., Ray of Sickness: +4)
        elif save_atk and (save_atk.startswith("+") or save_atk.startswith("-")):
            result["needs_player_roll"] = True
            result["prompt_player"] = f"Haz tu tirada de ataque con {spell['name']}."
            self.pending_player_roll = {
                "type": "spell_attack",
                "spell": spell["name"],
                "target": target["name"],
                "target_data": target,
                "attack_bonus": save_atk,
                "character_name": caster.get("name"),  # SAM-049: owner
            }

        self.results.append(result)
        return result

    def process_attack(self, attacker: dict, weapon: dict, target: dict) -> dict:
        """
        Process a weapon attack.
        Player rolls attack — we wait for SYSTEM EVENT.
        """
        result = {
            "action": "attack",
            "attacker": attacker["name"],
            "weapon": weapon["name"],
            "target": target["name"],
            "target_ac": target.get("ac", 10),
            "needs_player_roll": True,
            "prompt_player": f"Haz tu tirada de ataque con {weapon['name']} (bono {weapon.get('bonus', '+0')})."
        }
        self.pending_player_roll = {
            "type": "weapon_attack",
            "weapon": weapon,
            "target": target["name"],
            "target_data": target
        }
        self.results.append(result)
        return result

    def process_skill_check(self, character: dict, skill: str, dc: int = None) -> dict:
        """
        Process a skill check. Player rolls — we wait.
        DC is determined by orchestrator/interpreter or defaults.
        """
        result = {
            "action": "skill_check",
            "character": character.get("name", "Unknown"),
            "skill": skill,
            "dc": dc,
            "needs_player_roll": True,
            "prompt_player": f"Haz una tirada de {skill}."
        }
        self.pending_player_roll = {
            "type": "skill_check",
            "skill": skill,
            "dc": dc,
            # SAM-049/SAM-053: the check belongs to whoever declared it. The
            # orchestrator overrides character_name with the authoritative
            # sender_name, but stamping here means an ownerless skill pending
            # can never be created, whatever the call site.
            "character_name": character.get("name"),
            "character_id": character.get("id"),
        }
        self.results.append(result)
        return result

    # ─────────────────────────────────────
    # DICE RESULT PROCESSING
    # ─────────────────────────────────────

    def process_player_roll(self, character: dict, roll_data: dict) -> dict:
        """
        Process a SYSTEM EVENT dice roll from a player.
        roll_data: {"dice": "1d20", "result": 18, "rolls": [18]}
        """
        pending = self.pending_player_roll
        if not pending:
            # SAM-053: no pending action. This used to return silently WITHOUT
            # appending to self.results — empty facts dropped the request into
            # narrate_roleplay, where the LLM improvised a total (and sometimes
            # a legacy DM_ROLL tag). Now it renders as an ORPHAN ROLL fact so
            # the narrator answers honestly through narrate_mechanics.
            # Informative only: nothing is blocked, no action is consumed.
            char_name = character.get("name", "Unknown")
            dice_str = str(roll_data.get("dice", "")).strip() or "dice"
            rolls = roll_data.get("rolls") or []
            raw = rolls[0] if len(rolls) == 1 else (
                roll_data.get("result", 0) if not rolls else ", ".join(str(x) for x in rolls)
            )
            result = {
                "action": "orphan_roll",
                "character": char_name,
                "dice": dice_str,
                "raw": raw,
                "rolls": rolls,
            }
            print(f"🎲 Orphan roll: {char_name} {dice_str}={raw} — no pending")
            self.results.append(result)
            return {"action": "freeform_roll", "roll": roll_data, "character": char_name}

        # SAM-049: the pending belongs to a specific character. A die from anyone
        # else is THEIR own freeform roll — never consume or resolve someone
        # else's pending. This is the ONLY ownership check outside combat (the
        # turn guard only runs when combat.active), so it guards exploration too
        # (e.g. Björn's Perception pending vs a die Fekas rolls).
        owner = (pending.get("character_name") or "").strip().lower()
        roller = (character.get("name") or "").strip().lower()
        if owner and roller and owner != roller:
            print(f"🚫 Roll by {character.get('name')} ignored — pending belongs to "
                  f"{pending.get('character_name')} (preserved)")
            return {"action": "freeform_roll", "roll": roll_data, "character": character.get("name", "Unknown")}

        # SAM-039/042: strict dice validation. If the rolled dice don't match
        # what the pending action requires, reject WITHOUT touching state and
        # keep the pending intact so the correct die can be rolled next request.
        invalid = self._check_dice(pending, roll_data)
        if invalid:
            result = {"action": "invalid_dice", **invalid}
            self.results.append(result)
            print(f"⛔ Invalid dice: expected {invalid['expected']}, got {invalid['rolled']} — pending preserved")
            return result

        self.pending_player_roll = None  # Clear pending

        if pending["type"] == "spell_damage":
            return self._resolve_spell_damage(character, roll_data, pending)
        elif pending["type"] == "weapon_attack":
            return self._resolve_weapon_attack(character, roll_data, pending)
        elif pending["type"] == "spell_attack":
            return self._resolve_spell_attack(character, roll_data, pending)
        elif pending["type"] == "skill_check":
            return self._resolve_skill_check(character, roll_data, pending)
        elif pending["type"] == "weapon_damage":
            return self._resolve_weapon_damage(character, roll_data, pending)
        elif pending["type"] == "sneak_damage":
            return self._resolve_sneak_damage(character, roll_data, pending)
        elif pending["type"] == "healing":
            # Parse modifier from healing dice notation (e.g. "2d4+2" → +2)
            healing_dice = pending.get("healing_dice", "")
            heal_mod = 0
            if "+" in healing_dice:
                try:
                    heal_mod = int(healing_dice.split("+")[1])
                except (ValueError, IndexError):
                    pass

            total_healing = roll_data.get("result", 0) + heal_mod
            target = pending.get("target_data", {}) or {}
            target_name = pending.get("target_name", "Unknown")
            target_status = target.get("status", {}) if target else {}
            hp_current = target_status.get("hp_current", 0)
            hp_max = target_status.get("hp_max", hp_current)

            hp_result = calculate_hp_change(hp_current, total_healing, hp_max, is_damage=False)

            result = {
                "action": "healing_applied",
                "healer": character.get("name", "Unknown"),
                "target": target_name,
                "item": pending.get("item", ""),
                "healing_rolls": roll_data.get("rolls", []),
                "healing_modifier": heal_mod,
                "total_healing": hp_result.get("actual_change", total_healing),
                "new_hp": hp_result["new_hp"],
                "hp_max": hp_max,
            }

            self.state_updates.append({
                "type": "player_hp",
                "character_name": target_name,
                "character_id": (target or {}).get("id"),  # SAM-029
                "damage": -total_healing,  # Negative = healing
                "new_hp": hp_result["new_hp"],
                "hp_max": hp_max,
                "is_unconscious": False,
            })

            self.results.append(result)
            return result

        elif pending["type"] == "self_damage":
            damage = roll_data.get("result", 0)
            char = pending.get("character_data", character)
            status = char.get("status", {}) if char else {}
            hp_current = status.get("hp_current", 0)
            hp_max = status.get("hp_max", hp_current)
            hp_result = calculate_hp_change(hp_current, damage, hp_max)

            char_name = pending.get("character_name", char.get("name", "Unknown") if char else "Unknown")
            result = {
                "action": "self_damage_applied",
                "character": char_name,
                "damage": damage,
                "new_hp": hp_result["new_hp"],
                "hp_max": hp_max,
                "is_unconscious": hp_result.get("is_unconscious", False),
            }
            self.state_updates.append({
                "type": "player_hp",
                "character_name": char_name,
                "character_id": (char or {}).get("id"),  # SAM-029
                "damage": damage,
                "new_hp": hp_result["new_hp"],
                "hp_max": hp_max,
                "is_unconscious": hp_result.get("is_unconscious", False),
            })
            self.results.append(result)
            return result

        return {"action": "unknown_roll", "roll": roll_data}

    def _check_dice(self, pending: dict, roll_data: dict) -> Optional[dict]:
        """
        SAM-039/042: validate that the player rolled the dice the pending action
        requires. Returns a rejection dict {reason, expected, rolled} or None when
        the roll is valid (or there's nothing to validate against).

        - attack rolls (weapon/spell) → must be a d20 (faces only; advantage /
          disadvantage legitimately send two d20s, so the count is not checked).
        - damage rolls (weapon/spell/sneak) → must match BOTH the number of dice
          and the faces of pending["damage_spec"] (e.g. a nat-20 crit needs 2d12,
          not 1d12).
        """
        ptype = pending.get("type", "")
        is_attack = ptype in ("weapon_attack", "spell_attack")
        if is_attack:
            # SAM-045: a d20; count 1 (normal) or 2 (advantage/disadvantage) only.
            exp_count, exp_sides, exp_display = None, 20, "1d20"
        elif ptype in ("weapon_damage", "spell_damage", "sneak_damage"):
            spec = pending.get("damage_spec") or pending.get("dice") or ""
            if not spec:
                return None  # no expected spec at all — stay lenient
            exp_count, exp_sides = parse_dice_notation(spec)
            exp_display = clean_dice_spec(spec) or str(spec)
            # SAM-046/Change 3: fail-closed — a degenerate/unparseable spec must
            # NEVER let a roll through (the old fail-open dropped a 1d20 onto a
            # fixed-damage "1d1" pending).
            if exp_count is None or exp_count < 1 or (exp_sides or 0) < 2:
                print(f"⚠️ Unparseable damage_spec: {spec!r} — rejecting roll (fail-closed)")
                return {"reason": "unparseable", "expected": exp_display or "?",
                        "rolled": str(roll_data.get("dice", "")).strip() or "?"}
        else:
            return None  # skill_check / healing / self_damage: no strict check

        dice_str = str(roll_data.get("dice", "")).strip()
        rolled_count, rolled_sides = parse_dice_notation(dice_str)
        if rolled_count is None:
            rolls = roll_data.get("rolls") or []
            if not rolls:
                return None  # nothing to compare — accept
            rolled_count, rolled_sides = len(rolls), None
        rolled_display = dice_str or f"{rolled_count}d{rolled_sides or '?'}"

        # Faces (both attack and damage must match the die type).
        if rolled_sides is not None and rolled_sides != exp_sides:
            return {"reason": ("attack" if is_attack else "faces"),
                    "expected": exp_display, "rolled": rolled_display}
        # Count.
        if is_attack:
            if rolled_count not in (1, 2):  # SAM-045: 1d20 or 2d20; reject 0 / 3+
                return {"reason": "attack", "expected": exp_display, "rolled": rolled_display}
        elif rolled_count != exp_count:
            return {"reason": "count", "expected": exp_display, "rolled": rolled_display}
        return None

    def _pick_d20(self, roll_data: dict):
        """
        SAM-059: pick the authoritative d20 out of a roll.

        NO advantage/disadvantage state exists anywhere in the pipeline — not in
        the intent, not in the pending, not in CombatState. SAM-045 accepts 2d20
        as advantage/disadvantage but nothing records WHICH it was, and taking
        rolls[0] was arbitrary: on 13-ago Björn rolled [19, 7] and got the 19
        purely by luck. With [7, 19] the same swing would have missed.

        Until SAM-065 tracks it for real: two d20 → take the HIGHEST, and say so
        in the facts. Never rolls[0] in silence.

        Returns (raw_roll, note_or_None).
        """
        rolls = roll_data.get("rolls") or []
        if not rolls:
            return int(roll_data.get("result", 0) or 0), None
        if len(rolls) == 1:
            return int(rolls[0]), None

        # Only claim advantage when the dice really are d20s. Non-d20 multi-dice
        # reaching a d20 resolver is a different defect (validation leniency on
        # skill checks); behave as before rather than mislabel it.
        _, sides = parse_dice_notation(roll_data.get("dice", ""))
        if sides is not None and sides != 20:
            return int(rolls[0]), None
        if sides is None and any(int(r) > 20 for r in rolls):
            return int(rolls[0]), None

        picked = max(int(r) for r in rolls)
        listed = ", ".join(str(int(r)) for r in rolls)
        count_word = "two" if len(rolls) == 2 else str(len(rolls))
        note = (f"ADVANTAGE ASSUMED: {count_word} d20 rolled ({listed}); "
                f"using {picked}.")
        print(f"🎯 {note}")
        return picked, note

    def _resolve_spell_damage(self, character: dict, roll_data: dict, pending: dict) -> dict:
        """Player rolled damage for a spell."""
        damage = roll_data["result"]
        target = pending["target_data"]

        result = {
            "action": "spell_damage_applied",
            "caster": character.get("name", "Unknown"),
            "spell": pending["spell"],
            "target": target["name"],
            "damage": damage,
            "damage_rolls": roll_data.get("rolls", [])
        }

        if target.get("is_npc"):
            old_hp = target.get("hp", 0)
            hp_result = calculate_hp_change(old_hp, damage, target.get("hp_max", old_hp))
            result["target_hp"] = hp_result["new_hp"]
            result["target_hp_max"] = target.get("hp_max", old_hp)
            result["target_killed"] = hp_result["is_unconscious"]

            # Update combat state
            self.combat.update_npc_hp(target["name"], hp_result["new_hp"],
                                      killer=character.get("name"))

        self.results.append(result)
        return result

    def _resolve_weapon_attack(self, character: dict, roll_data: dict, pending: dict) -> dict:
        """Player rolled attack with a weapon."""
        weapon = pending["weapon"]
        target = pending["target_data"]

        # Parse attack bonus from weapon
        bonus = 0
        bonus_str = weapon.get("bonus", "+0")
        try:
            bonus = int(bonus_str.replace("+", ""))
        except Exception:
            pass

        raw_roll, roll_note = self._pick_d20(roll_data)  # SAM-059
        hit_result = check_hit(raw_roll, bonus, target.get("ac", 10))

        result = {
            "action": "weapon_attack_result",
            "roll_note": roll_note,
            "attacker": character.get("name", "Unknown"),
            "weapon": weapon["name"],
            "target": target["name"],
            "attack_roll": raw_roll,
            "modifier": bonus,
            "total": hit_result["total"],
            "target_ac": target.get("ac", 10),
            "hit": hit_result["hit"],
            "critical": hit_result["critical"],
            "fumble": hit_result["fumble"]
        }

        if hit_result["hit"]:
            # Need damage roll from player. SAM-046: normalize Unarmed Strike (and
            # any fixed/unparseable damage) to 1d4+STR so it rolls like any weapon.
            eff_damage = self._effective_damage(weapon, character)
            damage_dice = self._double_dice(eff_damage) if hit_result["critical"] else eff_damage
            result["needs_player_roll"] = True
            result["damage_dice"] = damage_dice
            result["prompt_player"] = f"{'¡CRÍTICO! ' if hit_result['critical'] else ''}¡Impacto! Tira {damage_dice} de daño."
            self.pending_player_roll = {
                "type": "weapon_damage",
                # Carry the NORMALIZED damage so the modifier parse in
                # _resolve_weapon_damage and the prompt agree.
                "weapon": {**weapon, "damage": eff_damage},
                "target": target["name"],
                "target_data": target,
                "critical": hit_result["critical"],
                # SAM-042: single source of truth for the damage prompt + validation
                # (already doubled by _double_dice when critical).
                "damage_spec": clean_dice_spec(damage_dice),
                # SAM-003: carry the Sneak Attack chain hint to the damage roll
                "sneak_dice": pending.get("sneak_dice"),
                "character_name": pending.get("character_name"),
            }
        else:
            result["needs_player_roll"] = False
            result["prompt_player"] = "¡Fallo!" if not hit_result["fumble"] else "¡Pifia!"

        self.results.append(result)
        return result

    def _resolve_weapon_damage(self, character: dict, roll_data: dict, pending: dict) -> dict:
        """Player rolled damage for a weapon hit."""
        target = pending["target_data"]

        # Parse damage modifier from weapon damage string (e.g., "1d8+2")
        damage_mod = 0
        damage_str = pending["weapon"].get("damage", "")
        if "+" in damage_str:
            try:
                damage_mod = int(damage_str.split("+")[1])
            except Exception:
                pass
        elif "-" in damage_str and "d" in damage_str:
            try:
                damage_mod = int(damage_str.split("-")[1]) * -1
            except Exception:
                pass

        total_damage = roll_data["result"] + damage_mod

        result = {
            "action": "weapon_damage_applied",
            "attacker": character.get("name", "Unknown"),
            "weapon": pending["weapon"]["name"],
            "target": target["name"],
            "damage_rolls": roll_data.get("rolls", []),
            "damage_modifier": damage_mod,
            "total_damage": total_damage
        }

        if target.get("is_npc"):
            old_hp = target.get("hp", 0)
            hp_result = calculate_hp_change(old_hp, total_damage, target.get("hp_max", old_hp))
            result["target_hp"] = hp_result["new_hp"]
            result["target_hp_max"] = target.get("hp_max", old_hp)
            result["target_killed"] = hp_result["is_unconscious"]
            self.combat.update_npc_hp(target["name"], hp_result["new_hp"],
                                      killer=character.get("name"))

            # SAM-003: chain Sneak Attack damage on the same target, same action.
            # Skip if the weapon damage already killed it (no point in overkill).
            sneak_dice = pending.get("sneak_dice")
            if sneak_dice and not result["target_killed"]:
                result["needs_player_roll"] = True
                result["prompt_player"] = f"¡Sneak Attack! Tira {sneak_dice} de daño adicional."
                self.pending_player_roll = {
                    "type": "sneak_damage",
                    "dice": sneak_dice,
                    "damage_spec": clean_dice_spec(sneak_dice),  # SAM-042
                    "target": target["name"],
                    "target_data": {**target, "hp": hp_result["new_hp"]},
                    "character_name": pending.get("character_name"),
                }

        self.results.append(result)
        return result

    def _resolve_sneak_damage(self, character: dict, roll_data: dict, pending: dict) -> dict:
        """Player rolled Sneak Attack bonus damage (chained after weapon damage)."""
        damage = roll_data.get("result", 0)
        target = pending["target_data"]

        result = {
            "action": "sneak_damage_applied",
            "attacker": character.get("name", "Unknown"),
            "target": target["name"],
            "dice": pending.get("dice", ""),
            "damage_rolls": roll_data.get("rolls", []),
            "total_damage": damage,
        }

        if target.get("is_npc"):
            old_hp = target.get("hp", 0)
            hp_result = calculate_hp_change(old_hp, damage, target.get("hp_max", old_hp))
            result["target_hp"] = hp_result["new_hp"]
            result["target_hp_max"] = target.get("hp_max", old_hp)
            result["target_killed"] = hp_result["is_unconscious"]
            self.combat.update_npc_hp(target["name"], hp_result["new_hp"],
                                      killer=character.get("name"))

        # Sneak Attack is once per turn (5e RAW)
        self.combat.mark_sneak_used()

        self.results.append(result)
        return result

    def _resolve_spell_attack(self, character: dict, roll_data: dict, pending: dict) -> dict:
        """Player rolled attack for a spell (e.g., Ray of Sickness)."""
        target = pending["target_data"]
        bonus = 0
        try:
            bonus = int(pending.get("attack_bonus", "+0").replace("+", ""))
        except Exception:
            pass

        raw_roll, roll_note = self._pick_d20(roll_data)  # SAM-059
        hit_result = check_hit(raw_roll, bonus, target.get("ac", 10))

        result = {
            "action": "spell_attack_result",
            "roll_note": roll_note,
            "caster": character.get("name", "Unknown"),
            "spell": pending["spell"],
            "target": target["name"],
            "attack_roll": raw_roll,
            "modifier": bonus,
            "total": hit_result["total"],
            "hit": hit_result["hit"],
            "critical": hit_result["critical"]
        }

        if hit_result["hit"]:
            result["needs_player_roll"] = True
            result["prompt_player"] = "¡Impacto! Tira el daño."
            self.pending_player_roll = {
                "type": "spell_damage",
                "spell": pending["spell"],
                "target": target["name"],
                "target_data": target,
                "character_name": pending.get("character_name") or character.get("name"),  # SAM-049
            }
        else:
            result["needs_player_roll"] = False

        self.results.append(result)
        return result

    def _calculate_skill_modifier(self, character: dict, skill_name: str):
        """Calculate total skill modifier: ability mod + proficiency (if proficient) + expertise."""
        stats = character.get("stats") or {}
        status = character.get("status") or {}
        prof_bonus = int(status.get("proficiency_bonus", 2) or 2)
        skill_profs = status.get("skill_proficiencies") or {}

        # Normalize skill name for lookup (accent-insensitive — SAM-053)
        skill_key = _strip_accents(skill_name).replace(" ", "_").replace("(", "").replace(")", "")

        # Spanish name → canonical English key, before anything else.
        if skill_key in SKILL_ALIASES:
            skill_key = SKILL_ALIASES[skill_key]
        else:
            # Handle formats like "Wisdom (Perception)" / "prueba_de_sigilo"
            for known_skill in SKILL_ABILITY_MAP:
                if known_skill in skill_key:
                    skill_key = known_skill
                    break
            else:
                for alias, canonical in SKILL_ALIASES.items():
                    if alias in skill_key:
                        skill_key = canonical
                        break

        # Get ability modifier
        ability = SKILL_ABILITY_MAP.get(skill_key, "wis")
        ability_score = int(stats.get(ability, 10) or 10)
        ability_mod = (ability_score - 10) // 2

        # Check proficiency
        prof_level = str(skill_profs.get(skill_key, "none")).lower()
        if prof_level == "expertise":
            total = ability_mod + (prof_bonus * 2)
        elif prof_level == "proficient":
            total = ability_mod + prof_bonus
        else:
            total = ability_mod

        return total, ability_mod, prof_bonus, prof_level, ability

    def _resolve_skill_check(self, character: dict, roll_data: dict, pending: dict) -> dict:
        """Player rolled a skill check."""
        dc = pending.get("dc", 10)
        raw_roll, roll_note = self._pick_d20(roll_data)  # SAM-059

        modifier, ability_mod, prof_bonus, prof_level, ability = self._calculate_skill_modifier(
            character, pending.get("skill", "")
        )

        total = raw_roll + modifier

        result = {
            "action": "skill_check_result",
            "roll_note": roll_note,
            "character": character.get("name", "Unknown"),
            "skill": pending["skill"],
            "roll": raw_roll,
            "modifier": modifier,
            "total": total,
            "dc": dc,
            "success": total >= dc if dc else None,
            "ability": ability.upper(),
            "ability_mod": ability_mod,
            "prof_level": prof_level,
        }

        self.results.append(result)
        return result

    # ─────────────────────────────────────
    # NPC TURNS
    # ─────────────────────────────────────

    def resolve_npc_turn(self, npc: dict, targets: list[dict]) -> list[dict]:
        """
        Resolve an NPC's (or SAM-delegated PC's) entire turn.
        npc: attacker data (name, hp, ac, attacks, etc.)
        targets: who the attacker can hit — real players (is_npc=False) when a
                 monster acts, enemy NPCs (is_npc=True) when a delegated PC acts.
                 Damage routing depends on it (SAM-036).
        Returns list of action results.
        """
        results = []

        if not targets:
            return results

        # Pick target (for now: first in list — TODO: smarter targeting)
        target = targets[0]

        attacks = npc.get("attacks", [])
        total_damage_to_target = {}  # {target_name: total_damage}

        for attack in attacks:
            bonus = 0
            try:
                raw_bonus = str(attack.get("bonus", "+0")).strip()
                # Handles "+5", "-1", "5", " +3 " correctly
                bonus = int(raw_bonus.replace("+", "").strip())
            except Exception:
                pass

            attack_roll = DiceRoller.roll(20)
            hit_result = check_hit(attack_roll, bonus, target.get("ac", 10))

            atk_result = {
                "action": "npc_attack",
                "attacker": npc["name"],
                "weapon": attack.get("name", "Attack"),
                "target": target["name"],
                "attack_roll": attack_roll,
                "modifier": bonus,
                "total": hit_result["total"],
                "target_ac": target.get("ac", 10),
                "hit": hit_result["hit"],
                "critical": hit_result["critical"]
            }

            if hit_result["hit"]:
                damage_dice_raw = attack.get("damage", "1d6")
                # Strip damage type suffix — "2d10 fire" → dice="2d10", type="fire"
                # "1d6+2 slashing" → dice="1d6+2", type="slashing"
                dice_tokens = str(damage_dice_raw).strip().split()
                damage_dice = dice_tokens[0] if dice_tokens else "1d6"
                damage_type = " ".join(dice_tokens[1:]) if len(dice_tokens) > 1 else ""

                damage_mod = 0
                if "+" in damage_dice:
                    parts = damage_dice.split("+")
                    damage_dice = parts[0]
                    try:
                        damage_mod = int(parts[1])
                    except Exception:
                        pass

                dice_parts = damage_dice.lower().split("d")
                try:
                    count = int(dice_parts[0]) if dice_parts[0] else 1
                    sides = int(dice_parts[1]) if len(dice_parts) > 1 else 6
                except ValueError:
                    # Malformed dice string — safe fallback
                    count, sides = 1, 6

                if hit_result["critical"]:
                    count *= 2

                damage_result = DiceRoller.roll_with_modifier(count, sides, damage_mod)
                atk_result["damage"] = damage_result["total"]
                atk_result["damage_rolls"] = damage_result["rolls"]
                atk_result["damage_modifier"] = damage_mod
                atk_result["damage_type"] = damage_type
                atk_result["damage_spec"] = f"{count}d{sides}" + (f"+{damage_mod}" if damage_mod > 0 else (str(damage_mod) if damage_mod < 0 else ""))

                target_name = target["name"]
                total_damage_to_target[target_name] = (
                    total_damage_to_target.get(target_name, 0) + damage_result["total"]
                )

            results.append(atk_result)

        # Apply accumulated damage per target (one call, not one per attack)
        for target_name, total_dmg in total_damage_to_target.items():
            target_char = next((t for t in targets if t["name"] == target_name), None)
            if target_char:
                # Read HP from top-level fields; fall back to nested "status" dict
                # (raw DB character rows store these inside status).
                status = target_char.get("status") or {}
                hp_current = (
                    target_char.get("hp_current")
                    if target_char.get("hp_current") is not None
                    else status.get("hp_current",
                         target_char.get("hp", status.get("hp_max", 0)))
                )
                hp_max = (
                    target_char.get("hp_max")
                    if target_char.get("hp_max") is not None
                    else status.get("hp_max", hp_current or 0)
                )
                # Treat missing hp_max as at least current hp (guard against 0/0 state)
                if not hp_max or hp_max < (hp_current or 0):
                    hp_max = hp_current or 0
                hp_result = calculate_hp_change(hp_current or 0, total_dmg, hp_max)

                if target_char.get("is_npc"):
                    # SAM-036: delegated PC hitting an enemy NPC — the NPC's HP
                    # lives in combat state, never in the characters table.
                    self.combat.update_npc_hp(target_name, hp_result["new_hp"],
                                              killer=npc.get("name"))
                else:
                    # Real NPC hitting a player — persist via state_update.
                    self.state_updates.append({
                        "type": "player_hp",
                        "character_name": target_name,
                        "character_id": target_char.get("id"),  # SAM-029
                        "damage": total_dmg,
                        "new_hp": hp_result["new_hp"],
                        "hp_max": hp_max,
                        "is_unconscious": hp_result["is_unconscious"]
                    })

                results.append({
                    "action": "damage_applied",
                    "target": target_name,
                    "total_damage": total_dmg,
                    "new_hp": hp_result["new_hp"],
                    "hp_max": hp_max,
                    "is_unconscious": hp_result["is_unconscious"]
                })

        self.results.extend(results)
        return results

    # ─────────────────────────────────────
    # XP & LEVELING
    # ─────────────────────────────────────

    def award_xp(self, characters: list[dict], xp_amount: int) -> list[dict]:
        """
        Award XP split evenly among characters (rounded up) and check level-up.
        XP lives in status.xp on DB rows (top-level "xp" kept as fallback).
        On level-up, hp_max grows by class average + CON mod per level gained
        (5e fixed average); hp_current grows the same amount (expands, not heals).
        All values are precomputed here — server.py only persists them.
        """
        results = []
        if not characters or xp_amount <= 0:
            return results

        xp_each = -(-xp_amount // len(characters))  # ceil division

        for char in characters:
            status = char.get("status") or {}
            stats = char.get("stats") or {}  # top-level column (SAM-018)
            current_xp = int(status.get("xp", char.get("xp", 0)) or 0)
            current_level = int(char.get("level", 1) or 1)
            new_xp = current_xp + xp_each
            new_level = get_level_for_xp(new_xp)
            leveled_up = new_level > current_level

            result = {
                "character": char["name"],
                "xp_gained": xp_each,
                "total_xp": new_xp,
                "old_level": current_level,
                "new_level": new_level,
                "leveled_up": leveled_up
            }

            update = {
                "type": "xp_update",
                "character_name": char["name"],
                "character_id": char.get("id"),  # SAM-029
                "xp_gained": xp_each,
                "new_xp": new_xp,
                "new_level": new_level,
                "leveled_up": leveled_up
            }

            if leveled_up:
                cls_raw = str(char.get("class", "") or "").lower().strip()
                cls = cls_raw.split()[0] if cls_raw else ""
                con = int(stats.get("con", 10) or 10)
                con_mod = (con - 10) // 2
                per_level = max(1, HP_AVG_PER_LEVEL.get(cls, 5) + con_mod)
                hp_gain = per_level * (new_level - current_level)
                hp_max = int(status.get("hp_max", 0) or 0)
                hp_current = int(status.get("hp_current", hp_max) or 0)
                update["new_hp_max"] = hp_max + hp_gain
                update["new_hp_current"] = hp_current + hp_gain
                result["hp_gain"] = hp_gain
                result["new_hp_max"] = hp_max + hp_gain

            self.state_updates.append(update)
            results.append(result)

        self.results.extend(results)
        return results

    # ─────────────────────────────────────
    # UTILITIES
    # ─────────────────────────────────────

    def _get_spell_damage_dice(self, spell: dict, caster: dict) -> str:
        """Determine damage dice for a spell based on caster level."""
        level = caster.get("level", 1)
        name = spell.get("name", "").lower()

        # Cantrip scaling
        if spell.get("level", "").lower() == "cantrip":
            if level >= 17:
                dice_count = 4
            elif level >= 11:
                dice_count = 3
            elif level >= 5:
                dice_count = 2
            else:
                dice_count = 1

            if "toll the dead" in name:
                return f"{dice_count}d12"
            elif "sacred flame" in name:
                return f"{dice_count}d8"
            else:
                return f"{dice_count}d8"  # Default cantrip

        # Leveled spells — TODO: spell slot scaling
        return "1d8"  # Safe default

    def _effective_damage(self, weapon: dict, character: dict) -> str:
        """
        SAM-046: return a rollable NdM[+X] damage string for a weapon. Unarmed
        Strike — or any fixed/unparseable damage value ("5", "1") — normalizes to
        1d4+STR so it flows through the normal roll + validation path instead of
        producing an ugly "1d1+4" prompt that let any die slip through.
        """
        raw = weapon.get("damage", "")
        name_norm = re.sub(r"[^a-z0-9]", "", str(weapon.get("name", "")).lower())
        count, sides = parse_dice_notation(raw)
        if "unarmedstrike" in name_norm or count is None or (sides or 0) < 2:
            stats = character.get("stats") or {}  # top-level column (SAM-018)
            try:
                str_mod = (int(stats.get("str", 10) or 10) - 10) // 2
            except (TypeError, ValueError):
                str_mod = 0
            mod = f"+{str_mod}" if str_mod > 0 else (str(str_mod) if str_mod < 0 else "")
            return f"1d4{mod}"
        return clean_dice_spec(raw) or raw

    def _double_dice(self, damage_notation: str) -> str:
        """Double dice for critical hits. '1d8+2' -> '2d8+2'. '2d10 fire' -> '4d10 fire'."""
        # Strip damage type suffix first (e.g., "2d10 fire", "1d6+2 slashing")
        tokens = str(damage_notation).strip().split()
        dice_expr = tokens[0] if tokens else "1d6"
        damage_type = " ".join(tokens[1:]) if len(tokens) > 1 else ""

        parts = dice_expr.split("+")
        dice = parts[0].strip()
        modifier = parts[1].strip() if len(parts) > 1 else None

        dice_parts = dice.lower().split("d")
        try:
            count = int(dice_parts[0]) if dice_parts[0] else 1
            sides = dice_parts[1] if len(dice_parts) > 1 else "6"
        except ValueError:
            count, sides = 1, "6"

        doubled = f"{count * 2}d{sides}"
        if modifier:
            doubled += f"+{modifier}"
        if damage_type:
            doubled += f" {damage_type}"
        return doubled

    def get_results_summary(self) -> str:
        """Generate a plain text summary of all mechanical results for the narrator."""
        lines = []
        for r in self.results:
            action = r.get("action", "")

            # SAM-059: the advantage disclosure rides above whatever the roll
            # resolved into, so the narrator can quote it either way.
            if r.get("roll_note"):
                lines.append(r["roll_note"])

            if action == "spell" and r.get("save"):
                save = r["save"]
                lines.append(
                    f"{r['caster']} casts {r['spell']} on {r['target']}. "
                    f"{r['target']} {save['ability']} save: "
                    f"rolled {save['roll']}+{save['modifier']}={save['total']} "
                    f"vs DC {save['dc']} → {'SUCCESS' if save['success'] else 'FAIL'}."
                )
                if r.get("prompt_player"):
                    lines.append(f"→ {r['prompt_player']}")

            # SAM-041: declarations that arm a pending MUST render facts —
            # empty facts drop the request into the roleplay template, which
            # forbids combat mechanics (SAM-033) and denies the action.
            elif action == "spell" and r.get("needs_player_roll"):
                lines.append(
                    f"{r['caster']} casts {r['spell']} at {r['target']}. Awaiting spell attack roll."
                )
                if r.get("prompt_player"):
                    lines.append(f"→ {r['prompt_player']}")

            elif action == "attack":
                lines.append(
                    f"{r['attacker']} declares an attack with {r['weapon']} against {r['target']} "
                    f"(AC {r.get('target_ac', '?')}). Awaiting attack roll."
                )
                if r.get("prompt_player"):
                    lines.append(f"→ {r['prompt_player']}")

            elif action == "skill_check":
                lines.append(
                    f"{r['character']} attempts a {r['skill']} check. Awaiting d20 roll."
                )
                if r.get("prompt_player"):
                    lines.append(f"→ {r['prompt_player']}")

            elif action == "spell_damage_applied":
                lines.append(
                    f"{r['caster']}'s {r['spell']} deals {r['damage']} damage to {r['target']}. "
                    f"{r['target']} HP: {r.get('target_hp', '?')}/{r.get('target_hp_max', '?')}."
                    f"{' KILLED!' if r.get('target_killed') else ''}"
                )

            elif action == "weapon_attack_result":
                hit_text = "CRITICAL HIT!" if r.get("critical") else "HIT!" if r["hit"] else "MISS!"
                lines.append(
                    f"{r['attacker']} attacks {r['target']} with {r['weapon']}: "
                    f"rolled {r['attack_roll']}+{r['modifier']}={r['total']} "
                    f"vs AC {r['target_ac']} → {hit_text}"
                )
                if r.get("prompt_player"):
                    lines.append(f"→ {r['prompt_player']}")

            elif action == "weapon_damage_applied":
                lines.append(
                    f"{r['attacker']}'s {r['weapon']} deals {r['total_damage']} damage to {r['target']}. "
                    f"{r['target']} HP: {r.get('target_hp', '?')}/{r.get('target_hp_max', '?')}."
                    f"{' KILLED!' if r.get('target_killed') else ''}"
                )
                if r.get("prompt_player"):
                    lines.append(f"→ {r['prompt_player']}")

            elif action == "sneak_damage_applied":
                lines.append(
                    f"{r['attacker']}'s Sneak Attack ({r.get('dice', '')}) deals {r['total_damage']} "
                    f"extra damage to {r['target']} — same attack, the blade finds a vital spot. "
                    f"{r['target']} HP: {r.get('target_hp', '?')}/{r.get('target_hp_max', '?')}."
                    f"{' KILLED!' if r.get('target_killed') else ''}"
                )

            elif action == "npc_attack":
                hit_text = "CRITICAL HIT!" if r.get("critical") else "HIT!" if r["hit"] else "MISS!"
                lines.append(
                    f"{r['attacker']} attacks {r['target']} with {r['weapon']}: "
                    f"rolled {r['attack_roll']}+{r['modifier']}={r['total']} "
                    f"vs AC {r['target_ac']} → {hit_text}"
                )
                if r.get("damage"):
                    dmg_type = r.get("damage_type", "")
                    type_suffix = f" {dmg_type}" if dmg_type else ""
                    lines.append(
                        f"  Damage: {r['damage_rolls']} + {r.get('damage_modifier', 0)} = {r['damage']}{type_suffix} total"
                    )

            elif action == "damage_applied":
                lines.append(
                    f"{r['target']} takes {r['total_damage']} total damage. "
                    f"HP: {r['new_hp']}/{r['hp_max']}."
                    f"{' UNCONSCIOUS!' if r.get('is_unconscious') else ''}"
                )

            elif action == "skill_check_result":
                dc_text = (
                    f" vs DC {r['dc']} → {'SUCCESS' if r['success'] else 'FAIL'}"
                    if r.get("dc") else ""
                )
                prof_text = ""
                pl = r.get("prof_level", "none")
                if pl == "expertise":
                    prof_text = " (Expertise)"
                elif pl == "proficient":
                    prof_text = " (Proficient)"
                lines.append(
                    f"{r['character']} {r['skill']} ({r.get('ability', '?')}) check{prof_text}: "
                    f"rolled {r['roll']} + {r['modifier']} = {r['total']}{dc_text}"
                )

            elif action == "healing_applied":
                lines.append(
                    f"{r['healer']} uses {r.get('item', 'healing')} on {r['target']}. "
                    f"Healing: {r.get('healing_rolls', [])} + {r.get('healing_modifier', 0)} = "
                    f"{r['total_healing']} HP restored. "
                    f"{r['target']} HP: {r['new_hp']}/{r['hp_max']}."
                )

            elif action == "self_damage_applied":
                lines.append(
                    f"{r['character']} takes {r['damage']} self-inflicted damage. "
                    f"HP: {r['new_hp']}/{r['hp_max']}."
                    f"{' UNCONSCIOUS!' if r.get('is_unconscious') else ''}"
                )

            elif action == "orphan_roll":
                # SAM-053: a die with no pending action behind it. Informative,
                # not an error — nothing is blocked and no action is consumed.
                lines.append(
                    f"ORPHAN ROLL: {r['character']} rolled {r['dice']} = {r['raw']}. "
                    f"No pending action is registered, so this roll resolves nothing. "
                    f"Ask them to declare the action first."
                )

            elif action == "invalid_dice":
                reason = r.get("reason", "")
                if reason == "attack":
                    lines.append(
                        f"INVALID DICE: an attack roll uses 1d20 (or 2d20 with "
                        f"advantage/disadvantage). Got {r.get('rolled')}. Roll 1d20."
                    )
                elif reason == "unparseable":
                    lines.append(
                        f"INVALID DICE: the requested dice are misconfigured "
                        f"({r.get('expected')}). Roll the dice S.A.M. asked for."
                    )
                else:
                    detail = ("Wrong die type" if reason == "faces"
                              else "Wrong number of dice" if reason == "count"
                              else "Wrong dice")
                    lines.append(
                        f"INVALID DICE: expected {r.get('expected')}, got {r.get('rolled')}. "
                        f"{detail} — roll {r.get('expected')}."
                    )

        return "\n".join(lines)
