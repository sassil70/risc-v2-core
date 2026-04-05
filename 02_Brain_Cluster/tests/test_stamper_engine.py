import asyncio
import os
import json
import shutil
from services.rics_stamper import stamp_rics_report
from services.synthesis_engine import _resolve_project_semantic_path

async def test_stamper():
    # 1. Setup Mock Project
    project_id = "PDF_TEST_001"
    storage_root = os.path.join(os.path.dirname(__file__), "storage", "projects", project_id)
    os.makedirs(storage_root, exist_ok=True)
    
    # 2. Mock Master State
    master_state = {
        "metadata": {"reference_number": "TX-1002-RICS"}
    }
    with open(os.path.join(storage_root, "Property_Master_State.json"), "w") as f:
        json.dump(master_state, f)
        
    # 3. Mock Approved Room for E1 Ceilings
    os.makedirs(os.path.join(storage_root, "g_room_01"), exist_ok=True)
    
    # Create a dummy image
    dummy_img = os.path.join(storage_root, "dummy.png")
    from PIL import Image
    img = Image.new('RGB', (120, 120), color = 'red')
    img.save(dummy_img)

    room_data = {
        "room_name": "Living Room Ceiling",
        "floor_name": "Ground Floor",
        "is_approved": True,
        "ai_room_narrative": "The ceiling exhibits significant artex texturing, potentially containing asbestos. Water stains are visible near the bay window, indicating historical ingress from the flat roof above. Recommend urgent invasive testing.",
        "selected_diagnostic_images": [dummy_img, dummy_img]
    }
    
    with open(os.path.join(storage_root, "g_room_01", "room_final.json"), "w") as f:
        json.dump(room_data, f)
        
    print(f"Mock Data prepared at: {storage_root}")
    
    # 4. Trigger Stamper
    print("Triggering PyMuPDF Stamper...")
    pdf_path = stamp_rics_report(project_id, storage_root)
    
    print(f"\nSUCCESS! RICS PDF generated at: {pdf_path}")

if __name__ == "__main__":
    asyncio.run(test_stamper())
