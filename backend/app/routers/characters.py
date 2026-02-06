from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from supabase import Client, create_client
import os
from dotenv import load_dotenv
from app.core.security import verify_token

load_dotenv()

router = APIRouter(prefix="/api/characters", tags=["characters"])

# Supabase Auth & Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Models ---

load_dotenv()

router = APIRouter(prefix="/api/characters", tags=["characters"])

# Supabase Auth & Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Models ---
class ActiveEffect(BaseModel):
    name: str
    duration: Optional[int] = None # Turns
    description: str

class CharacterBase(BaseModel):
    name: str
    race: Optional[str] = None
    class_: Optional[str] = Field(None, alias="class")
    level: int = 1
    stats: Dict[str, Any] = {} # {"str": 10, "dex": 12...}
    active_effects: List[Dict[str, Any]] = [] # [{"name": "Bless", ...}]
    status: Dict[str, Any] = {} # HP, slots, inventory, etc.
    bio: Optional[str] = None
    image_url: Optional[str] = None

class CharacterCreate(CharacterBase):
    user_id: str
    campaign_id: str

class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    level: Optional[int] = None
    stats: Optional[Dict[str, Any]] = None
    active_effects: Optional[List[Dict[str, Any]]] = None
    status: Optional[Dict[str, Any]] = None # HP, slots, etc.
    bio: Optional[str] = None
    image_url: Optional[str] = None

class CharacterResponse(CharacterBase):
    id: str
    user_id: str
    campaign_id: str
    status: Dict[str, Any] = {}
    
    class Config:
        populate_by_name = True

# --- Endpoints ---
@router.post("/import", response_model=Dict[str, Any])
async def import_character_pdf(file: UploadFile = File(...), user: dict = Depends(verify_token)):
    """
    Uploads a PDF, uses Gemini to parse it, and returns the Character JSON.
    Does NOT save to DB yet (Client must confirm).
    """
    from app.services.ai import sam_brain
    
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        contents = await file.read()
        character_data = sam_brain.parse_character_pdf(contents)
        return character_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=CharacterResponse)
def create_character(char: CharacterCreate, user: dict = Depends(verify_token)):
    try:
        print(f"DEBUG: Create Character Payload: {char.model_dump()}")

        # 1. Enforce user_id
        user_id = user['sub']
        if char.user_id and char.user_id != user_id:
            raise HTTPException(status_code=403, detail="Cannot create character for another user")
        char.user_id = user_id 

        # 2. Validate/Fix Campaign ID
        # The frontend sends a hardcoded ID which might not exist in this DB instance.
        # We check if it exists. If not, we assign to the first available campaign.
        
        camp_check = supabase.table("campaigns").select("id").eq("id", char.campaign_id).execute()
        if not camp_check.data:
            print(f"WARNING: Campaign {char.campaign_id} not found. Fallback to default...")
            
            # Find ANY campaign
            any_camp = supabase.table("campaigns").select("id").limit(1).execute()
            if any_camp.data:
                new_cid = any_camp.data[0]['id']
                print(f"DEBUG: Reassigning to existing campaign: {new_cid}")
                char.campaign_id = new_cid
            else:
                # No campaigns exist? Create one for the system.
                print("DEBUG: No campaigns found! Creating 'Default Campaign'...")
                new_camp_res = supabase.table("campaigns").insert({
                    "name": "The Lost Mines (Default)",
                    "gm_id": user_id, 
                    "status": "active"
                }).execute()
                if new_camp_res.data:
                     char.campaign_id = new_camp_res.data[0]['id']

        # 3. Insert Character
        data = char.model_dump(by_alias=True)
        response = supabase.table("characters").insert(data).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create character (DB returned no data)")
            
        return response.data[0]

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR Creating Character: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{character_id}", response_model=CharacterResponse)
def get_character(character_id: str, user: dict = Depends(verify_token)):
    # Optional: Check if character belongs to user or is public
    response = supabase.table("characters").select("*").eq("id", character_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Character not found")
    return response.data[0]

@router.get("/user/me", response_model=List[CharacterResponse])
def list_my_characters(user: dict = Depends(verify_token)):
    user_id = user['sub']
    response = supabase.table("characters").select("*").eq("user_id", user_id).execute()
    return response.data

# Deprecated/Admin only? Keeping for now but protected
@router.get("/user/{user_id}", response_model=List[CharacterResponse])
def list_user_characters(user_id: str, user: dict = Depends(verify_token)):
    # Verify requesting user is the target user
    if user['sub'] != user_id:
         raise HTTPException(status_code=403, detail="Access denied")
    response = supabase.table("characters").select("*").eq("user_id", user_id).execute()
    return response.data

@router.patch("/{character_id}", response_model=CharacterResponse)
def update_character(character_id: str, updates: CharacterUpdate, user: dict = Depends(verify_token)):
    # Verify ownership before update
    print(f"DEBUG: PATCH /characters/{character_id} called by {user['sub']}")
    print(f"DEBUG: Payload: {updates.model_dump(exclude_unset=True)}")

    # Fetch existing first (Get status for merging)
    existing = supabase.table("characters").select("user_id, status").eq("id", character_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Character not found")
    
    current_record = existing.data[0]
    if current_record['user_id'] != user['sub']:
        raise HTTPException(status_code=403, detail="Not authorized to update this character")

    data = updates.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No updates provided")
        
    # Deep Merge 'status' if present (Prevents wiping other status fields like hp_max)
    if "status" in data:
        current_status = current_record.get("status") or {}
        print(f"DEBUG: Current Status: {current_status}")
        # Simple top-level merge is sufficient for now (hp_current overwrites old, others kept)
        merged_status = {**current_status, **data["status"]}
        data["status"] = merged_status
        print(f"DEBUG: Merged Status: {merged_status}")
        
    response = supabase.table("characters").update(data).eq("id", character_id).execute()
    if not response.data:
        print(f"DEBUG: Update Failed! Response: {response}")
        raise HTTPException(status_code=404, detail="Update failed")
    
    print(f"DEBUG: Update Success. New Data: {response.data[0]}")
    return response.data[0]

@router.delete("/{character_id}")
def delete_character(character_id: str, user: dict = Depends(verify_token)):
    # Verify ownership before delete
    existing = supabase.table("characters").select("user_id").eq("id", character_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Character not found")
    
    if existing.data[0]['user_id'] != user['sub']:
        raise HTTPException(status_code=403, detail="Not authorized to delete this character")

    response = supabase.table("characters").delete().eq("id", character_id).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Delete failed")
    
    return {"message": "Character deleted successfully"}
