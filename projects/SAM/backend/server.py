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

                    # Apply state updates (HP, XP, inventory)
                    for update in result.get("state_updates", []):
                        try:
                            if update.get("type") == "player_hp":
                                for char in party_characters:
                                    if char.get("name") == update.get("character_name"):
                                        merged = {**char.get("status", {}), "hp_current": update["new_hp"]}
                                        sam_brain.supabase.table("characters").update({"status": merged}).eq("id", char["id"]).execute()
                                        print(f"💚 HP updated: {update['character_name']} → {update['new_hp']}")
                                        break

                            elif update.get("type") == "xp_update":
                                for char in party_characters:
                                    if char.get("name") == update.get("character_name"):
                                        merged = {**char.get("status", {}), "xp": update["new_xp"]}
                                        update_data = {"status": merged}
                                        if update.get("leveled_up"):
                                            update_data["level"] = update["new_level"]
                                            print(f"🎉 LEVEL UP! {update['character_name']} → Level {update['new_level']}")
                                        sam_brain.supabase.table("characters").update(update_data).eq("id", char["id"]).execute()
                                        break

                            elif update.get("type") == "spell_slot_consume":
                                target_name = update.get("character_name")
                                level = update.get("level")
                                if level is None:
                                    print(f"⚠️ spell_slot_consume missing level for {target_name}")
                                    continue
                                level_key = str(level)
                                applied = False
                                for char in party_characters:
                                    if char.get("name") != target_name:
                                        continue
                                    status = dict(char.get("status") or {})
                                    slots = dict(status.get("spell_slots") or {})
                                    if not slots:
                                        print(f"⚠️ Spell slot consume skipped: {target_name} has no spell_slots")
                                        break
                                    slot = dict(slots.get(level_key) or {})
                                    if not slot or "total" not in slot:
                                        print(f"⚠️ Spell slot consume skipped: {target_name} has no slot at level {level_key}")
                                        break
                                    total = int(slot.get("total", 0) or 0)
                                    used = int(slot.get("used", 0) or 0)
                                    new_used = min(total, used + 1)
                                    slot["used"] = new_used
                                    slots[level_key] = slot
                                    status["spell_slots"] = slots
                                    sam_brain.supabase.table("characters").update({"status": status}).eq("id", char["id"]).execute()
                                    print(f"🔮 Spell slot consumed: {target_name} Level {level_key} → {new_used}/{total}")
                                    applied = True
                                    break
                                if not applied:
                                    print(f"⚠️ Spell slot consume: character {target_name} not found in party")

                            elif update.get("type") == "inventory_remove":
                                target_name = update.get("character_name")
                                item_name = (update.get("item_name") or "").strip()
                                qty_to_remove = int(update.get("qty", 1) or 1)
                                if not item_name:
                                    print(f"⚠️ inventory_remove missing item_name for {target_name}")
                                    continue
                                applied = False
                                for char in party_characters:
                                    if char.get("name") != target_name:
                                        continue
                                    status = dict(char.get("status") or {})
                                    inventory = list(status.get("inventory") or [])
                                    target_lower = item_name.lower()
                                    idx = next(
                                        (i for i, it in enumerate(inventory)
                                         if isinstance(it, dict) and (it.get("item") or "").lower() == target_lower),
                                        None,
                                    )
                                    if idx is None:
                                        print(f"⚠️ inventory_remove: '{item_name}' not in {target_name}'s inventory")
                                        break
                                    item_obj = dict(inventory[idx])
                                    current_qty = int(item_obj.get("qty", 1) or 1)
                                    new_qty = current_qty - qty_to_remove
                                    if new_qty <= 0:
                                        inventory.pop(idx)
                                        print(f"📦 Item consumed: {target_name} used {item_name} (removed from inventory)")
                                    else:
                                        item_obj["qty"] = new_qty
                                        inventory[idx] = item_obj
                                        print(f"📦 Item consumed: {target_name} used {item_name} (qty remaining: {new_qty})")
                                    status["inventory"] = inventory
                                    sam_brain.supabase.table("characters").update({"status": status}).eq("id", char["id"]).execute()
                                    applied = True
                                    break
                                if not applied:
                                    print(f"⚠️ inventory_remove: character {target_name} not found in party")
                        except Exception as upd_e:
                            print(f"⚠️ State update failed: {upd_e}")

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
