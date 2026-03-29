import os
from google import genai
from dotenv import load_dotenv

# Load your API key from .env
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ ERROR: GOOGLE_API_KEY not found in .env file.")
else:
    client = genai.Client(api_key=api_key)
    print("--- 🔍 SEARCHING FOR VALID MODEL NAMES ---")
    try:
        # This calls the Google API to list every model you can access
        for model in client.models.list():
            print(f"✅ VALID NAME: {model.name}")
    except Exception as e:
        print(f"❌ API ERROR: {e}")