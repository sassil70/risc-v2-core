
import asyncio
import json
import os
from forensic_engine import analyze_session

# CONFIG
SESSION_ID = "12472807-e22e-4cbc-91b1-d15067140f45"
STORAGE_ROOT = r"C:\Users\Salim B Assil\Documents\Smart_Inspection_Project\RISC_V2_Core_System\storage"

async def main():
    print(f"--- TESTING FINAL AI PIPELINE ---")
    session_dir = os.path.join(STORAGE_ROOT, "sessions", SESSION_ID)
    init_path = os.path.join(session_dir, "session_init.json")
    
    with open(init_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Loaded session data. Identifying rooms...")
    
    try:
        report = await analyze_session(SESSION_ID, data)
        print("\n--- ANALYSIS COMPLETE ---")
        print(json.dumps(report, indent=2)[:2000] + "...")
        
        # Save results to a verification file
        verify_path = os.path.join(session_dir, "verification_audit.json")
        with open(verify_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Saved to {verify_path}")
        
    except Exception as e:
        print(f"CRASH: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
