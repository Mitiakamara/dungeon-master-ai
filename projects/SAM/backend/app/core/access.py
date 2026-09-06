"""
Campaign access helpers — instrucción 239 (A3).

One place answers "may this user act inside this campaign?". Access holds if
at least one of these is true:
  - they own a character in it        (characters.user_id + campaign_id)
  - they are its GM                    (campaigns.gm_id)
  - they are a platform admin          (profiles.role = 'admin')

`/api/chat` gates an explicit campaign_id with can_access_campaign; the admin
`/delegate` resolver reuses is_gm_or_admin so an admin who is not the GM can
delegate too (SAM-004). Reuses the Supabase client from core.security.
"""
from app.core.security import supabase


def is_admin(user_id: str) -> bool:
    """profiles.role == 'admin' (platform-wide)."""
    if not user_id:
        return False
    try:
        res = supabase.table("profiles").select("role").eq("id", user_id).limit(1).execute()
        return bool(res.data) and res.data[0].get("role") == "admin"
    except Exception as e:
        print(f"⚠️ is_admin lookup failed for {user_id}: {e}")
        return False


def is_gm(user_id: str, campaign_id: str) -> bool:
    """campaigns.gm_id == user_id."""
    if not user_id or not campaign_id:
        return False
    try:
        res = supabase.table("campaigns").select("gm_id").eq("id", campaign_id).limit(1).execute()
        return bool(res.data) and res.data[0].get("gm_id") == user_id
    except Exception as e:
        print(f"⚠️ is_gm lookup failed for {user_id}/{campaign_id}: {e}")
        return False


def is_gm_or_admin(user_id: str, campaign_id: str) -> bool:
    return is_gm(user_id, campaign_id) or is_admin(user_id)


def has_character_in_campaign(user_id: str, campaign_id: str) -> bool:
    if not user_id or not campaign_id:
        return False
    try:
        res = (supabase.table("characters").select("id")
               .eq("user_id", user_id).eq("campaign_id", campaign_id).limit(1).execute())
        return bool(res.data)
    except Exception as e:
        print(f"⚠️ has_character_in_campaign lookup failed for {user_id}/{campaign_id}: {e}")
        return False


def can_access_campaign(user_id: str, campaign_id: str) -> bool:
    """Character in campaign, or GM, or admin — the common case checks first."""
    return has_character_in_campaign(user_id, campaign_id) or is_gm_or_admin(user_id, campaign_id)
