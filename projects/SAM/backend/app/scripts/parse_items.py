
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
    
    # Process in batches of 3
    batch_size = 3
    
    # SRD Chapter 5: Equipment starts around page 65.
    # Weapons ~ p.67, Armor ~ p.65.
    start_page = 65 
    
    # Scan a good chunk for weapons/armor tables and descriptions
    end_scan = min(total_pages, 85) 
    
    print(f"Starting ITEM ingestion from page {start_page} to {end_scan}...")
    
    for i in range(start_page, end_scan, batch_size):
        end_page = min(i + batch_size, end_scan)
        
        message_parts = [
            {
                "type": "text", 
                "text": """
                You are an expert D&D 5e Rules Lawyer.
                Extract detailed ITEM (Weapons, Armor, Gear) information from these page images into a structured JSON list.
                
                For WEAPONS/ARMOR in tables:
                - Create an entry for each row.
                - name (e.g. "Longsword")
                - type (e.g. "Martial Melee Weapon" or "Heavy Armor")
                - properties (object) {damage: "1d8 slashing", cost: "15gp", weight: "3lb", properties: ["Versatile (1d10)"]}
                
                Standard Schema for all:
                - name (string)
                - type (string)
                - rarity (string, default "Common")
                - description (string)
                - properties (object)
                
                IMPORTANT:
                - Return ONLY raw JSON list.
                - If no items found, return empty list [].
                """
            }
        ]
        
        print(f"Rendering pages {i} to {end_page} as images...")
        for j in range(i, end_page):
            # Render page to image (Zoom 3x for OCR quality)
            pix = doc[j].get_pixmap(matrix=fitz.Matrix(3, 3))
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
            
            # --- FIX: Handle Multi-part Content ---
            if isinstance(content, list):
                # If it's a list, it might be [{'type': 'text', 'text': '...'}]
                # We only want the text from the text parts.
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
                    # print("JSON load failed, trying ast.literal_eval...")
                    batch_data = ast.literal_eval(content)
                except Exception:
                    print(f"FAILED RAW CONTENT: {content[:200]}...")
                    continue
            
            # Additional Unwrap if AI was weird again
            if isinstance(batch_data, dict) and "items" in batch_data:
                batch_data = batch_data["items"]
            
            # Handle single dict
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
    pdf_path = os.path.join(base_dir, "resources", "SRD_CC_v5.2.1.pdf")
    output_path = "items_data.json"
    
    print(f"Looking for PDF at: {pdf_path}")
    
    if os.path.exists(pdf_path):
        process_file_in_chunks(pdf_path, output_path)
    else:
        print(f"File {pdf_path} not found.")
