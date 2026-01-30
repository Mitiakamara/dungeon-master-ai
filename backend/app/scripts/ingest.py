import os
import tempfile
from dotenv import load_dotenv
from supabase import create_client, Client
from langchain_community.document_loaders import PyPDFLoader, UnstructuredEPubLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore

load_dotenv()

# Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") # Must be service_role for admin tasks or anon if policies allow
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
BUCKET_NAME = "rulebooks"

import pypandoc

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials in .env")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is missing!")

# Ensure Pandoc is available
try:
    pypandoc.get_pandoc_version()
except OSError:
    print("Pandoc not found. Downloading...")
    pypandoc.download_pandoc()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def ingest_pdfs():
    print(f"--- connect to Supabase: {SUPABASE_URL} ---")
    
    # 1. List files in Bucket
    print(f"Listing files in '{BUCKET_NAME}'...")
    files = supabase.storage.from_(BUCKET_NAME).list()
    
    if not files:
        print("No files found in bucket. Did you upload the PDFs?")
        return

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004", 
        google_api_key=GOOGLE_API_KEY
    )
    
    # 2. Process each file
    for file in files:
        file_name = file['name']
        print(f"Processing: {file_name}...")
        
        # Determine extension
        ext = os.path.splitext(file_name)[1].lower()
        if ext not in [".pdf", ".epub"]:
            print(f"  Skipping unsupported file type: {ext}")
            continue

        # Download to temp file with correct extension
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            print("  Downloading...")
            data = supabase.storage.from_(BUCKET_NAME).download(file_name)
            tmp.write(data)
            tmp_path = tmp.name
        
        try:
            # Select Loader
            if ext == ".pdf":
                loader = PyPDFLoader(tmp_path)
            elif ext == ".epub":
                loader = UnstructuredEPubLoader(tmp_path)
            
            # Load
            print(f"  Loading {ext}...")
            docs = loader.load()
            print(f"  Loaded {len(docs)} documents/pages.")
            
            # Split Text
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len
            )
            chunks = text_splitter.split_documents(docs)
            print(f"  Split into {len(chunks)} chunks.")
            
            # Add Metadata
            for chunk in chunks:
                chunk.metadata["source"] = file_name
            
            # Vectorize & Store (SupabaseVectorStore)
            print("  Vectorizing and storing (this may take a moment)...")
            SupabaseVectorStore.from_documents(
                documents=chunks,
                embedding=embeddings,
                client=supabase,
                table_name="documents",
                query_name="match_documents" 
            )
            print("  Done!")
            
        except Exception as e:
            print(f"  ERROR processing {file_name}: {e}")
        finally:
            os.remove(tmp_path)

if __name__ == "__main__":
    ingest_pdfs()
