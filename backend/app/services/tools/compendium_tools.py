
from langchain_core.tools import tool
from supabase import Client
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Note: We need a Supabase Client instance.
# Ideally, we inject dependencies, but for tools, we might need a global or closure.
# For simplicity in this project, we create a fresh client or re-use if passed.

def get_supabase() -> Client:
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

def get_embeddings():
    return GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=os.getenv("GOOGLE_API_KEY"))

@tool
def search_spells(query: str) -> str:
    """
    Search the D&D 5e Spells Compendium for rules, damage, range, and effects.
    Use this when the user asks about a specific spell (e.g. "How much damage does Fireball do?").
    """
    try:
        supabase = get_supabase()
        embeddings = get_embeddings()
        vector = embeddings.embed_query(query)
        
        # Call the RPC function defined in Postgres
        res = supabase.rpc("match_compendium", {
            "query_embedding": vector,
            "match_threshold": 0.5,
            "match_count": 3,
            "table_name": "spells"
        }).execute()
        
        if not res.data:
            return "No matching spells found in the Compendium."
            
        # Format results
        output = "Spells Found:\n"
        for item in res.data:
            output += f"- {item['content']} (Similarity: {item['similarity']:.2f})\n"
        return output
    except Exception as e:
        return f"Error searching spells: {e}"

@tool
def search_monsters(query: str) -> str:
    """
    Search the D&D 5e Monsters Compendium for stat blocks, HP, AC, and attacks.
    Use this when the DM asks for monster stats (e.g. "What is a Goblin's AC?").
    """
    try:
        supabase = get_supabase()
        embeddings = get_embeddings()
        vector = embeddings.embed_query(query)
        
        res = supabase.rpc("match_compendium", {
            "query_embedding": vector,
            "match_threshold": 0.5,
            "match_count": 3,
            "table_name": "monsters"
        }).execute()
        
        if not res.data:
            return "No matching monsters found."
            
        output = "Monsters Found:\n"
        for item in res.data:
            output += f"- {item['content']} (Similarity: {item['similarity']:.2f})\n"
        return output
    except Exception as e:
        return f"Error searching monsters: {e}"

@tool
def search_items(query: str) -> str:
    """
    Search the D&D 5e Items Compendium for weapons, armor, and magic items.
    Use this when asking about equipment stats (e.g. "Damage of a Longsword?").
    """
    try:
        supabase = get_supabase()
        embeddings = get_embeddings()
        vector = embeddings.embed_query(query)
        
        res = supabase.rpc("match_compendium", {
            "query_embedding": vector,
            "match_threshold": 0.5,
            "match_count": 3,
            "table_name": "items"
        }).execute()
        
        if not res.data:
            return "No matching items found."
            
        output = "Items Found:\n"
        for item in res.data:
            output += f"- {item['content']} (Similarity: {item['similarity']:.2f})\n"
        return output
    except Exception as e:
        return f"Error searching items: {e}"

ALL_TOOLS = [search_spells, search_monsters, search_items]
