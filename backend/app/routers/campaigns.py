from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from supabase import Client, create_client
import os
from dotenv import load_dotenv
from app.core.security import verify_token
from app.services.ingestion import IngestionService

load_dotenv()

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

# Supabase Auth & Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Models ---
class CampaignBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "active"
    settings: Dict[str, Any] = {} # Phase 9: Tuning (difficulty, tone)
    rules: Optional[str] = None # text summary of rules context

class CampaignCreate(CampaignBase):
    pass

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    rules: Optional[str] = None

class CampaignResponse(CampaignBase):
    id: str
    gm_id: str
    created_at: str

# --- Endpoints ---

@router.get("/", response_model=List[CampaignResponse])
def list_campaigns(user: dict = Depends(verify_token)):
    # RLS Policies on Supabase will filter viewing rights
    # Usually we want "Campaigns I am GM of" or "Campaigns I am Player in"
    # But for now, lists all visible campaigns
    response = supabase.table("campaigns").select("*").execute()
    return response.data

@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: str, user: dict = Depends(verify_token)):
    response = supabase.table("campaigns").select("*").eq("id", campaign_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return response.data[0]

@router.post("/", response_model=CampaignResponse)
def create_campaign(campaign: CampaignCreate, user: dict = Depends(verify_token)):
    gm_id = user['sub']
    
    data = campaign.model_dump()
    data['gm_id'] = gm_id
    
    response = supabase.table("campaigns").insert(data).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to create campaign")
    return response.data[0]

@router.patch("/{campaign_id}", response_model=CampaignResponse)
def update_campaign(campaign_id: str, updates: CampaignUpdate, user: dict = Depends(verify_token)):
    # Verify GM ownership
    existing = supabase.table("campaigns").select("gm_id, settings").eq("id", campaign_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    current_record = existing.data[0]
    if current_record['gm_id'] != user['sub']:
        raise HTTPException(status_code=403, detail="Only the GM can update campaign settings")

    data = updates.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No updates provided")

    # Deep Merge Settings if present
    if "settings" in data:
        current_settings = current_record.get("settings") or {}
        merged_settings = {**current_settings, **data["settings"]}
        data["settings"] = merged_settings

    response = supabase.table("campaigns").update(data).eq("id", campaign_id).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Update failed")
    return response.data[0]

@router.delete("/{campaign_id}")
def delete_campaign(campaign_id: str, user: dict = Depends(verify_token)):
    # Verify GM ownership
    existing = supabase.table("campaigns").select("gm_id").eq("id", campaign_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if existing.data[0]['gm_id'] != user['sub']:
        raise HTTPException(status_code=403, detail="Only the GM can delete the campaign")

    response = supabase.table("campaigns").delete().eq("id", campaign_id).execute()
    return {"message": "Campaign deleted successfully"}

@router.post("/{campaign_id}/modules")
async def upload_campaign_module(
    campaign_id: str, 
    file: UploadFile = File(...), 
    user: dict = Depends(verify_token)
):
    # Verify GM ownership
    existing = supabase.table("campaigns").select("gm_id").eq("id", campaign_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if existing.data[0]['gm_id'] != user['sub']:
        raise HTTPException(status_code=403, detail="Only the GM can upload modules")

    try:
        contents = await file.read()
        result = await IngestionService.ingest_campaign_module(contents, file.filename, campaign_id)
        return result
    except Exception as e:
        print(f"Upload Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
