import os
import json
from pathlib import Path

# Paths to scan
PATHS_TO_SCAN = [
    r"c:\Users\Salim B Assil\Documents\Smart_Inspection_Project\RISC_V2_Core_System\02_Brain_Cluster\storage\sessions",
    r"c:\Users\Salim B Assil\Documents\Smart_Inspection_Project\Smart_Surveyor_NextGen\01_Control_Module\control_backend\sessions"
]

def scan_folder():
    print(f"{'Session Name':<40} | {'Images':<8} | {'Audio':<8} | {'JSON?':<6} | {'Source'}")
    print("-" * 100)

    total_props = 0
    total_images = 0
    total_audio = 0
    total_json = 0

    for base_path in PATHS_TO_SCAN:
        if not os.path.exists(base_path):
            continue
            
        # Walk immediate subdirectories
        for entry in os.scandir(base_path):
            if entry.is_dir():
                sess_path = Path(entry.path)
                
                # Counters
                img_count = 0
                audio_count = 0
                has_json = False
                name = entry.name # Default to folder name

                # Recursive file scan in this session
                for root, dirs, files in os.walk(sess_path):
                    for f in files:
                        lower_f = f.lower()
                        if lower_f.endswith(('.jpg', '.jpeg', '.png')):
                            img_count += 1
                        elif lower_f.endswith(('.m4a', '.mp3', '.wav')):
                            audio_count += 1
                        elif f == 'session.json' or f.endswith('_init.json'):
                            has_json = True
                            # Try to extract real name
                            try:
                                with open(os.path.join(root, f), 'r', encoding='utf-8') as jf:
                                    data = json.load(jf)
                                    # Fallbacks for name
                                    name = data.get('title') or data.get('address') or data.get('id') or name
                            except:
                                pass

                # Only report if it has ANY data
                if img_count > 0 or audio_count > 0 or has_json:
                    print(f"{str(name)[:38]:<40} | {img_count:<8} | {audio_count:<8} | {str(has_json):<6} | {base_path.split(os.sep)[-2]}")
                    total_props += 1
                    total_images += img_count
                    total_audio += audio_count
                    if has_json: total_json += 1

    print("-" * 100)
    print(f"TOTAL PROPERTIES: {total_props}")
    print(f"TOTAL IMAGES:     {total_images}")
    print(f"TOTAL AUDIO:      {total_audio}")
    print(f"TOTAL JSON FILES: {total_json}")

if __name__ == "__main__":
    scan_folder()
