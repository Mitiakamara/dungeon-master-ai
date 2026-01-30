import os
import fitz  # PyMuPDF
import json
import time
import ast
import base64
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

# Load env from parent directory
load_dotenv(dotenv_path="../../.env") # Adjust if running from scripts dir

# Initialize Gemini
# Use 1.5 Flash for speed/cost.
llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0)

def process_file_in_chunks(pdf_path, output_path):
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    all_spells = []
    
    # Process in batches of 3 pages (Images are token heavy!)
    batch_size = 3
    
    # Full Ingestion: Start from page 10 (skip TOC)
    start_page = 10
    
    print(f"Starting FULL VISUAL ingestion from page {start_page} to {total_pages}...")
    
    for i in range(start_page, total_pages, batch_size):
        end_page = min(i + batch_size, total_pages)
        
        # Prepare content parts
        message_parts = [
            {
                "type": "text", 
                "text": """
                You are an expert D&D 5e Rules Lawyer.
                Extract detailed spell information from these page images into a structured JSON list.
                
                Each spell object MUST have:
                - name (string)
                - level (int) (Use 0 for Cantrip)
                - school (string)
                - casting_time (string)
                - range (string)
                - components (string)
                - duration (string)
                - description (string) - Include the FULL text.
                - classes (list of strings)
                
                IMPORTANT:
                - Return ONLY raw JSON list.
                - If no spells found, return empty list [].
                """
            }
        ]
        
        print(f"Rendering pages {i} to {end_page} as images...")
        for j in range(i, end_page):
            # Render page to image (Zoom 2x for OCR quality)
            pix = doc[j].get_pixmap(matrix=fitz.Matrix(2, 2))
            img_data = pix.tobytes("jpeg")
            b64_str = base64.b64encode(img_data).decode("utf-8")
            
            message_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64_str}"}
            })
            
        print("Sending to Gemini Vision...")
        
        try:
            msg = HumanMessage(content=message_parts)
            res = llm.invoke([msg])
            content = res.content
            
            # Helper for list output
            if isinstance(content, list):
                content = "".join([str(c) for c in content])
            
            # Clean md code blocks
            content = content.replace("```json", "").replace("```", "").strip()
            
            if not content:
                print("Empty response.")
                continue

            try:
                batch_data = json.loads(content)
            except json.JSONDecodeError:
                # Fallback
                try:
                    print("JSON load failed, trying ast.literal_eval...")
                    batch_data = ast.literal_eval(content)
                except Exception:
                    print(f"FAILED RAW CONTENT: {content[:200]}...")
                    continue
            
            if isinstance(batch_data, list):
                all_spells.extend(batch_data)
                print(f"Extracted {len(batch_data)} spells from batch.")
            else:
                print("AI returned valid JSON but not a list.")
            
            # Anti-rate limit sleep (Images take more quota)
            time.sleep(2) 
            
        except Exception as e:
            print(f"Error parsing batch {i}-{end_page}: {e}")
            
    # Save Final
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_spells, f, indent=2, ensure_ascii=False)
    print(f"Compeleted! Saved {len(all_spells)} spells to {output_path}")

if __name__ == "__main__":
    # Absolute path to resources
    base_dir = r"C:\Users\FranciscoGetFinanced\Dropbox\Antigravity\dungeon-master-ai"
    pdf_path = os.path.join(base_dir, "resources", "spells.pdf")
    output_path = "spells_data.json"
    
    print(f"Looking for PDF at: {pdf_path}")
    
    if os.path.exists(pdf_path):
        process_file_in_chunks(pdf_path, output_path)
    else:
        print(f"File {pdf_path} not found.")
