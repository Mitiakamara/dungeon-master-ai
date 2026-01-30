from fastapi import FastAPI, HTTPException, Depends
from app.core.security import verify_token
from pydantic import BaseModel
from typing import List, Optional

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
    history: List[str] = []
    character_context: Optional[str] = "No character selected." # Frontend will send summary string for now

class RollRequest(BaseModel):
    expression: str # e.g. "1d20+5"
    visibility: Visibility = Visibility.PUBLIC

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"status": "online", "system": "S.A.M."}

@app.post("/api/chat")
async def chat_with_gm(request: ChatRequest, user: dict = Depends(verify_token)):
    """
    Send a message to S.A.M. and get a narrative response.
    Persists data to Supabase 'messages' table to trigger Realtime updates.
    """
    try:
        user_id = user['sub']
        print(f"DEBUG CHAT REQUEST: {request.message} from {user_id}")
        
        # [PHASE 13] PERSISTENCE LAYER - SAVE USER MESSAGE
        # We need a campaign_id. For now, we'll try to find the user's most recent campaign or use a NULL if allowed.
        # Ideally, Frontend should pass campaign_id. We'll default to NULL/None and hope schema allows it 
        # or we update schema later.
        
        try:
            sam_brain.supabase.table("messages").insert({
                "role": "user",
                "content": request.message,
                "user_id": user_id,
                # "campaign_id": ... # Pending Frontend update
            }).execute()
        except Exception as db_e:
            print(f"WARNING: Basic insert failed (likely FK constraint). Attempting to find campaign...")
            # Fallback: Find first campaign for user
            camps = sam_brain.supabase.table("campaigns").select("id").eq("user_id", user_id).limit(1).execute()
            if camps.data:
                cid = camps.data[0]['id']
                sam_brain.supabase.table("messages").insert({
                    "role": "user",
                    "content": request.message,
                    "user_id": user_id,
                    "campaign_id": cid
                }).execute()
            else:
                 print(f"ERROR: No campaign found for user. Message might not be saved.")

        # [PHASE 11] ADMIN COMMAND INTERCEPTOR
        if request.message.strip().startswith("/"):
            try:
                import sys
                print(f"DEBUG: sys.path: {sys.path}")
                from app.services.admin import AdminService
                print(f"DEBUG: AdminService imported: {AdminService}")
                admin_response = AdminService.handle_command(request.message)
                return {
                    "response": admin_response,
                    "image_url": None
                }
            except Exception as e:
                import traceback
                print(f"DEBUG IMPORT ERROR: {traceback.format_exc()}")
                return {
                    "response": f"ADMIN ERROR: {str(e)}",
                    "image_url": None
                }

        response = sam_brain.generate_response(
            request.message, 
            request.history,
            request.character_context
        )
        
        # [PHASE 13] PERSISTENCE LAYER - SAVE AI MESSAGE
        try:
            # Re-fetch campaign ID if we found one earlier, or try insert null
            # For speed, we just try insert again or use the same logic
            # Simplified: Just insert role=assistant
             sam_brain.supabase.table("messages").insert({
                "role": "assistant",
                "content": response['response'],
                "image_url": response.get('image_url'),
                "metadata": response.get('debug_info'),
                # "campaign_id": ... 
            }).execute()
        except Exception as e:
             # Retry with campaign lookup if needed (duplicate logic, but safer)
             # In production we'd refactor this into a helper "save_message"
             pass

        return response # Returns {"response": "...", "image_url": "..."}
    except Exception as e:
        print(f"CHAT ENDPOINT ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
