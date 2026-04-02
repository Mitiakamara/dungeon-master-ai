"""
Interpreter Agent — Lightweight LLM call to parse player intent.
Converts natural language into structured action dicts.
Uses a SHORT, focused prompt — no narrative, no personality.
"""

import json
import re
from typing import Optional


class IntentInterpreter:
    """Parses player messages into structured game intents."""

    SYSTEM_PROMPT = """You are a D&D 5e action parser. Your ONLY job is to convert a player's message into a JSON action.

CONTEXT:
- Character: {character_name} ({character_class} Level {character_level})
- Available spells: {spell_list}
- Available attacks: {attack_list}
- In combat: {in_combat}
- Current target options: {target_options}

RESPOND WITH ONLY A JSON OBJECT. No explanation, no markdown, no backticks.

ACTION TYPES:

1. Spell cast:
{{"type": "spell", "spell_name": "Sacred Flame", "target": "Guard 1"}}

2. Weapon attack:
{{"type": "attack", "weapon": "Warhammer", "target": "Guard 1"}}

3. Skill check:
{{"type": "skill_check", "skill": "Perception", "description": "looking for traps"}}

4. Movement:
{{"type": "movement", "description": "I move behind the pillar"}}

5. Roleplay/dialogue:
{{"type": "roleplay", "description": "I ask the merchant about the gem"}}

6. Item use:
{{"type": "item", "item": "Potion of Healing", "target": "self"}}

7. Class ability:
{{"type": "ability", "ability": "Channel Divinity: Touch of Death", "target": "Guard 1"}}

8. Free action (talking, looking, etc.):
{{"type": "free_action", "description": "I look around the room"}}

RULES:
- If the player names a spell, match it to their spell list. If not found, use closest match.
- If the player says "attack" without specifying a weapon, use their first available weapon.
- If target is ambiguous and there's only one enemy, use that enemy.
- If you can't determine the action type, use "roleplay".
- NEVER add fields that aren't in the templates above.
- ALWAYS respond with valid JSON only.
"""

    def __init__(self, llm):
        """
        llm: a LangChain LLM instance (ChatGoogleGenerativeAI)
        """
        self.llm = llm

    def parse_intent(self,
                     message: str,
                     character_context: dict,
                     combat_state: dict = None,
                     targets: list[str] = None) -> dict:
        """
        Parse a player's message into a structured intent.

        Returns dict like:
        {"type": "spell", "spell_name": "Sacred Flame", "target": "Guard 1"}
        """
        # First, check for SYSTEM EVENT (dice roll) — no LLM needed
        system_event = self._parse_system_event(message)
        if system_event:
            return system_event

        # Build context for the prompt
        spell_list = self._extract_spell_names(character_context)
        attack_list = self._extract_attack_names(character_context)
        target_options = targets or []
        in_combat = bool(combat_state and combat_state.get("active"))

        prompt = self.SYSTEM_PROMPT.format(
            character_name=character_context.get("name", "Unknown"),
            character_class=character_context.get("class", "Unknown"),
            character_level=character_context.get("level", 1),
            spell_list=", ".join(spell_list) if spell_list else "None",
            attack_list=", ".join(attack_list) if attack_list else "Unarmed Strike",
            in_combat=in_combat,
            target_options=", ".join(target_options) if target_options else "None specified"
        )

        try:
            from langchain_core.messages import SystemMessage, HumanMessage

            response = self.llm.invoke([
                SystemMessage(content=prompt),
                HumanMessage(content=message)
            ])

            # Parse JSON from response
            text = response.content.strip()
            # Clean markdown fences if present
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*', '', text)
            text = text.strip()

            intent = json.loads(text)

            # Validate required fields
            if "type" not in intent:
                intent["type"] = "roleplay"

            return intent

        except json.JSONDecodeError as e:
            print(f"⚠️ Interpreter JSON parse error: {e}")
            return {"type": "roleplay", "description": message}
        except Exception as e:
            print(f"⚠️ Interpreter error: {e}")
            return {"type": "roleplay", "description": message}

    def _parse_system_event(self, message: str) -> Optional[dict]:
        """
        Parse a [SYSTEM EVENT] dice roll. No LLM needed.
        Input: "[SYSTEM EVENT] Baol Gortsh rolled 1d20. Result: 18 (Rolls: 18)."
        Output: {"type": "dice_roll", "dice": "1d20", "result": 18, "rolls": [18]}
        """
        match = re.match(
            r'\[SYSTEM EVENT\]\s*(.+?)\s+rolled\s+(\d+d\d+)\.\s*Result:\s*(\d+)\s*\(Rolls?:\s*([\d,\s]+)\)',
            message
        )
        if match:
            character_name = match.group(1).strip()
            dice = match.group(2)
            result = int(match.group(3))
            rolls = [int(r.strip()) for r in match.group(4).split(",")]
            return {
                "type": "dice_roll",
                "character_name": character_name,
                "dice": dice,
                "result": result,
                "rolls": rolls
            }
        return None

    def _extract_spell_names(self, context: dict) -> list[str]:
        """Extract spell names from character context."""
        spells = context.get("status", {}).get("spells", [])
        return [s.get("name", "") for s in spells if s.get("name")]

    def _extract_attack_names(self, context: dict) -> list[str]:
        """Extract weapon/attack names from character context."""
        attacks = context.get("status", {}).get("attacks", [])
        return [a.get("name", "") for a in attacks if a.get("name")]

    def parse_system_event_static(self, message: str) -> Optional[dict]:
        """Static method version for use without LLM (SYSTEM EVENTs only)."""
        return self._parse_system_event(message)
