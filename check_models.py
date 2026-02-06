
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load env variables from .env file (assuming it's in parent directory or current)
# Try multiple paths
paths = [".env", "../.env", "../../.env", "backend/.env"]
loaded = False
for p in paths:
    if os.path.exists(p):
        print(f"Loading env from {p}")
        load_dotenv(p)
        loaded = True
        break

if not loaded:
    print("Warning: No .env file found.")

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("ERROR: GOOGLE_API_KEY not found in environment.")
else:
    print(f"API Key found: {api_key[:5]}...{api_key[-3:]}")
    try:
        genai.configure(api_key=api_key)
        output = "\nListing available models:\n"
        for m in genai.list_models():
            if 'embedContent' in m.supported_generation_methods:
                output += f"- {m.name} (Supported methods: {m.supported_generation_methods})\n"
        print(output)
        with open("models_list.txt", "w", encoding="utf-8") as f:
            f.write(output)
    except Exception as e:
        err_msg = f"Error listing models: {e}"
        print(err_msg)
        with open("models_list.txt", "w", encoding="utf-8") as f:
            f.write(err_msg)
