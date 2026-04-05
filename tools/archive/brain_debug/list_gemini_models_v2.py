from google import genai
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def list_models_v2():
    api_key = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    
    print("--- GenAI SDK Available Models ---")
    try:
        # The new SDK list_models might return an iterator
        for model in client.models.list():
            print(f"- {model.name} | {model.display_name}")
            # print(f"  Supported: {model.supported_generation_methods}") 
            # Note: The object structure might be different in V1 SDK
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_models_v2()
