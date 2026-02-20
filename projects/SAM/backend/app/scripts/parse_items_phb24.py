
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

llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0)

def process_file_in_chunks(pdf_path, output_path):
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    all_items = []
    
    # Process in batches
    batch_size = 4
    
    # Target Range: Equipment Ch 6
    start_page = 215
    end_scan = 240
    
    print(f"Starting SPANISH ITEM ingestion from page {start_page} to {end_scan}...")
    
    for i in range(start_page, end_scan, batch_size):
        end_page = min(i + batch_size, end_scan)
        
        message_parts = [
            {
                "type": "text", 
                "text": """
                You are an expert D&D 5e/2024 Rules Lawyer.
                Analyze these pages from the 'Manual del Jugador 2024' (Spanish).
                Look for **EQUIPMENT TABLES** (Weapons/Armas, Armor/Armaduras).
                
                Task:
                1. Identify rows in the table (Sword, Axe, Bow, etc.).
                2. Translate the Item Name to ENGLISH (e.g., "Espada Larga" -> "Longsword").
                3. Extract properties.
                
                Schema (JSON List):
                [
                  {
                    "name": "Longsword",
                    "type": "Martial Melee Weapon",
                    "rarity": "Common",
                    "properties": {
                        "damage": "1d8 slashing", 
                        "cost": "15gp", 
                        "weight": "3lb",
                        "properties": ["Versatile (1d10)"]
                    },
                    "source": "PHB 2024"
                  }
                ]
                
                IMPORTANT:
                - Return ONLY raw JSON list.
                - TRANSLATE names to English so they match the database.
                - If no tables found, return empty list [].
                """
            }
        ]
        
        print(f"Rendering pages {i} to {end_page} as images...")
        for j in range(i, end_page):
            try:
                pix = doc[j].get_pixmap(matrix=fitz.Matrix(2, 2))
                img_data = pix.tobytes("jpeg")
                b64_str = base64.b64encode(img_data).decode("utf-8")
                
                message_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64_str}"}
                })
            except Exception as e:
                print(f"Error render page {j}: {e}")
            
        print("Sending to Gemini Vision...")
        
        try:
            msg = HumanMessage(content=message_parts)
            res = llm.invoke([msg])
            content = res.content
            
            # --- FIX: Handle Multi-part Content ---
            if isinstance(content, list):
                full_text = ""
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        full_text += part.get("text", "")
                    elif isinstance(part, str):
                        full_text += part
                content = full_text
            # ----------------------------------------
            
            content = content.replace("```json", "").replace("```", "").strip()
            
            if not content:
                print("Empty response.")
                continue

            try:
                batch_data = json.loads(content)
            except json.JSONDecodeError:
                try:
                    batch_data = ast.literal_eval(content)
                except Exception:
                    print(f"FAILED RAW CONTENT: {content[:200]}...")
                    continue
            
            if isinstance(batch_data, dict) and "items" in batch_data:
                batch_data = batch_data["items"]
            
            if isinstance(batch_data, dict):
                batch_data = [batch_data]
            
            if isinstance(batch_data, list):
                all_items.extend(batch_data)
                print(f"Extracted {len(batch_data)} items from batch.")
            else:
                print("AI returned valid JSON but not a list.")
            
            time.sleep(2) 
            
        except Exception as e:
            print(f"Error parsing batch {i}-{end_page}: {e}")
            
    # Save Final
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)
    print(f"Compeleted! Saved {len(all_items)} items to {output_path}")

if __name__ == "__main__":
    base_dir = r"C:\Users\FranciscoGetFinanced\Dropbox\Antigravity\dungeon-master-ai"
    # Exact filename provided by USER
    pdf_path = os.path.join(base_dir, "resources", "Manual del Jugador 2024_122311_Batch Compress.pdf")
    output_path = "items_phb24.json"
    
    print(f"Looking for PDF at: {pdf_path}")
    
    if os.path.exists(pdf_path):
        process_file_in_chunks(pdf_path, output_path)
    else:
        print(f"File {pdf_path} not found.")
