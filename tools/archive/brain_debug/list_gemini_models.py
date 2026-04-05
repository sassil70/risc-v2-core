import asyncio
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load Env
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def list_models():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: No API Key")
        return
        
    genai.configure(api_key=api_key)
    
    print("--- Available Models ---")
    try:
        count = 0 
        for model in genai.list_models():
            count += 1
            print(f"- {model.name}")
            print(f"  Methods: {model.supported_generation_methods}")
        
        if count == 0:
            print("No models found. Check API Key permissions/region.")
            
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
