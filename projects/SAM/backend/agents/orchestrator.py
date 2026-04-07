"""
Orchestrator — Coordinates all agents into a coherent game loop.
This is the main entry point that replaces the monolithic ai.py flow.

Pipeline:
1. Receive player message + context
2. Interpreter: parse intent (LLM or regex for dice rolls)
3. Mechanic: execute game logic (Python pure)
4. Knowledge: RAG lookup if needed (embeddings)
5. Narrator: generate narrative (LLM creative)
6. Return: narrative + state updates + combat state
"""

import json
import re
from typing import Optional

from .interpreter import IntentInterpreter
from .mechanic import MechanicEngine
from .narrator import Narrator
from .combat_state import CombatState
from .dice import DiceRoller
from .rules import get_level_for_xp


class SAMOrchestrator:
    """Main game loop coordinator."""

    def __init__(self, interpreter_llm, narrator_llm, knowledge_service=None):
        """
        interpreter_llm: lightweight LLM for intent parsing
        narrator_llm: creative LLM for narration
        knowledge_service: RAG service for spell/monster/campaign lookups
        """
        self.interpreter = IntentInterpreter(interpreter_llm)
        self.narrator = Narrator(narrator_llm)
        self.knowledge = knowledge_service  # Can be None initially

    def process_message(self,
                        message: str,
                        sender_name: str,
                        character_context: dict,
                        party_characters: list[dict],
                        combat_data: dict = None,
                        campaign_context: str = "",
                        dm_style: str = "",
                        history: list = None) -> dict:
        """
        Main entry point. Processes a player message through the full pipeline.

        Returns:
        {
            "narrative": str,                # The story text to show players
            "state_updates": list,           # DB updates (HP, XP, inventory)
            "combat_state": dict|None,       # Updated combat state for campaigns.settings
            "prompt_player_roll": str|None,  # If we need a dice roll from the player
        }
        """
        # Initialize mechanic engine with current combat state
        combat = CombatState.from_dict(combat_data) if combat_data else CombatState()
        engine = MechanicEngine(combat)
        engine.reset_turn()

        # ─── STEP 1: Parse intent ───
        targets = self._get_target_options(combat)
        intent = self.interpreter.parse_intent(
            message=message,
            character_context=character_context,
            combat_state=combat_data,
            targets=targets
        )

        print(f"🎯 Intent: {json.dumps(intent, default=str)}")

        # ─── STEP 2: Execute mechanics based on intent ───
        mechanical_facts = ""
        prompt_player_roll = None

        if intent["type"] == "dice_roll":
            # Player rolled dice — process the result
            self._handle_dice_roll(engine, intent, character_context, combat)
            mechanical_facts = engine.get_results_summary()

            # Check if we need another roll from the player
            if engine.pending_player_roll:
                prompt_player_roll = self._get_roll_prompt(engine.pending_player_roll)

            # After resolving player action, resolve NPC turns if applicable
            if not engine.pending_player_roll and combat.active:
                npc_facts = self._resolve_npc_turns(engine, combat, party_characters)
                if npc_facts:
                    mechanical_facts += "\n" + npc_facts

        elif intent["type"] == "spell":
            self._handle_spell(engine, intent, character_context, combat)
            mechanical_facts = engine.get_results_summary()
            if engine.pending_player_roll:
                prompt_player_roll = self._get_roll_prompt(engine.pending_player_roll)

        elif intent["type"] == "attack":
            self._handle_attack(engine, intent, character_context, combat)
            mechanical_facts = engine.get_results_summary()
            if engine.pending_player_roll:
                prompt_player_roll = self._get_roll_prompt(engine.pending_player_roll)

        elif intent["type"] == "skill_check":
            skill = intent.get("skill", "Perception")
            dc = intent.get("dc")  # May be None — narrator will determine
            engine.process_skill_check(character_context, skill, dc)
            mechanical_facts = engine.get_results_summary()
            prompt_player_roll = f"Tira 1d20 para {skill}."

        elif intent["type"] == "self_damage":
            # Self-inflicted or environmental damage — ask for damage roll, then apply to self
            damage_dice = intent.get("damage_dice", "1d4")
            description = intent.get("description", "self-inflicted damage")
            mechanical_facts = f"{sender_name} is taking {description}. Awaiting damage roll: {damage_dice}"
            prompt_player_roll = f"Tira {damage_dice} de daño."
            engine.pending_player_roll = {
                "type": "self_damage",
                "character_name": sender_name,
                "character_data": character_context,
            }

        elif intent["type"] in ("roleplay", "movement", "free_action", "item", "ability"):
            # No mechanics — pure narration
            mechanical_facts = ""

        # Warning if a dice roll happened but no state updates were generated
        if intent["type"] == "dice_roll" and not engine.state_updates:
            print(f"⚠️ Dice roll processed but no state_updates generated — damage may be narrative-only")

        # ─── STEP 3: RAG lookup if needed ───
        rag_context = ""
        if self.knowledge and intent["type"] in ("roleplay", "movement", "free_action"):
            try:
                rag_context = self.knowledge.search(message) or ""
            except Exception as e:
                print(f"⚠️ RAG lookup failed: {e}")

        full_campaign_context = campaign_context
        if rag_context:
            full_campaign_context = f"{campaign_context}\n\nRELEVANT CAMPAIGN INFO:\n{rag_context}"

        # ─── STEP 4: Generate narrative ───
        character_context_str = self._format_character_context(character_context)
        party_context_str = self._format_party_context(party_characters)

        if mechanical_facts:
            # Add roll prompt to facts so narrator includes it
            if prompt_player_roll:
                mechanical_facts += f"\n→ PROMPT PLAYER: {prompt_player_roll}"

            # Add turn advancement info
            if combat.active:
                current = combat.get_current_turn()
                if current:
                    mechanical_facts += f"\n→ Current turn: {current['name']}"

            narrative = self.narrator.narrate_mechanics(
                mechanical_facts=mechanical_facts,
                player_message=message,
                character_name=sender_name,
                character_context=character_context_str,
                party_context=party_context_str,
                campaign_context=full_campaign_context,
                dm_style=dm_style,
                history=history
            )
        else:
            narrative = self.narrator.narrate_roleplay(
                player_message=message,
                character_name=sender_name,
                character_context=character_context_str,
                party_context=party_context_str,
                campaign_context=full_campaign_context,
                dm_style=dm_style,
                history=history
            )

        # ─── STEP 5: Compile response ───
        return {
            "narrative": narrative,
            "state_updates": engine.state_updates,
            "combat_state": combat.to_dict() if combat.active else {"active": False},
            "prompt_player_roll": prompt_player_roll,
        }

    # ─────────────────────────────────────
    # INTENT HANDLERS
    # ─────────────────────────────────────

    def _handle_dice_roll(self, engine: MechanicEngine, intent: dict,
                          character_context: dict, combat: CombatState) -> dict:
        """Handle a SYSTEM EVENT dice roll."""
        roll_data = {
            "dice": intent.get("dice", "1d20"),
            "result": intent.get("result", 0),
            "rolls": intent.get("rolls", [])
        }
        return engine.process_player_roll(character_context, roll_data)

    def _handle_spell(self, engine: MechanicEngine, intent: dict,
                      character_context: dict, combat: CombatState) -> dict:
        """Handle a spell cast."""
        spell_name = intent.get("spell_name", "")
        target_name = intent.get("target", "")

        spell = self._find_spell(character_context, spell_name)
        if not spell:
            return {"action": "error", "message": f"Spell '{spell_name}' not found"}

        target = self._find_target(target_name, combat)
        if not target:
            return {"action": "error", "message": f"Target '{target_name}' not found"}

        return engine.process_spell(character_context, spell, target)

    def _handle_attack(self, engine: MechanicEngine, intent: dict,
                       character_context: dict, combat: CombatState) -> dict:
        """Handle a weapon attack."""
        weapon_name = intent.get("weapon", "")
        target_name = intent.get("target", "")

        weapon = self._find_weapon(character_context, weapon_name)
        if not weapon:
            # Default to first available weapon
            attacks = character_context.get("status", {}).get("attacks", [])
            weapon = attacks[0] if attacks else {"name": "Unarmed Strike", "bonus": "+0", "damage": "1"}

        target = self._find_target(target_name, combat)
        if not target:
            return {"action": "error", "message": f"Target '{target_name}' not found"}

        return engine.process_attack(character_context, weapon, target)

    def _resolve_npc_turns(self, engine: MechanicEngine, combat: CombatState,
                           party_characters: list[dict]) -> str:
        """Resolve all consecutive NPC turns after a player's turn."""
        npc_facts_lines = []

        # Advance past the current player's turn
        combat.advance_turn()

        # Keep resolving while it's an NPC's turn
        max_iterations = 20  # Safety valve
        iterations = 0

        while combat.active and iterations < max_iterations:
            current = combat.get_current_turn()
            if not current:
                break

            if not current.get("is_npc", False):
                # It's a player's turn — stop resolving
                break

            # Resolve NPC turn
            npc_data = current
            players_in_combat = [
                p for p in party_characters
                if p.get("name") in [c["name"] for c in combat.initiative_order if not c.get("is_npc")]
            ]

            if players_in_combat:
                results = engine.resolve_npc_turn(npc_data, players_in_combat)
                npc_facts_lines.append(f"\n--- {current['name']}'s turn ---")
                for r in results:
                    if r.get("action") == "npc_attack":
                        hit = "CRITICAL!" if r.get("critical") else "HIT!" if r["hit"] else "MISS"
                        npc_facts_lines.append(
                            f"{r['attacker']} attacks {r['target']} with {r['weapon']}: "
                            f"rolled {r['attack_roll']}+{r['modifier']}={r['total']} "
                            f"vs AC {r['target_ac']} → {hit}"
                        )
                        if r.get("damage"):
                            npc_facts_lines.append(
                                f"  Damage: {r['damage']} ({r.get('damage_rolls', [])})"
                            )
                    elif r.get("action") == "damage_applied":
                        npc_facts_lines.append(
                            f"{r['target']} takes {r['total_damage']} damage. "
                            f"HP: {r['new_hp']}/{r['hp_max']}"
                            f"{' → UNCONSCIOUS!' if r.get('is_unconscious') else ''}"
                        )

            combat.advance_turn()
            iterations += 1

        # Report whose turn it is now
        next_turn = combat.get_current_turn()
        if next_turn and not next_turn.get("is_npc"):
            npc_facts_lines.append(f"\n→ It's now {next_turn['name']}'s turn.")

        return "\n".join(npc_facts_lines)

    # ─────────────────────────────────────
    # LOOKUP HELPERS
    # ─────────────────────────────────────

    def _find_spell(self, character_context: dict, spell_name: str) -> Optional[dict]:
        """Find a spell in the character's spell list."""
        spells = character_context.get("status", {}).get("spells", [])
        spell_name_lower = spell_name.lower()

        # Exact match first
        for s in spells:
            if s.get("name", "").lower() == spell_name_lower:
                return s

        # Partial match fallback
        for s in spells:
            if spell_name_lower in s.get("name", "").lower():
                return s

        return None

    def _find_weapon(self, character_context: dict, weapon_name: str) -> Optional[dict]:
        """Find a weapon in the character's attack list."""
        attacks = character_context.get("status", {}).get("attacks", [])
        weapon_name_lower = weapon_name.lower()

        for a in attacks:
            if weapon_name_lower in a.get("name", "").lower():
                return a

        return None

    def _find_target(self, target_name: str, combat: CombatState) -> Optional[dict]:
        """Find a target in the combat state."""
        if not target_name:
            # Default to first living NPC
            for c in combat.initiative_order:
                if c.get("is_npc") and c.get("hp", 0) > 0:
                    return c
            return None

        target_lower = target_name.lower()
        for c in combat.initiative_order:
            if target_lower in c.get("name", "").lower():
                return c

        return None

    def _get_target_options(self, combat: CombatState) -> list[str]:
        """Get list of valid targets for the interpreter."""
        if not combat.active:
            return []
        return [c["name"] for c in combat.initiative_order if c.get("is_npc") and c.get("hp", 0) > 0]

    def _get_roll_prompt(self, pending: dict) -> str:
        """Generate a human-readable prompt for the player to roll dice."""
        ptype = pending.get("type", "")
        if ptype == "weapon_attack":
            weapon = pending.get("weapon", {})
            return f"Tira 1d20 para tu ataque con {weapon.get('name', 'arma')}."
        elif ptype == "weapon_damage":
            weapon = pending.get("weapon", {})
            return f"Tira {weapon.get('damage', '1d6')} de daño."
        elif ptype == "spell_damage":
            return f"Tira el daño de {pending.get('spell', 'tu hechizo')}."
        elif ptype == "skill_check":
            return f"Tira 1d20 para {pending.get('skill', 'tu check')}."
        elif ptype == "self_damage":
            return "Tira el daño correspondiente."
        return "Tira los dados."

    def _format_character_context(self, ctx: dict) -> str:
        """Format character context for the narrator."""
        if not ctx:
            return "No character info."

        status = ctx.get("status", {})
        return (
            f"{ctx.get('name', 'Unknown')} — "
            f"{ctx.get('race', '')} {ctx.get('class', '')} Level {ctx.get('level', 1)}\n"
            f"HP: {status.get('hp_current', '?')}/{status.get('hp_max', '?')} | AC: {status.get('ac', '?')}\n"
            f"Spells: {', '.join(s.get('name', '') for s in status.get('spells', []))}\n"
            f"Attacks: {', '.join(a.get('name', '') for a in status.get('attacks', []))}"
        )

    def _format_party_context(self, party: list[dict]) -> str:
        """Format party info for the narrator."""
        if not party:
            return "Solo adventure."

        lines = []
        for p in party:
            status = p.get("status", {})
            lines.append(
                f"- {p.get('name', '?')} ({p.get('class', '?')} Lvl {p.get('level', '?')}) "
                f"HP: {status.get('hp_current', '?')}/{status.get('hp_max', '?')}"
            )
        return "\n".join(lines)
