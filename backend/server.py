from fastapi import FastAPI, HTTPException
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
async def chat_with_gm(request: ChatRequest):
    """
    Send a message to S.A.M. and get a narrative response.
    """
    try:
        print(f"DEBUG CHAT REQUEST: {request.message}")
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
        return response # Returns {"response": "...", "image_url": "..."}
    except Exception as e:
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
