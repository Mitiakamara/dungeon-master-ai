
import os
import json
import time
from dotenv import load_dotenv
from supabase import create_client, Client
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Load vars
load_dotenv(dotenv_path="../../.env")

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")

if not url or not key:
    raise ValueError("Missing Supabase credentials in .env")

supabase: Client = create_client(url, key)
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

def seed_items(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        items = json.load(f)
        
    print(f"Loaded {len(items)} items from {json_path}")
    
    # Process in batches
    batch_size = 20
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        rows = []
        
        # Prepare text for embedding
        texts_to_embed = [
            f"Item: {m.get('name')}. Type: {m.get('type')}. Props: {str(m.get('properties'))}. Desc: {m.get('description')}" for m in batch
        ]
        
        try:
            print(f"Generating embeddings for batch {i}...")
            # Batch embed
            vectors = embeddings.embed_documents(texts_to_embed)
            
            # MANUAL STATS OVERRIDE (Forcing quality for common items)
            OVERRIDES = {
                "Dagger": {"damage": "1d4 piercing", "properties": ["Finesse", "Light", "Thrown (20/60)"]},
                "Shortsword": {"damage": "1d6 piercing", "properties": ["Finesse", "Light"]},
                "Longsword": {"damage": "1d8 slashing", "properties": ["Versatile (1d10)"]},
                "Greatsword": {"damage": "2d6 slashing", "properties": ["Heavy", "Two-Handed"]},
                "Greataxe": {"damage": "1d12 slashing", "properties": ["Heavy", "Two-Handed"]},
                "Shortbow": {"damage": "1d6 piercing", "properties": ["Ammunition (80/320)", "Two-Handed"]},
                "Longbow": {"damage": "1d8 piercing", "properties": ["Ammunition (150/600)", "Heavy", "Two-Handed"]},
                "Leather Armor": {"ac": "11 + Dex Modifier"},
                "Chain Mail": {"ac": "16", "stealth": "Disadvantage", "str_req": 13},
                "Plate Armor": {"ac": "18", "stealth": "Disadvantage", "str_req": 15},
                "Shield": {"ac": "+2"}
            }

            for idx, item in enumerate(batch):
                name = item.get("name")
                if not name:
                    print(f"Skipping nameless item at index {idx}")
                    continue
                
                # Apply Override
                if name in OVERRIDES:
                    print(f"Applying manual stats for {name}")
                    if "properties" not in item: item["properties"] = {}
                    item["properties"].update(OVERRIDES[name])

                rows.append({
                    "name": item.get("name"),
                    "type": item.get("type"),
                    "rarity": item.get("rarity", "Common"),
                    "description": item.get("description", ""),
                    "properties": item.get("properties", {}),
                    "source": "SRD 5.1",
                    "embedding": vectors[idx]
                })
                
            # Insert into DB
            print(f"Inserting {len(rows)} rows into 'items'...")
            res = supabase.table("items").upsert(rows).execute()
            
            time.sleep(1) # Rate limit safety
            
        except Exception as e:
            print(f"Error processing batch {i}: {e}")
            
    print("Seeding Complete.")

if __name__ == "__main__":
    json_path = "items_data.json"
    if os.path.exists(json_path):
        seed_items(json_path)
    else:
        print(f"{json_path} not found. Run parse_items.py first.")
