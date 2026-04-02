"""
Mechanic Agent — Pure Python game engine.
Receives structured intents, executes mechanics, returns facts.
Zero LLM calls. Zero XML. Zero guessing.
"""

from .dice import DiceRoller
from .rules import (
    calculate_hp_change, check_hit, check_save,
    get_level_for_xp, xp_to_next_level, XP_THRESHOLDS
)
from .combat_state import CombatState
from typing import Optional
import json


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
                        "target_data": target
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
                "attack_bonus": save_atk
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
            "dc": dc
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
            # No pending action — this might be initiative or a freeform roll
            return {"action": "freeform_roll", "roll": roll_data, "character": character.get("name", "Unknown")}

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

        return {"action": "unknown_roll", "roll": roll_data}

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
            self.combat.update_npc_hp(target["name"], hp_result["new_hp"])

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

        raw_roll = roll_data["rolls"][0] if roll_data.get("rolls") else roll_data["result"]
        hit_result = check_hit(raw_roll, bonus, target.get("ac", 10))

        result = {
            "action": "weapon_attack_result",
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
            # Need damage roll from player
            damage_dice = weapon.get("damage", "1d6")
            if hit_result["critical"]:
                damage_dice = self._double_dice(damage_dice)
            result["needs_player_roll"] = True
            result["damage_dice"] = damage_dice
            result["prompt_player"] = f"{'¡CRÍTICO! ' if hit_result['critical'] else ''}¡Impacto! Tira {damage_dice} de daño."
            self.pending_player_roll = {
                "type": "weapon_damage",
                "weapon": weapon,
                "target": target["name"],
                "target_data": target,
                "critical": hit_result["critical"]
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
            self.combat.update_npc_hp(target["name"], hp_result["new_hp"])

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

        raw_roll = roll_data["rolls"][0] if roll_data.get("rolls") else roll_data["result"]
        hit_result = check_hit(raw_roll, bonus, target.get("ac", 10))

        result = {
            "action": "spell_attack_result",
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
                "target_data": target
            }
        else:
            result["needs_player_roll"] = False

        self.results.append(result)
        return result

    def _resolve_skill_check(self, character: dict, roll_data: dict, pending: dict) -> dict:
        """Player rolled a skill check."""
        dc = pending.get("dc", 10)
        raw_roll = roll_data["rolls"][0] if roll_data.get("rolls") else roll_data["result"]

        # TODO: extract modifier from character context based on skill
        modifier = 0

        result = {
            "action": "skill_check_result",
            "character": character.get("name", "Unknown"),
            "skill": pending["skill"],
            "roll": raw_roll,
            "modifier": modifier,
            "total": raw_roll + modifier,
            "dc": dc,
            "success": (raw_roll + modifier) >= dc if dc else None
        }

        self.results.append(result)
        return result

    # ─────────────────────────────────────
    # NPC TURNS
    # ─────────────────────────────────────

    def resolve_npc_turn(self, npc: dict, players: list[dict]) -> list[dict]:
        """
        Resolve an NPC's entire turn.
        npc: NPC data from combat state (name, hp, ac, attacks, etc.)
        players: list of player characters in the encounter
        Returns list of action results.
        """
        results = []

        if not players:
            return results

        # Pick target (for now: first player — TODO: smarter targeting)
        target = players[0]

        attacks = npc.get("attacks", [])
        total_damage_to_target = {}  # {target_name: total_damage}

        for attack in attacks:
            bonus = 0
            try:
                bonus = int(str(attack.get("bonus", "+0")).replace("+", ""))
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
                damage_dice = attack.get("damage", "1d6")
                damage_mod = 0
                if "+" in damage_dice:
                    parts = damage_dice.split("+")
                    damage_dice = parts[0]
                    try:
                        damage_mod = int(parts[1])
                    except Exception:
                        pass

                dice_parts = damage_dice.lower().split("d")
                count = int(dice_parts[0]) if dice_parts[0] else 1
                sides = int(dice_parts[1]) if len(dice_parts) > 1 else 6

                if hit_result["critical"]:
                    count *= 2

                damage_result = DiceRoller.roll_with_modifier(count, sides, damage_mod)
                atk_result["damage"] = damage_result["total"]
                atk_result["damage_rolls"] = damage_result["rolls"]
                atk_result["damage_modifier"] = damage_mod

                target_name = target["name"]
                total_damage_to_target[target_name] = (
                    total_damage_to_target.get(target_name, 0) + damage_result["total"]
                )

            results.append(atk_result)

        # Apply accumulated damage per target (one call, not one per attack)
        for target_name, total_dmg in total_damage_to_target.items():
            target_char = next((p for p in players if p["name"] == target_name), None)
            if target_char:
                hp_current = target_char.get("hp_current", target_char.get("hp", 0))
                hp_max = target_char.get("hp_max", hp_current)
                hp_result = calculate_hp_change(hp_current, total_dmg, hp_max)

                self.state_updates.append({
                    "type": "player_hp",
                    "character_name": target_name,
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
        """Award XP to characters and check for level up."""
        results = []
        xp_each = xp_amount // len(characters) if characters else 0

        for char in characters:
            current_xp = char.get("xp", 0)
            current_level = char.get("level", 1)
            new_xp = current_xp + xp_each
            new_level = get_level_for_xp(new_xp)

            result = {
                "character": char["name"],
                "xp_gained": xp_each,
                "total_xp": new_xp,
                "old_level": current_level,
                "new_level": new_level,
                "leveled_up": new_level > current_level
            }

            self.state_updates.append({
                "type": "xp_update",
                "character_name": char["name"],
                "new_xp": new_xp,
                "new_level": new_level,
                "leveled_up": new_level > current_level
            })

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

    def _double_dice(self, damage_notation: str) -> str:
        """Double dice for critical hits. '1d8+2' -> '2d8+2'."""
        parts = damage_notation.split("+")
        dice = parts[0].strip()
        modifier = parts[1].strip() if len(parts) > 1 else None

        dice_parts = dice.lower().split("d")
        count = int(dice_parts[0]) if dice_parts[0] else 1
        sides = dice_parts[1] if len(dice_parts) > 1 else "6"

        doubled = f"{count * 2}d{sides}"
        if modifier:
            doubled += f"+{modifier}"
        return doubled

    def get_results_summary(self) -> str:
        """Generate a plain text summary of all mechanical results for the narrator."""
        lines = []
        for r in self.results:
            action = r.get("action", "")

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

            elif action == "npc_attack":
                hit_text = "CRITICAL HIT!" if r.get("critical") else "HIT!" if r["hit"] else "MISS!"
                lines.append(
                    f"{r['attacker']} attacks {r['target']} with {r['weapon']}: "
                    f"rolled {r['attack_roll']}+{r['modifier']}={r['total']} "
                    f"vs AC {r['target_ac']} → {hit_text}"
                )
                if r.get("damage"):
                    lines.append(
                        f"  Damage: {r['damage_rolls']} + {r.get('damage_modifier', 0)} = {r['damage']} total"
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
                lines.append(
                    f"{r['character']} {r['skill']} check: "
                    f"rolled {r['roll']}+{r['modifier']}={r['total']}{dc_text}"
                )

        return "\n".join(lines)
