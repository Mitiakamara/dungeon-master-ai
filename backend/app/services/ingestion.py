import os
import tempfile
import shutil
from typing import List
from dotenv import load_dotenv
from supabase import create_client, Client

from langchain_community.document_loaders import PyPDFLoader, UnstructuredEPubLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore

load_dotenv()

# Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class IngestionService:
    @staticmethod
    async def ingest_campaign_module(file_bytes: bytes, filename: str, campaign_id: str) -> dict:
        """
        Ingests a campaign module (PDF/EPUB) into the 'documents' table.
        Tags it with {"campaign_id": campaign_id, "source": filename}.
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

            # 5. Add Metadata
            for chunk in chunks:
                chunk.metadata["source"] = filename
                chunk.metadata["campaign_id"] = campaign_id
                chunk.metadata["type"] = "campaign_module"

            # 6. Vectorize & Store
            embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004", 
                google_api_key=GOOGLE_API_KEY
            )
            
            SupabaseVectorStore.from_documents(
                documents=chunks,
                embedding=embeddings,
                client=supabase,
                table_name="documents",
                query_name="match_documents" 
            )
            
            return {"status": "success", "chunks": len(chunks), "file": filename}

        except Exception as e:
            print(f"Ingestion Error: {e}")
            raise e
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
