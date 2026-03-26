from fastapi import FastAPI, HTTPException, Depends
from app.core.security import verify_token
from pydantic import BaseModel
from typing import List, Optional, Dict, Union
import asyncio
import re
import json

# Import S.A.M. Core Modules
from app.core.dice import DiceRoller, Visibility
from app.services.ai import sam_brain
from app.services.admin import AdminService
from app.routers import characters, campaigns, messages

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

# --- Data Models ---
class ChatRequest(BaseModel):
    message: str
    history: List[Union[str, Dict[str, str]]] = []
    character_context: Optional[str] = "No character selected."

class RollRequest(BaseModel):
    expression: str # e.g. "1d20+5"
    visibility: Visibility = Visibility.PUBLIC

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
        print(f"DEBUG CHAT REQUEST: '{request.message}' (cleaned: '{msg_clean}') from {user_id}")
        
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

            response = sam_brain.generate_response(
                request.message,
                db_history if db_history else request.history,
                request.character_context,
                sender_name=char_name
            )

            # Parse and strip <COMBAT> tag, update campaign settings
            ai_text = response.get('response', '')
            combat_match = re.search(r'<COMBAT>(.*?)</COMBAT>', ai_text, re.DOTALL)
            if combat_match and cid:
                try:
                    combat_data = json.loads(combat_match.group(1))
                    sam_brain.supabase.table("campaigns").update({
                        "settings": {"combat": combat_data}
                    }).eq("id", cid).execute()
                    print(f"⚔️ Combat state updated: turn={combat_data.get('current_turn')}, round={combat_data.get('round')}, active={combat_data.get('active')}")
                except Exception as combat_e:
                    print(f"WARNING: Failed to parse/save combat state: {combat_e}")
                # Strip COMBAT tag from response before saving to DB
                response['response'] = re.sub(r'<COMBAT>.*?</COMBAT>', '', ai_text, flags=re.DOTALL).strip()

            # [PHASE 13] PERSISTENCE LAYER - SAVE AI MESSAGE
            try:
                ai_payload = {
                    "role": "assistant",
                    "content": response['response'],
                    "image_url": response.get('image_url'),
                    "metadata": response.get('debug_info'),
                    "user_id": user_id
                }
                if cid:
                    ai_payload["campaign_id"] = cid

                sam_brain.supabase.table("messages").insert(ai_payload).execute()
            except Exception as e:
                print(f"FAILED TO SAVE AI MESSAGE: {e}")

            return response # Returns {"response": "...", "image_url": "..."}

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
