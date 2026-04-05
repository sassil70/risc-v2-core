from google import genai
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def test_versions():
    api_key = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    
    # User's specifically requested models (found in list_models earlier)
    targets = [
        "gemini-2.5-flash-native-audio-latest",
        "gemini-2.5-flash-native-audio-preview-12-2025",
        "gemini-2.0-flash-exp" 
    ]
    
    print("--- STRICT VERSION TESTING ---")
    
    for model in targets:
        print(f"\n[TARGET] {model}")
        try:
            # Try simple text generation first
            response = client.models.generate_content(
                model=model,
                contents="Define yourself."
            )
            print(f"[SUCCESS] {response.text}")
        except Exception as e:
            print(f"[FAILED] {e}")

if __name__ == "__main__":
    test_versions()
