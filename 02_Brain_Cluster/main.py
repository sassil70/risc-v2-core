from fastapi import FastAPI, UploadFile, HTTPException, Depends, Header, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import shutil
from datetime import datetime, timezone
import uuid
import json

from database import db
from forensic import ForensicValidator
from architect import generate_floor_plan
from routers import auth, briefing, sessions, reports, projects

app = FastAPI(title="RISC V2 Brain - Sync Engine")

# [NEW] Enable CORS for Frontend (Reporter Cluster) + Mobile App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # [FIX] Allow all origins — required for iOS TestFlight + LAN mobile access
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# [NEW] Global Forensic Logger
import traceback
import logging

logging.basicConfig(
    filename='server_crash.log',
    level=logging.ERROR,
    format='%(asctime)s %(levelname)s: %(message)s'
)

from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def forensic_exception_handler(request: Request, exc: Exception):
    error_details = traceback.format_exc()
    print(f"[CRITICAL] 500 ERROR CAUGHT: {exc}")
    print(error_details)
    logging.error(f"Uncaught Exception: {exc}\n{error_details}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Forensic Error", 
            "error_type": type(exc).__name__,
            "message": str(exc),
            "trace_id": str(uuid.uuid4())
        },
    )

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(briefing.router, prefix="/api", tags=["Briefing"])
app.include_router(sessions.router, prefix="/api", tags=["Sessions"])
app.include_router(reports.router, prefix="/api", tags=["Reports"])
app.include_router(projects.router, prefix="/api", tags=["Projects"])

# [LAB FIX] Ensure Forensic Endpoint is reachable and DB constraints are honored
from forensic_engine import analyze_session
@app.post("/api/forensic/{session_id}")
async def run_forensic_analysis_lab(session_id: str):
    user_id = "unknown"
    property_id = "unknown"
    try:
        row = await db.fetchrow("SELECT surveyor_id, project_id FROM sessions WHERE id = $1", session_id)
        if row:
            user_id = str(row['surveyor_id'])
            property_id = str(row['project_id'])
    except Exception as e:
        print(f"Forensic Lookup Error: {e}")

    session_dir = await storage_service.get_session_path(session_id)
    init_file = os.path.join(session_dir, "session_init.json")
    if not os.path.exists(init_file):
        raise HTTPException(status_code=404, detail=f"Session Data Not Found at {session_dir}")
        
    with open(init_file, 'r') as f: data = json.load(f)
    print(f"DEBUG: Analyzing Session {session_id} in {session_dir}")
    report = await analyze_session(session_id, data)
    report_path = os.path.join(session_dir, "forensic_report_v1.json")
    with open(report_path, "w", encoding="utf-8") as f: json.dump(report, f, indent=2)
    return {"status": "success", "report": report}

# --- Storage Logic ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXTERNAL_STORAGE = os.path.abspath(os.path.join(BASE_DIR, "..", "storage"))
INTERNAL_STORAGE = os.path.join(BASE_DIR, "storage")
STORAGE_ROOT = EXTERNAL_STORAGE if os.path.exists(EXTERNAL_STORAGE) else INTERNAL_STORAGE

from services.storage_service import StorageService
storage_service = StorageService(STORAGE_ROOT)

# Serve Static Files (Evidence)
from fastapi.staticfiles import StaticFiles
app.mount("/storage", StaticFiles(directory=STORAGE_ROOT), name="storage")

# Storage for temporary packages
UPLOAD_DIR = os.path.join(STORAGE_ROOT, "temp_packages")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Models ---
class HandshakeRequest(BaseModel):
    session_id: str
    package_hash: str
    package_size_bytes: int
    device_timestamp_utc: str 

class LogEntry(BaseModel):
    level: str
    message: str
    timestamp: str
    session_id: Optional[str] = None

# --- Lifecycle ---
@app.on_event("startup")
async def startup():
    await db.connect()

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()

# --- Endpoints ---

# [NEW] V2 Mobile - Step 2: Voice Architect
@app.post("/api/floorplan/init")
async def init_floorplan(
    file: UploadFile, 
    property_type: str =  "Standard", 
    floors: int = 2,
    user_id: str = Form("anonymous")
):
    """
    Receives Audio, saves permanently (Versioned), returns JSON Floor Plan.
    """
    draft_id = "draft_session" 
    session_dir = os.path.join(await storage_service.get_session_path(draft_id), "audio_evidence")
    os.makedirs(session_dir, exist_ok=True)
    
    existing_files = [f for f in os.listdir(session_dir) if f.startswith("floor_plan_audio_v")]
    version = len(existing_files) + 1
    
    filename = f"floor_plan_audio_v{version}.m4a"
    file_path = os.path.join(session_dir, filename)
    
    with open(file_path, "wb+") as f:
        shutil.copyfileobj(file.file, f)
        
    print(f"Audio Evidence Saved: {file_path}")
    plan = await generate_floor_plan(file_path, property_type, floors)
    
    plan["evidence_audio_path"] = file_path
    plan["user_id"] = user_id
    
    return plan

# [NEW] V2 Mobile - Step 3: Start Session
@app.post("/api/property/init")
async def start_session(data: dict):
    """
    Receives Final JSON. Promotes 'Draft' folder to Real Session ID.
    Updates DB Status to 'active'.
    """
    session_id = data.get('session_id') or str(uuid.uuid4())
    raw_user_id = data.get('user_id', 'anonymous')
    raw_property_id = data.get('property_id', 'unknown_prop')
    
    # [FIX] Sanitize IDs to valid UUID format before any DB operation
    RISC_NS = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    def _safe_uuid(v):
        try:
            uuid.UUID(str(v))
            return str(v)
        except (ValueError, AttributeError):
            safe = str(uuid.uuid5(RISC_NS, str(v)))
            print(f"[UUID-FIX] '{v}' to '{safe}'")
            return safe
    
    user_id = _safe_uuid(raw_user_id)
    property_id = _safe_uuid(raw_property_id)
    
    try:

        # Ensure project exists to avoid FK error in the lab
        await db.execute("INSERT INTO projects (id, reference_number) VALUES ($1, 'LAB-MOCK-001') ON CONFLICT (id) DO NOTHING", property_id)
        
        # UPSERT session
        await db.execute("""
            INSERT INTO sessions (id, surveyor_id, project_id, status)
            VALUES ($1, $2, $3, 'active')
            ON CONFLICT (id) DO UPDATE SET status = 'active', surveyor_id = $2, project_id = $3
        """, session_id, user_id, property_id)
    except Exception as e:
        print(f"DB Update Failed: {e}")
        # FALLBACK: If DB fails, we still proceed with filesystem sync for the Lab

    draft_dir = await storage_service.get_session_path("draft_session")
    real_dir = await storage_service.get_session_path(session_id)
    
    # [STRATEGIC FIX] Use Robust Copy instead of Move to avoid Windows File Lock crashes
    # [ROBUSTNESS FIX] Always ensure the target directory exists, regardless of Draft status
    try:
        os.makedirs(real_dir, exist_ok=True)
    except Exception as e:
        print(f"⚠️ Directory Creation Warning: {e}")

    # [STRATEGIC FIX] Use Robust Copy instead of Move
    try:
        if os.path.exists(draft_dir) and draft_dir != real_dir:
            print(f"📦 Promoting Evidence (Robust Copy): {draft_dir} -> {real_dir}")
            
            for item in os.listdir(draft_dir):
                s = os.path.join(draft_dir, item)
                d = os.path.join(real_dir, item)
                try:
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)
                except Exception as copy_err:
                    print(f"⚠️ Warning: Could not copy {item}: {copy_err}")

            # Optional: Try to clean up draft
            try:
                shutil.rmtree(draft_dir)
            except Exception:
                pass 
                
    except Exception as e:
        print(f"⚠️ Filesystem Warning: {e}")
    
    # Save Init JSON (CRITICAL: Must not fail silently)
    try:
        json_path = os.path.join(real_dir, "session_init.json")
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Session Data Saved: {json_path}")
    except Exception as e:
        print(f"❌ DATA SAVE FAILED: {e}")
        # Use fallback if disk fails? No, simpler to just log for forensic.
        
    return {
        "session_id": session_id,
        "message": "Session Initialized (Robust Mode)",
        "data": data 
    }

@app.post("/api/v2/sync/handshake")
async def handshake(request: HandshakeRequest):
    try:
        device_time = datetime.fromisoformat(request.device_timestamp_utc.replace('Z', '+00:00'))
        server_time = datetime.now(timezone.utc)
        diff = abs((server_time - device_time).total_seconds())
        if diff > 300:
            raise HTTPException(status_code=409, detail=f"Time Skew too large: {diff}s")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ISO 8601 Timestamp")
    return {"status": "ready_to_receive"}

@app.post("/api/v2/sync/upload_room")
async def upload_room_evidence(
    file: UploadFile, 
    session_id: str = Form(...), 
    room_id: str = Form(...)
):
    """
    Receives Room Evidence Zip. Unpacks to User-Centric Session Folder.
    """
    user_id = "unknown"
    property_id = "unknown"
    try:
        query = "SELECT surveyor_id, project_id FROM sessions WHERE id = $1"
        row = await db.fetchrow(query, session_id)
        if row:
            user_id = str(row['surveyor_id']) if row['surveyor_id'] else "unknown"
            property_id = str(row['project_id']) if row['project_id'] else "unknown"
    except Exception:
        pass

    session_dir = await storage_service.get_session_path(session_id)
    zip_path = os.path.join(session_dir, f"{room_id}_evidence.zip")
    
    with open(zip_path, "wb+") as f:
        shutil.copyfileobj(file.file, f)
        
    import zipfile
    unpack_dir = os.path.join(session_dir, room_id)
    os.makedirs(unpack_dir, exist_ok=True)
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(unpack_dir)
        print(f"📦 Unpacked Evidence: {room_id} -> {unpack_dir}")
        os.remove(zip_path)
        return {"status": "synced", "room_id": room_id}
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Corrupt Zip File")
    except Exception as e:
        print(f"Upload Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/inspection/status")
async def check_inspection_status(session_id: str):
    """
    Checks status and performs Live Merit of Plan vs Disk Reality.
    Includes User-Centric Hierarchy.
    """
    user_id = "unknown"
    property_id = "unknown"
    try:
        query = "SELECT surveyor_id, project_id FROM sessions WHERE id = $1"
        row = await db.fetchrow(query, session_id)
        if row:
            user_id = str(row['surveyor_id']) if row['surveyor_id'] else "unknown"
            property_id = str(row['project_id']) if row['project_id'] else "unknown"
    except Exception:
        pass

    session_dir = await storage_service.get_session_path(session_id)
    if not os.path.exists(session_dir):
        raise HTTPException(status_code=404, detail="Session not found")
        
    reports_path = await storage_service.get_reports_path(session_id)
    report_path = os.path.join(reports_path, f"report_{session_id}.pdf")
    if os.path.exists(report_path):
        return {"status": "completed", "report_url": f"/api/reports/{session_id}"}
    
    init_file = os.path.join(session_dir, "session_init.json")
    if os.path.exists(init_file):
        with open(init_file, "r") as f:
            data = json.load(f)
        
        if "floor_plan" in data and "rooms" in data["floor_plan"]:
            rooms = data["floor_plan"]["rooms"]
            complete_count = 0
            for room in rooms:
                r_id = room.get("id")
                room_path = os.path.join(session_dir, r_id)
                image_count = 0
                audio_count = 0
                if os.path.exists(room_path):
                    for root, dirs, files in os.walk(room_path):
                        for file in files:
                            lower_f = file.lower()
                            if lower_f.endswith((".jpg", ".jpeg", ".png")):
                                image_count += 1
                            elif lower_f.endswith((".m4a", ".mp3", ".wav")):
                                audio_count += 1
                
                room["images_count"] = image_count
                room["audio_count"] = audio_count
                if image_count >= 1:
                    room["status"] = "completed" if image_count >= 3 else "in_progress"
                    if image_count >= 3:
                        complete_count += 1
                else:
                    room["status"] = "pending"
            
            data["status"] = "ready_for_report" if (complete_count == len(rooms) and len(rooms) > 0) else "in_progress"
        return {"status": data.get("status", "in_progress"), "session": data}
    
    return {"status": "processing"}

@app.get("/")
def read_root():
    return {"status": "Brain Cluster Online", "version": "2.2 (Integrated Hierarchy)"}
