"""
Knowledge Agent — RAG service for campaign modules and D&D compendium.
Reuses existing embedding + Supabase vector search infrastructure.
"""

from google import genai
from google.genai import types


class KnowledgeService:
    """Provides RAG lookups for campaign context and D&D rules."""

    def __init__(self, supabase_client, genai_client):
        """
        supabase_client: Supabase client instance
        genai_client: google.genai.Client instance for embeddings
        """
        self.supabase = supabase_client
        self.genai_client = genai_client

    def _embed(self, text: str) -> list:
        """Generate a 768d embedding vector for a query."""
        response = self.genai_client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config=types.EmbedContentConfig(
                output_dimensionality=768,
                task_type="RETRIEVAL_QUERY",
            ),
        )
        return response.embeddings[0].values

    def search_campaign_context(self, query: str, top_k: int = 3, threshold: float = 0.5) -> str:
        """Search campaign module documents via vector similarity."""
        try:
            vector = self._embed(query)
            response = self.supabase.rpc(
                "match_documents",
                {
                    "query_embedding": vector,
                    "match_threshold": threshold,
                    "match_count": top_k,
                }
            ).execute()

            docs = response.data if response.data else []
            if not docs:
                return ""
            return "\n\n".join([d.get("content", "") for d in docs])
        except Exception as e:
            print(f"⚠️ RAG campaign search error: {e}")
            return ""

    def search_spell(self, query: str) -> str:
        """Search D&D 5e spell compendium."""
        return self._search_compendium(query, "spells", "Spells")

    def search_monster(self, query: str) -> str:
        """Search D&D 5e monster compendium."""
        return self._search_compendium(query, "monsters", "Monsters")

    def search_item(self, query: str) -> str:
        """Search D&D 5e item compendium."""
        return self._search_compendium(query, "items", "Items")

    def search(self, query: str) -> str:
        """General search — campaign context first, then compendium."""
        result = self.search_campaign_context(query)
        if result:
            return result
        return ""

    def _search_compendium(self, query: str, table_name: str, label: str) -> str:
        """Search a compendium table via vector similarity."""
        try:
            vector = self._embed(query)
            res = self.supabase.rpc(
                "match_compendium",
                {
                    "query_embedding": vector,
                    "match_threshold": 0.5,
                    "match_count": 3,
                    "table_name": table_name,
                }
            ).execute()

            if not res.data:
                return f"No matching {label.lower()} found."

            output = f"{label} Found:\n"
            for item in res.data:
                output += f"- {item['content']} (Similarity: {item['similarity']:.2f})\n"
            return output
        except Exception as e:
            return f"Error searching {label.lower()}: {e}"
