
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def get_count(table):
    try:
        # head=True returns count only, not data
        res = supabase.table(table).select("*", count="exact", head=True).execute()
        return res.count
    except Exception as e:
        print(f"Error counting {table}: {e}")
        return 0

if __name__ == "__main__":
    spells = get_count("spells")
    monsters = get_count("monsters")
    items = get_count("items")
    
    print(f"--- DATABASE REPORT ---")
    print(f"🔮 Spells:   {spells}")
    print(f"🐉 Monsters: {monsters}")
    print(f"⚔️ Items:    {items}")
    print(f"-----------------------")
