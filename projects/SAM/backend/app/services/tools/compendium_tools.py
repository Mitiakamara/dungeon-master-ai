
from langchain_core.tools import tool
from supabase import Client
import os
from google import genai
from google.genai import types

# Note: We need a Supabase Client instance.
# Ideally, we inject dependencies, but for tools, we might need a global or closure.
# For simplicity in this project, we create a fresh client or re-use if passed.

def get_supabase() -> Client:
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

def embed_query(text: str) -> list:
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=768,
            task_type="RETRIEVAL_QUERY",
        ),
    )
    return response.embeddings[0].values

@tool
def search_spells(query: str) -> str:
    """
    Search the D&D 5e Spells Compendium for rules, damage, range, and effects.
    Use this when the user asks about a specific spell (e.g. "How much damage does Fireball do?").
    """
    try:
        supabase = get_supabase()
        vector = embed_query(query)

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
        vector = embed_query(query)

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
        vector = embed_query(query)

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
