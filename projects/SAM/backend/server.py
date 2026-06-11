from fastapi import FastAPI, HTTPException, Depends
from app.core.security import verify_token
from pydantic import BaseModel
from typing import List, Optional, Dict, Union
import asyncio
import re
import json
import os

# Import S.A.M. Core Modules
from app.core.dice import DiceRoller, Visibility
from app.services.ai import sam_brain
from app.services.admin import AdminService
from app.routers import characters, campaigns, messages, invitations

# Import Multi-Agent System
from agents.orchestrator import SAMOrchestrator
from agents.knowledge import KnowledgeService
from agents.memory import MemoryService
from langchain_google_genai import ChatGoogleGenerativeAI
from google import genai
import logging

logger = logging.getLogger(__name__)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="S.A.M. - Storytelling AI Master")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(characters.router)
app.include_router(campaigns.router)
app.include_router(messages.router)
app.include_router(invitations.router)

# --- Data Models ---
class ChatRequest(BaseModel):
    message: str
    history: List[Union[str, Dict[str, str]]] = []
    character_context: Optional[str] = "No character selected."

class RollRequest(BaseModel):
    expression: str # e.g. "1d20+5"
    visibility: Visibility = Visibility.PUBLIC

# --- Multi-Agent Orchestrator ---
try:
    _google_api_key = os.getenv("GOOGLE_API_KEY")
    _interpreter_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", temperature=0.1,
        google_api_key=_google_api_key
    )
    _narrator_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", temperature=0.9,
        google_api_key=_google_api_key
    )
    _genai_client = genai.Client(api_key=_google_api_key)
    _knowledge = KnowledgeService(sam_brain.supabase, _genai_client)
    sam_orchestrator = SAMOrchestrator(_interpreter_llm, _narrator_llm, _knowledge)
    print("✅ SAMOrchestrator initialized")
except Exception as e:
    print(f"⚠️ SAMOrchestrator init failed, will use legacy SAMBrain only: {e}")
    sam_orchestrator = None

# Memory service for persistent campaign memories
try:
    memory_service = MemoryService(sam_brain.supabase)
    print("✅ MemoryService initialized")
except Exception as e:
    print(f"⚠️ MemoryService init failed: {e}")
    memory_service = None

# Lock per campaign to prevent simultaneous SAM responses
_campaign_locks: dict[str, asyncio.Lock] = {}

def get_campaign_lock(campaign_id: str) -> asyncio.Lock:
    if campaign_id not in _campaign_locks:
        _campaign_locks[campaign_id] = asyncio.Lock()
    return _campaign_locks[campaign_id]


def apply_state_updates(supabase, party_characters, state_updates):
    """
    Apply per-character status changes atomically (SAM-044). ACCUMULATE all
    changes for a character in memory, then FLUSH one write per character — so
    multiple updates in one request (XP + gold + item + HP + slots) no longer
    clobber each other. Previously every handler did its own read-modify-write
    of the WHOLE status off the stale in-memory snapshot → last-write-wins.

    Characters resolve by id when the update carries `character_id`, else by
    name (SAM-029). Top-level columns (level/class on level-up) flush in the
    same write as the status.

    Returns {"status": {char_id: status}, "top": {char_id: top_cols}} for
    logging/testing.
    """
    pending_status: dict = {}   # char_id -> accumulated status dict
    pending_top: dict = {}      # char_id -> top-level cols (level/class)
    name_by_id: dict = {}       # char_id -> name (for logging)

    def _find_char(upd):
        uid = upd.get("character_id")
        if uid:
            return next((c for c in party_characters if c.get("id") == uid), None)
        uname = (upd.get("character_name") or "").lower().strip()
        if not uname:
            return None
        return next((c for c in party_characters
                     if (c.get("name") or "").lower().strip() == uname), None)

    def _working_status(char):
        cid = char["id"]
        if cid not in pending_status:
            pending_status[cid] = dict(char.get("status") or {})
            name_by_id[cid] = char.get("name")
        return pending_status[cid]

    def _working_top(char):
        cid = char["id"]
        if cid not in pending_top:
            pending_top[cid] = {}
        return pending_top[cid]

    for update in state_updates or []:
        try:
            utype = update.get("type")

            if utype == "player_hp":
                char = _find_char(update)
                if not char:
                    print(f"⚠️ player_hp: character {update.get('character_name')} not found")
                    continue
                _working_status(char)["hp_current"] = update["new_hp"]
                print(f"💚 HP: {char.get('name')} → {update['new_hp']}")

            elif utype == "xp_update":
                # SAM-021: values arrive precomputed from the orchestrator.
                char = _find_char(update)
                if not char:
                    print(f"⚠️ xp_update: character {update.get('character_name')} not found")
                    continue
                status = _working_status(char)
                status["xp"] = update["new_xp"]
                if update.get("leveled_up"):
                    top = _working_top(char)
                    top["level"] = update["new_level"]
                    if update.get("new_hp_max") is not None:
                        status["hp_max"] = update["new_hp_max"]
                        status["hp_current"] = update["new_hp_current"]
                    # Keep "Barbarian 7"-style class suffix in sync
                    cls = str(char.get("class") or "")
                    cls_parts = cls.rsplit(" ", 1)
                    if len(cls_parts) == 2 and cls_parts[1].isdigit():
                        top["class"] = f"{cls_parts[0]} {update['new_level']}"
                    print(f"🎉 LEVEL UP: {char.get('name')} → level {update['new_level']}")
                print(f"⭐ XP: {char.get('name')} +{update.get('xp_gained', '?')} → {update['new_xp']}")

            elif utype == "money_award":
                # SAM-021 f2: gold precomputed by the orchestrator
                char = _find_char(update)
                if not char:
                    print(f"⚠️ money_award: character {update.get('character_name')} not found")
                    continue
                gp = int(update.get("gp", 0) or 0)
                if gp <= 0:
                    continue
                status = _working_status(char)
                money = dict(status.get("money") or {})
                money["gp"] = int(money.get("gp", 0) or 0) + gp
                status["money"] = money
                print(f"💰 Loot: {char.get('name')} +{gp} gp")

            elif utype == "item_award":
                # SAM-021 f2: flavor item named by the LLM, validated upstream
                char = _find_char(update)
                if not char:
                    print(f"⚠️ item_award: character {update.get('character_name')} not found")
                    continue
                item = dict(update.get("item") or {})
                if not item.get("item"):
                    print(f"⚠️ item_award missing item name for {char.get('name')}")
                    continue
                status = _working_status(char)
                inventory = list(status.get("inventory") or [])
                inventory.append(item)
                status["inventory"] = inventory
                print(f"🎁 Loot: {char.get('name')} receives {item['item']}")

            elif utype == "spell_slot_consume":
                level = update.get("level")
                if level is None:
                    print(f"⚠️ spell_slot_consume missing level for {update.get('character_name')}")
                    continue
                char = _find_char(update)
                if not char:
                    print(f"⚠️ spell_slot_consume: character {update.get('character_name')} not found in party")
                    continue
                level_key = str(level)
                status = _working_status(char)
                slots = dict(status.get("spell_slots") or {})
                if not slots:
                    print(f"⚠️ Spell slot consume skipped: {char.get('name')} has no spell_slots")
                    continue
                slot = dict(slots.get(level_key) or {})
                if not slot or "total" not in slot:
                    print(f"⚠️ Spell slot consume skipped: {char.get('name')} has no slot at level {level_key}")
                    continue
                total = int(slot.get("total", 0) or 0)
                used = int(slot.get("used", 0) or 0)
                new_used = min(total, used + 1)
                slot["used"] = new_used
                slots[level_key] = slot
                status["spell_slots"] = slots
                print(f"🔮 Spell slot consumed: {char.get('name')} Level {level_key} → {new_used}/{total}")

            elif utype == "inventory_remove":
                item_name = (update.get("item_name") or "").strip()
                if not item_name:
                    print(f"⚠️ inventory_remove missing item_name for {update.get('character_name')}")
                    continue
                char = _find_char(update)
                if not char:
                    print(f"⚠️ inventory_remove: character {update.get('character_name')} not found in party")
                    continue
                qty_to_remove = int(update.get("qty", 1) or 1)
                status = _working_status(char)
                inventory = list(status.get("inventory") or [])
                target_lower = item_name.lower()
                idx = next(
                    (i for i, it in enumerate(inventory)
                     if isinstance(it, dict) and (it.get("item") or "").lower() == target_lower),
                    None,
                )
                if idx is None:
                    print(f"⚠️ inventory_remove: '{item_name}' not in {char.get('name')}'s inventory")
                    continue
                item_obj = dict(inventory[idx])
                current_qty = int(item_obj.get("qty", 1) or 1)
                new_qty = current_qty - qty_to_remove
                if new_qty <= 0:
                    inventory.pop(idx)
                    print(f"📦 Item consumed: {char.get('name')} used {item_name} (removed from inventory)")
                else:
                    item_obj["qty"] = new_qty
                    inventory[idx] = item_obj
                    print(f"📦 Item consumed: {char.get('name')} used {item_name} (qty remaining: {new_qty})")
                status["inventory"] = inventory
        except Exception as upd_e:
            print(f"⚠️ State update failed: {upd_e}")

    # FLUSH (SAM-044): one write per character — accumulated status plus any
    # top-level columns (level/class) from a level-up.
    for cid, status in pending_status.items():
        try:
            update_data = {"status": status}
            update_data.update(pending_top.get(cid, {}))
            supabase.table("characters").update(update_data).eq("id", cid).execute()
            print(f"💾 Status flushed: {name_by_id.get(cid)} ({len(status)} keys)")
        except Exception as flush_e:
            print(f"⚠️ Status flush failed for {name_by_id.get(cid)}: {flush_e}")

    return {"status": pending_status, "top": pending_top}

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"status": "online", "system": "S.A.M."}

@app.get("/api/version")
def get_version():
    return {"version": "1.0.2", "deployed_at": "2026-02-04", "fix": "Admin Debug Tracing"}

@app.post("/api/chat")
async def chat_with_gm(request: ChatRequest, user: dict = Depends(verify_token)):
    """
    Send a message to S.A.M. and get a narrative response.
    Persists data to Supabase 'messages' table to trigger Realtime updates.
    """
    try:
        user_id = user.get('sub', 'unknown_user')
        msg_clean = request.message.strip()
        print(f"DEBUG CHAT REQUEST: '{msg_clean}' from {user_id}")

        # [PHASE 18] MULTIPLAYER ROUTING
        cid = None
        char_name = "Player"
        try:
            # 1. Player Mode: Check if User has a Character in a Campaign
            # We take the first character found (MVP). In future, frontend could send specific campaign_id.
            chars = sam_brain.supabase.table("characters").select("campaign_id, name").eq("user_id", user_id).limit(1).execute()
            if chars.data and chars.data[0].get('campaign_id'):
                 cid = chars.data[0]['campaign_id']
                 char_name = chars.data[0].get('name', 'Player')
                 print(f"DEBUG: Found Campaign ID: {cid} via Character '{char_name}' (Player Mode)")
            
            # 2. GM Mode: Fallback to Campaign Ownership
            if not cid:
                camps = sam_brain.supabase.table("campaigns").select("id").eq("gm_id", user_id).limit(1).execute()
                if camps.data:
                    cid = camps.data[0]['id']
                    print(f"DEBUG: Found Campaign ID: {cid} via GM Ownership")
                    
        except Exception as e:
            print(f"WARNING: Campaign Lookup Failed: {e}")

        try:
            user_payload = {
                "role": "user",
                "content": request.message,
                "user_id": user_id,
                "sender_id": user_id,
                "metadata": {"character_name": char_name},
            }
            if cid:
                user_payload["campaign_id"] = cid

            sam_brain.supabase.table("messages").insert(user_payload).execute()
        except Exception as db_e:
            print(f"WARNING: User insert failed: {db_e}")

        # [PHASE 11] ADMIN COMMAND INTERCEPTOR
        if msg_clean.startswith("/"):
            print(f"DEBUG: Detected Admin Command '{msg_clean}'")
            try:
                from app.services.admin import AdminService
                # Pass user_id so admin commands affect THIS user
                admin_response = AdminService.handle_command(request.message, user_id)
                print(f"DEBUG: Admin Response: {admin_response[:50]}...")

                # Persist admin response to messages so it syncs via Realtime.
                # /reset broadcasts its own CLEAR_CHAT message, so skip it here.
                if cid and not msg_clean.startswith("/reset"):
                    try:
                        sam_brain.supabase.table("messages").insert({
                            "campaign_id": cid,
                            "sender_id": None,
                            "user_id": user_id,
                            "content": admin_response,
                            "role": "assistant",
                            "visibility": "public",
                        }).execute()
                    except Exception as db_e:
                        print(f"WARNING: Admin response insert failed: {db_e}")

                return {
                    "response": admin_response,
                    "image_url": None
                }
            except Exception as e:
                import traceback
                print(f"DEBUG ADMIN ERROR: {traceback.format_exc()}")
                return {
                    "response": f"ADMIN ERROR: {str(e)}",
                    "image_url": None
                }
        
        print("DEBUG: proceeding to AI generation...")

        # Acquire campaign lock to serialize SAM responses per campaign
        lock = get_campaign_lock(cid) if cid else None
        if lock:
            await lock.acquire()
            print(f"🔒 Lock acquired for campaign {cid}")

        try:
            # Fetch recent messages from DB (INSIDE lock so second request sees updated history)
            db_history = []
            if cid:
                try:
                    db_history_response = sam_brain.supabase.table("messages") \
                        .select("role, content, metadata, sender_id") \
                        .eq("campaign_id", cid) \
                        .order("created_at", desc=True) \
                        .limit(21) \
                        .execute()
                    if db_history_response.data:
                        raw_history = list(reversed(db_history_response.data))
                        # Exclude the current user's message (already inserted above, will be passed as user_input)
                        raw_history = [
                            msg for msg in raw_history
                            if not (msg.get("content") == request.message and msg.get("sender_id") == user_id
                                    and msg == raw_history[-1])
                        ]
                        # Map DB format to generate_response format
                        db_history = [
                            {
                                "role": msg.get("role", "user"),
                                "content": msg.get("content", ""),
                                "sender_name": (msg.get("metadata") or {}).get("character_name", "") if msg.get("sender_id") else "S.A.M.",
                            }
                            for msg in raw_history
                        ]
                    print(f"📜 DB History: {len(db_history)} messages for campaign {cid}")
                except Exception as hist_e:
                    print(f"WARNING: DB history fetch failed, falling back to frontend history: {hist_e}")
                    db_history = request.history

            # Fetch campaign settings for DM style
            campaign_settings = {}
            if cid:
                try:
                    camp_settings_res = sam_brain.supabase.table("campaigns").select("settings").eq("id", cid).execute()
                    if camp_settings_res.data:
                        campaign_settings = camp_settings_res.data[0].get("settings", {})
                except Exception as e:
                    print(f"⚠️ Failed to fetch campaign settings: {e}")

            # --- Try multi-agent orchestrator first, fallback to legacy ---
            ai_response_text = ""
            image_url = None
            debug_info = None
            sam_orchestrator_failed = False

            if sam_orchestrator:
                try:
                    # Fetch actual character from DB (not the frontend text string)
                    char_ctx = {}
                    party_characters = []
                    if cid:
                        party_result = sam_brain.supabase.table("characters").select("*").eq("campaign_id", cid).execute()
                        party_characters = party_result.data if party_result and party_result.data else []
                        # Find the sender's character
                        for pc in party_characters:
                            if pc.get("user_id") == user_id:
                                char_ctx = pc
                                break
                    if not char_ctx:
                        # Fallback: try to find any character for this user
                        char_result = sam_brain.supabase.table("characters").select("*").eq("user_id", user_id).limit(1).execute()
                        char_ctx = char_result.data[0] if char_result and char_result.data else {}

                    # Build DM style
                    dm_style = sam_brain._build_dm_style(campaign_settings) if campaign_settings else ""

                    # Get combat state
                    combat_data = campaign_settings.get("combat", None) if campaign_settings else None

                    # Fetch persistent campaign memories for context
                    memories = []
                    memories_text = ""
                    if memory_service and cid:
                        try:
                            memories = await memory_service.get_memories(cid)
                            memories_text = memory_service.format_memories_for_context(memories)
                        except Exception as mem_e:
                            logger.warning(f"⚠️ Memory fetch failed: {mem_e}")

                    # Call orchestrator
                    result = sam_orchestrator.process_message(
                        message=request.message,
                        sender_name=char_name,
                        character_context=char_ctx,
                        party_characters=party_characters,
                        combat_data=combat_data,
                        campaign_context=memories_text,
                        dm_style=dm_style,
                        history=db_history if db_history else request.history,
                    )

                    ai_response_text = result["narrative"]
                    print(f"🤖 Orchestrator response ({len(ai_response_text)} chars)")

                    # Apply state updates atomically per character (SAM-044 /
                    # SAM-029): accumulate all changes, then flush one write each.
                    apply_state_updates(
                        sam_brain.supabase, party_characters,
                        result.get("state_updates", []),
                    )

                    # Update combat state
                    combat_state = result.get("combat_state")
                    if combat_state and cid:
                        try:
                            sam_brain.supabase.table("campaigns").update({
                                "settings": {**campaign_settings, "combat": combat_state}
                            }).eq("id", cid).execute()
                            if combat_state.get("active"):
                                print(f"⚔️ Combat: round {combat_state.get('round')}")
                        except Exception as combat_e:
                            print(f"⚠️ Combat state update failed: {combat_e}")

                except Exception as orch_e:
                    print(f"⚠️ Orchestrator failed, falling back to legacy SAMBrain: {orch_e}")
                    import traceback
                    traceback.print_exc()
                    sam_orchestrator_failed = True
                else:
                    sam_orchestrator_failed = False

            if not sam_orchestrator or (sam_orchestrator and sam_orchestrator_failed):
                # Legacy fallback
                print("📜 Using legacy SAMBrain")
                response = sam_brain.generate_response(
                    request.message,
                    db_history if db_history else request.history,
                    request.character_context,
                    sender_name=char_name,
                    campaign_settings=campaign_settings
                )
                ai_response_text = response.get('response', '')
                image_url = response.get('image_url')
                debug_info = response.get('debug_info')

                # Parse and strip <COMBAT> tag (legacy path)
                combat_match = re.search(r'<COMBAT>(.*?)</COMBAT>', ai_response_text, re.DOTALL)
                if combat_match and cid:
                    try:
                        combat_data = json.loads(combat_match.group(1))
                        sam_brain.supabase.table("campaigns").update({
                            "settings": {"combat": combat_data}
                        }).eq("id", cid).execute()
                        print(f"⚔️ Combat state updated (legacy): turn={combat_data.get('current_turn')}")
                    except Exception as combat_e:
                        print(f"WARNING: Failed to parse/save combat state: {combat_e}")
                    ai_response_text = re.sub(r'<COMBAT>.*?</COMBAT>', '', ai_response_text, flags=re.DOTALL).strip()

            # [PHASE 13] PERSISTENCE LAYER - SAVE AI MESSAGE
            try:
                ai_payload = {
                    "role": "assistant",
                    "content": ai_response_text,
                    "image_url": image_url,
                    "metadata": debug_info,
                    "user_id": user_id
                }
                if cid:
                    ai_payload["campaign_id"] = cid

                sam_brain.supabase.table("messages").insert(ai_payload).execute()
            except Exception as e:
                print(f"FAILED TO SAVE AI MESSAGE: {e}")

            # Schedule memory extraction as fire-and-forget background task.
            # Runs AFTER this request returns and the lock is released, so
            # it never blocks the player on the ~90s extraction call.
            if memory_service and cid and ai_response_text:
                _existing = [m["content"] for m in memories] if memories else []
                _cid = cid
                _msg = msg_clean
                _resp = ai_response_text

                async def _extract_memories_bg():
                    try:
                        count = await memory_service.extract_and_store(
                            _cid, _msg, _resp, _existing
                        )
                        if count > 0:
                            logger.debug(f"🧠 {count} new memories extracted for campaign {_cid}")
                    except Exception as e:
                        logger.warning(f"Memory extraction failed: {e}")

                asyncio.create_task(_extract_memories_bg())

            return {"response": ai_response_text, "image_url": image_url}

        finally:
            if lock and lock.locked():
                lock.release()
                print(f"🔓 Lock released for campaign {cid}")
    except Exception as e:
        import traceback
        trace = traceback.format_exc()
        print(f"CHAT ENDPOINT ERROR: {e}\n{trace}")
        # Return error as chat message so user sees it in UI
        return {
            "response": f"⚠️ **SYSTEM ERROR:** {str(e)}\n\n*(Check server logs for trace)*",
            "image_url": None
        }

@app.post("/api/roll")
async def roll_dice(request: RollRequest):
    """
    Roll dice (secure RNG) with visibility options.
    """
    try:
        # 1. Calculate Result
        result = DiceRoller.roll(request.expression)
        
        # 2. Apply Visibility Logic (Mock user ID for now)
        final_output = DiceRoller.resolve_visibility(result, request.visibility, user_id="user_123")
        
        return final_output
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
