import os
import json
import tempfile
from typing import List
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai

from langchain_community.document_loaders import PyPDFLoader, UnstructuredEPubLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

# Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)

EMBED_MODEL = "models/gemini-embedding-001"
EMBED_DIMS = 768
EMBED_BATCH_SIZE = 100  # Max texts per embed_content call

class IngestionService:
    @staticmethod
    async def ingest_campaign_module(file_bytes: bytes, filename: str, campaign_id: str) -> dict:
        """
        Ingests a campaign module (PDF/EPUB) into the 'documents' table.
        Uses Google's native SDK for embeddings (768 dims) and direct Supabase inserts.
        """

        # 1. Determine Extension
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".pdf", ".epub"]:
            raise ValueError(f"Unsupported file type: {ext}. Only .pdf and .epub supported.")

        # 2. Save to Temp File
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            # 3. Load Documents
            print(f"Loading {filename}...")
            if ext == ".pdf":
                loader = PyPDFLoader(tmp_path)
            elif ext == ".epub":
                loader = UnstructuredEPubLoader(tmp_path)

            docs = loader.load()

            if not docs:
                return {"status": "empty", "chunks": 0}

            # 4. Split Text
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len
            )
            chunks = text_splitter.split_documents(docs)
            print(f"Split {filename} into {len(chunks)} chunks.")

            # 5. Build texts and metadata
            texts = [chunk.page_content for chunk in chunks]
            metadata = {
                "source": filename,
                "campaign_id": campaign_id,
                "type": "campaign_module"
            }

            # 6. Embed in batches using native Google SDK
            all_embeddings = []
            for i in range(0, len(texts), EMBED_BATCH_SIZE):
                batch = texts[i:i + EMBED_BATCH_SIZE]
                response = genai.embed_content(
                    model=EMBED_MODEL,
                    content=batch,
                    output_dimensionality=EMBED_DIMS,
                    task_type="retrieval_document",
                )
                all_embeddings.extend(response["embedding"])
                print(f"Embedded batch {i // EMBED_BATCH_SIZE + 1} ({len(batch)} chunks)")

            # 7. Insert into Supabase in batches
            rows = []
            for idx, text in enumerate(texts):
                rows.append({
                    "content": text,
                    "metadata": json.dumps(metadata),
                    "embedding": all_embeddings[idx],
                })

            for i in range(0, len(rows), EMBED_BATCH_SIZE):
                batch = rows[i:i + EMBED_BATCH_SIZE]
                supabase.table("documents").insert(batch).execute()
                print(f"Inserted batch {i // EMBED_BATCH_SIZE + 1} ({len(batch)} rows)")

            return {"status": "success", "chunks": len(chunks), "file": filename}

        except Exception as e:
            print(f"Ingestion Error: {e}")
            raise e
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
