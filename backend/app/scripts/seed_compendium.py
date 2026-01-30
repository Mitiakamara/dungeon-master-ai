
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

def seed_spells(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        spells = json.load(f)
        
    print(f"Loaded {len(spells)} spells from {json_path}")
    
    # Process in batches
    batch_size = 20
    
    for i in range(0, len(spells), batch_size):
        batch = spells[i:i+batch_size]
        rows = []
        
        # Prepare text for embedding
        texts_to_embed = [
            f"{s['name']}: {s['description']}" for s in batch
        ]
        
        try:
            print(f"Generating embeddings for batch {i}...")
            # Batch embed
            vectors = embeddings.embed_documents(texts_to_embed)
            
            for idx, spell in enumerate(batch):
                rows.append({
                    "name": spell.get("name"),
                    "level": spell.get("level", 0),
                    "school": spell.get("school", "Unknown"),
                    "casting_time": spell.get("casting_time", "Unknown"),
                    "range": spell.get("range", "Unknown"),
                    "components": spell.get("components", "Unknown"),
                    "duration": spell.get("duration", "Unknown"),
                    "description": spell.get("description", ""),
                    "classes": spell.get("classes", []),
                    "source": "System (spells.pdf)",
                    "embedding": vectors[idx]
                })
                
            # Insert into DB
            print(f"Inserting {len(rows)} rows into 'spells'...")
            res = supabase.table("spells").upsert(rows).execute()
            # print(res)
            
        except Exception as e:
            print(f"Error processing batch {i}: {e}")
            
    print("Seeding Complete.")

if __name__ == "__main__":
    json_path = "spells_data.json"
    if os.path.exists(json_path):
        seed_spells(json_path)
    else:
        print(f"{json_path} not found. Run parse_spells.py first.")
