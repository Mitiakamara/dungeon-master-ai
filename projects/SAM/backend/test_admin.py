
import requests
import json

url = "http://localhost:8000/api/chat"
headers = {"Content-Type": "application/json"}
payload = {
    "message": "/help",
    "history": [],
    "character_context": "TestContext"
}

try:
    print(f"Sending POST to {url}...")
    response = requests.post(url, headers=headers, json=payload, timeout=5)
    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())
except Exception as e:
    print("Error:", e)
