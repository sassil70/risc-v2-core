from google import genai
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def brute_force_v3():
    api_key = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    
    potential_ids = [
        "gemini-3.0-flash-exp",
        "gemini-3.0-flash-preview",
        "gemini-3.0-flash-001",
        "gemini-3.0-pro-exp",
        "gemini-3.0-pro-preview",
        "gemini-3.0-flash",
        "gemini-3.0-flash-preview-001"
    ]
    
    print("--- BRUTE FORCE GEMINI 3.0 IDs ---")
    
    for model_id in potential_ids:
        print(f"\nTesting: {model_id} ...")
        try:
            response = client.models.generate_content(
                model=model_id,
                contents="Verify."
            )
            print(f"[FOUND] {model_id} responded: {response.text}")
            return # Stop on first success
        except Exception as e:
            if "404" in str(e):
                print(f"[404] Not Found")
            else:
                print(f"[ERROR] {e}")

if __name__ == "__main__":
    brute_force_v3()
