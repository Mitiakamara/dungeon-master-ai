
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
load_dotenv(dotenv_path="../../.env")

# Initialize Gemini
llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0)

def process_file_in_chunks(pdf_path, output_path):
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    all_monsters = []
    
    # Process in batches of 3 pages (Images are token heavy!)
    batch_size = 3
    
    # SRD usually has monsters later. Let's guess start page or process all.
    # Monsters usually start around page 250+ in full SRD?
    # Actually, let's scan a range or ask user.
    # For now, let's scan pages 100-110 as a test, or just start from 0 if uncertain.
    # The file name is `SRD_CC_v5.2.1.pdf` (Creative Commons).
    # This document puts Monsters in a specific section.
    # Let's assume start_page = 0 for now but print progress.
    # User can cancel if slow.
    # SRD Monsters Section: approx 254 to 398
    start_page = 254
    end_scan = 398
    
    # DEBUG LIMIT REMOVED
    # limit_pages = 6
    # total_pages_to_process = min(total_pages, start_page + limit_pages)
    
    print(f"Starting FULL MONSTER ingestion from page {start_page} to {end_scan}...")
    
    for i in range(start_page, end_scan, batch_size):
        end_page = min(i + batch_size, total_pages)
        
        # Prepare content parts
        message_parts = [
            {
                "type": "text", 
                "text": """
                You are an expert D&D 5e Rules Lawyer.
                Extract detailed MONSTER stat blocks from these page images into a structured JSON list.
                
                Each monster object MUST have:
                - name (string)
                - size (string)
                - type (string) (e.g. "Humanoid", "Dragon")
                - alignment (string)
                - ac (string or int)
                - hp (string or int)
                - speed (string)
                - stats (object) {str, dex, con, int, wis, cha}
                - skills (object) {perception, stealth, etc}
                - challenge_rating (string or float)
                - actions (list of objects) {name, desc}
                
                IMPORTANT:
                - Return ONLY raw JSON list.
                - If no monsters found on these pages, return empty list [].
                """
            }
        ]
        
        print(f"Rendering pages {i} to {end_page} as images...")
        for j in range(i, end_page):
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
            
            if isinstance(content, list):
                content = "".join([str(c) for c in content])
            
            content = content.replace("```json", "").replace("```", "").strip()
            
            if not content:
                print("Empty response.")
                continue

            try:
                batch_data = json.loads(content)
            except json.JSONDecodeError:
                try:
                    print("JSON load failed, trying ast.literal_eval...")
                    batch_data = ast.literal_eval(content)
                except Exception:
                    print(f"FAILED RAW CONTENT: {content[:200]}...")
                    continue
            
            if isinstance(batch_data, dict):
                batch_data = [batch_data]

            if isinstance(batch_data, list):
                all_monsters.extend(batch_data)
                print(f"Extracted {len(batch_data)} monsters from batch.")
            else:
                print("AI returned valid JSON but not a list.")
            
            time.sleep(2) 
            
        except Exception as e:
            print(f"Error parsing batch {i}-{end_page}: {e}")
            
    # Save Final
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_monsters, f, indent=2, ensure_ascii=False)
    print(f"Compeleted! Saved {len(all_monsters)} monsters to {output_path}")

if __name__ == "__main__":
    base_dir = r"C:\Users\FranciscoGetFinanced\Dropbox\Antigravity\dungeon-master-ai"
    pdf_path = os.path.join(base_dir, "resources", "SRD_CC_v5.2.1.pdf")
    output_path = "monsters_data.json"
    
    print(f"Looking for PDF at: {pdf_path}")
    
    if os.path.exists(pdf_path):
        process_file_in_chunks(pdf_path, output_path)
    else:
        print(f"File {pdf_path} not found.")
