from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# Create a default campaign
data = {
    "name": "Solo Adventure",
    "description": "Your personal campaign with S.A.M.",
    "status": "active",
    "gm_id": "726c6923-b63c-4981-b0fc-bb7191fd42e4" # Francisco's User ID from logs
}

try:
    print("Inserting Campaign...")
    # NOTE: If RLS is strictly enforcing Authenticated Users, this script might fail if the SERVICE_ROLE KEY isn't used
    # But we are using the generic SUPABASE_KEY. Let's see. If it fails, I'll update it to check for SERVICE_ROLE_KEY.
    response = supabase.table("campaigns").insert(data).execute()
    print("Success:", response.data)
except Exception as e:
    print("Error:", e)
