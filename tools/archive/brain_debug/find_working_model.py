from google import genai
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def find_working_model():
    api_key = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key) # Default v1beta
    
    candidates = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-001",
        "gemini-1.5-flash-002",
        "gemini-1.5-pro",
        "gemini-1.5-pro-001",
        "gemini-1.5-pro-002",
        "gemini-pro",
        "gemini-flash-experimental",
        "models/gemini-1.5-flash",
        "models/gemini-1.5-flash-001"
    ]
    
    print("--- SEARCHING FOR WORKING MODEL ---")
    
    for model in candidates:
        print(f"\nTesting: {model} ...")
        try:
            response = client.models.generate_content(
                model=model,
                contents="Hello"
            )
            print(f"[SUCCESS] {model} IS WORKING! Response: {response.text}")
            return
        except Exception as e:
            if "404" in str(e):
                print(f"[404] Not Found")
            else:
                print(f"[ERROR] {e}")

if __name__ == "__main__":
    find_working_model()
