import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def test_gemini_3():
    api_key = os.getenv("GOOGLE_API_KEY")
    genai.configure(api_key=api_key)
    
    target_model = "gemini-3-flash-preview" # Exact name from list
    
    print(f"--- TESTING {target_model} ---")
    try:
        model = genai.GenerativeModel(target_model)
        response = model.generate_content("Hello")
        print(f"[SUCCESS] {target_model} Answer: {response.text}")
    except Exception as e:
        print(f"[FAILED] Error: {e}")

if __name__ == "__main__":
    test_gemini_3()
