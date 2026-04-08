"""
Memory Agent — Persistent narrative memory for campaigns.

After each SAM response, this service uses a lightweight LLM call to extract
new narrative facts (NPCs met, locations discovered, plot decisions, items
found, etc.) and stores them in the `campaign_memories` table.

Memories are later injected into the narrator's `campaign_context` so SAM
remembers what happened across sessions, even when the chat history window
has scrolled past those events.
"""

import json
import logging
import os

from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)


EXTRACTION_PROMPT = """You are a memory extractor for a D&D 5e campaign. Your ONLY job is to read the most recent exchange between a player and the Dungeon Master and extract NEW narrative facts worth remembering long-term.

EXISTING MEMORIES (do NOT repeat these):
{existing}

LATEST PLAYER MESSAGE:
{player_message}

LATEST DM RESPONSE:
{sam_response}

EXTRACTION RULES:
1. Extract ONLY new narrative facts. If something is already in EXISTING MEMORIES, skip it.
2. IGNORE pure game mechanics: dice rolls, damage numbers, HP changes, AC values, modifiers, initiative order, save DCs.
3. FOCUS on narrative: NPCs introduced, locations discovered, plot reveals, decisions made, items found, alliances/enemies, promises, secrets, mysteries.
4. Each memory must be a SHORT factual sentence in past tense (max ~150 chars).
5. Classify each memory with a `type`:
   - "fact"     — generic world/lore fact
   - "npc"      — a character was introduced or their nature/intent was revealed
   - "location" — a place was discovered, named, or described
   - "plot"     — a story beat, reveal, or major event
   - "item"     — a notable item was found, identified, or lost (not random loot)
   - "decision" — the party made a choice that changes the story
6. Assign `importance` 1–10:
   - 10 = plot-critical (boss revealed, ally killed, prophecy uttered)
   - 7-9 = significant (major NPC met, key location found, big decision)
   - 4-6 = useful context (side NPC, minor location, item)
   - 1-3 = trivial flavor (almost forgettable)
7. If NOTHING new is worth remembering, respond with exactly: []
8. Respond with a JSON array ONLY. No markdown, no backticks, no explanation.

OUTPUT FORMAT:
[{{"content": "The party met Eldric, a one-eyed dwarf blacksmith in Phandalin.", "type": "npc", "importance": 6}}, {{"content": "Sildar Hallwinter was rescued from goblin captivity in Cragmaw Hideout.", "type": "plot", "importance": 8}}]

If nothing new: []
"""


class MemoryService:
    """Extracts and stores persistent narrative memories per campaign."""

    def __init__(self, supabase_client):
        """
        supabase_client: a configured Supabase client (injected, not created here).
        """
        self.supabase = supabase_client
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.1,
            max_tokens=1024,
            max_retries=1,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )

    async def extract_and_store(
        self,
        campaign_id: str,
        player_message: str,
        sam_response: str,
        existing_memories: list,
    ) -> int:
        """
        Extract new narrative facts from the latest exchange and store them.

        existing_memories: list of strings (already-known memories) to avoid duplicates.
        Returns the number of memories inserted. Never raises — failures log and return 0.
        """
        try:
            existing_text = (
                "\n".join(f"- {m}" for m in existing_memories)
                if existing_memories
                else "(none yet)"
            )
            prompt = EXTRACTION_PROMPT.format(
                existing=existing_text,
                player_message=player_message,
                sam_response=sam_response,
            )

            from langchain_core.messages import HumanMessage

            response = self.llm.invoke([HumanMessage(content=prompt)])
            text = (response.content or "").strip()

            # Strip any stray markdown fences just in case
            if text.startswith("```"):
                text = text.strip("`")
                if text.lower().startswith("json"):
                    text = text[4:].strip()

            try:
                facts = json.loads(text)
            except json.JSONDecodeError as e:
                logger.warning(f"MemoryService: failed to parse JSON ({e}). Raw: {text[:200]}")
                return 0

            if not isinstance(facts, list) or not facts:
                return 0

            inserted = 0
            for fact in facts:
                if not isinstance(fact, dict):
                    continue
                content = (fact.get("content") or "").strip()
                if not content:
                    continue

                fact_type = fact.get("type", "fact")
                if fact_type not in ("fact", "npc", "location", "plot", "item", "decision"):
                    fact_type = "fact"

                try:
                    importance = int(fact.get("importance", 5))
                except (TypeError, ValueError):
                    importance = 5
                importance = max(1, min(10, importance))

                try:
                    self.supabase.table("campaign_memories").insert({
                        "campaign_id": campaign_id,
                        "content": content,
                        "type": fact_type,
                        "importance": importance,
                        "source": "auto",
                    }).execute()
                    inserted += 1
                except Exception as ins_e:
                    logger.warning(f"MemoryService: insert failed for fact: {ins_e}")

            if inserted:
                logger.info(f"🧠 MemoryService: stored {inserted} new memories for campaign {campaign_id}")
            return inserted

        except Exception as e:
            logger.exception(f"MemoryService.extract_and_store failed: {e}")
            return 0

    async def get_memories(self, campaign_id: str, limit: int = 15) -> list:
        """Fetch top memories for a campaign, ordered by importance then recency."""
        try:
            res = (
                self.supabase.table("campaign_memories")
                .select("content, type, importance")
                .eq("campaign_id", campaign_id)
                .order("importance", desc=True)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.warning(f"MemoryService.get_memories failed: {e}")
            return []

    def format_memories_for_context(self, memories: list) -> str:
        """Format a memory list into a string block for the narrator's context."""
        if not memories:
            return ""

        lines = ["=== CAMPAIGN MEMORIES (What has happened so far) ==="]
        for m in memories:
            mtype = (m.get("type") or "fact").upper()
            content = m.get("content", "")
            lines.append(f"- [{mtype}] {content}")
        lines.append("=== END MEMORIES ===")
        return "\n".join(lines) + "\n"
