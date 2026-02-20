from pypdf import PdfReader
import os

pdf_path = "../resources/Mitia_Kamara_93488088.pdf"

try:
    reader = PdfReader(pdf_path)
    print(f"Total Pages: {len(reader.pages)}")
    
    print("--- FORM FIELDS ---")
    fields = reader.get_form_text_fields()
    if fields:
        for k, v in list(fields.items())[:20]: # Print first 20 fields
            print(f"{k}: {v}")
    else:
        print("No form fields found.")
    print("-------------------")
    
    # Extract text from the first page (usually main stats)
    page1 = reader.pages[0]
    text = page1.extract_text()
    
    print("--- PAGE 1 TEXT DUMP ---")
    print(text)
    print("------------------------")
    
    # Check 2nd page for bio/backstory if exists
    if len(reader.pages) > 1:
        page2 = reader.pages[1]
        text2 = page2.extract_text()
        print("--- PAGE 2 TEXT DUMP ---")
        print(text2[:500]) # First 500 chars
        print("------------------------")

except Exception as e:
    print(f"Error reading PDF: {e}")
