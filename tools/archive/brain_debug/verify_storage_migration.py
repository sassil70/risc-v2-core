import os
import shutil
import sys

# Mocking the import environment
sys.path.append(os.path.join(os.getcwd(), "services"))
from storage_service import StorageService

def verify_migration():
    storage_root = r"C:\Users\Salim B Assil\Documents\Smart_Inspection_Project\RISC_V2_Core_System\storage"
    service = StorageService(storage_root)
    
    # Target Session
    session_id = "f1dde834-97d2-4c1a-a3e0-4464361d5ff1"
    legacy_path = os.path.join(storage_root, "sessions", session_id)
    
    if not os.path.exists(legacy_path):
        print(f"❌ Legacy path not found: {legacy_path}")
        return
    
    # New Hierarchy Target
    user_id = "surv_01"
    property_id = "prop_mirdif_01"
    new_path = service.get_session_path(user_id, property_id, session_id)
    
    print(f"[INFO] Migrating: {legacy_path} -> {new_path}")
    
    # Copy instead of move for safety in test
    try:
        # We need to copy the contents, not the directory itself into the new_path
        # because new_path already includes the session_id
        for item in os.listdir(legacy_path):
            s = os.path.join(legacy_path, item)
            d = os.path.join(new_path, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
        
        print("[SUCCESS] Migration Successful!")
        print(f"Check directory: {new_path}")
        
    except Exception as e:
        print(f"[ERROR] Migration Failed: {e}")

if __name__ == "__main__":
    verify_migration()
