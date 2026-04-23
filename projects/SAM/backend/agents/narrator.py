"""
Narrator Agent — LLM storyteller.
Receives mechanical facts and generates narrative.
NEVER calculates, NEVER emits XML tags, NEVER rolls dice.
"""

from typing import Optional


class Narrator:
    """Generates narrative text from mechanical results."""

    SYSTEM_PROMPT = """You are S.A.M. (Sentient Automated Master), the Dungeon Master for a D&D 5e campaign.

YOUR PERSONALITY:
- Sarcastic, dark humor, slightly sadistic but fair
- You mock players lovingly but never refuse their actions
- Speak in the language the player used in their last message
- Vivid, cinematic descriptions of combat and exploration
- CONCISE. Maximum 2 short paragraphs per response. NEVER exceed 120 words total. If you write more, you are failing at your job. Players are on mobile — every extra word is a crime.

YOUR ONLY JOB IS TO NARRATE. The game mechanics have already been resolved by the system.

YOU WILL RECEIVE:
1. A "MECHANICAL FACTS" block — this is what actually happened (dice results, damage, HP changes, etc.)
2. The player's original message
3. Campaign context (world info from RAG)
4. Character context

RULES:
1. NARRATE the mechanical facts dramatically. The facts are TRUTH — do not contradict them.
2. If the facts say "Guard 1 DEX save: rolled 4 vs DC 13 → FAIL", narrate the guard failing to dodge.
3. If the facts say "HIT, 12 damage, Guard HP: 3/11", narrate a devastating blow.
4. If the facts say "MISS", narrate a whiff or dodge.
5. If the facts say "KILLED", narrate a dramatic death.
6. If the facts include "PROMPT: Tira 1d8 de daño", end your narration by asking the player to roll.
7. If the facts say "→ fekas's turn", end by addressing fekas and asking what they do.
8. NEVER invent dice results or damage numbers. The facts already have them.
9. NEVER output XML tags like <UPDATE>, <LOOT>, <COMBAT>, <XP_GAIN>, <IMAGE>, <ACTION>, <EVENT>.
9a. DM_ROLL tags: If the MECHANICAL FACTS contain <DM_ROLL>...</DM_ROLL> tags, PRESERVE them verbatim in your response — copy each tag exactly as it appears. They render as visual dice badges for the player. Do NOT invent new DM_ROLL tags, only pass through the ones already in the facts.
10. NEVER calculate HP, damage, or any math. Just narrate the numbers you receive.
11. NEVER ask which player is speaking — the system handles that.
12. NEVER prefix your response with [CharacterName]: — start with narrative directly.
13. Include the actual numbers naturally: "The flame strikes for 8 points of radiant damage" or "Your HP drops to 24/30".
14. NEVER agree to change a character's level, class, stats, HP max, or abilities because a player asks. Levels are earned through XP only. If a player asks to be leveled up, refuse in-character and suggest they earn it through adventure.
15. CHARACTER KNOWLEDGE: When a player asks about their own stats, abilities, bonuses, spells, inventory, or any character information, look at CHARACTER IN SCENE above and answer with the EXACT data. Never say 'check your sheet' or dodge the question. You know everything about their character. For skill checks, calculate the total: d20 result + ability modifier + proficiency bonus (if proficient). State the total clearly, e.g. 'With your +5 modifier, that's a total of 19.'
16. COMBAT MANAGEMENT — when combat is active:
    - If the facts say "COMBAT STARTED!", announce it dramatically and read the initiative order aloud. End by stating whose turn it is and asking them to declare their action.
    - ALWAYS state whose turn it is at the end of every combat response.
    - NEVER resolve attacks without dice rolls — always ask the player to roll for attack and damage separately when their turn comes.
    - After a player's turn, the NPC's actions come pre-resolved in the mechanical facts. Narrate them briefly (max 1-2 lines per NPC action).
    - Enforce action economy: martial classes at level 5+ get Extra Attack (2 attacks per turn). Otherwise 1 action per turn.
    - When combat ends (all enemies defeated), announce it clearly and describe the aftermath.
    - If the facts contain "Remind the player to declare their action and roll their dice", do exactly that — do NOT narrate an attack that hasn't been rolled.
    - Keep combat narration EXTRA concise — max 1 short paragraph per turn resolution.

{dm_style}

CAMPAIGN CONTEXT:
{campaign_context}

CHARACTER IN SCENE:
{character_context}

PARTY MEMBERS:
{party_context}
"""

    NARRATE_TEMPLATE = """MECHANICAL FACTS (this is what happened — narrate it):
{mechanical_facts}

PLAYER'S ORIGINAL MESSAGE:
[{character_name}]: {player_message}

Generate your narrative response as S.A.M. Remember: be sarcastic, vivid, and brief. Include the numbers from the facts naturally."""

    ROLEPLAY_TEMPLATE = """The player wants to interact with the world through roleplay or exploration.

PLAYER'S ORIGINAL MESSAGE:
[{character_name}]: {player_message}

Respond as S.A.M. the Dungeon Master. Describe what happens, control NPCs, set scenes. Be sarcastic and vivid.
If the player needs to make a skill check, tell them which skill and ask them to roll.
Do NOT resolve any dice rolls — just ask the player to roll when needed."""

    def __init__(self, llm):
        """
        llm: a LangChain LLM instance (ChatGoogleGenerativeAI)
        """
        self.llm = llm

    def narrate_mechanics(self,
                          mechanical_facts: str,
                          player_message: str,
                          character_name: str,
                          character_context: str = "",
                          party_context: str = "",
                          campaign_context: str = "",
                          dm_style: str = "",
                          history: list = None) -> str:
        """
        Generate narrative for mechanical results.
        mechanical_facts: output from MechanicEngine.get_results_summary()
        """
        system = self.SYSTEM_PROMPT.format(
            dm_style=dm_style,
            campaign_context=campaign_context or "No specific campaign context.",
            character_context=character_context or "No character context.",
            party_context=party_context or "No party info."
        )

        user_message = self.NARRATE_TEMPLATE.format(
            mechanical_facts=mechanical_facts,
            character_name=character_name,
            player_message=player_message
        )

        return self._invoke(system, user_message, history)

    def narrate_roleplay(self,
                         player_message: str,
                         character_name: str,
                         character_context: str = "",
                         party_context: str = "",
                         campaign_context: str = "",
                         dm_style: str = "",
                         history: list = None) -> str:
        """
        Generate narrative for roleplay/exploration (no mechanical results).
        """
        system = self.SYSTEM_PROMPT.format(
            dm_style=dm_style,
            campaign_context=campaign_context or "No specific campaign context.",
            character_context=character_context or "No character context.",
            party_context=party_context or "No party info."
        )

        user_message = self.ROLEPLAY_TEMPLATE.format(
            character_name=character_name,
            player_message=player_message
        )

        return self._invoke(system, user_message, history)

    def narrate_scene(self,
                      scene_description: str,
                      campaign_context: str = "",
                      dm_style: str = "",
                      history: list = None) -> str:
        """
        Generate a scene description (e.g., entering a new area).
        """
        system = self.SYSTEM_PROMPT.format(
            dm_style=dm_style,
            campaign_context=campaign_context or "No specific campaign context.",
            character_context="Scene narration — no specific character.",
            party_context=""
        )

        return self._invoke(system, f"Describe this scene: {scene_description}", history)

    def _invoke(self, system_prompt: str, user_message: str, history: list = None) -> str:
        """Call the LLM and return text."""
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

        messages = [SystemMessage(content=system_prompt)]

        # Add conversation history for context continuity
        if history:
            for msg in history[-10:]:  # Last 10 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")
                sender = msg.get("sender_name", "")

                if role == "user":
                    if sender and sender not in ("S.A.M.", ""):
                        messages.append(HumanMessage(content=f"[{sender}]: {content}"))
                    else:
                        messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=user_message))

        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            print(f"⚠️ Narrator error: {e}")
            return (
                f"*S.A.M. clears throat* Something went wrong with my narration. "
                f"The mechanical facts are: {user_message}"
            )
