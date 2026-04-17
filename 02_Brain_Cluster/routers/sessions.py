from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from database import db
import uuid
import json
import os

router = APIRouter()

# [CRITICAL FIX] UUID Sanitizer — converts non-UUID strings to deterministic UUIDs
RISC_NS = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
def _safe_uuid(v):
    """Convert any string to a valid UUID. If already UUID, return as-is."""
    try:
        uuid.UUID(str(v))
        return str(v)
    except (ValueError, AttributeError):
        safe = str(uuid.uuid5(RISC_NS, str(v)))
        print(f"[UUID-FIX] '{v}' → '{safe}'")
        return safe


from services.storage_service import get_storage_service

# --- Storage Logic ---
storage_service = get_storage_service()

# --- Models ---
class Session(BaseModel):
    id: str
    title: str
    status: str
    created_at: datetime
    project_id: Optional[str] = None
    surveyor_id: Optional[str] = None

class SessionCreate(BaseModel):
    title: str
    surveyor_id: str
    project_id: str

# --- Endpoints ---

@router.get("/surveyor/test")
async def test_route():
    return {"status": "Sessions Router Active"}

@router.get("/surveyor/sessions", response_model=List[Session])
async def get_sessions(user_id: str):
    """
    List all sessions for a specific surveyor.
    """
    # Use started_at as created_at. Handle missing title with coalesce or update schema.
    # Postgres UUID columns reject non-UUID strings. 'anonymous' must be bypassed or replaced.
    valid_uuid = user_id if len(user_id) == 36 else '00000000-0000-0000-0000-000000000000'
    
    query = """
        SELECT id, COALESCE(title, 'Untitled Session') as title, status, started_at as created_at, project_id, surveyor_id 
        FROM sessions 
        WHERE surveyor_id = $1 
        ORDER BY started_at DESC
    """
    try:
        rows = await db.fetch(query, valid_uuid)
    except Exception as e:
        print(f"Session fetch error: {e}")
        rows = []
    results = []
    for row in rows:
        d = dict(row)
        d['id'] = str(d['id'])
        if d.get('project_id'): d['project_id'] = str(d['project_id'])
        if d.get('surveyor_id'): d['surveyor_id'] = str(d['surveyor_id'])
        results.append(d)
    return results

# --- Helper: Storage Repository (Single Source of Truth) ---
def scan_permament_storage():
    """
    Scans the STORAGE_ROOT for valid session folders.
    Returns a list of standardized session objects.
    """
    results = []
    sessions_dir = os.path.join(storage_service.storage_root, "sessions")
    
    if not os.path.exists(sessions_dir):
        return []

    for item in os.listdir(sessions_dir):
        item_path = os.path.join(sessions_dir, item)
        if os.path.isdir(item_path):
            # 1. Base Metadata
            session_meta = {
                "id": item,
                "title": f"Inspection: {item[:8]}...", # Default
                "status": "in_progress",
                "created_at": datetime.fromtimestamp(os.path.getctime(item_path)),
                "project_id": "local",
                "surveyor_id": "local"
            }
            
            # 2. Enrich from session_init.json (The Truth)
            init_file = os.path.join(item_path, "session_init.json")
            if os.path.exists(init_file):
                try:
                    with open(init_file, 'r') as f:
                        data = json.load(f)
                        if "address" in data:
                            addr = data["address"]
                            session_meta["title"] = addr.get("full_address", addr.get("city", session_meta["title"]))
                        if "status" in data:
                            session_meta["status"] = data["status"]
                        # We could also parse timestamp but os.ctime is reliable enough for lists
                except Exception:
                    pass # Keep default metadata if file is unreadable
            
            results.append(session_meta)
            
    # Sort by newest first
    results.sort(key=lambda x: x['created_at'], reverse=True)
    return results

@router.get("/sessions", response_model=List[Session])
async def get_all_sessions():
    """
    Admin/Dashboard: List ALL sessions.
    Hybrid Strategy: Pefer DB, seamlessly merge/fallback to Storage.
    """
    db_results = []
    try:
        query = """
            SELECT id, COALESCE(title, 'Untitled Session') as title, status, started_at as created_at, project_id, surveyor_id 
            FROM sessions 
            ORDER BY started_at DESC
        """
        rows = await db.fetch(query)
        for row in rows:
            d = dict(row)
            d['id'] = str(d['id'])
            if d.get('project_id'): d['project_id'] = str(d['project_id'])
            if d.get('surveyor_id'): d['surveyor_id'] = str(d['surveyor_id'])
            db_results.append(d)
    except Exception:
        # DB unavailable, proceed to storage scan
        pass

    # If DB is empty or down, use Storage
    if not db_results:
        print(f"DEBUG: Entering Storage Scan. Root: {STORAGE_ROOT}")
        try:
            return scan_permament_storage()
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"CRITICAL ERROR in scan: {e}")
            return []
    
    return db_results

@router.post("/surveyor/sessions", response_model=Session)
async def create_session(session: SessionCreate):
    """
    Create a new inspection session or return an existing active/pending session for the project.
    """
    # 0. Check for existing active/pending session for this project
    if session.project_id:
        check_active_query = """
            SELECT id, title, status, started_at as created_at, project_id, surveyor_id
            FROM sessions
            WHERE surveyor_id = $1 AND project_id = $2 AND status IN ('pending', 'active')
            ORDER BY started_at DESC LIMIT 1
        """
        existing_row = await db.fetchrow(check_active_query, _safe_uuid(session.surveyor_id), _safe_uuid(session.project_id))
        if existing_row:
            result = dict(existing_row)
            result['id'] = str(result['id'])
            result['project_id'] = str(result['project_id'])
            result['surveyor_id'] = str(result['surveyor_id'])
            # We must also ensure any existing floor_plan from storage is sent back, but this endpoint just returns the Session model. 
            # The client usually calls `/inspection/status` to get the full floor_plan anyway.
            return result

    # 1. Generate ID
    session_id = str(uuid.uuid4())
    
    # 1.5 Title Deduplication
    base_title = session.title.strip()
    final_title = base_title
    
    # Check for identical titles
    check_query = "SELECT title FROM sessions WHERE surveyor_id = $1 AND title ILIKE $2"
    existing_titles_rows = await db.fetch(check_query, _safe_uuid(session.surveyor_id), f"{base_title}%")
    existing_titles = [r['title'] for r in existing_titles_rows]
    
    if base_title in existing_titles:
        counter = 2
        while True:
            candidate = f"{base_title} ({counter})"
            if candidate not in existing_titles:
                final_title = candidate
                break
            counter += 1

    # 2. Insert into DB
    query = """
        INSERT INTO sessions (id, title, surveyor_id, project_id, status, started_at)
        VALUES ($1, $2, $3, $4, 'pending', NOW())
        RETURNING id, title, status, started_at as created_at, project_id, surveyor_id
    """
    
    try:
        row = await db.fetchrow(
            query, 
            session_id, 
            final_title, 
            _safe_uuid(session.surveyor_id), 
            _safe_uuid(session.project_id)
        )
        result = dict(row)
        result['id'] = str(result['id'])
        result['project_id'] = str(result['project_id'])
        result['surveyor_id'] = str(result['surveyor_id'])
        # return result -> moved to end
    except Exception as e:
        print(f"Session Creation Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")

    # 3. [NEW] Hydrate from Project (Dashboard Integration)
    if session.project_id:
        try:
            # Fetch Project Data
            project_row = await db.fetchrow("SELECT site_metadata FROM projects WHERE id = $1", session.project_id)
            if project_row and project_row['site_metadata']:
                raw_meta = project_row['site_metadata']
                project_data = json.loads(raw_meta) if isinstance(raw_meta, str) else raw_meta
                
                # Construct Session Data
                session_data = {
                    "id": session_id,
                    "title": final_title,
                    "status": "pending",
                    "created_at": datetime.now().isoformat(),
                    "project_id": session.project_id,
                    "surveyor_id": session.surveyor_id,
                    "floor_plan": {
                        "rooms": project_data.get("rooms", [])
                    },
                    "address": {
                        "full_address": final_title 
                    }
                }

                # Write to Disk
                session_dir = await storage_service.get_session_path(session_id)
                os.makedirs(session_dir, exist_ok=True)
                with open(os.path.join(session_dir, "session_init.json"), "w") as f:
                    json.dump(session_data, f, indent=2)
                
                print(f"Session {session_id} hydrated from Project {session.project_id}")
        except Exception as e:
            print(f"Failed to hydrate session from project: {e}")

    return result
@router.get("/surveyor/sessions/{session_id}")
async def get_session_details(session_id: str):
    """
    Get full session details including the JSON data blob (Floor Plan).
    """
@router.get("/sessions/{session_id}")
async def get_session_details(session_id: str):
    """
    Get full session details.
    Truth is on Disk, but we use the DB to find the hierarchical path.
    """
    # 1. Get User/Property mapping from DB
    user_id = "unknown"
    property_id = "unknown"
    try:
        query = "SELECT surveyor_id, project_id, status, started_at, data FROM sessions WHERE id = $1"
        row = await db.fetchrow(query, session_id)
        if row:
            user_id = str(row['surveyor_id']) if row['surveyor_id'] else "unknown"
            property_id = str(row['project_id']) if row['project_id'] else "unknown"
            
            # 2. Try Disk Hierarchy (New Semantic Structure)
            session_dir = await storage_service.get_session_path(session_id)
            init_file = os.path.join(session_dir, "session_init.json")
            
            if os.path.exists(init_file):
                with open(init_file, 'r') as f:
                    data = json.load(f)
                data['id'] = session_id 
                return data
            
            # Fallback to DB data if file missing
            result = dict(row)
            session_data = json.loads(result['data']) if result['data'] else {}
            return {**session_data, **result}
    except Exception as e:
        print(f"Session Retrieval Error: {e}")
        
    raise HTTPException(status_code=404, detail="Session not found")

@router.get("/sessions/{session_id}/rooms/{room_id}/images")
async def get_room_images(session_id: str, room_id: str):
    """
    List all evidence media (Images & Audio) for a specific room.
    """
    # 1. Get User/Property mapping from DB to find the path
    user_id = "unknown"
    property_id = "unknown"
    try:
        query = "SELECT surveyor_id, project_id FROM sessions WHERE id = $1"
        row = await db.fetchrow(query, session_id)
        if row:
            user_id = str(row['surveyor_id']) if row['surveyor_id'] else "unknown"
            property_id = str(row['project_id']) if row['project_id'] else "unknown"
            
        # 2. Get the room directory in the hierarchy
        session_dir = await storage_service.get_session_path(session_id)
        room_dir = os.path.join(session_dir, room_id)
        
        if not os.path.exists(room_dir):
            return {"images": [], "audio": []}

        images = []
        audio = []
        
        for root, dirs, files in os.walk(room_dir):
            for f in files:
                lower_f = f.lower()
                abs_file = os.path.abspath(os.path.join(root, f))
                
                # web_path should be relative to the storage MOUNT, not the host storage root
                # but it must follow the new structure
                try:
                    rel_to_storage = os.path.relpath(abs_file, storage_service.storage_root)
                    web_path = "/storage/" + rel_to_storage.replace("\\", "/")
                    
                    if lower_f.endswith(('.jpg', '.jpeg', '.png')):
                         images.append(web_path)
                    elif lower_f.endswith(('.m4a', '.mp3', '.wav')):
                         audio.append(web_path)
                except ValueError:
                    continue
                    
        return {"images": images, "audio": audio}
    except Exception as e:
        print(f"Error listing media: {e}")
        return {"images": [], "audio": []}
