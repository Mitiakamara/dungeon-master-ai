from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from supabase import Client, create_client
import os
from dotenv import load_dotenv
from app.core.security import verify_token

load_dotenv()

router = APIRouter(prefix="/api/messages", tags=["messages"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Models ---
class PrivateMessageCreate(BaseModel):
    campaign_id: str
    receiver_id: str # User ID
    content: str
    subject: Optional[str] = None
    sender_character_id: Optional[str] = None
    receiver_character_id: Optional[str] = None

class PrivateMessageResponse(BaseModel):
    id: str
    campaign_id: str
    sender_id: Optional[str] = None
    receiver_id: Optional[str] = None
    sender_character_id: Optional[str] = None
    receiver_character_id: Optional[str] = None
    content: str
    subject: Optional[str] = None
    is_read: bool
    created_at: str

# --- Endpoints ---

@router.get("/", response_model=List[PrivateMessageResponse])
def get_my_messages(user: dict = Depends(verify_token)):
    user_id = user['sub']
    # Select messages where I am receiver OR sender
    # Supabase syntax for OR is a bit tricky via python client sometimes, using comma in .or_()
    # "receiver_id.eq.USER_ID,sender_id.eq.USER_ID"
    response = supabase.table("private_messages").select("*").or_(f"receiver_id.eq.{user_id},sender_id.eq.{user_id}").order("created_at", desc=True).execute()
    return response.data

@router.post("/", response_model=PrivateMessageResponse)
def send_message(msg: PrivateMessageCreate, user: dict = Depends(verify_token)):
    sender_id = user['sub']
    
    data = msg.model_dump()
    data['sender_id'] = sender_id
    
    # We rely on RLS/Backend Logic to ensure sender owns the sender_character_id if provided?
    # For now, we trust the client or checking RLS in Supabase
    
    response = supabase.table("private_messages").insert(data).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to send message")
        
    return response.data[0]

@router.patch("/{message_id}/read", response_model=PrivateMessageResponse)
def mark_message_read(message_id: str, is_read: bool = True, user: dict = Depends(verify_token)):
    user_id = user['sub']
    
    # Verify I am the receiver
    existing = supabase.table("private_messages").select("receiver_id").eq("id", message_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if existing.data[0]['receiver_id'] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this message")
        
    response = supabase.table("private_messages").update({"is_read": is_read}).eq("id", message_id).execute()
    return response.data[0]
