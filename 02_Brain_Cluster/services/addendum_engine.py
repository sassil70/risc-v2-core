import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger("AddendumEngine")
MODEL_NAME = os.getenv("GEMINI_MODEL_KEY", "gemini-3-flash-preview")

async def process_voice_addendum(project_id: str, room_id: str, audio_path: str):
    """
    Surgically updates a room's JSON report based on a voice addendum,
    then triggers the Macro-AI Synthesis engine to update the Master State.
    """
    from database import db
    from services.storage_service import get_storage_service
    from services.synthesis_engine import synthesize_property_master_state
    from services.prompt_engine import get_prompt_engine
    
    storage = get_storage_service()
    
    # 1. Locate the Project Context
    project_query = "SELECT reference_number, client_name FROM projects WHERE id = $1"
    project_row = await db.fetchrow(project_query, project_id)
    if not project_row:
        raise ValueError(f"Project {project_id} not found.")
        
    ref = project_row['reference_number'] or "UNKNOWN_REF"
    client = project_row['client_name'] or "Unknown_Client"
    
    safe_ref = str(ref).replace("/", "-").replace("\\", "-").replace(" ", "_")
    safe_client = str(client).replace("/", "-").replace("\\", "-").replace(" ", "_")
    project_folder = f"{safe_ref}_{safe_client}"
    
    # 2. Find the Latest Room JSON in Semantic Storage
    # We must scan all sessions for this project and find the latest [room_id].json
    sessions_query = "SELECT id FROM sessions WHERE project_id = $1 ORDER BY started_at DESC"
    session_rows = await db.fetch(sessions_query, project_id)
    
    target_filepath = None
    target_session_id = None
    existing_room_data = {
        "room_id": room_id,
        "room_name": "Unknown Room",
        "context": "General",
        "analysis": {"summary": "No previous inspection data.", "elements": []}
    }
    
    for s_row in session_rows:
        session_id = str(s_row['id'])
        reports_dir = await storage.get_reports_path(session_id)
        potential_path = os.path.join(reports_dir, f"{room_id}.json")
        if os.path.exists(potential_path):
            target_filepath = potential_path
            target_session_id = session_id
            try:
                with open(potential_path, 'r', encoding='utf-8') as f:
                    existing_room_data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to read {potential_path}: {e}")
            break # Found the latest one
            
    # If room was never scanned, we create a new standalone session folder for addendums
    if not target_filepath:
        import uuid
        import datetime
        fallback_session_id = f"addendum_{uuid.uuid4().hex[:8]}"
        await db.execute(
            "INSERT INTO sessions (id, project_id, started_at) VALUES ($1, $2, $3)",
            fallback_session_id, project_id, datetime.datetime.now(datetime.timezone.utc)
        )
        reports_dir = await storage.get_reports_path(fallback_session_id)
        target_filepath = os.path.join(reports_dir, f"{room_id}.json")
        target_session_id = fallback_session_id
        logger.info(f"Target Room JSON not found. Creating baseline at {target_filepath}")

    # 3. Upload Audio to Gemini
    print(f"Uploading Voice Addendum for Room {room_id}...")
    try:
        audio_file = genai.upload_file(audio_path, mime_type="audio/mp4") 
    except Exception as e:
        raise RuntimeError(f"Gemini Upload Failed: {e}")

    # 4. Generate the Update
    print(f"Generating Surgical Update for Room {room_id}...")
    prompt_engine = get_prompt_engine()
    prompt = prompt_engine.render_prompt("addendum/room_modification.j2", {
        "current_report": json.dumps(existing_room_data, indent=2),
        "voice_addendum": "SEE ATTACHED AUDIO" # Direct instruction for multimodal
    })
    
    model = genai.GenerativeModel(MODEL_NAME, system_instruction=prompt)
    
    try:
        response = model.generate_content(["Please apply the attached spoken modifications.", audio_file])
        text = response.text.strip()
        
        # Clean JSON markdown blocks
        if "```json" in text:
            text = text.split("```json")[-1]
        elif "```JSON" in text:
            text = text.split("```JSON")[-1]
        elif "```" in text:
            text = text.split("```")[-1]
            
        if "```" in text:
            text = text.split("```")[0]
            
        updated_room_json = json.loads(text.strip())
        
        # Safety enforcement
        updated_room_json["room_id"] = room_id
        
        # 5. Save Back to Semantic Storage
        with open(target_filepath, 'w', encoding='utf-8') as f:
            json.dump(updated_room_json, f, indent=4)
            
        print(f"✅ Room {room_id} Successfully Patched at {target_filepath}")
        
    except Exception as e:
        print(f"❌ Addendum Generation Failed: {e}")
        raise RuntimeError(f"Modification Failed: {e}")
        
    # 6. Trigger Synthesis Ripple
    print("Triggering Macro-Synthesis Ripple...")
    await synthesize_property_master_state(project_id)
    print("✅ Macro-Synthesis Complete.")

    return updated_room_json
