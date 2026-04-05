
import asyncio
import os
import json
from forensic_engine import analyze_session

SESSION_ID = "c96caac1-027d-4b77-9c00-ae710194e260"
# Point to correct storage location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXTERNAL_STORAGE = os.path.abspath(os.path.join(BASE_DIR, "..", "storage"))
INTERNAL_STORAGE = os.path.join(BASE_DIR, "storage")
STORAGE_ROOT = EXTERNAL_STORAGE if os.path.exists(EXTERNAL_STORAGE) else INTERNAL_STORAGE

async def main():
    print(f"--- STANDALONE FORENSIC TEST ---")
    print(f"Session: {SESSION_ID}")
    
    session_dir = os.path.join(STORAGE_ROOT, "sessions", SESSION_ID)
    init_file = os.path.join(session_dir, "session_init.json")
    
    try:
        with open(init_file, 'r', encoding='utf-8') as f: # Force UTF-8 here
            data = json.load(f)
    except Exception as e:
        print(f"Failed to load init file: {e}")
        return

    try:
        result = await analyze_session(SESSION_ID, data)
        print("\n\n--- SUCCESS ---")
        print(json.dumps(result, indent=2)[:500] + "...") # Preview
    except Exception as e:
        print(f"\n\n--- CRASH ---")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
