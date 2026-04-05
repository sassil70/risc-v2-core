import requests
import os
import json
import zipfile
import time
import uuid

# Configuration
BRAIN_URL = "http://localhost:8001"
STORAGE_ROOT = "../storage" # Relative to Lab folder

class MockWitness:
    def __init__(self, user_id="tester_1", property_id="prop_789"):
        self.user_id = user_id
        self.property_id = property_id
        self.session_id = str(uuid.uuid4())
        print(f"Starting Mock Inspection: {self.session_id}")

    def run_scenario(self, scenario_name, rooms_data, assets_dir):
        """
        Simulates the full APK flow for a scenario.
        """
        print(f"\n--- Testing Scenario: {scenario_name} ---")

        # 1. Step 1: Voice Architect (Floor Plan Generation)
        # We mock this by sending a dummy audio and getting a floor plan
        print("1. Initializing Floor Plan (Voice Architect)...")
        # In a real test, we'd have a .m4a in assets_dir
        # For now, we simulate the 'plan' returned
        mock_plan = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "property_id": self.property_id,
            "floor_plan": {
                "rooms": rooms_data
            }
        }
        
        # 2. Step 2: Start Session
        print("2. Starting Official Session...")
        res = requests.post(f"{BRAIN_URL}/api/property/init", json=mock_plan)
        if res.status_code != 200:
            print(f"Failed to init property: {res.text}")
            return

        # 3. Step 3: Upload Room Evidence (Simulate SYNC)
        print("3. Uploading Evidence Zips...")
        for room in rooms_data:
            room_id = room['id']
            room_assets = os.path.join(assets_dir, room_id)
            if not os.path.exists(room_assets):
                # Try scenario-specific folder
                room_assets = os.path.join(assets_dir) 
                
            if not os.path.exists(room_assets):
                print(f"No assets found for room {room_id}, skipping upload.")
                continue

            # Create Zip
            zip_path = f"{room_id}_test.zip"
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for root, dirs, files in os.walk(room_assets):
                    for file in files:
                        zipf.write(os.path.join(root, file), file)

            # Upload
            with open(zip_path, 'rb') as f:
                upload_res = requests.post(
                    f"{BRAIN_URL}/api/v2/sync/upload_room",
                    data={"session_id": self.session_id, "room_id": room_id},
                    files={"file": f}
                )
            os.remove(zip_path)
            print(f"   Room {room_id} Synced: {upload_res.status_code}")

        # 4. Step 4: Verify Status
        print("4. Verifying Inspection Status...")
        status_res = requests.get(f"{BRAIN_URL}/api/inspection/status", params={"session_id": self.session_id})
        print(f"   Status: {status_res.json().get('status')}")

        # 5. Step 5: Trigger AI Report
        print("5. Triggering Forensic AI Analysis...")
        report_res = requests.post(f"{BRAIN_URL}/api/forensic/{self.session_id}")
        if report_res.status_code == 200:
            print("Forensic Analysis Completed!")
            print(f"   Report Preview: http://localhost:8001/api/reports/{self.session_id}")
        else:
            print(f"AI Generation Failed: {report_res.text}")

if __name__ == "__main__":
    # Test Scenario A: External Shared Manhole
    # Use STRICT UUID-styled strings to satisfy Postgres UUID columns
    witness_a = MockWitness(user_id="e725ade1-1234-5678-90ab-cde456789012", property_id="a7b8c9d0-1234-5678-90ab-cde456789012")
    rooms_a = [
        {"id": "ext_front", "name": "Front Garden", "type": "external", "floor": 0, "contexts": ["Manhole"]}
    ]
    
    # EXECUTE SCENARIO A
    # witness_a.run_scenario("Shared Manhole", rooms_a, "Forensic_Lab_V2/scenarios/scenario_a_manhole")

    # Test Scenario B: Water Ingress / Rising Damp in Kitchen
    witness_b = MockWitness(user_id="e725ade1-1234-5678-90ab-cde456789012", property_id="a7b8c9d0-1234-5678-90ab-cde456789012")
    rooms_b = [
        {"id": "kitchen_main", "name": "Kitchen", "type": "internal", "floor": 0, "contexts": ["Walls", "Plumbing"]}
    ]
    
    # Test Scenario C: Fire Door Safety / Structural
    witness_c = MockWitness(user_id="e725ade1-1234-5678-90ab-cde456789012", property_id="a7b8c9d0-1234-5678-90ab-cde456789012")
    rooms_c = [
        {"id": "hallway_main", "name": "Hallway", "type": "internal", "floor": 0, "contexts": ["Doors", "Fire Safety"]}
    ]
    
    # EXECUTE SCENARIO C
    witness_c.run_scenario("Fire Door Safety", rooms_c, "Forensic_Lab_V2/scenarios/scenario_c_door")

    print("\nScenario Execution Finished.")
