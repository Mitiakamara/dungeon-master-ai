from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

user_id = "726c6923-b63c-4981-b0fc-bb7191fd42e4"

# Schema: id, email, username, avatar_url
data = {
    "id": user_id,
    "username": "Francisco",
    "avatar_url": "https://avatars.githubusercontent.com/u/124599?v=4", # Placeholder
    "email": "francisco@example.com"
}

try:
    print(f"Inserting Profile for {user_id}...")
    response = supabase.table("profiles").insert(data).execute()
    print("Success:", response.data)
except Exception as e:
    print("Error:", e)
