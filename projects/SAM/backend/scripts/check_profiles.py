from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

try:
    print("Checking Profiles...")
    response = supabase.table("profiles").select("*").execute()
    print(response.data)
except Exception as e:
    print("Error:", e)
