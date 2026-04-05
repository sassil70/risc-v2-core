import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key Found: {bool(api_key)}")
if api_key:
    print(f"API Key prefix: {api_key[:5]}...")

genai.configure(api_key=api_key)

try:
    print("Listing Models...")
    models = [m.name for m in genai.list_models()]
    print(f"Available Models: {len(models)}")
    for m in models:
        print(f" - {m}")
        
    target_model = os.getenv("GEMINI_MODEL_KEY", "gemini-2.0-flash-exp")
    print(f"Target Model: {target_model}")
    
    if "models/" + target_model in models or target_model in models:
        print("[OK] Target model found in list.")
    else:
        print("[WARN] Target model NOT explicitly in list (might still work if alias).")
        
    print("Testing Generation...")
    model = genai.GenerativeModel(target_model)
    response = model.generate_content("Hello, system check.")
    print(f"[OK] Response: {response.text}")
    
except Exception as e:
    print(f"[ERROR] Error: {e}")
