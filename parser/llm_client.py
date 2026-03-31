import os
from dotenv import load_dotenv
from google import genai

# ✅ Load .env from ROOT directory explicitly
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env")



    return genai.Client(api_key=api_key)