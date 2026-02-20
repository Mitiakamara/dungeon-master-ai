
import fitz  # PyMuPDF
import os

def find_keywords(pdf_path, keywords):
    doc = fitz.open(pdf_path)
    print(f"Scanning {len(doc)} pages for keywords: {keywords}")
    
    hits = []
    
    # scan every page
    for i in range(len(doc)):
        text = doc[i].get_text().lower()
        
        score = 0
        for kw in keywords:
            if kw.lower() in text:
                score += 1
        
        if score > 0:
            hits.append((i, score, text[:100].replace('\n', ' ')))
            
    # Sort by score desc
    hits.sort(key=lambda x: x[1], reverse=True)
    
    print("\n--- TOP MATCHES ---")
    for page, score, preview in hits[:10]:
        print(f"Page {page} (Score {score}): {preview}...")

if __name__ == "__main__":
    base_dir = r"C:\Users\FranciscoGetFinanced\Dropbox\Antigravity\dungeon-master-ai"
    pdf_path = os.path.join(base_dir, "resources", "Manual del Jugador 2024_122311_Batch Compress.pdf")
    
    # Spanish keywords for Weapons Table
    keywords = ["tabla de armas", "armas marciales", "armas simples", "propiedades", "daño", "coste"]
    
    if os.path.exists(pdf_path):
        find_keywords(pdf_path, keywords)
    else:
        print("PDF not found.")
