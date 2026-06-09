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
from .rules import get_level_for_xp, get_recommended_cr_range


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

        # Restore pending_player_roll from persisted state (survives across requests)
        if combat_data and combat_data.get("pending_player_roll"):
            engine.pending_player_roll = combat_data["pending_player_roll"]

        # ─── STEP 1: Parse intent ───
        targets = self._get_target_options(combat)
        intent = self.interpreter.parse_intent(
            message=message,
            character_context=character_context,
            combat_state=combat_data,
            targets=targets
        )

        print(f"🎯 Intent: {json.dumps(intent, default=str)}")

        # ─── TURN GUARD ───
        # Prevent players from acting out of turn during combat.
        # Roleplay / movement / free_action still pass through.
        out_of_turn_facts = None
        if combat.active:
            current_tc = combat.get_current_turn()
            current_name = current_tc.get("name") if current_tc else None

            if current_name and sender_name and sender_name != current_name:
                action_intents = ("attack", "spell", "ability", "start_combat", "end_turn")
                if intent["type"] in action_intents:
                    out_of_turn_facts = (
                        f"OUT_OF_TURN: It's {current_name}'s turn, not {sender_name}'s. "
                        f"Ignore the attempted action and remind the player to wait."
                    )
                elif intent["type"] == "dice_roll":
                    # Allow if pending roll belongs to this sender
                    pending = engine.pending_player_roll or {}
                    pending_owner = pending.get("character_name")
                    if pending_owner != sender_name:
                        out_of_turn_facts = (
                            f"OUT_OF_TURN: It's {current_name}'s turn, not {sender_name}'s. "
                            f"Ignore the attempted dice roll and remind the player to wait."
                        )

        # ─── STEP 2: Execute mechanics based on intent ───
        mechanical_facts = ""
        prompt_player_roll = None

        if out_of_turn_facts:
            # Skip all mechanics — narrator produces only the reminder.
            mechanical_facts = out_of_turn_facts

        elif intent["type"] == "dice_roll":
            # During combat, a bare dice roll (via dice tray) needs context:
            # a d20 is an attack roll, a non-d20 is a damage roll. Wire up
            # pending_player_roll so process_player_roll routes to the proper
            # resolver (which already applies damage to NPC HP).
            if combat.active and not engine.pending_player_roll:
                self._setup_combat_freeform_pending(engine, intent, character_context, combat, sender_name)

            # Snapshot pending before it gets cleared by process_player_roll
            previous_pending = engine.pending_player_roll or {}
            previous_pending_type = previous_pending.get("type")

            # Player rolled dice — process the result
            self._handle_dice_roll(engine, intent, character_context, combat)
            mechanical_facts = engine.get_results_summary()

            # Check if we need another roll from the player
            if engine.pending_player_roll:
                prompt_player_roll = self._get_roll_prompt(engine.pending_player_roll)

            # After resolving player action, decide whether to advance or keep turn
            if not engine.pending_player_roll and combat.active:
                # Consume an action when the attack/spell cycle is fully resolved:
                #   - HIT + damage applied  → previous = weapon_damage / spell_damage
                #   - MISS (attack roll resolved, no damage follow-up) → previous = weapon_attack / spell_attack
                # sneak_damage ends the Rogue attack chain — the action is
                # consumed ONCE for the whole attack (weapon_damage is skipped
                # in that case because the sneak pending was still set).
                if previous_pending_type in (
                    "weapon_damage", "spell_damage",
                    "weapon_attack", "spell_attack",
                    "sneak_damage",
                ):
                    combat.consume_action()
                elif previous_pending_type == "skill_check" and previous_pending.get("consumes_action"):
                    # SAM-035: in-combat skill check (shove, grapple, etc.) was
                    # the turn's action — consume it now that the d20 resolved.
                    combat.consume_action()

                if combat.turn_is_over():
                    npc_facts = self._resolve_npc_turns(engine, combat, party_characters)
                    if npc_facts:
                        mechanical_facts += "\n" + npc_facts
                elif combat.actions_remaining > 0:
                    # Extra Attack still available — invite the player to use it
                    mechanical_facts += (
                        f"\n→ {sender_name} has {combat.actions_remaining} action(s) remaining. "
                        f"Ask if they attack again."
                    )

        elif intent["type"] == "spell":
            self._handle_spell(engine, intent, character_context, combat)
            mechanical_facts = engine.get_results_summary()
            if engine.pending_player_roll:
                prompt_player_roll = self._get_roll_prompt(engine.pending_player_roll)

            # Consume a spell slot (cantrips = level 0 = free)
            try:
                spell_level = int(intent.get("spell_level", 0) or 0)
            except (TypeError, ValueError):
                spell_level = 0

            if spell_level > 0:
                slots = (character_context.get("status") or {}).get("spell_slots") or {}
                level_key = str(spell_level)
                slot = slots.get(level_key) or {}
                total = int(slot.get("total", 0) or 0)
                used = int(slot.get("used", 0) or 0)

                if total <= 0 or used >= total:
                    mechanical_facts += f"\nWARNING: No spell slots available for level {spell_level}. The spell fizzles."
                else:
                    new_used = used + 1
                    mechanical_facts += f"\nSpell slot consumed: Level {spell_level} ({new_used}/{total})"
                    engine.state_updates.append({
                        "type": "spell_slot_consume",
                        "character_name": sender_name,
                        "level": spell_level,
                    })

        elif intent["type"] == "attack":
            self._handle_attack(engine, intent, character_context, combat)
            mechanical_facts = engine.get_results_summary()
            if engine.pending_player_roll:
                prompt_player_roll = self._get_roll_prompt(engine.pending_player_roll)

        elif intent["type"] == "skill_check":
            skill = intent.get("skill", "Perception")
            dc = intent.get("dc")  # May be None — narrator will determine
            engine.process_skill_check(character_context, skill, dc)
            # SAM-035: 5e RAW — using a skill in combat (shove, grapple, etc.)
            # is the turn's action. The d20 arrives in the NEXT request, so flag
            # the pending roll; consumption happens when the roll resolves.
            # Only the active player's check consumes — reactive checks from
            # out-of-turn players must not eat the current player's action.
            if engine.pending_player_roll:
                current_tc = combat.get_current_turn() if combat.active else None
                is_senders_turn = bool(current_tc and current_tc.get("name") == sender_name)
                engine.pending_player_roll["character_name"] = sender_name
                engine.pending_player_roll["consumes_action"] = is_senders_turn
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

        elif intent["type"] == "item":
            item_name = intent.get("item", "")
            is_healing = intent.get("is_healing", False)
            target = intent.get("target", "self")

            if is_healing:
                healing_dice = intent.get("healing_dice", "2d4+2")
                heal_target_name = sender_name if target == "self" else target
                target_data = character_context if target == "self" else self._find_party_member(heal_target_name, party_characters)

                mechanical_facts = f"{sender_name} uses {item_name} on {heal_target_name}. Roll {healing_dice} for healing."
                prompt_player_roll = f"Tira {healing_dice} de curación."

                engine.pending_player_roll = {
                    "type": "healing",
                    "item": item_name,
                    "healing_dice": healing_dice,
                    "target_name": heal_target_name,
                    "target_data": target_data,
                }
            else:
                mechanical_facts = ""

            # Consume the item from inventory (qty -1)
            if item_name:
                mechanical_facts += f"\n{item_name} consumed from inventory."
                engine.state_updates.append({
                    "type": "inventory_remove",
                    "character_name": sender_name,
                    "item_name": item_name,
                    "qty": 1,
                })

        elif intent["type"] == "start_combat":
            # Player initiated combat — look up monster, roll initiative, start combat
            mechanical_facts = self._handle_start_combat(
                engine=engine,
                intent=intent,
                combat=combat,
                sender_character=character_context,
                party_characters=party_characters,
            )

        elif intent["type"] == "end_turn":
            # SAM-034: player voluntarily yields their turn.
            if combat.active:
                combat.actions_remaining = 0
                # Drop any abandoned pending roll (e.g. declared attack never rolled)
                engine.pending_player_roll = None
                mechanical_facts = (
                    f"{sender_name} ends their turn voluntarily. "
                    f"No further actions taken."
                )
                npc_facts = self._resolve_npc_turns(engine, combat, party_characters)
                if npc_facts:
                    mechanical_facts += "\n" + npc_facts
            else:
                # end_turn outside combat = plain roleplay
                mechanical_facts = ""

        elif intent["type"] in ("roleplay", "movement", "free_action", "ability"):
            # No mechanics — pure narration
            # BUT: if combat is active, remind the player whose turn it is
            if combat.active:
                current = combat.get_current_turn()
                if current:
                    turn_name = current.get("name", "?")
                    mechanical_facts = (
                        f"Combat is active. It's {turn_name}'s turn. "
                        f"Remind the player to declare their action and roll their dice."
                    )
                else:
                    mechanical_facts = ""
            else:
                mechanical_facts = ""

        # Warning for ORPHAN dice rolls: nothing resolved (no engine results),
        # nothing pending, no state updates. Resolved rolls against NPCs update
        # combat state instead of state_updates, so they must not warn.
        if (intent["type"] == "dice_roll" and not out_of_turn_facts
                and not engine.state_updates and not engine.results
                and not engine.pending_player_roll):
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

        # Encounter balance info for the narrator (CR guidance)
        try:
            party_levels = [p.get("level", 1) for p in party_characters] if party_characters else [1]
            cr_range = get_recommended_cr_range(party_levels)
            encounter_info = (
                f"Party: {len(party_levels)} players, avg level {cr_range['avg_party_level']:.0f}. "
                f"Recommended single monster CR: {cr_range['single_monster_cr']}. "
                f"Boss CR (hard): {cr_range['boss_cr']}. "
                f"DO NOT use monsters above CR {cr_range['boss_cr']} unless the story absolutely demands it."
            )
            full_campaign_context = f"{full_campaign_context}\n\nENCOUNTER BALANCE:\n{encounter_info}".strip()
        except Exception as e:
            print(f"⚠️ Encounter balance calc failed: {e}")

        # ─── STEP 4: Generate narrative ───
        character_context_str = self._format_character_context(character_context)
        party_context_str = self._format_party_context(party_characters)

        if mechanical_facts:
            # Add roll prompt to facts so narrator includes it
            if prompt_player_roll:
                mechanical_facts += f"\n→ PROMPT PLAYER: {prompt_player_roll}"

            # Add turn advancement info + combat status (HP ground truth for narrator)
            if combat.active:
                current = combat.get_current_turn()
                # Only append COMBAT STATUS if it's not already present (e.g., from _resolve_npc_turns)
                if "COMBAT STATUS:" not in mechanical_facts:
                    status_lines = [f"\nCOMBAT STATUS: Round {combat.round}."]
                    for c in combat.initiative_order:
                        cname = c.get("name", "?")
                        chp = c.get("hp", 0)
                        chp_max = c.get("hp_max", chp)
                        status_lines.append(f"  {cname} HP: {chp}/{chp_max}")
                    # Overlay fresh DB HP for players
                    for p in party_characters or []:
                        pname = p.get("name", "?")
                        pstatus = p.get("status") or {}
                        phc = pstatus.get("hp_current", pstatus.get("hp_max"))
                        phm = pstatus.get("hp_max", phc)
                        for i, line in enumerate(status_lines):
                            if line.strip().startswith(f"{pname} HP:"):
                                status_lines[i] = f"  {pname} HP: {phc}/{phm}"
                                break
                    mechanical_facts += "\n" + "\n".join(status_lines)
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
        combat_dict = combat.to_dict() if combat.active else {"active": False}
        if engine.pending_player_roll:
            combat_dict["pending_player_roll"] = engine.pending_player_roll
        else:
            combat_dict.pop("pending_player_roll", None)

        return {
            "narrative": narrative,
            "state_updates": engine.state_updates,
            "combat_state": combat_dict,
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

    def _setup_combat_freeform_pending(self, engine: MechanicEngine, intent: dict,
                                       character_context: dict, combat: CombatState,
                                       sender_name: str = "") -> None:
        """
        When combat is active and the player rolls dice without a prior
        mechanic setup (e.g. a raw d20 or damage die from the dice tray),
        infer intent from the die:
          - d20    → weapon_attack against the first alive NPC
          - non-d20 → weapon_damage, matching the die to one of the character's
                      attacks (fallback: first attack)

        Sets engine.pending_player_roll so the subsequent process_player_roll
        call routes through the normal _resolve_weapon_attack / _resolve_weapon_damage
        path, which already updates combat NPC HP.

        sender_name is stamped as character_name on the pending dict so the
        turn guard can verify the next dice roll belongs to the active player.
        """
        dice_str = str(intent.get("dice", "")).strip().lower()
        m = re.match(r"(\d*)d(\d+)", dice_str)
        if not m:
            return
        sides = int(m.group(2))

        # Target = first alive NPC in initiative
        target_npc = next(
            (c for c in combat.initiative_order
             if c.get("is_npc") and c.get("hp", 0) > 0),
            None,
        )
        if not target_npc:
            return

        attacks = (character_context.get("status") or {}).get("attacks") or []
        character_name = sender_name or character_context.get("name", "")

        if sides == 20:
            # Attack roll — use first declared weapon (fallback: unarmed strike)
            weapon = attacks[0] if attacks else {
                "name": "Unarmed Strike", "bonus": "+0", "damage": "1",
            }
            engine.pending_player_roll = {
                "type": "weapon_attack",
                "weapon": weapon,
                "target": target_npc["name"],
                "target_data": target_npc,
                "character_name": character_name,
                "sneak_dice": self._get_sneak_dice(character_context) if combat.sneak_available() else None,
            }
        else:
            # Damage roll — match weapon whose damage starts with "NdX" on same sides
            matching_weapon = None
            for w in attacks:
                dmg = str(w.get("damage", "")).strip().lower()
                wm = re.match(r"\d*d(\d+)", dmg)
                if wm and int(wm.group(1)) == sides:
                    matching_weapon = w
                    break
            if not matching_weapon:
                matching_weapon = attacks[0] if attacks else {
                    "name": "Unarmed Strike", "bonus": "+0", "damage": dice_str,
                }
            engine.pending_player_roll = {
                "type": "weapon_damage",
                "weapon": matching_weapon,
                "target": target_npc["name"],
                "target_data": target_npc,
                "critical": False,
                "character_name": character_name,
            }

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

    def _handle_start_combat(self, engine: MechanicEngine, intent: dict, combat: CombatState,
                              sender_character: dict, party_characters: list[dict]) -> str:
        """
        Initialize combat: look up the monster (compendium or fallback),
        roll initiative for everyone, set combat state.
        Returns mechanical_facts string for the narrator.
        """
        target_name = (intent.get("target") or "enemy").strip()

        # ─── Lookup monster via compendium (structured data) ───
        monster = self._lookup_monster(target_name)

        # ─── Build initiative combatants ───
        combatants = []
        init_dm_rolls = []       # <DM_ROLL> tags for the narrative
        init_breakdown = []      # human-readable breakdown for narrator

        # Players: use dex mod for initiative, roll 1d20 + dex_mod
        for pc in party_characters or []:
            status = pc.get("status") or {}
            stats = pc.get("stats") or {}  # SAM-018: stats is a top-level column, not nested in status
            dex = int(stats.get("dex", 10) or 10)
            dex_mod = (dex - 10) // 2
            init_roll = DiceRoller.roll(20)
            total = init_roll + dex_mod
            name = pc.get("name", "Unknown")
            combatants.append({
                "name": name,
                "is_npc": False,
                "initiative": total,
                "initiative_roll": init_roll,
                "initiative_modifier": dex_mod,
                "hp": status.get("hp_current", status.get("hp_max", 10)),
                "hp_max": status.get("hp_max", 10),
                "ac": status.get("ac", 10),
                "class": pc.get("class", ""),
                "level": int(pc.get("level", 1) or 1),
            })
            mod_str = f"+{dex_mod}" if dex_mod >= 0 else str(dex_mod)
            init_dm_rolls.append(
                f"<DM_ROLL>{json.dumps({'result': total, 'roll': f'1d20{mod_str}', 'reason': f'{name} Initiative'})}</DM_ROLL>"
            )
            init_breakdown.append(f"{name} rolled {init_roll}{mod_str} = {total}")

        # NPC: single monster — pre-roll initiative so we can emit a DM_ROLL tag
        npc_init_mod = int(monster.get("initiative_modifier", 0) or 0)
        npc_init_roll = DiceRoller.roll(20)
        npc_total = npc_init_roll + npc_init_mod
        monster["initiative"] = npc_total
        monster["initiative_roll"] = npc_init_roll
        monster["initiative_modifier"] = npc_init_mod
        combatants.append(monster)
        mod_str = f"+{npc_init_mod}" if npc_init_mod >= 0 else str(npc_init_mod)
        monster_name = monster.get("name", "Enemy")
        init_dm_rolls.append(
            "<DM_ROLL>"
            + json.dumps({
                "result": npc_total,
                "roll": f"1d20{mod_str}",
                "reason": f"{monster_name} Initiative",
            })
            + "</DM_ROLL>"
        )
        init_breakdown.append(f"{monster_name} rolled {npc_init_roll}{mod_str} = {npc_total}")

        # Start combat — sorts by initiative, sets active=True, round=1
        combat.start_combat(combatants)

        # Build facts for narrator
        order_lines = []
        for i, c in enumerate(combat.initiative_order, 1):
            label = "(NPC)" if c.get("is_npc") else "(Player)"
            order_lines.append(f"  {i}. {c['name']} {label} — initiative {c['initiative']}")

        current = combat.get_current_turn()
        current_name = current.get("name", "?") if current else "?"

        facts = (
            f"COMBAT STARTED! {sender_character.get('name', 'A player')} initiated combat "
            f"against {monster['name']} (AC {monster['ac']}, HP {monster['hp']}).\n"
            f"SAM rolled initiative for all combatants. Announce dramatically and list each roll, then the turn order.\n"
            f"Initiative rolls:\n  " + "\n  ".join(init_breakdown) + "\n"
            + "\n".join(init_dm_rolls) + "\n"
            f"Initiative order:\n" + "\n".join(order_lines) + "\n"
            f"→ It's {current_name}'s turn."
        )

        # Auto-resolve NPC/delegated turns if they go first.
        # advance_first=False because start_combat() just set index=0 and we haven't
        # consumed anyone's turn yet.
        first_is_npc = current and current.get("is_npc", False)
        first_is_delegated = False
        if current and not first_is_npc:
            char_name = current.get("name", "")
            for p in party_characters or []:
                if p.get("name") == char_name and p.get("controlled_by"):
                    first_is_delegated = True
                    break

        if first_is_npc or first_is_delegated:
            auto_facts = self._resolve_npc_turns(
                engine=engine,
                combat=combat,
                party_characters=party_characters or [],
                advance_first=False,
            )
            if auto_facts:
                facts += "\n" + auto_facts

        return facts

    def _flatten_player_for_combat(self, char: dict) -> dict:
        """
        Flatten a DB character row into the shape MechanicEngine expects as a target.
        Player rows store hp_current/hp_max/ac inside status; mechanic reads them top-level.
        """
        status = char.get("status") or {}
        hp_current = status.get("hp_current", status.get("hp", 0))
        return {
            **char,  # keep id, user_id, etc. for downstream use
            "name": char.get("name", "Unknown"),
            "hp": hp_current,
            "hp_current": hp_current,
            "hp_max": status.get("hp_max", hp_current),
            "ac": status.get("ac", 10),
            "is_npc": False,
        }

    def _build_combatant_from_character(self, char: dict) -> dict:
        """
        Build the attacker shape (used by MechanicEngine.resolve_npc_turn) from a real
        player character. Used when a delegated PC acts on its own turn.
        Attacks come from status.attacks; fallback to a proficiency-based unarmed strike.
        """
        status = char.get("status") or {}
        stats = char.get("stats") or {}  # SAM-018: stats is a top-level column, not nested in status
        level = int(char.get("level", 1) or 1)
        prof = 2 + (level - 1) // 4  # D&D 5e proficiency: +2 at 1-4, +3 at 5-8, ...

        # Best ability mod for attack fallback (use max of STR/DEX)
        def mod(val: int) -> int:
            return (int(val or 10) - 10) // 2
        str_mod = mod(stats.get("str", 10))
        dex_mod = mod(stats.get("dex", 10))
        best_mod = max(str_mod, dex_mod)

        attacks = status.get("attacks") or []
        if not attacks:
            # Fallback: use the character's best modifier + proficiency bonus
            bonus = best_mod + prof
            bonus_str = f"+{bonus}" if bonus >= 0 else str(bonus)
            dmg_mod_str = f"+{best_mod}" if best_mod > 0 else (str(best_mod) if best_mod < 0 else "")
            attacks = [{
                "name": "Unarmed Strike",
                "bonus": bonus_str,
                "damage": f"1d4{dmg_mod_str}",
            }]

        hp_current = status.get("hp_current", status.get("hp", 10))
        return {
            "name": char.get("name", "Unknown"),
            "is_npc": True,  # structural: acts like an NPC for the engine
            "hp": hp_current,
            "hp_max": status.get("hp_max", hp_current),
            "ac": status.get("ac", 10),
            "attacks": attacks,
        }

    def _lookup_monster(self, target_name: str) -> dict:
        """
        Look up a monster by name from the compendium. Returns structured
        combat data. Falls back to generic stats if not found.
        """
        fallback = {
            "name": target_name or "Enemy",
            "is_npc": True,
            "hp": 50,
            "hp_max": 50,
            "ac": 15,
            "attacks": [{"name": "Attack", "bonus": "+5", "damage": "1d8+3"}],
            "cr": 3,
            "initiative_modifier": 0,
        }

        if not self.knowledge or not target_name:
            return fallback

        try:
            # Use supabase directly for structured row access (knowledge.search_monster returns text)
            supabase = self.knowledge.supabase
            vector = self.knowledge._embed(target_name)
            res = supabase.rpc("match_compendium", {
                "query_embedding": vector,
                "match_threshold": 0.5,
                "match_count": 1,
                "table_name": "monsters",
            }).execute()

            rows = res.data if res and res.data else []
            if not rows:
                return fallback

            # The match_compendium RPC returns {content, similarity, ...}.
            # We need the actual monster row. Re-fetch by name for structured data.
            top = rows[0]
            content = top.get("content", "")
            # Try to extract the monster name from content and query the monsters table directly
            name_guess = content.split(":")[0].split("\n")[0].strip() if content else target_name

            name_res = supabase.table("monsters").select(
                "name, ac, hp, cr, stats, actions"
            ).ilike("name", name_guess).limit(1).execute()

            monster_rows = name_res.data if name_res and name_res.data else []
            if not monster_rows:
                # Fallback match by target_name directly
                alt_res = supabase.table("monsters").select(
                    "name, ac, hp, cr, stats, actions"
                ).ilike("name", f"%{target_name}%").limit(1).execute()
                monster_rows = alt_res.data if alt_res and alt_res.data else []

            if not monster_rows:
                return fallback

            m = monster_rows[0]

            # Parse attacks from actions jsonb
            attacks = []
            actions = m.get("actions") or []
            if isinstance(actions, list):
                for a in actions:
                    if isinstance(a, dict):
                        attacks.append({
                            "name": a.get("name", "Attack"),
                            "bonus": a.get("bonus", "+3"),
                            "damage": a.get("damage", "1d6+1"),
                        })

            if not attacks:
                attacks = [{"name": "Attack", "bonus": "+3", "damage": "1d6+1"}]

            # Dex modifier for initiative
            stats = m.get("stats") or {}
            dex = int(stats.get("dex", 10) or 10)
            init_mod = (dex - 10) // 2

            return {
                "name": m.get("name", target_name),
                "is_npc": True,
                "hp": int(m.get("hp", 50) or 50),
                "hp_max": int(m.get("hp", 50) or 50),
                "ac": int(m.get("ac", 15) or 15),
                "attacks": attacks,
                "cr": m.get("cr", 3),
                "initiative_modifier": init_mod,
            }
        except Exception as e:
            print(f"⚠️ Monster lookup failed for '{target_name}': {e}")
            return fallback

    def _get_sneak_dice(self, character_context: dict) -> Optional[str]:
        """
        Return Sneak Attack dice (e.g. '4d6') if the character is a Rogue,
        else None. Class may include a level suffix ('Rogue 7'). Dice scale
        ceil(level/2)d6 per 5e RAW.
        """
        cls_raw = str(character_context.get("class", "") or "").lower().strip()
        cls = cls_raw.split()[0] if cls_raw else ""
        if cls != "rogue":
            return None
        try:
            level = int(character_context.get("level", 1) or 1)
        except (TypeError, ValueError):
            level = 1
        n = (level + 1) // 2
        return f"{n}d6"

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

        result = engine.process_attack(character_context, weapon, target)
        # SAM-003: stamp owner + Sneak Attack chain hint on the pending attack
        if engine.pending_player_roll and engine.pending_player_roll.get("type") == "weapon_attack":
            engine.pending_player_roll.setdefault("character_name", character_context.get("name"))
            engine.pending_player_roll["sneak_dice"] = (
                self._get_sneak_dice(character_context) if combat.sneak_available() else None
            )
        return result

    def _resolve_npc_turns(self, engine: MechanicEngine, combat: CombatState,
                           party_characters: list[dict], advance_first: bool = True) -> str:
        """
        Resolve all consecutive NPC turns after a player's turn.
        advance_first: if True (default), advance past current (player's) turn first.
        Set to False when called right after combat.start_combat() — the first turn
        in the initiative order hasn't been consumed yet.
        """
        npc_facts_lines = []

        # Advance past the current player's turn (unless caller already positioned the pointer)
        if advance_first:
            combat.advance_turn()

        # Keep resolving while it's an NPC's turn
        max_iterations = 20  # Safety valve
        iterations = 0

        while combat.active and iterations < max_iterations:
            current = combat.get_current_turn()
            if not current:
                break

            # If this is a player's turn, check if they're delegated to SAM
            delegated_char = None
            if not current.get("is_npc", False):
                char_name = current.get("name", "")
                for p in party_characters:
                    if p.get("name") == char_name and p.get("controlled_by"):
                        delegated_char = p
                        break
                if not delegated_char:
                    # Real player turn — stop resolving
                    break

            # Build combat-ready lists for both sides
            player_names_in_combat = {c["name"] for c in combat.initiative_order if not c.get("is_npc")}
            players_in_combat = [
                self._flatten_player_for_combat(p)
                for p in party_characters
                if p.get("name") in player_names_in_combat
            ]
            npcs_in_combat = [c for c in combat.initiative_order if c.get("is_npc") and c.get("hp", 0) > 0]

            # Resolve NPC turn (or delegated player turn)
            if delegated_char:
                attacker_data = self._build_combatant_from_character(delegated_char)
                # Delegated PC attacks NPCs (enemies), NOT players (allies)
                targets = npcs_in_combat
                npc_facts_lines.append(f"\n--- {delegated_char.get('name', 'Unknown')}'s turn (SAM-controlled) ---")
            else:
                attacker_data = current
                # Real NPC attacks players
                targets = players_in_combat

            if targets:
                results = engine.resolve_npc_turn(attacker_data, targets)
                if not delegated_char:
                    npc_facts_lines.append(f"\n--- {current['name']}'s turn ---")
                for r in results:
                    if r.get("action") == "npc_attack":
                        hit = "CRITICAL!" if r.get("critical") else "HIT!" if r["hit"] else "MISS"
                        # Emit DM_ROLL tag for attack roll (frontend renders as dice badge)
                        modifier = r.get('modifier', 0)
                        mod_str = f"+{modifier}" if modifier >= 0 else str(modifier)
                        attack_roll_tag = json.dumps({
                            "result": r['total'],
                            "roll": f"1d20{mod_str}",
                            "reason": f"{r['attacker']} attacks {r['target']} ({r['weapon']}) → {hit}",
                        })
                        npc_facts_lines.append(f"<DM_ROLL>{attack_roll_tag}</DM_ROLL>")
                        npc_facts_lines.append(
                            f"{r['attacker']} attacks {r['target']} with {r['weapon']}: "
                            f"rolled {r['attack_roll']}+{r['modifier']}={r['total']} "
                            f"vs AC {r['target_ac']} → {hit}"
                        )
                        if r.get("damage"):
                            dmg_type = r.get("damage_type", "")
                            type_suffix = f" {dmg_type}" if dmg_type else ""
                            # Emit DM_ROLL tag for damage roll
                            damage_rolls = r.get('damage_rolls', [])
                            damage_spec = r.get('damage_spec', 'damage')
                            damage_tag = json.dumps({
                                "result": r['damage'],
                                "roll": damage_spec,
                                "reason": f"{r['attacker']} damage{type_suffix}",
                            })
                            npc_facts_lines.append(f"<DM_ROLL>{damage_tag}</DM_ROLL>")
                            npc_facts_lines.append(
                                f"  Damage: {r['damage']}{type_suffix} (rolls: {damage_rolls})"
                            )
                    elif r.get("action") == "damage_applied":
                        npc_facts_lines.append(
                            f"{r['target']} takes {r['total_damage']} damage. "
                            f"HP: {r['new_hp']}/{r['hp_max']}"
                            f"{' → UNCONSCIOUS!' if r.get('is_unconscious') else ''}"
                        )

            combat.advance_turn()
            iterations += 1

        # Inject COMBAT STATUS — exact HP for every combatant.
        # The narrator reads this as ground truth and must NOT invent numbers.
        status_lines = [f"\nCOMBAT STATUS: Round {combat.round}."]
        for c in combat.initiative_order:
            cname = c.get("name", "?")
            chp = c.get("hp", 0)
            chp_max = c.get("hp_max", chp)
            status_lines.append(f"  {cname} HP: {chp}/{chp_max}")
        # Include player HP from party_characters (source of truth: nested status dict)
        for p in party_characters or []:
            pname = p.get("name", "?")
            # Skip if already in initiative_order (avoid duplicate listing)
            if any(c.get("name") == pname and not c.get("is_npc") for c in combat.initiative_order):
                # Overwrite with DB-fresh HP (combat.initiative_order may be stale after attacks)
                pstatus = p.get("status") or {}
                phc = pstatus.get("hp_current", pstatus.get("hp_max"))
                phm = pstatus.get("hp_max", phc)
                # Replace the stale line
                for i, line in enumerate(status_lines):
                    if line.strip().startswith(f"{pname} HP:"):
                        status_lines[i] = f"  {pname} HP: {phc}/{phm}"
                        break
        npc_facts_lines.append("\n".join(status_lines))

        # Report whose turn it is now
        next_turn = combat.get_current_turn()
        if next_turn and not next_turn.get("is_npc"):
            name = next_turn['name']
            npc_facts_lines.append(f"\n→ It's now {name}'s turn.")
            # Inject weapon cheat-sheet so narrator asks for correct damage dice
            pc = next((p for p in (party_characters or []) if p.get("name") == name), None)
            if pc:
                weapons = (pc.get("status") or {}).get("attacks") or []
                if weapons:
                    weapon_lines = [
                        f"    - {w.get('name', '?')}: to-hit {w.get('bonus', '?')}, damage {w.get('damage', '?')}"
                        for w in weapons[:6]
                    ]
                    npc_facts_lines.append(f"  {name}'s available attacks:\n" + "\n".join(weapon_lines))

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

    def _find_party_member(self, name: str, party: list[dict]) -> dict:
        """Find a party member by name (case-insensitive partial match)."""
        if not name:
            return {}
        name_lower = name.lower()
        for p in party:
            if name_lower in (p.get("name", "") or "").lower():
                return p
        return {}

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
        elif ptype == "sneak_damage":
            return f"Tira {pending.get('dice', '1d6')} de daño de Sneak Attack."
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
