
import requests
import json
import os

# Configuration (from User provided data)
SUPABASE_URL = "https://jnijfysatnaxodvgbnfj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpuaWpmeXNhdG5heG9kdmdibmZqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODg2MTM4NiwiZXhwIjoyMDg0NDM3Mzg2fQ.Ix5NrueUYf7gEvjim92MJ6dnIskG_tCmio3N3up7ZMY"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def debug_request():
    print(f"--- Debugging Supabase REST API ---")
    print(f"Target: {SUPABASE_URL}/rest/v1/messages")

    # 1. READ (SELECT)
    print("\n[1] Attempting READ (SELECT * limit 1)...")
    try:
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/messages?select=*&limit=1", headers=HEADERS)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            if data:
                print("Success! Row keys found:", list(data[0].keys()))
                if "role" in data[0]:
                    print("✅ Column 'role' Exists.")
                else:
                    print("❌ Column 'role' MISSING in returned data!")
            else:
                print("Success! Table is empty (no rows), but connection worked.")
        else:
            print("Error Response:", resp.text)
    except Exception as e:
        print(f"Exception during READ: {e}")

    # 2. WRITE (INSERT)
    print("\n[2] Attempting WRITE (INSERT)...")
    payload = {
        "role": "system",
        "content": "[DEBUG] Raw REST Insert Test",
        "user_id": "00000000-0000-0000-0000-000000000000" # Dummy UUID
    }
    
    try:
        resp = requests.post(f"{SUPABASE_URL}/rest/v1/messages", headers=HEADERS, json=payload)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 201:
            print("✅ INSERT SUCCESS!")
            print("Response:", resp.json())
        else:
            print("❌ INSERT FAILED")
            print("Response:", resp.text)
            
    except Exception as e:
        print(f"Exception during WRITE: {e}")

if __name__ == "__main__":
    debug_request()
