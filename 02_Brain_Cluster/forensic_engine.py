import google.generativeai as genai
import os
import json
import asyncio
from dotenv import load_dotenv
from database import db
from services.storage_service import get_storage_service

storage_service = get_storage_service()

load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("WARNING: GEMINI_API_KEY or GOOGLE_API_KEY not found in env.")
genai.configure(api_key=api_key)

# Model
MODEL_NAME = os.getenv("GEMINI_MODEL_KEY", "models/gemini-2.5-flash")

from services.prompt_engine import get_prompt_engine

async def analyze_session(session_id: str, session_data: dict):
    """
    Main Entry Point: Orchestrates the Full Forensic Analysis.
    """
    print(f"Let's START FORENSIC ANALYSIS: {session_id}")
    
    prompt_engine = get_prompt_engine()
    system_prompt = prompt_engine.render_prompt("forensic_surveyor.j2", {})
    
    if "ERROR" in system_prompt:
        return {"error": f"Prompt rendering failed: {system_prompt}"}

    final_report = {"rooms": []}
    rooms = session_data.get("floor_plan", {}).get("rooms", [])
    
    tasks = []
    processed_ids = set()
    for room in rooms:
        rid = room.get("id")
        if rid in processed_ids:
            continue
        processed_ids.add(rid)
        tasks.append(analyze_room(room, [session_id], system_prompt))
        
    results = await asyncio.gather(*tasks)
    final_report["rooms"] = [r for r in results if r]
    
    return final_report

async def analyze_room(room, room_dirs: list, system_prompt, excluded_photos: list = None):
    """
    Analyzes a single room using visual evidence + audio voice notes.
    Accepts room_dirs: list of session directories containing this room's data.
    Aggregates evidence across ALL sessions/visits.
    excluded_photos: list of filenames to skip (excluded by surveyor).
    """
    room_id = room.get("id")
    room_name = room.get("name")
    print(f"   -> Analyzing Room: {str(room_name).encode('ascii', 'replace')} ({room_id})")
    
    # ============================================================
    # 1. Aggregate ALL evidence across ALL session directories
    # ============================================================
    if excluded_photos is None:
        excluded_photos = []
    images = []           # (rel_path, abs_path, context_name)
    audio_files = []      # (abs_path, context_name)
    timeline_entries = [] # Sorted by timestamp for ordered chain
    seen_filenames = set()
    
    for session_dir in room_dirs:
        room_dir = os.path.join(session_dir, room_id)
        if not os.path.exists(room_dir):
            continue
        
        valid_img_exts = ('.jpg', '.jpeg', '.png')
        valid_audio_exts = ('.m4a', '.mp3', '.wav', '.aac', '.opus')
        
        for root, dirs, files in os.walk(room_dir):
            # Determine context from folder name
            folder_name = os.path.basename(root)
            context_name = "General"
            if folder_name.startswith("Context_"):
                context_name = folder_name.replace("Context_", "").replace("_", " ")
            
            for file in sorted(files):
                if file in seen_filenames:
                    continue
                seen_filenames.add(file)
                abs_path = os.path.join(root, file)
                
                if file.lower().endswith(valid_img_exts):
                    # Skip excluded photos
                    if file in excluded_photos:
                        print(f"      [EXCLUDED] Skipping {file} (excluded by surveyor)")
                        continue
                    rel_path = os.path.relpath(abs_path, room_dir)
                    images.append((rel_path, abs_path, context_name))
                
                elif file.lower().endswith(valid_audio_exts):
                    audio_files.append((abs_path, context_name))
                
                elif file.startswith("timeline_") and file.endswith(".json"):
                    try:
                        with open(abs_path, "r", encoding="utf-8") as tf:
                            tdata = json.load(tf)
                            timeline_entries.append(tdata)
                    except Exception as e:
                        print(f"      [WARN] Failed to read timeline {file}: {e}")
    
    if not images:
        print(f"      [SKIP] No images in {room_id}")
        return None
    
    # ============================================================
    # 2. Build Timeline Map (Photo → Context + Timestamp)
    # ============================================================
    timeline_map = {}
    for tdata in timeline_entries:
        ctx = tdata.get("context_type") or tdata.get("context", "Unknown")
        for photo in tdata.get("evidence", tdata.get("photos", [])):
            fname = photo.get("filename")
            if fname:
                timeline_map[fname] = {
                    "context": ctx,
                    "timestamp": photo.get("timestamp"),
                    "audio_reference": tdata.get("audio_file")
                }
    
    # ============================================================
    # 3. Build Ordered Evidence Chain for Gemini Prompt
    # ============================================================
    # Sort timeline entries by start_time
    timeline_entries.sort(key=lambda t: t.get("start_time", ""))
    
    evidence_chain = []
    evidence_chain.append(f"Room: {room_name} (ID: {room_id})")
    evidence_chain.append(f"Total Evidence: {len(images)} photos, {len(audio_files)} audio recordings across {len(timeline_entries)} inspection sessions")
    evidence_chain.append("")
    evidence_chain.append("=== CHRONOLOGICAL EVIDENCE CHAIN ===")
    
    for tdata in timeline_entries:
        ctx = tdata.get("context_type") or tdata.get("context", "Unknown")
        start = tdata.get("start_time", "Unknown")
        end = tdata.get("end_time", "Unknown")
        duration = tdata.get("audio_duration", 0)
        is_green = tdata.get("is_green", False)
        photos = tdata.get("evidence", tdata.get("photos", []))
        
        evidence_chain.append(f"\n--- Context: {ctx} ---")
        evidence_chain.append(f"Time: {start} → {end} ({duration}s recording)")
        evidence_chain.append(f"Status: {'COMPLETE ✓' if is_green else 'PARTIAL'}")
        evidence_chain.append(f"Audio: Surveyor voice note included as audio part (LISTEN CAREFULLY)")
        
        for p in photos:
            fname = p.get("filename", "unknown")
            ts = p.get("timestamp", "N/A")
            evidence_chain.append(f"  Photo: {fname} at {ts}")
    
    evidence_chain.append("\n=== PHOTO REFERENCE TABLE ===")
    evidence_chain.append("(Link your analysis to specific image filenames)")
    
    # LIMIT: Send max 15 images per room
    selected_images = images[:15]
    
    for img_rel, img_abs, ctx in selected_images:
        meta = timeline_map.get(os.path.basename(img_rel), {"context": ctx})
        evidence_chain.append(f"- {os.path.basename(img_rel)}: Context={meta['context']}, Timestamp={meta.get('timestamp', 'N/A')}")
    
    # ============================================================
    # 4. Upload to Gemini (Images + Audio + Prompt)
    # ============================================================
    gemini_parts = [
        "\n".join(evidence_chain),
        "\nInstructions: "
        "1. LISTEN to all audio voice notes — they contain the surveyor's professional observations about each context. "
        "2. Use the surveyor's spoken observations as PRIMARY evidence alongside the photos. "
        "3. Link your analysis to SPECIFIC image filenames. "
        "4. Cross-reference audio observations with photo evidence — note any correlations or contradictions. "
        "5. Highlight any context mismatches between metadata and actual content."
    ]
    
    try:
        # Upload images
        for img_rel, img_abs, ctx in selected_images:
            try:
                uploaded_file = genai.upload_file(img_abs, mime_type="image/jpeg")
                gemini_parts.append(uploaded_file)
            except Exception as e:
                print(f"      [WARN] Failed to upload image {img_rel}: {e}")
        
        # Upload audio files (Gemini 2.5 Flash supports multimodal audio)
        # Limit to max 8 audio files to stay within token budget
        selected_audio = audio_files[:8]
        for audio_path, ctx in selected_audio:
            try:
                # Determine correct mime type
                ext = os.path.splitext(audio_path)[1].lower()
                mime_map = {
                    '.m4a': 'audio/mp4',
                    '.mp3': 'audio/mpeg',
                    '.wav': 'audio/wav',
                    '.aac': 'audio/aac',
                    '.opus': 'audio/ogg',
                }
                mime_type = mime_map.get(ext, 'audio/mp4')
                
                uploaded_audio = genai.upload_file(audio_path, mime_type=mime_type)
                gemini_parts.append(uploaded_audio)
                print(f"      [AUDIO] Uploaded {os.path.basename(audio_path)} ({ctx}) as {mime_type}")
            except Exception as e:
                print(f"      [WARN] Failed to upload audio {audio_path}: {e}")
        
        print(f"      [GEMINI] Sending {len(selected_images)} images + {len(selected_audio)} audio files for room {room_id}")
        
        # Call Model
        model = genai.GenerativeModel(MODEL_NAME, system_instruction=system_prompt)
        response = await model.generate_content_async(gemini_parts)
        
        # Parse
        response_text = response.text
        clean_text = response_text.replace("```json", "").replace("```", "").strip()
        analysis = json.loads(clean_text)
        
        if "rooms" in analysis and len(analysis["rooms"]) > 0:
            return analysis["rooms"][0]
        
        return analysis
        
    except Exception as e:
        print(f"      X Analysis Failed for {room_id}: {str(e).encode('ascii', 'replace')}")
        return {
            "room_id": room_id,
            "error": str(e),
            "elements": []
        }

async def generate_partial_room_report(session_dirs: list, room_id: str, session_data: dict, excluded_photos: list = None):
    """
    Gemini Arch: Generates the report for a SINGLE room.
    Accepts session_dirs: list of ALL session directories to scan for evidence.
    excluded_photos: list of filenames to skip.
    """
    print(f"Let's START PARTIAL FORENSIC ANALYSIS for Room {room_id} across {len(session_dirs)} session dirs")
    prompt_engine = get_prompt_engine()
    system_prompt = prompt_engine.render_prompt("forensic_surveyor.j2", {})
    
    if "ERROR" in system_prompt:
        return {"error": f"Prompt rendering failed: {system_prompt}"}
        
    rooms = session_data.get("floor_plan", {}).get("rooms", [])
    target_room = next((r for r in rooms if r.get("id") == room_id), None)
    
    if not target_room:
        return {"error": f"Room {room_id} not found in session data."}
        
    result = await analyze_room(target_room, session_dirs, system_prompt, excluded_photos=excluded_photos or [])
    return result

async def voice_edit_partial_report(current_chunk_json: dict, edit_instruction: str):
    """
    Gemini Arch: Performs a surgical edit on a JSON chunk based on a voice instruction.
    """
    print(f"Applying Surgical Voice Edit to Chunk. Instruction: {edit_instruction}")
    
    system_instruction = (
        "You are an expert RICS Surveyor Assistant. "
        "You will be given a JSON object representing a section of a Building Survey Report. "
        "You will also be given a voice instruction from the Lead Surveyor. "
        "Your task is to apply the surveyor's instruction to the JSON object. "
        "CRITICAL: You MUST return ONLY the updated valid JSON object. Do not change the JSON schema structure. "
        "Keep the same keys, just update the values (e.g. description, condition rating, defects) as requested."
    )
    
    prompt = f"VOICE INSTRUCTION:\n{edit_instruction}\n\nCURRENT JSON CHUNK:\n{json.dumps(current_chunk_json, indent=2)}"
    
    model = genai.GenerativeModel(MODEL_NAME, system_instruction=system_instruction)
    
    try:
        response = await model.generate_content_async(prompt)
        response_text = response.text
        clean_text = response_text.replace("```json", "").replace("```", "").strip()
        updated_chunk = json.loads(clean_text)
        return updated_chunk
    except Exception as e:
        print(f"Voice Edit Failed: {str(e)}")
        return current_chunk_json
