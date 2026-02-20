
import json
import os
import time
import json
import os
import time
from supabase import create_client, Client
from dotenv import load_dotenv
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv(dotenv_path="../../.env")

# Supabase Setup
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
if not url or not key:
    raise ValueError("Missing Supabase credentials")

supabase: Client = create_client(url, key)

# Embeddings Setup
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

def seed_items():
    filename = "items_phb24.json"
    if not os.path.exists(filename):
        print(f"{filename} not found.")
        return

    with open(filename, 'r', encoding='utf-8') as f:
        items = json.load(f)

    print(f"Loaded {len(items)} items from {filename}")
    
    for i, item in enumerate(items):
        try:
            name = item.get("name")
            if not name:
                continue
                
            print(f"Processing [{i+1}/{len(items)}]: {name}")
            
            # Prepare Text for Embedding
            # content = f"{name} ({item.get('type')}). {item.get('properties')}"
            props = item.get("properties", {})
            text_desc = f"{name}. {item.get('type')}. "
            if isinstance(props, dict):
                for k, v in props.items():
                    text_desc += f"{k}: {v}. "
            
            # Generate Embedding
            vector = embeddings.embed_query(text_desc)
            
            # Construct DB Record
            record = {
                "name": name,
                "type": item.get("type", "Equipment"),
                "rarity": item.get("rarity", "Common"),
                "description": text_desc,
                "properties": props,
                "embedding": vector,
                "source": "PHB 2024"
            }
            
            # Upsert (Match on Name if possible, but 'id' is primary key usually)
            # We don't have ID. We can try to match by name via select first?
            # Or just Insert and ignore duplicates?
            # Let's try upserting by name if we had a unique constraint.
            # Current schema: id is UUID. name is not unique text?
            # Let's simple check.
            
            existing = supabase.table("items").select("id").eq("name", name).execute()
            if existing.data:
                # Update
                tid = existing.data[0]['id']
                supabase.table("items").update(record).eq("id", tid).execute()
                print(f"  -> Updated {name}")
            else:
                # Insert
                supabase.table("items").insert(record).execute()
                print(f"  -> Inserted {name}")
                
            time.sleep(0.5) # Rate limit protection
            
        except Exception as e:
            print(f"Error seeding {item.get('name')}: {e}")

if __name__ == "__main__":
    seed_items()
