
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

def seed_monsters(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        monsters = json.load(f)
        
    print(f"Loaded {len(monsters)} monsters from {json_path}")
    
    # Process in batches
    batch_size = 20
    
    for i in range(0, len(monsters), batch_size):
        batch = monsters[i:i+batch_size]
        rows = []
        
        # Prepare text for embedding
        texts_to_embed = [
            f"Monster: {m.get('name', 'Unknown')}. Type: {m.get('type')}. CR: {m.get('challenge_rating')}. Actions: {str(m.get('actions'))}" for m in batch
        ]
        
        try:
            print(f"Generating embeddings for batch {i}...")
            # Batch embed
            vectors = embeddings.embed_documents(texts_to_embed)
            
            for idx, monster in enumerate(batch):
                if not monster.get("name"):
                    print(f"Skipping nameless monster at index {idx}")
                    continue
                    
                rows.append({
                    "name": monster.get("name"),
                    "size": monster.get("size"),
                    "type": monster.get("type"),
                    "alignment": monster.get("alignment"),
                    "ac": int(monster.get("ac")) if str(monster.get("ac")).isdigit() else 0, # Simple safe cast
                    "hp": int(monster.get("hp")) if str(monster.get("hp")).isdigit() else 0,
                    "cr": float(monster.get("challenge_rating")) if str(monster.get("challenge_rating")).replace('.','',1).isdigit() else 0.0,
                    "speed": monster.get("speed"),
                    "stats": monster.get("stats", {}),
                    "skills": monster.get("skills", {}),
                    "actions": monster.get("actions", []),
                    "source": "SRD 5.1",
                    "embedding": vectors[idx]
                })
                
            # Insert into DB
            print(f"Inserting {len(rows)} rows into 'monsters'...")
            res = supabase.table("monsters").upsert(rows).execute()
            
            time.sleep(1) # Rate limit safety
            
        except Exception as e:
            print(f"Error processing batch {i}: {e}")
            
    print("Seeding Complete.")

if __name__ == "__main__":
    json_path = "monsters_data.json"
    if os.path.exists(json_path):
        seed_monsters(json_path)
    else:
        print(f"{json_path} not found. Run parse_monsters.py first.")
