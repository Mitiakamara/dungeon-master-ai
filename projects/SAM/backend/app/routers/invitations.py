from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from supabase import Client, create_client
import os
import secrets
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from app.core.security import verify_token
from app.core.access import is_admin

load_dotenv()

router = APIRouter(prefix="/api/invitations", tags=["invitations"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Characters for readable invite codes (no ambiguous 0/O, 1/I/L)
CODE_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def verify_admin(user_id: str) -> bool:
    """Check if user has admin role in profiles (single source: core.access)."""
    return is_admin(user_id)


def generate_code(length: int = 6) -> str:
    """Generate a short readable invite code."""
    return "".join(secrets.choice(CODE_CHARS) for _ in range(length))


# --- Models ---
class CreateInvitationRequest(BaseModel):
    campaign_id: Optional[str] = None
    max_uses: int = 1
    expires_hours: Optional[int] = 48


class ValidateCodeRequest(BaseModel):
    code: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    username: str
    invitation_code: str


# --- Endpoints ---

@router.post("/")
def create_invitation(req: CreateInvitationRequest, user: dict = Depends(verify_token)):
    """Generate a new invitation code (admin only)."""
    user_id = user["sub"]
    if not verify_admin(user_id):
        raise HTTPException(status_code=403, detail="Admin access required")

    code = generate_code()
    # Ensure uniqueness (retry once if collision)
    existing = supabase.table("invitations").select("id").eq("code", code).execute()
    if existing.data:
        code = generate_code(8)

    expires_at = None
    if req.expires_hours:
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=req.expires_hours)).isoformat()

    payload = {
        "code": code,
        "created_by": user_id,
        "max_uses": req.max_uses,
        "is_active": True,
    }
    if req.campaign_id:
        payload["campaign_id"] = req.campaign_id
    if expires_at:
        payload["expires_at"] = expires_at

    result = supabase.table("invitations").insert(payload).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create invitation")

    inv = result.data[0]
    return {"code": inv["code"], "expires_at": inv.get("expires_at"), "max_uses": inv["max_uses"]}


@router.get("/")
def list_invitations(user: dict = Depends(verify_token)):
    """List all invitations (admin only)."""
    user_id = user["sub"]
    if not verify_admin(user_id):
        raise HTTPException(status_code=403, detail="Admin access required")

    result = supabase.table("invitations").select("*").order("created_at", desc=True).execute()
    return result.data or []


@router.delete("/{invitation_id}")
def deactivate_invitation(invitation_id: str, user: dict = Depends(verify_token)):
    """Deactivate an invitation (admin only). Does not delete from DB."""
    user_id = user["sub"]
    if not verify_admin(user_id):
        raise HTTPException(status_code=403, detail="Admin access required")

    result = supabase.table("invitations").update({"is_active": False}).eq("id", invitation_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Invitation not found")

    return {"message": "Invitation deactivated"}


@router.post("/validate")
def validate_code(req: ValidateCodeRequest):
    """Validate an invitation code (public, no auth required)."""
    code = req.code.strip().upper()

    result = supabase.table("invitations").select("*").eq("code", code).eq("is_active", True).execute()
    if not result.data:
        return {"valid": False, "reason": "not_found"}

    inv = result.data[0]

    # Check expiration
    if inv.get("expires_at"):
        expires = datetime.fromisoformat(inv["expires_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expires:
            return {"valid": False, "reason": "expired"}

    # Check uses
    if inv["current_uses"] >= inv["max_uses"]:
        return {"valid": False, "reason": "used"}

    return {"valid": True, "campaign_id": inv.get("campaign_id")}


@router.post("/register")
def register_with_code(req: RegisterRequest):
    """Register a new user with an invitation code (public, no auth required)."""
    code = req.invitation_code.strip().upper()

    # 1. Validate code
    inv_result = supabase.table("invitations").select("*").eq("code", code).eq("is_active", True).execute()
    if not inv_result.data:
        raise HTTPException(status_code=400, detail="Invalid invitation code")

    inv = inv_result.data[0]

    if inv.get("expires_at"):
        expires = datetime.fromisoformat(inv["expires_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expires:
            raise HTTPException(status_code=400, detail="Invitation code has expired")

    if inv["current_uses"] >= inv["max_uses"]:
        raise HTTPException(status_code=400, detail="Invitation code has been fully used")

    # 2. Create user in Supabase Auth (service role)
    try:
        auth_response = supabase.auth.admin.create_user({
            "email": req.email,
            "password": req.password,
            "email_confirm": True,
            "user_metadata": {"username": req.username},
        })

        if not auth_response.user:
            raise HTTPException(status_code=500, detail="Failed to create user account")

        new_user_id = auth_response.user.id
    except Exception as e:
        error_msg = str(e)
        if "already been registered" in error_msg or "already exists" in error_msg:
            raise HTTPException(status_code=409, detail="Email already registered")
        raise HTTPException(status_code=500, detail=f"Registration failed: {error_msg}")

    # 3. Increment uses and deactivate if maxed out
    new_uses = inv["current_uses"] + 1
    update_data = {"current_uses": new_uses}
    if new_uses >= inv["max_uses"]:
        update_data["is_active"] = False

    supabase.table("invitations").update(update_data).eq("id", inv["id"]).execute()

    return {"message": "Account created", "user_id": str(new_user_id)}
