
import fitz
import os

pdf_path = r"C:\Users\FranciscoGetFinanced\Dropbox\Antigravity\dungeon-master-ai\resources\SRD_CC_v5.2.1.pdf"
doc = fitz.open(pdf_path)

print(f"Total Pages: {len(doc)}")

for i in range(len(doc)):
    text = doc[i].get_text()
    # Logic: Look for large header "Monsters" or "Appendix B" or "Stat Blocks"
    if "Monsters" in text and "Challenge" in text and "XP" in text:
         # Rough heuristic: A page with "Monsters", "Challenge" and "XP" likely has stat blocks or the intro.
         print(f"Potential Match on Page {i}")
         if i > 50: # Skip ToC
             print(f"First significant match after ToC: {i}")
             break
