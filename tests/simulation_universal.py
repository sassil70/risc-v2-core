import asyncio
import os
import shutil
import zipfile
import json
from datetime import datetime

# --- Simulation Configuration ---
SOURCE_SESSION_DIR = r"c:\Users\Salim B Assil\Documents\Smart_Inspection_Project\Smart_Surveyor_NextGen\01_Control_Module\control_backend\sessions\prop_1766632779"
TARGET_BRAIN_DIR = r"c:\Users\Salim B Assil\Documents\Smart_Inspection_Project\RISC_V2_Core_System\02_Brain_Cluster\storage\sessions"
OUTPUT_REPORT_DIR = r"c:\Users\Salim B Assil\Documents\Smart_Inspection_Project\RISC_V2_Core_System\03_Reporter_Cluster\output"
SESSION_ID = "sim_universal_user_001"

# --- Import System Components (Mock communication by direct import) ---
import sys
from unittest.mock import MagicMock, AsyncMock

# Mock Database MUST be done BEFORE importing processor
sys.modules['database'] = MagicMock()
sys.modules['database'].db = AsyncMock()

sys.path.append(r"c:\Users\Salim B Assil\Documents\Smart_Inspection_Project\RISC_V2_Core_System\02_Brain_Cluster")
sys.path.append(r"c:\Users\Salim B Assil\Documents\Smart_Inspection_Project\RISC_V2_Core_System\03_Reporter_Cluster")

from processor import PackageProcessor
from ai_engine import AIEngine

async def run_universal_simulation():
    print("STARTED: Universal User Simulation (End-to-End)")
    
    # 1. WITNESS SIMULATION: Create a Signed Package from Old Data
    print("\n[Phase 1] Witness: Packaging data...")
    pkg_path = f"{SESSION_ID}.zip"
    
    # Create fake manifest based on old session (Source of Truth)
    manifest = {
        "sessionId": SESSION_ID,
        "timestamp": datetime.now().isoformat(),
        "surveyorId": "UNIVERSAL_ADMIN",
        "files": []
    }
    
    with zipfile.ZipFile(pkg_path, 'w') as zf:
        # Walk source dir and add relevant files (Images only for simulation)
        found_images = False
        source_rooms = os.path.join(SOURCE_SESSION_DIR, "rooms")
        print(f"DEBUG: Looking for images in {source_rooms}")
        
        if os.path.exists(source_rooms):
            for root, dirs, files in os.walk(source_rooms):
                for file in files:
                    if file.lower().endswith(('.jpg', '.png', '.jpeg')):
                        # Add to zip
                        arcname = f"media/{file}"
                        zf.write(os.path.join(root, file), arcname)
                        manifest['files'].append({"path": arcname, "hash": "dummyhash", "notes": "Simulated Image"})
                        found_images = True
                        if len(manifest['files']) >= 3: break # Limit to 3 images for speed
                if found_images: break
        
        if not found_images:
            print("WARNING: No images found in source session. Creating dummy image.")
            with open("dummy.jpg", "w") as f: f.write("fake image")
            zf.write("dummy.jpg", "media/dummy.jpg")
            manifest['files'].append({"path": "media/dummy.jpg", "hash": "dummyhash"})
            os.remove("dummy.jpg")
            
        zf.writestr("session_manifest.json", json.dumps(manifest))
    
    print(f"Package Created: {pkg_path} ({len(manifest['files'])} files)")

    # 2. BRAIN SIMULATION: Process Package
    print("\n[Phase 2] Brain: Processing Package...")
    # Use dirname of TARGET_BRAIN_DIR which is "storage"
    processor = PackageProcessor(storage_root=os.path.dirname(TARGET_BRAIN_DIR)) 
    
    try:
        result = await processor.process(pkg_path, "simulated_hash")
        print(f"Brain Processed: {result['status']}")
    except Exception as e:
        print(f"Brain Failed: {e}")
        return

    # 3. REPORTER SIMULATION: AI Analysis (The "Universal User" triggering it)
    print("\n[Phase 3] Reporter: AI Analysis with RICS Context...")
    engine = AIEngine()
    
    # Simulate retrieving assets from "DB" (relying on what we just processed)
    # The brain stores directly in storage/sessions/{session_id}
    # BUT wait, the processor uses specific logic. Let's verify paths.
    # Processor uses: storage_root + session_id
    # We passed dirname(TARGET_BRAIN_DIR) i.e. .../storage/sessions
    # So it should be .../storage/sessions/{session_id}
    brain_session_path = os.path.join(os.path.dirname(TARGET_BRAIN_DIR), SESSION_ID)
    
    final_report = "## Universal User Simulation Report\n\n"
    
    for file_info in manifest['files']:
        rel_path = file_info['path']
        full_path = os.path.join(brain_session_path, rel_path)
        
        if not os.path.exists(full_path):
            print(f"Asset missing: {full_path}")
            # Try debugging path
            print(f"Expected: {full_path}")
            continue
            
        print(f"Analyzing: {rel_path}")
        
        try:
            import PIL.Image
            try:
                img = PIL.Image.open(full_path)
            except:
                print("Could not open image (might be dummy or corrupt). Skipping.")
                continue

            # PROMPT
            system_prompt = "You are analyzing a defect found during a home survey. Describe the defect, assign a Condition Rating (1, 2, or 3), and suggest remedial actions."
            user_content = ["Analyze this image according to RICS standards.", img]
            
            # API CALL
            ai_response = await engine.generate_report_section(system_prompt, user_content, use_rag=True)
            
            # Print safe preview
            preview = ai_response[:100].encode('ascii', 'ignore').decode('ascii')
            print(f"AI Insight: {preview}...")
            final_report += f"### Asset: {rel_path}\n{ai_response}\n\n"
            
        except Exception as e:
            print(f"AI Analysis Failed for {rel_path}: {e}")

    # 4. EXPORT
    os.makedirs(OUTPUT_REPORT_DIR, exist_ok=True)
    report_path = os.path.join(OUTPUT_REPORT_DIR, f"report_{SESSION_ID}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(final_report)
        
    print(f"\nSIMULATION COMPLETE. Report generated: {report_path}")
    
    # Cleanup
    if os.path.exists(pkg_path): os.remove(pkg_path)

if __name__ == "__main__":
    asyncio.run(run_universal_simulation())
