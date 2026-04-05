import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def test_legacy_sdk():
    api_key = os.getenv("GOOGLE_API_KEY")
    genai.configure(api_key=api_key)
    
    print("--- LEGACY SDK MODEL LIST ---")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"List Error: {e}")
        
    print("\n--- LEGACY SDK GENERATION TEST ---")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Hello")
        print(f"[SUCCESS] gemini-1.5-flash responded: {response.text}")
    except Exception as e:
        print(f"[FAILED] gemini-1.5-flash error: {e}")

if __name__ == "__main__":
    test_legacy_sdk()
