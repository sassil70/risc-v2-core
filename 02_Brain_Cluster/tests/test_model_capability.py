from google import genai
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def test_models():
    api_key = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    
    candidates = [
        "gemini-1.5-flash",  # Base GA model (Should work)
        "gemini-2.0-flash-exp", # Target
        "gemini-2.5-flash-native-audio-latest"
    ]
    
    print("--- Testing Generation Capability ---")
    
    # Test 1: Standard v1beta (Default)
    print("\n[TEST 1] Standard Client (v1/v1beta)")
    for model in candidates:
        print(f"\nTesting: {model} ...")
        try:
            response = client.models.generate_content(
                model=model,
                contents="Hello"
            )
            print(f"[SUCCESS] {model} responded: {response.text[:50]}...")
        except Exception as e:
            print(f"[FAILED] {model} error: {e}")

    # Test 2: Alpha Client
    print("\n[TEST 2] Alpha Client (v1alpha)")
    try:
        client_alpha = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
        for model in candidates:
            print(f"\nTesting (Alpha): {model} ...")
            try:
                response = client_alpha.models.generate_content(
                    model=model,
                    contents="Hello"
                )
                print(f"[SUCCESS] {model} responded: {response.text[:50]}...")
            except Exception as e:
                print(f"[FAILED] {model} error: {e}")
    except Exception as e:
        print(f"[FAILED] Could not init Alpha client: {e}")

if __name__ == "__main__":
    test_models()
