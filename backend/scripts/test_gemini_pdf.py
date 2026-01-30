import google.generativeai as genai
import os
from dotenv import load_dotenv
import pathlib

# Load env from parent directory (backend)
load_dotenv(dotenv_path=".env")

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("Error: GOOGLE_API_KEY not set.")
    exit(1)

genai.configure(api_key=api_key)

# Test with Gemini Flash Stable
model = genai.GenerativeModel('gemini-flash-latest')

pdf_path = "../resources/Mitia_Kamara_93488088.pdf"

print(f"Reading PDF: {pdf_path}")
try:
    pdf_data = pathlib.Path(pdf_path).read_bytes()
    
    prompt = """
    Analyze this D&D character sheet PDF.
    Extract the following data in strict JSON format:
    {
        "name": "Character Name",
        "race": "Race",
        "class": "Class (including level)",
        "level": 1,
        "stats": {
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10
        },
        "bio": "Summarize the background and traits."
    }
    Only return the JSON.
    """
    
    print("Sending to Gemini 1.5 Flash...")
    response = model.generate_content([
        {'mime_type': 'application/pdf', 'data': pdf_data},
        prompt
    ])
    
    print("Response:")
    print(response.text)

except Exception as e:
    print(f"Error: {e}")
