import os
import json
import logging
import asyncio
import google.generativeai as genai

logger = logging.getLogger("SynthesisEngine")

MODEL_NAME = os.getenv("GEMINI_MODEL_KEY", "gemini-3-flash-preview")

async def _resolve_project_semantic_path(project_id: str):
    """
    Helps components find the dedicated semantic folder for a specific project.
    """
    from database import db
    from services.storage_service import get_storage_service
    
    storage = get_storage_service()
    
    # Fast check: If project_id is not a UUID, query by reference_number
    import uuid
    try:
        uuid.UUID(str(project_id))
        query = "SELECT reference_number, client_name FROM projects WHERE id = $1"
    except ValueError:
        query = "SELECT reference_number, client_name FROM projects WHERE reference_number = $1"
        
    row = await db.fetchrow(query, project_id)
    if not row:
        return None
        
    ref = row['reference_number'] or "UNKNOWN_REF"
    client = row['client_name'] or "Unknown_Client"
    
    safe_ref = str(ref).replace("/", "-").replace("\\", "-").replace(" ", "_")
    safe_client = str(client).replace("/", "-").replace("\\", "-").replace(" ", "_")
    project_folder = f"{safe_ref}_{safe_client}"
    
    return os.path.join(storage.storage_root, "Projects", project_folder)

async def synthesize_property_master_state(project_id: str):
    """
    1. Find all sessions for the project.
    2. Read all room JSON reports from those sessions.
    3. Aggregate into a single master state.
    4. Pass to Gemini to generate Executive Summary.
    5. Save Master State to Project's semantic folder.
    """
    # Late imports for dependencies resolving order
    from database import db
    from services.storage_service import get_storage_service
    from services.prompt_engine import get_prompt_engine
    
    storage = get_storage_service()
    
    # 1. Get Project Details & Sessions
    project_query = "SELECT reference_number, client_name, site_metadata FROM projects WHERE id = $1"
    project_row = await db.fetchrow(project_query, project_id)
    if not project_row:
        raise ValueError(f"Project {project_id} not found.")
        
    ref = project_row['reference_number'] or "UNKNOWN_REF"
    client = project_row['client_name'] or "Unknown_Client"
    
    # Handle potentially malformed JSON strings in DB gracefully
    raw_metadata = project_row['site_metadata']
    if isinstance(raw_metadata, str):
        try:
            site_metadata = json.loads(raw_metadata)
        except json.JSONDecodeError:
            site_metadata = {}
    elif isinstance(raw_metadata, dict):
        site_metadata = raw_metadata
    else:
        site_metadata = {}
    
    sessions_query = "SELECT id, started_at FROM sessions WHERE project_id = $1 ORDER BY started_at ASC"
    session_rows = await db.fetch(sessions_query, project_id)
    
    aggregated_rooms = {}
    
    for s_row in session_rows:
        session_id = str(s_row['id'])
        reports_dir = await storage.get_reports_path(session_id)
        
        if os.path.exists(reports_dir):
            for filename in os.listdir(reports_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(reports_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            room_data = json.load(f)
                            room_id = room_data.get('room_id', filename.replace('.json', ''))
                            # Overwrite older session data with newer session data for the same room
                            aggregated_rooms[room_id] = room_data
                    except Exception as e:
                        logger.error(f"Error reading room report {filepath}: {e}")
                        
    # Separate the executive summary room from standard rooms
    executive_room = aggregated_rooms.get("executive_summary")
    standard_rooms = [r for r in aggregated_rooms.values() if r.get('room_id') != 'executive_summary']

    # 2. Build Master State
    master_state = {
        "project_id": project_id,
        "reference_number": ref,
        "client_name": client,
        "property_details": {
            "type": site_metadata.get("property_type", "Unknown"),
            "floors": site_metadata.get("number_of_floors", 1),
            "tenure": site_metadata.get("tenure", "Unknown"),
            "occupancy_status": site_metadata.get("occupancy_status", "Unknown"),
            "construction_age": site_metadata.get("construction_age", "Unknown"),
            "weather_conditions": site_metadata.get("weather_conditions", "Unknown"),
            "utilities_services": site_metadata.get("utilities_services", {}),
            "address": site_metadata.get("address", {})
        },
        "rooms": standard_rooms,
        "global_executive_raw": executive_room.get("ai_room_narrative", "Surveyor did not provide a recorded overall opinion.") if executive_room else "Surveyor did not provide a recorded overall opinion."
    }
    
    # 3. Generate Executive Summary using Gemini
    prompt_engine = get_prompt_engine()
    prompt = prompt_engine.render_prompt("synthesis/executive_summary.j2", {
        "property_master_state": json.dumps(master_state, indent=2)
    })
    
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = await model.generate_content_async(prompt)
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
            
        exec_summary = json.loads(text.strip())
        master_state["executive_summary"] = exec_summary
    except Exception as e:
        logger.error(f"AI Synthesis Failed: {e}")
        master_state["executive_summary"] = {
            "error": str(e),
            "section_a": {
                "overall_opinion": "AI Synthesis Failed. See error logs.",
                "key_defects": []
            },
            "section_b": {
                "structural_integrity": "Data aggregation completed, but AI analysis failed.",
                "safety_concerns": []
            }
        }

    # 4. Save Master State to Project's Semantic Directory
    safe_ref = str(ref).replace("/", "-").replace("\\", "-").replace(" ", "_")
    safe_client = str(client).replace("/", "-").replace("\\", "-").replace(" ", "_")
    project_folder = f"{safe_ref}_{safe_client}"
    
    project_path = os.path.join(storage.storage_root, "Projects", project_folder)
    os.makedirs(project_path, exist_ok=True)
    master_file_path = os.path.join(project_path, "Property_Master_State.json")
    
    with open(master_file_path, 'w', encoding='utf-8') as f:
        json.dump(master_state, f, indent=4)
        
    return master_state
