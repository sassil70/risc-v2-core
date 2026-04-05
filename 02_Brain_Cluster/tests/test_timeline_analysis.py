
import asyncio
import json
import os
import sys

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from forensic_engine import analyze_session

# TARGET SESSION (Known to have timeline files)
SESSION_ID = "bbfa2567-f85f-4937-9810-f8b0b59121f7"
STORAGE_ROOT = r"C:\Users\Salim B Assil\Documents\Smart_Inspection_Project\RISC_V2_Core_System\storage"

async def test_timeline_analysis():
    print(f"--- STARTING TIMELINE MAPPING TEST: {SESSION_ID} ---")
    
    session_dir = os.path.join(STORAGE_ROOT, "sessions", SESSION_ID)
    init_path = os.path.join(session_dir, "session_init.json")
    
    if not os.path.exists(init_path):
        print(f"ERROR: Session {SESSION_ID} not found at {init_path}")
        return

    with open(init_path, "r", encoding="utf-8") as f:
        session_data = json.load(f)

    # Run Analysis
    try:
        print("Running analyze_session (this may take 30-60s)...")
        report = await analyze_session(SESSION_ID, session_data)
        
        print("\n--- TEST RESULTS ---")
        # Check first room
        if report.get("rooms"):
            room = report["rooms"][0]
            print(f"Room: {room.get('room_id')}")
            for element in room.get("elements", []):
                print(f"  Element: {element.get('name')}")
                print(f"    Evidence Photos: {element.get('evidence_photos')}")
                print(f"    Context Match: {element.get('context_match')}")
                print(f"    Privacy Alert: {element.get('privacy_alert')}")
                
            # Final Validation
            has_evidence = any(len(e.get("evidence_photos", [])) > 0 for e in room.get("elements", []))
            if has_evidence:
                print("\nSUCCESS: AI successfully linked specific images to forensic observations.")
            else:
                print("\nFAILURE: AI returned report but evidence_photos are empty.")
        else:
            print("FAILURE: No rooms analyzed.")
            
        # Save for review
        with open("timeline_test_output.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
            
    except Exception as e:
        print(f"TEST CRASHED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_timeline_analysis())
