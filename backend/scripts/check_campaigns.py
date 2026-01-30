from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

print("Checking Campaigns...")
response = supabase.table("campaigns").select("*").execute()
print(response.data)

if not response.data:
    print("Creating Default Campaign...")
    # Assuming user_id is needed, but for now we just want a placeholder if possible
    # We might need a real user_id from the auth system if RLS enforces it.
    # For this check script, we just want to see if FOREIGN KEY constraint is hitting.
