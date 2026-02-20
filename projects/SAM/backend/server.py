from fastapi import FastAPI, HTTPException, Depends
from app.core.security import verify_token
from pydantic import BaseModel
from typing import List, Optional, Dict, Union

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
    character_context: Optional[str] = "No character selected." # Frontend will send summary string for now

class RollRequest(BaseModel):
    expression: str # e.g. "1d20+5"
    visibility: Visibility = Visibility.PUBLIC

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
        try:
            # 1. Player Mode: Check if User has a Character in a Campaign
            # We take the first character found (MVP). In future, frontend could send specific campaign_id.
            chars = sam_brain.supabase.table("characters").select("campaign_id").eq("user_id", user_id).limit(1).execute()
            if chars.data and chars.data[0].get('campaign_id'):
                 cid = chars.data[0]['campaign_id']
                 print(f"DEBUG: Found Campaign ID: {cid} via Character (Player Mode)")
            
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
        response = sam_brain.generate_response(
            request.message, 
            request.history,
            request.character_context
        )
        
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
