import asyncio
import os
from services.gemini_service import get_gemini_service

async def test_connection():
    print("--- TESTING GEMINI CONNECTION ---")
    
    # Debug Env
    api_key_env = os.environ.get("GOOGLE_API_KEY")
    print(f"DEBUG: GOOGLE_API_KEY present in os.environ? {bool(api_key_env)}")
    if api_key_env:
        print(f"DEBUG: Key length: {len(api_key_env)}")

    # 1. Initialize
    try:
        service = get_gemini_service()
        print(f"[OK] Service Initialized (Model: {service.MODEL_NAME})")
    except Exception as e:
        print(f"[FAIL] Service Initialization Failed: {e}")
        return

    # 2. Define Assets
    audio_path = r"C:\Users\Salim B Assil\Documents\Smart_Inspection_Project\RISC_V2_Core_System\storage\sessions\c96caac1-027d-4b77-9c00-ae710194e260\audio_evidence\floor_plan_audio_v1.m4a"
    
    # 3. Test Payload
    print(f"Testing with Audio: {audio_path}")
    if not os.path.exists(audio_path):
        print("[WARN] Audio file not found on disk. Skipping audio upload test.")
        audio_path = None
    
    prompt = """
    This is a system connectivity test. 
    1. Acknowledge this message.
    2. If audio is attached, briefly summarize the tone of the speaker.
    3. Output strictly in JSON format: {"status": "connected", "audio_analysis": "..."}
    """
    
    # 4. Call Service
    try:
        response = await service.analyze_evidence(
            images_paths=[], 
            audio_path=audio_path,
            prompt_text=prompt
        )
        print("\n--- RESPONSE FROM GEMINI ---")
        print(response)
        print("\n----------------------------")
        
        if "connected" in response:
            print("[OK] TEST PASSED: Gemini is responding.")
        else:
            print("[WARN] TEST WARNING: Response checking logic matched nothing, check raw output.")
            
    except Exception as e:
        print(f"[FAIL] TEST FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
