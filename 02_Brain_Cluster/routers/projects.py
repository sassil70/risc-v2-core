from fastapi import APIRouter, HTTPException, BackgroundTasks, Form, File, UploadFile
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import uuid
import json
import zipfile
import io
from database import db
import os
import logging

logger = logging.getLogger("projects")

router = APIRouter()

# --- Models ---
class Room(BaseModel):
    id: str
    name: str # e.g. "Living Room"
    type: str # e.g. "general", "kitchen", "wet_room"
    floor_name: Optional[str] = "Ground Floor"
    status: str = "pending"
    images_count: int = 0
    audio_count: int = 0
    has_partial_report: bool = False

class ProjectCreate(BaseModel):
    reference_number: str
    client_name: str
    metadata: Optional[dict] = {}

class ProjectResponse(BaseModel):
    id: str
    reference_number: str
    client_name: Optional[str]
    metadata: Optional[dict] = {}
    rooms: List[Room] = []
    created_at: str

class AddRoomRequest(BaseModel):
    name: str
    type: str
    floor_name: Optional[str] = "Ground Floor"

# --- Endpoints ---

@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects():
    """
    List all projects with their room configurations.
    """
    query = """
        SELECT id, reference_number, client_name, site_metadata, created_at 
        FROM projects 
        ORDER BY created_at DESC
    """
    rows = await db.fetch(query)
    
    results = []
    for row in rows:
        metadata = json.loads(row['site_metadata']) if isinstance(row['site_metadata'], str) else row['site_metadata']
        # Handle cases where metadata might be None or empty
        rooms_data = metadata.get('rooms', []) if metadata else []
        
        # Enrich rooms with media counts
        enriched_rooms = await _enrich_rooms_with_media_counts(str(row['id']), rooms_data)
        
        results.append({
            "id": str(row['id']),
            "reference_number": row['reference_number'],
            "client_name": row['client_name'],
            "metadata": metadata,
            "rooms": enriched_rooms,
            "created_at": str(row['created_at'])
        })
    return results

@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """
    Get a specific project's details and rooms to construct the Property Hub.
    """
    query = "SELECT id, reference_number, client_name, site_metadata, created_at FROM projects WHERE id = $1"
    row = await db.fetchrow(query, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
        
    metadata = json.loads(row['site_metadata']) if isinstance(row['site_metadata'], str) else row['site_metadata']
    rooms_data = metadata.get('rooms', []) if metadata else []
    
    # Enrich rooms with media counts
    enriched_rooms = await _enrich_rooms_with_media_counts(project_id, rooms_data)
    
    return {
        "id": str(row['id']),
        "reference_number": row['reference_number'],
        "client_name": row['client_name'],
        "metadata": metadata,
        "rooms": enriched_rooms,
        "created_at": str(row['created_at'])
    }

@router.post("/projects", response_model=ProjectResponse)
async def create_project(project: ProjectCreate):
    """
    Create a new inspection project foundation.
    """
    project_id = str(uuid.uuid4())
    
    # Initialize site_metadata with provided metadata and empty rooms list
    initial_metadata = project.metadata or {}
    initial_metadata["rooms"] = []
    
    query = """
        INSERT INTO projects (id, reference_number, client_name, site_metadata)
        VALUES ($1, $2, $3, $4)
        RETURNING created_at
    """
    try:
        val = await db.fetchval(query, project_id, project.reference_number, project.client_name, json.dumps(initial_metadata))
        return {
            "id": project_id,
            "reference_number": project.reference_number,
            "client_name": project.client_name,
            "metadata": initial_metadata,
            "rooms": [],
            "created_at": str(val)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Project Creation Failed: {e}")

@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, project_update: ProjectCreate):
    """
    Update an existing inspection project's foundation.
    """
    # 1. Check if exists and get current rooms
    select_query = "SELECT site_metadata, created_at FROM projects WHERE id = $1"
    row = await db.fetchrow(select_query, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")

    existing_metadata = json.loads(row['site_metadata']) if isinstance(row['site_metadata'], str) else row['site_metadata']
    existing_rooms = existing_metadata.get('rooms', []) if existing_metadata else []
    
    # 2. Update metadata while preserving rooms
    new_metadata = project_update.metadata or {}
    new_metadata["rooms"] = existing_rooms

    update_query = """
        UPDATE projects
        SET reference_number = $1, client_name = $2, site_metadata = $3
        WHERE id = $4
    """
    try:
        await db.execute(update_query, project_update.reference_number, project_update.client_name, json.dumps(new_metadata))
        return {
            "id": project_id,
            "reference_number": project_update.reference_number,
            "client_name": project_update.client_name,
            "metadata": new_metadata,
            "rooms": existing_rooms,
            "created_at": str(row['created_at'])
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Project Update Failed: {e}")

@router.post("/projects/{project_id}/rooms", response_model=List[Room])
async def add_room(project_id: str, room: AddRoomRequest):
    """
    Add a room (Scope) to the project.
    """
    # 1. Generate unique room ID
    room_id = f"{room.type}_{uuid.uuid4().hex[:8]}"
    
    new_room = {
        "id": room_id,
        "name": room.name,
        "type": room.type,
        "floor_name": room.floor_name,
        "status": "pending"
    }
    
    # 2. Append to JSONB array using PostgreSQL operators (Atomic Update avoids Race Condition)
    room_json = json.dumps(new_room)
    update_query = """
        UPDATE projects
        SET site_metadata = jsonb_set(
            COALESCE(site_metadata, '{}'::jsonb),
            '{rooms}',
            COALESCE((site_metadata->'rooms')::jsonb, '[]'::jsonb) || $1::jsonb
        )
        WHERE id = $2
        RETURNING site_metadata
    """
    row = await db.fetchrow(update_query, room_json, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
        
    metadata = json.loads(row['site_metadata']) if isinstance(row['site_metadata'], str) else row['site_metadata']
    return metadata.get('rooms', [])

from services.synthesis_engine import synthesize_property_master_state

@router.post("/projects/{project_id}/synthesize")
async def trigger_synthesis(project_id: str):
    """
    Triggers the Macro-AI Synthesis engine to aggregate all historical room data
    for a project into a Master State JSON with an Executive Summary.
    """
    try:
        master_state = await synthesize_property_master_state(project_id)
        return {"status": "success", "message": "Synthesis complete", "master_state": master_state}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {e}")

from fastapi import UploadFile, Form
import shutil
from services.addendum_engine import process_voice_addendum

@router.post("/projects/{project_id}/rooms/{room_id}/addendum")
async def addendum_endpoint(
    project_id: str, 
    room_id: str, 
    audio_file: UploadFile
):
    """
    Receives an audio file (Voice Addendum) and surgically updates the Room's JSON.
    """
    from services.storage_service import get_storage_service
    import uuid
    storage = get_storage_service()
    
    # Save audio temporarily
    temp_dir = os.path.join(storage.storage_root, "temp_addendums")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}.m4a")
    
    with open(temp_path, "wb+") as f:
        shutil.copyfileobj(audio_file.file, f)
        
    try:
        updated_json = await process_voice_addendum(project_id, room_id, temp_path)
        return {"status": "success", "room_id": room_id, "updated_data": updated_json}
    except Exception as e:
        # The original snippet had logger.error and raise HTTPException after a return, which is unreachable.
        # Assuming the intent was to log and raise on error.
        # logger.error(f"Failed to generate report for room {room_id}: {str(e)}") # logger not imported
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# --- PHASE 4.5: WebView Report Editor ---
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from services.synthesis_engine import _resolve_project_semantic_path # Import needed for this section
from pydantic import BaseModel
from typing import List

class RoomApprovalPayload(BaseModel):
    selected_diagnostic_images: List[str]

@router.put("/projects/{project_id}/rooms/{room_id}/approve")
async def approve_room(project_id: str, room_id: str, payload: RoomApprovalPayload):
    """
    Called by the Witness App to approve a room's AI narrative 
    and lock in the 1-3 selected diagnostic images into the final JSON state.
    """
    project_dir = await _resolve_project_semantic_path(project_id)
    if not project_dir:
        raise HTTPException(status_code=404, detail="Project not found")

    # Locate the definitive _final.json for this specific room
    room_final_path = None
    for root, dirs, files in os.walk(project_dir):
        if f"{room_id}_final.json" in files:
            room_final_path = os.path.join(root, f"{room_id}_final.json")
            break

    if not room_final_path:
        raise HTTPException(status_code=404, detail="Room final state JSON not found")

    with open(room_final_path, 'r', encoding='utf-8') as f:
        room_data = json.load(f)

    # Mutate state to official approval
    room_data['is_approved'] = True
    room_data['selected_diagnostic_images'] = payload.selected_diagnostic_images

    with open(room_final_path, 'w', encoding='utf-8') as f:
        json.dump(room_data, f, indent=4)

    # Critical: Trigger re-synthesis to ripple this approval up to the Master State
    await synthesize_property_master_state(project_id)

    return {"status": "success", "message": "Room images locked and approved."}

from services.rics_stamper import stamp_rics_report

@router.post("/projects/{project_id}/generate_final_rics_pdf")
async def generate_final_pdf(project_id: str):
    """
    Triggers the Macro-AI Synthesis, then routes the data to PyMuPDF to stamp T.pdf.
    """
    project_dir = await _resolve_project_semantic_path(project_id)
    if not project_dir:
        raise HTTPException(status_code=404, detail="Project not found")
        
    try:
        # 1. Fire the AI Synthesis Engine to aggregate everything
        await synthesize_property_master_state(project_id)
        
        # 2. Stamp the final PDF
        pdf_path = stamp_rics_report(project_id, project_dir)
        if pdf_path:
            return {"status": "success", "message": "RICS PDF Generated", "pdf_path": pdf_path}
        else:
            raise HTTPException(status_code=500, detail="PDF generation failed internally")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === NEW: Markdown-First Pipeline (with legal sections + Gemini) ===

@router.post("/projects/{project_id}/generate-final-report")
async def generate_final_report_md(project_id: str):
    """
    NEW Markdown-First pipeline for RICS Level 3 report generation.
    
    Pipeline:
      1. Gather project data + room data
      2. Map rooms → RICS elements  
      3. Generate Gemini narratives per element (30s timeout each)
      4. Generate smart legal sections H, I, L (45s timeout each)
      5. Auto-compute Section B (condition tables)
      6. Assemble full Markdown via Jinja2 skeleton
      7. Save MD for editing (voice/web/mobile)
      8. Generate PDF via PyMuPDF with manual headers/footers
    """
    from services.md_report_builder import MdReportBuilder
    
    project_dir = await _resolve_project_semantic_path(project_id)
    if not project_dir:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        # Load project meta
        project_meta_path = os.path.join(project_dir, "project_meta.json")
        project_data = None
        if os.path.exists(project_meta_path):
            with open(project_meta_path) as f:
                project_data = json.load(f)
        
        # Load rooms + project info from DB (projects.site_metadata JSONB)
        from database import db as _db
        proj_row = await _db.fetchrow(
            "SELECT id, reference_number, client_name, site_metadata FROM projects WHERE id = $1",
            project_id
        )
        if not proj_row:
            raise HTTPException(status_code=404, detail="Project not found in DB")
        
        metadata = proj_row.get("site_metadata") or {}
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        rooms_data = metadata.get("rooms", [])
        
        # Build ProjectInfo-compatible dict from DB + site_metadata
        if not project_data:
            # Transform address dict → string
            addr = metadata.get("address", {})
            if isinstance(addr, dict):
                addr_str = addr.get("full_address", "") or f"{addr.get('number', '')} {addr.get('street', '')}, {addr.get('city', '')} {addr.get('postcode', '')}".strip(", ")
            else:
                addr_str = str(addr) if addr else ""
            
            project_data = {
                "id": str(proj_row.get("id", project_id)),
                "reference": proj_row.get("reference_number", ""),
                "client_name": proj_row.get("client_name", ""),
                "address": addr_str,
                "inspection_date": metadata.get("inspection_date", ""),
                "report_date": metadata.get("report_date", ""),
                "surveyor_name": metadata.get("surveyor_name", ""),
            }
        
        # ── PHOTO PIPELINE: Enrich rooms with discovered photos ──
        from services.photo_discovery import enrich_rooms_with_photos
        rooms_data = enrich_rooms_with_photos(rooms_data, project_dir)
        logger.info(f"Photo enrichment: {sum(len(r.get('photos', [])) for r in rooms_data)} photos across {len(rooms_data)} rooms")
        
        # Initialize builder
        builder = MdReportBuilder(
            project_id=project_id,
            storage_base=os.path.dirname(project_dir)
        )
        
        # Step 1: Gather data (now with photos)
        builder.gather_data(project_data=project_data, rooms_data=rooms_data)
        
        # Step 2: Map rooms to RICS elements (photos flow through)
        builder.map_rooms_to_elements()
        
        # Step 3: Generate Gemini narratives for each element
        await builder.generate_narratives()
        
        # Step 4: Generate smart legal sections (H, I, L)
        await builder.generate_legal_sections()
        
        # Step 5: Auto-compute Section B
        builder.compute_section_b()
        
        # ── PHOTO INTELLIGENCE: Gemini-powered photo analysis ──
        photo_manifest = None
        try:
            from services.photo_intelligence import PhotoIntelligence
            from services.gemini_service import get_gemini_service
            
            gemini = get_gemini_service()
            pi = PhotoIntelligence(project_dir, gemini)
            photo_manifest = await pi.run()
            
            total_pi = sum(len(v) for v in photo_manifest.values())
            defects = sum(1 for v in photo_manifest.values() for p in v if p.get("has_defect"))
            logger.info(f"[PHOTO INTEL] Analyzed {total_pi} photos, {defects} defects across {len(photo_manifest)} elements")
        except Exception as pi_err:
            logger.warning(f"[PHOTO INTEL] Fallback to basic photos: {pi_err}")
            import traceback; traceback.print_exc()
        # ── END PHOTO INTELLIGENCE ──
        
        # Step 6: Assemble full Markdown (with enriched photo manifest)
        md_content = builder.assemble_md(photo_manifest=photo_manifest)
        
        # Step 7: Save MD for editing + as 'latest' for the report-md endpoint
        md_path = builder.save_md()
        latest_md_path = os.path.join(project_dir, "rics_report_latest.md")
        with open(latest_md_path, "w") as f:
            f.write(md_content)
        
        # Save as version for versioning system (captures version_id for PDF save)
        from services.report_versioning import ReportVersioning
        versioning = ReportVersioning(storage_base=os.path.dirname(project_dir))
        total_photos = len(builder.report.all_photos)
        saved_version = versioning.save_version(
            os.path.basename(project_dir), md_content,
            label="Auto-generated", changes_summary="Full report generated from inspection data",
            photo_count=total_photos
        )
        
        # Step 8: Build HTML + Generate PDF via Playwright (Chromium engine)
        pdf_path = None
        try:
            import re as _re
            import markdown as _md
            
            # Build HTML from MD (same logic as builder.generate_pdf)
            clean_md = _re.sub(r'^---\s*\n.*?\n---\s*\n', '', md_content, flags=_re.DOTALL)
            html_body = _md.markdown(clean_md, extensions=['tables', 'fenced_code', 'toc'])
            full_html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><style>{builder.css_content}</style></head>
<body>{html_body}</body>
</html>"""
            
            # Save HTML for debugging
            html_path = os.path.join(project_dir, "rics_report_latest.html")
            with open(html_path, "w") as f:
                f.write(full_html)
            
            # Generate PDF with Playwright
            from services.playwright_pdf_generator import generate_pdf_playwright
            pdf_output = os.path.join(project_dir, "RICS_Final_Report.pdf")
            pdf_path = await generate_pdf_playwright(
                full_html,
                pdf_output,
                reference=builder.report.project.reference or ""
            )
        except Exception as pdf_err:
            import traceback
            logger.error(f"Playwright PDF generation failed: {pdf_err}")
            traceback.print_exc()
            # Fallback to old PyMuPDF
            try:
                pdf_path = builder.generate_pdf(
                    output_path=os.path.join(project_dir, "RICS_Final_Report.pdf")
                )
            except Exception:
                pass
        
        # Save PDF to version storage
        if pdf_path and os.path.exists(pdf_path):
            versioning.save_version_pdf(
                os.path.basename(project_dir),
                saved_version.version_id,
                pdf_path
            )
        
        # Compute stats for Flutter UI
        all_elems = builder.report.get_all_elements()
        urgent_count = sum(1 for e in all_elems if e.condition_rating.value == 3)
        attention_count = sum(1 for e in all_elems if e.condition_rating.value == 2)
        
        return {
            "status": "success",
            "message": "RICS Level 3 Report generated (Markdown-First pipeline)",
            "pdf_path": pdf_path,
            "md_path": md_path,
            "stats": {
                "total_elements": len(all_elems),
                "urgent_items": urgent_count,
                "attention_items": attention_count,
                "total_photos": total_photos,
                "sections_generated": 13,  # A-M complete
            },
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

from fastapi.responses import FileResponse

@router.get("/projects/{project_id}/report/pdf")
async def get_report_pdf(project_id: str):
    """
    Serves the highly-formatted RICS V3 report as a PDF.
    Searches multiple locations where the PDF may have been generated.
    """
    project_dir = await _resolve_project_semantic_path(project_id)
    if not project_dir:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Search multiple possible PDF locations (generation saves to different paths)
    candidates = [
        os.path.join(project_dir, "RICS_Final_Report.pdf"),
        os.path.join(project_dir, "reports", "RICS_Final_Report.pdf"),
        os.path.join(project_dir, "reports", "RICS_Final_Report_v2.pdf"),
        os.path.join(project_dir, "RICS_Final_Report_v2.pdf"),
    ]
    
    pdf_path = None
    for candidate in candidates:
        if os.path.exists(candidate):
            pdf_path = candidate
            break
    
    if not pdf_path:
        raise HTTPException(status_code=404, detail="PDF not generated yet. Please trigger generation first.")
            
    return FileResponse(path=pdf_path, media_type="application/pdf", filename="RICS_Final_Report.pdf")


# --- Phase 5: Evidence & Partial Reports (Project-Based) ---

from services.storage_service import get_storage_service
_project_storage_service = get_storage_service()


async def _get_project_folder(project_id: str) -> str:
    """Find the project's storage folder on the filesystem by checking all sessions in DB."""
    from database import db as _db
    query = "SELECT id FROM sessions WHERE project_id = $1 ORDER BY started_at DESC"
    rows = await _db.fetch(query, project_id)
    
    for row in rows:
        session_path = await _project_storage_service.get_session_path(str(row['id']))
        # The project folder is the parent of the session folder
        project_folder = os.path.dirname(session_path)
        if os.path.exists(project_folder):
            return project_folder
    
    raise HTTPException(status_code=404, detail="No storage folder found for this project")


def _get_all_session_dirs(project_folder: str) -> list:
    """List all session directories inside a project folder, sorted newest first."""
    if not os.path.exists(project_folder):
        return []
    session_dirs = []
    for entry in os.listdir(project_folder):
        full = os.path.join(project_folder, entry)
        if os.path.isdir(full) and "_Session_" in entry:
            session_dirs.append(full)
    # Sort by folder name (date prefix) descending = newest first
    session_dirs.sort(reverse=True)
    return session_dirs


async def _enrich_rooms_with_media_counts(project_id: str, rooms_data: list) -> list:
    """Enrich room data with images_count, audio_count, and has_partial_report
    by scanning ALL session directories for the project on the filesystem."""
    try:
        project_folder = await _get_project_folder(project_id)
        session_dirs = _get_all_session_dirs(project_folder)
    except Exception:
        # No session yet — return rooms as is with 0 counts
        for room in rooms_data:
            room.setdefault('images_count', 0)
            room.setdefault('audio_count', 0)
            room.setdefault('has_partial_report', False)
        return rooms_data
    
    for room in rooms_data:
        room_id = room.get('id', '')
        img_count = 0
        audio_count = 0
        has_report = False
        
        # Scan ALL session dirs for this room's files
        for session_dir in session_dirs:
            room_dir = os.path.join(session_dir, room_id)
            if os.path.exists(room_dir):
                for root, dirs, files in os.walk(room_dir):
                    for f in files:
                        fl = f.lower()
                        if fl.endswith(('.jpg', '.jpeg', '.png')):
                            img_count += 1
                        elif fl.endswith(('.m4a', '.mp3', '.wav', '.aac', '.opus', '.ogg')):
                            audio_count += 1
                        elif fl == 'partial_report.json':
                            has_report = True
        
        room['images_count'] = img_count
        room['audio_count'] = audio_count
        room['has_partial_report'] = has_report
    
    return rooms_data


@router.get("/projects/{project_id}/rooms/{room_id}/contexts")
async def get_room_contexts(project_id: str, room_id: str):
    """
    Get structured evidence grouped by context for a room.
    Scans ALL session directories to aggregate evidence across multiple inspection visits.
    Returns per-context: name, photo_count, audio_count, is_green, photo_urls, audio_urls.
    """
    try:
        project_folder = await _get_project_folder(project_id)
        session_dirs = _get_all_session_dirs(project_folder)
    except Exception:
        return {"contexts": [], "total_photos": 0, "total_audio": 0}
    
    # Aggregate per context across all sessions
    context_data = {}  # {"Walls": {photos: [...], audio: [...], timeline: {}}}
    
    for session_dir in session_dirs:
        room_dir = os.path.join(session_dir, room_id)
        if not os.path.exists(room_dir):
            continue
        
        for item in sorted(os.listdir(room_dir)):
            item_path = os.path.join(room_dir, item)
            if not os.path.isdir(item_path) or not item.startswith("Context_"):
                continue
            
            context_name = item.replace("Context_", "").replace("_", " ")
            
            if context_name not in context_data:
                context_data[context_name] = {
                    "photos": [], "audio": [], "timeline": None
                }
            
            for f_name in sorted(os.listdir(item_path)):
                full_path = os.path.join(item_path, f_name)
                try:
                    rel = os.path.relpath(full_path, _project_storage_service.storage_root)
                    url = "/storage/" + rel.replace("\\", "/")
                except ValueError:
                    continue
                
                fl = f_name.lower()
                if fl.endswith(('.jpg', '.jpeg', '.png')):
                    if url not in context_data[context_name]["photos"]:
                        context_data[context_name]["photos"].append(url)
                elif fl.endswith(('.m4a', '.mp3', '.wav', '.aac', '.opus')):
                    if url not in context_data[context_name]["audio"]:
                        context_data[context_name]["audio"].append(url)
                elif fl.startswith('timeline_') and fl.endswith('.json'):
                    try:
                        with open(full_path, 'r') as f:
                            context_data[context_name]["timeline"] = json.load(f)
                    except Exception:
                        pass
    
    # Build response
    contexts_list = []
    total_photos = 0
    total_audio = 0
    
    for ctx_name, data in context_data.items():
        photo_count = len(data["photos"])
        audio_count = len(data["audio"])
        total_photos += photo_count
        total_audio += audio_count
        
        # Determine status
        is_green = photo_count >= 3 and audio_count >= 1
        timeline = data.get("timeline") or {}
        
        contexts_list.append({
            "name": ctx_name,
            "photo_count": photo_count,
            "audio_count": audio_count,
            "is_green": is_green,
            "status": "completed" if is_green else ("in_progress" if photo_count > 0 else "pending"),
            "photo_urls": data["photos"],
            "audio_urls": data["audio"],
            "audio_duration": timeline.get("audio_duration", 0),
        })
    
    # Sort: pending first, then in_progress, then completed
    status_order = {"pending": 0, "in_progress": 1, "completed": 2}
    contexts_list.sort(key=lambda c: status_order.get(c["status"], 99))
    
    return {
        "contexts": contexts_list,
        "total_photos": total_photos,
        "total_audio": total_audio,
        "has_partial_report": os.path.exists(
            os.path.join(session_dirs[0] if session_dirs else "", room_id, "partial_report.json")
        ),
        "excluded_photos": _get_excluded_photos(project_folder, room_id),
    }


def _get_excluded_photos(project_folder: str, room_id: str) -> list:
    """Load the excluded photos list for a room."""
    excluded_file = os.path.join(project_folder, f"excluded_photos_{room_id}.json")
    if os.path.exists(excluded_file):
        try:
            with open(excluded_file, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_excluded_photos(project_folder: str, room_id: str, excluded: list):
    """Save the excluded photos list for a room."""
    excluded_file = os.path.join(project_folder, f"excluded_photos_{room_id}.json")
    with open(excluded_file, "w") as f:
        json.dump(excluded, f)


@router.post("/projects/{project_id}/rooms/{room_id}/toggle_photo_exclude")
async def toggle_photo_exclude(project_id: str, room_id: str, payload: dict):
    """
    Toggle a photo's exclusion status for report generation.
    If the photo is excluded, it will be re-included, and vice versa.
    Does NOT delete the file — only marks it for exclusion from reports.
    """
    filename = payload.get("filename")
    if not filename:
        raise HTTPException(status_code=400, detail="filename is required")
    
    try:
        project_folder = await _get_project_folder(project_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Project not found")
    
    excluded = _get_excluded_photos(project_folder, room_id)
    
    if filename in excluded:
        excluded.remove(filename)
        action = "included"
    else:
        excluded.append(filename)
        action = "excluded"
    
    _save_excluded_photos(project_folder, room_id, excluded)
    
    return {
        "status": "success",
        "action": action,
        "filename": filename,
        "excluded_photos": excluded,
    }

@router.post("/projects/{project_id}/rooms/{room_id}/upload_evidence")
async def upload_evidence(project_id: str, room_id: str, evidence: UploadFile = File(...), session_id: Optional[str] = Form(None)):
    """
    Receive a zip file containing evidence photos/audio for a room.
    Extracts safely to disk to prevent Memory OOM crashes.
    """
    if session_id:
        session_dir = await _project_storage_service.get_session_path(session_id)
    else:
        session_dir, session_id_fallback = await _get_session_dir_for_project(project_id)
        session_id = session_id_fallback
        
    room_dir = os.path.join(session_dir, room_id)
    os.makedirs(room_dir, exist_ok=True)
    
    import tempfile
    import shutil
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_zip:
        shutil.copyfileobj(evidence.file, temp_zip)
        temp_zip_path = temp_zip.name
        
    try:
        extracted_count = 0
        with zipfile.ZipFile(temp_zip_path, 'r') as zf:
            for member in zf.namelist():
                # Skip directory entries and hidden files
                if member.endswith('/') or member.startswith('__MACOSX') or member.startswith('.'):
                    continue
                
                # Extract to room_dir preserving the Context_X/ structure
                target_path = os.path.join(room_dir, member)
                target_dir = os.path.dirname(target_path)
                os.makedirs(target_dir, exist_ok=True)
                
                with open(target_path, 'wb') as out_file:
                    out_file.write(zf.read(member))
                extracted_count += 1
        
        print(f"[Upload] Extracted {extracted_count} files for room {room_id} in project {project_id}")
        return {"status": "success", "files_extracted": extracted_count, "room_id": room_id}
        
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip file")
    except Exception as e:
        print(f"[Upload Error] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)
async def _get_latest_session_for_project(project_id: str):
    """Resolve the latest session_id for a project from the DB."""
    query = """
        SELECT id FROM sessions 
        WHERE project_id = $1 
        ORDER BY started_at DESC 
        LIMIT 1
    """
    row = await db.fetchrow(query, project_id)
    return str(row['id']) if row else None

async def _get_session_dir_for_project(project_id: str):
    """Get the filesystem session directory with the most files for a project.
    Scans all session dirs and returns the one with actual evidence."""
    try:
        project_folder = await _get_project_folder(project_id)
        session_dirs = _get_all_session_dirs(project_folder)
    except Exception:
        # Fallback to DB-based approach
        session_id = await _get_latest_session_for_project(project_id)
        if not session_id:
            raise HTTPException(status_code=404, detail="No session found for this project")
        session_dir = await _project_storage_service.get_session_path(session_id)
        return session_dir, session_id
    
    if not session_dirs:
        raise HTTPException(status_code=404, detail="No session directories found")
    
    # Find the session dir with the most files (= the one with actual evidence)
    best_dir = session_dirs[0]
    best_count = 0
    for sd in session_dirs:
        count = sum(len(files) for _, _, files in os.walk(sd))
        if count > best_count:
            best_count = count
            best_dir = sd
    
    # Extract session_id from folder name (format: YYYY-MM-DD_Session_XXXXXXXX)
    folder_name = os.path.basename(best_dir)
    session_id_short = folder_name.split('_Session_')[-1] if '_Session_' in folder_name else 'unknown'
    return best_dir, session_id_short


@router.get("/projects/{project_id}/rooms/{room_id}/evidence")
async def get_room_evidence(project_id: str, room_id: str):
    """
    Lists evidence photos for a room, grouped by context subfolder.
    Scans ALL session directories for the project to find all evidence.
    Returns URLs that can be loaded via the /storage/ static mount.
    """
    try:
        project_folder = await _get_project_folder(project_id)
        session_dirs = _get_all_session_dirs(project_folder)
    except Exception:
        return {"evidence": [], "room_id": room_id, "message": "No storage folder found"}
    
    evidence = []
    valid_exts = ('.jpg', '.jpeg', '.png')
    seen_files = set()  # Deduplicate by filename
    
    for session_dir in session_dirs:
        room_dir = os.path.join(session_dir, room_id)
        if not os.path.exists(room_dir):
            continue
        
        for root, dirs, files in os.walk(room_dir):
            for file in files:
                if file.lower().endswith(valid_exts) and file not in seen_files:
                    seen_files.add(file)
                    abs_path = os.path.join(root, file)
                    rel_to_room = os.path.relpath(root, room_dir)
                    context = rel_to_room if rel_to_room != '.' else 'general'
                    try:
                        rel_to_storage = os.path.relpath(abs_path, _project_storage_service.storage_root)
                        url = "/storage/" + rel_to_storage.replace("\\", "/")
                        evidence.append({
                            "url": url,
                            "context": context,
                            "filename": file
                        })
                    except ValueError:
                        continue
    
    return {"evidence": evidence, "room_id": room_id, "count": len(evidence)}


@router.post("/projects/{project_id}/generate_partial_report")
async def generate_partial_report_for_project(project_id: str, payload: dict):
    """
    Generates a partial AI report for a specific room in the project.
    Aggregates evidence from ALL session directories.
    """
    room_id = payload.get("room_id")
    if not room_id:
        raise HTTPException(status_code=400, detail="room_id is required")
    
    # Collect ALL session dirs for this project
    try:
        project_folder = await _get_project_folder(project_id)
        all_session_dirs = _get_all_session_dirs(project_folder)
    except Exception:
        # Fallback to single session
        session_dir, _ = await _get_session_dir_for_project(project_id)
        all_session_dirs = [session_dir]
    
    if not all_session_dirs:
        raise HTTPException(status_code=404, detail="No session directories found")
    
    # Find session_init.json in any session dir
    session_data = None
    primary_session_dir = all_session_dirs[0]
    for sd in all_session_dirs:
        init_file = os.path.join(sd, "session_init.json")
        if os.path.exists(init_file):
            with open(init_file, 'r') as f:
                session_data = json.load(f)
            primary_session_dir = sd
            break
    
    if session_data is None:
        row = await db.fetchrow("SELECT site_metadata FROM projects WHERE id = $1", project_id)
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        metadata = json.loads(row['site_metadata']) if isinstance(row['site_metadata'], str) else row['site_metadata']
        session_data = {"floor_plan": {"rooms": metadata.get('rooms', [])}}
        init_file = os.path.join(primary_session_dir, "session_init.json")
        os.makedirs(primary_session_dir, exist_ok=True)
        with open(init_file, "w") as f:
            json.dump(session_data, f, indent=2, default=str)
    
    try:
        from forensic_engine import generate_partial_room_report
        # Pass ALL session dirs so forensic_engine aggregates evidence
        # Load excluded photos for this room
        excluded_photos = _get_excluded_photos(project_folder if 'project_folder' in dir() else all_session_dirs[0], room_id)
        report_chunk = await generate_partial_room_report(all_session_dirs, room_id, session_data, excluded_photos=excluded_photos)
        
        # --- POST-PROCESS: Inject ALL room photos by Context → RICS element mapping ---
        # Scan ALL session dirs for photos
        if report_chunk and isinstance(report_chunk, dict):
            elements = report_chunk.get("elements", [])
            if "rooms" in report_chunk and isinstance(report_chunk["rooms"], list) and len(report_chunk["rooms"]) > 0:
                elements = report_chunk["rooms"][0].get("elements", [])
            
            # 1. Scan all Context_* folders across ALL sessions
            context_photos = {}
            all_photos = []
            seen_files = set()
            
            for sd in all_session_dirs:
                room_dir = os.path.join(sd, room_id)
                if not os.path.exists(room_dir):
                    continue
                for item in os.listdir(room_dir):
                    item_path = os.path.join(room_dir, item)
                    if os.path.isdir(item_path) and item.startswith("Context_"):
                        context_key = item.replace("Context_", "").lower().replace("_", " ")
                        if context_key not in context_photos:
                            context_photos[context_key] = []
                        for f_name in sorted(os.listdir(item_path)):
                            if f_name.lower().endswith(('.jpg', '.jpeg', '.png')) and f_name not in seen_files:
                                seen_files.add(f_name)
                                full_path = os.path.join(item_path, f_name)
                                try:
                                    rel = os.path.relpath(full_path, _project_storage_service.storage_root)
                                    url = "/storage/" + rel.replace("\\", "/")
                                    context_photos[context_key].append(url)
                                    all_photos.append(url)
                                except ValueError:
                                    pass
            
            # 2. Map context keys → RICS element keywords
            CONTEXT_TO_RICS = {
                "walls": ["wall", "partition", "E5"],
                "ceiling": ["ceiling", "E1"],
                "floor": ["floor", "E2"],
                "doors": ["door", "joinery", "E6"],
                "windows": ["window", "E4", "glazing"],
                "heating": ["heating", "cooling", "hvac", "F4", "radiator", "boiler"],
                "electricity": ["electri", "wiring", "socket", "F2"],
                "plumbing": ["plumbing", "water", "pipe", "F3"],
                "general context": [],
            }
            
            general_photos = context_photos.get("general context", [])
            
            # 3. Inject photos into matching elements
            for elem in elements:
                matched_urls = []
                elem_text = (
                    (elem.get("rics_element", "") + " " + elem.get("name", ""))
                    .lower()
                )
                
                for ctx_key, ctx_urls in context_photos.items():
                    if ctx_key == "general context":
                        continue
                    keywords = CONTEXT_TO_RICS.get(ctx_key, [ctx_key])
                    for kw in keywords:
                        if kw.lower() in elem_text:
                            matched_urls.extend(ctx_urls)
                            break
                
                if not matched_urls and general_photos:
                    matched_urls = general_photos[:3]
                
                if not matched_urls and all_photos:
                    matched_urls = all_photos[:2]
                
                seen = set()
                unique_urls = []
                for u in matched_urls:
                    if u not in seen:
                        seen.add(u)
                        unique_urls.append(u)
                
                elem["evidence_photos"] = unique_urls
            
            print(f"   [POST-PROCESS] Injected {len(all_photos)} photos across {len(elements)} elements from {len(context_photos)} contexts ({len(all_session_dirs)} sessions)")
        # --- END POST-PROCESS ---
        
        # Save report in the primary session dir (the one with the most data)
        best_dir = primary_session_dir
        for sd in all_session_dirs:
            rd = os.path.join(sd, room_id)
            if os.path.exists(rd):
                best_dir = sd
                break
        
        room_dir = os.path.join(best_dir, room_id)
        os.makedirs(room_dir, exist_ok=True)
        chunk_path = os.path.join(room_dir, "partial_report.json")
        with open(chunk_path, "w", encoding="utf-8") as f:
            json.dump(report_chunk, f, indent=2)
        
        return {"status": "success", "room_id": room_id, "report_chunk": report_chunk}
    except Exception as e:
        print(f"Partial Report Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/partial_report")
async def get_partial_report_for_project(project_id: str, room_id: str):
    """Retrieves an existing partial report for a room in the project."""
    session_dir, session_id = await _get_session_dir_for_project(project_id)
    chunk_path = os.path.join(session_dir, room_id, "partial_report.json")
    
    if not os.path.exists(chunk_path):
        return None
    
    try:
        with open(chunk_path, 'r') as f:
            return json.load(f)
    except Exception:
        return None


@router.post("/projects/{project_id}/voice_edit_report")
async def voice_edit_report_for_project(project_id: str, payload: dict):
    """Applies voice edit instruction to a room's partial report."""
    room_id = payload.get("room_id")
    instruction = payload.get("instruction")
    if not room_id or not instruction:
        raise HTTPException(status_code=400, detail="room_id and instruction are required")
    
    session_dir, session_id = await _get_session_dir_for_project(project_id)
    chunk_path = os.path.join(session_dir, room_id, "partial_report.json")
    
    if not os.path.exists(chunk_path):
        raise HTTPException(status_code=404, detail="Partial report not found. Generate it first.")
    
    try:
        with open(chunk_path, 'r') as f:
            current_chunk = json.load(f)
        
        from forensic_engine import voice_edit_partial_report
        updated_chunk = await voice_edit_partial_report(current_chunk, instruction)
        
        with open(chunk_path, "w", encoding="utf-8") as f:
            json.dump(updated_chunk, f, indent=2)
        
        return {"status": "success", "room_id": room_id, "report_chunk": updated_chunk}
    except Exception as e:
        print(f"Voice Edit Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ======================================================================
# PHASE: FINAL REPORT — Markdown-First RICS Report System
# ======================================================================

class FinalReportRequest(BaseModel):
    """Request body for generating the final RICS report"""
    sections_to_regenerate: Optional[List[str]] = None  # e.g. ["D", "E"] or None for all

class VoiceEditRequest(BaseModel):
    """Request body for voice-editing the report"""
    voice_text: str
    confirm: bool = False  # If False, return preview; if True, apply

class MarkFinalRequest(BaseModel):
    """Request body for marking a version as final"""
    version_id: str

class ReportMdUpdate(BaseModel):
    """Request body for updating report Markdown content"""
    content: str
    changes_summary: str = ""


@router.post("/projects/{project_id}/generate-final-report")
async def generate_final_report(project_id: str, req: FinalReportRequest = None):
    """Generate the full RICS Level 3 PDF from all inspection data."""
    try:
        from services.md_report_builder import MdReportBuilder
        from services.report_versioning import ReportVersioning
        
        builder = MdReportBuilder(project_id=project_id)
        
        # Load project data from DB
        project = await db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Gather room data
        rooms = await db.get_project_rooms(project_id)
        rooms_data = []
        for room in rooms:
            room_json_path = f"project_data/{project_id}/rooms/{room['id']}/room_data.json"
            if os.path.exists(room_json_path):
                with open(room_json_path) as f:
                    rooms_data.append(json.load(f))
            else:
                rooms_data.append({
                    "id": room["id"],
                    "name": room.get("name", "Unknown"),
                    "type": room.get("type", "general"),
                    "notes": [],
                    "photos": []
                })
        
        # ── PHOTO BRIDGE v2: Use photo_discovery service for proper Context→RICS mapping ──
        try:
            from services.photo_discovery import enrich_rooms_with_photos
            project_folder = await _get_project_folder(project_id)
            rooms_data = enrich_rooms_with_photos(rooms_data, project_folder)
            total_injected = sum(len(r.get("photos", [])) for r in rooms_data)
            print(f"[PHOTO BRIDGE v2] Enriched {total_injected} photos across {len(rooms_data)} rooms")
        except Exception as photo_err:
            print(f"[PHOTO BRIDGE v2] Warning — could not scan evidence: {photo_err}")
            import traceback; traceback.print_exc()
        # ── END PHOTO BRIDGE v2 ──
        
        builder.gather_data(
            project_data={
                "id": project_id,
                "reference": project.get("reference", ""),
                "client_name": project.get("client_name", ""),
                "address": project.get("address", ""),
                "surveyor_name": project.get("surveyor_name", ""),
                "rics_number": project.get("rics_number", ""),
                "inspection_date": project.get("inspection_date", ""),
                "report_date": project.get("report_date", ""),
            },
            rooms_data=rooms_data
        )
        
        # Map rooms to elements
        builder.map_rooms_to_elements()
        
        # Populate Section C — About the Property (from DB)
        builder.report.section_c.property_type = project.get("property_type", "")
        builder.report.section_c.year_built = str(project.get("year_built", ""))
        builder.report.section_c.construction = project.get("construction", "")
        builder.report.section_c.tenure = project.get("tenure", "Assumed freehold")
        builder.report.section_c.storeys = str(project.get("storeys", ""))
        builder.report.section_c.accommodation = project.get("accommodation", "")
        builder.report.section_c.council_tax = project.get("council_tax", "")
        builder.report.section_c.epc_rating = project.get("epc_rating", "")
        
        # Log element distribution for debugging
        d_count = len(builder.report.section_d_elements)
        e_count = len(builder.report.section_e_elements)
        f_count = len(builder.report.section_f_elements)
        g_count = len(builder.report.section_g_elements)
        total_photos = sum(
            len(e.photos) for e in builder.report.get_all_elements()
        )
        print(f"[RICS ELEMENTS] D={d_count}, E={e_count}, F={f_count}, G={g_count}, Total photos={total_photos}")
        
        # Generate narratives (Gemini auto-initializes if GOOGLE_API_KEY is set)
        await builder.generate_narratives()
        
        # Generate smart legal sections H, I, L using Gemini
        try:
            await builder.generate_legal_sections()
            print("[RICS LEGAL] Sections H, I, L generated via Gemini")
        except Exception as legal_err:
            print(f"[RICS LEGAL] Warning — legal sections generation failed: {legal_err}")
        
        # Compute Section B
        builder.compute_section_b()
        
        # ── PHOTO INTELLIGENCE: Gemini-powered photo analysis ──
        photo_manifest = None
        try:
            from services.photo_intelligence import PhotoIntelligence
            from services.gemini_service import get_gemini_service
            
            gemini = get_gemini_service()
            pi = PhotoIntelligence(project_folder, gemini)
            photo_manifest = await pi.run()
            
            total_pi = sum(len(v) for v in photo_manifest.values())
            defects = sum(1 for v in photo_manifest.values() for p in v if p.get("has_defect"))
            print(f"[PHOTO INTEL] Analyzed {total_pi} photos, {defects} defects across {len(photo_manifest)} elements")
        except Exception as pi_err:
            print(f"[PHOTO INTEL] Warning — fallback to basic photos: {pi_err}")
            import traceback; traceback.print_exc()
        # ── END PHOTO INTELLIGENCE ──
        
        # Assemble MD (with enriched photo manifest if available)
        md_content = builder.assemble_md(photo_manifest=photo_manifest)
        
        # Generate PDF
        out_dir = f"project_data/{project_id}/reports"
        os.makedirs(out_dir, exist_ok=True)
        pdf_path = builder.generate_pdf(
            output_path=os.path.join(out_dir, f"RICS_Final_{project_id}.pdf")
        )
        
        # Save as version
        versioning = ReportVersioning(storage_base="project_data")
        version = versioning.save_version(
            project_id, md_content,
            label="Auto-generated", changes_summary="Full report generated from inspection data"
        )
        
        # Also save MD and HTML
        md_path = builder.save_md(os.path.join(out_dir, "rics_report_latest.md"))
        html_path = builder.save_html(os.path.join(out_dir, "rics_report_latest.html"))
        
        return {
            "status": "success",
            "pdf_path": pdf_path,
            "md_path": md_path,
            "html_path": html_path,
            "version": version.to_dict(),
            "stats": {
                "total_elements": len(builder.report.get_all_elements()),
                "total_photos": len(builder.report.all_photos),
                "urgent_items": len(builder.report.section_b.condition_ratings_urgent),
                "attention_items": len(builder.report.section_b.condition_ratings_attention),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Final Report Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════
# HELPER: Universal project directory resolver with fallback
# ══════════════════════════════════════════════════════════

async def _resolve_project_dir(project_id: str) -> tuple:
    """Resolve project directory with storage fallback.
    
    Returns (project_dir, pid, storage_base) — always valid.
    Tries:
      1. _resolve_project_semantic_path()
      2. STORAGE_ROOT/Projects/{project_id}
    """
    STORAGE_ROOT = os.environ.get("STORAGE_ROOT", "/app/storage")
    
    project_dir = await _resolve_project_semantic_path(project_id)
    if project_dir and os.path.exists(project_dir):
        return project_dir, os.path.basename(project_dir), os.path.dirname(project_dir)
    
    # Fallback: direct storage path
    direct_dir = os.path.join(STORAGE_ROOT, "Projects", project_id)
    if os.path.exists(direct_dir):
        return direct_dir, project_id, os.path.join(STORAGE_ROOT, "Projects")
    
    # Last resort: return storage-based path even if not existing yet
    return direct_dir, project_id, os.path.join(STORAGE_ROOT, "Projects")


# ══════════════════════════════════════════════════════════
# HELPER: Load report Markdown content from any location
# ══════════════════════════════════════════════════════════

async def _load_report_content(project_id: str):
    """Find and load report MD content using 4-strategy path resolution."""
    STORAGE_ROOT = os.environ.get("STORAGE_ROOT", "/app/storage")
    content = None
    
    # Strategy 1: Semantic project directory
    project_dir = await _resolve_project_semantic_path(project_id)
    if project_dir:
        latest_path = os.path.join(project_dir, "rics_report_latest.md")
        if os.path.exists(latest_path):
            with open(latest_path) as f:
                content = f.read()
    
    # Strategy 2: UUID directory in storage
    if content is None:
        uuid_dir = os.path.join(STORAGE_ROOT, "Projects", project_id)
        if os.path.exists(uuid_dir):
            latest_path = os.path.join(uuid_dir, "rics_report_latest.md")
            if os.path.exists(latest_path):
                with open(latest_path) as f:
                    content = f.read()
            if content is None:
                reports_dir = os.path.join(uuid_dir, "reports")
                if os.path.exists(reports_dir):
                    md_files = sorted([f for f in os.listdir(reports_dir) if f.endswith('.md')], reverse=True)
                    if md_files:
                        with open(os.path.join(reports_dir, md_files[0])) as f:
                            content = f.read()
    
    # Strategy 3: Versioning system
    if content is None:
        from services.report_versioning import ReportVersioning
        if project_dir:
            versioning = ReportVersioning(storage_base=os.path.dirname(project_dir))
            content = versioning.get_latest_content(os.path.basename(project_dir))
    
    # Strategy 4: project_data fallback
    if content is None:
        md_path = f"project_data/{project_id}/reports/rics_report_latest.md"
        if os.path.exists(md_path):
            with open(md_path) as f:
                content = f.read()
    
    return content


async def _save_report_content(project_id: str, content: str):
    """Save report MD content to all known locations."""
    STORAGE_ROOT = os.environ.get("STORAGE_ROOT", "/app/storage")
    
    # Save to UUID directory
    uuid_dir = os.path.join(STORAGE_ROOT, "Projects", project_id)
    if os.path.exists(uuid_dir):
        with open(os.path.join(uuid_dir, "rics_report_latest.md"), "w") as f:
            f.write(content)
    
    # Save to semantic directory
    project_dir = await _resolve_project_semantic_path(project_id)
    if project_dir and project_dir != uuid_dir:
        with open(os.path.join(project_dir, "rics_report_latest.md"), "w") as f:
            f.write(content)
    
    # Save to project_data
    pd_path = f"project_data/{project_id}/reports/rics_report_latest.md"
    os.makedirs(os.path.dirname(pd_path), exist_ok=True)
    with open(pd_path, "w") as f:
        f.write(content)


@router.get("/projects/{project_id}/report-md")
async def get_report_md(project_id: str):
    """Get the current Markdown content of the RICS report."""
    content = None
    STORAGE_ROOT = os.environ.get("STORAGE_ROOT", "/app/storage")
    
    # Strategy 1: Check project storage directory (where generate-final-report saves)
    project_dir = await _resolve_project_semantic_path(project_id)
    if project_dir:
        latest_path = os.path.join(project_dir, "rics_report_latest.md")
        if os.path.exists(latest_path):
            with open(latest_path) as f:
                content = f.read()
    
    # Strategy 2: Check UUID directory in storage (direct path)
    if content is None:
        uuid_dir = os.path.join(STORAGE_ROOT, "Projects", project_id)
        if os.path.exists(uuid_dir):
            # Check latest.md
            latest_path = os.path.join(uuid_dir, "rics_report_latest.md")
            if os.path.exists(latest_path):
                with open(latest_path) as f:
                    content = f.read()
            # Check reports/ subdirectory for any .md file
            if content is None:
                reports_dir = os.path.join(uuid_dir, "reports")
                if os.path.exists(reports_dir):
                    md_files = sorted([f for f in os.listdir(reports_dir) if f.endswith('.md')], reverse=True)
                    if md_files:
                        with open(os.path.join(reports_dir, md_files[0])) as f:
                            content = f.read()
    
    # Strategy 3: Check versioning system
    if content is None:
        from services.report_versioning import ReportVersioning
        if project_dir:
            versioning = ReportVersioning(storage_base=os.path.dirname(project_dir))
            content = versioning.get_latest_content(os.path.basename(project_dir))
    
    # Strategy 4: Fallback to project_data path
    if content is None:
        md_path = f"project_data/{project_id}/reports/rics_report_latest.md"
        if os.path.exists(md_path):
            with open(md_path) as f:
                content = f.read()
    
    if content is None:
        raise HTTPException(status_code=404, detail="No report found. Generate first.")
    
    return {"status": "success", "content": content, "project_id": project_id}


@router.put("/projects/{project_id}/report-md")
async def update_report_md(project_id: str, req: ReportMdUpdate):
    """Update the RICS report Markdown content (from mobile/web editor)."""
    from services.report_versioning import ReportVersioning
    
    project_dir, pid, storage_base = await _resolve_project_dir(project_id)
    versioning = ReportVersioning(storage_base=storage_base)
    
    # Save as new version
    version = versioning.save_version(
        pid, req.content,
        label="Web editor edit",
        changes_summary=req.changes_summary or "Edited via web editor"
    )
    
    # Save to project dir
    if project_dir:
        with open(os.path.join(project_dir, "rics_report_latest.md"), "w") as f:
            f.write(req.content)
    
    # Regenerate PDF after save
    pdf_path = None
    try:
        import re as _re
        import markdown as _md
        
        css_path = "/app/templates/rics_style.css"
        with open(css_path) as f:
            css = f.read()
        
        clean_md = _re.sub(r'^---\s*\n.*?\n---\s*\n', '', req.content, flags=_re.DOTALL)
        html_body = _md.markdown(clean_md, extensions=['tables', 'fenced_code', 'toc'])
        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><style>{css}</style></head>
<body>{html_body}</body>
</html>"""
        
        from services.playwright_pdf_generator import generate_pdf_playwright
        if project_dir:
            pdf_output = os.path.join(project_dir, "RICS_Final_Report.pdf")
        else:
            pdf_output = f"/tmp/RICS_{pid}.pdf"
        pdf_path = await generate_pdf_playwright(full_html, pdf_output, reference="")
        
        if pdf_path:
            versioning.save_version_pdf(pid, version.version_id, pdf_path)
    except Exception as e:
        logger.error(f"PDF regen after web edit: {e}")
    
    return {
        "status": "success",
        "version": version.to_dict(),
        "pdf_regenerated": pdf_path is not None,
        "project_id": project_id
    }


class AiEditRequest(BaseModel):
    """Request body for AI-powered text editing."""
    text: str
    action: str  # improve, concise, formal, translate, summarize, explain, custom
    custom_prompt: Optional[str] = None
    language: Optional[str] = "en"


@router.post("/projects/{project_id}/report-ai-edit")
async def ai_edit_text(project_id: str, req: AiEditRequest):
    """AI toolbar for TipTap editor — processes selected text with Gemini."""

    # Action → prompt mapping
    prompts = {
        "improve": "Improve the following text for a professional RICS survey report. Fix grammar, enhance clarity, and maintain a formal surveyor's tone. Return only the improved text, no explanation.",
        "concise": "Make this text more concise while preserving all technical details. This is for a RICS survey report. Return only the shortened text.",
        "formal": "Rewrite this text in a formal, professional RICS surveyor tone suitable for a Level 3 Building Survey report. Return only the rewritten text.",
        "translate_ar": "Translate this RICS survey text to Arabic. Maintain all technical terms. Return only the Arabic translation.",
        "translate_en": "Translate this text to English. Maintain all technical RICS terms. Return only the English translation.",
        "summarize": "Summarize this section for a RICS survey executive summary. Keep it to 2-3 sentences. Return only the summary.",
        "explain": "Explain this survey finding in plain language a homeowner can understand. Return only the explanation.",
        "expand": "Expand this brief note into a full RICS Level 3 surveyor narrative with professional detail. Return only the expanded text.",
    }

    action_key = req.action.lower().replace(" ", "_")
    prompt_prefix = prompts.get(action_key)
    
    if not prompt_prefix and req.custom_prompt:
        prompt_prefix = req.custom_prompt
    elif not prompt_prefix:
        prompt_prefix = prompts.get("improve", "Improve this text:")

    full_prompt = f"{prompt_prefix}\n\nText:\n{req.text}"

    try:
        from services.gemini_service import GeminiService
        svc = GeminiService()
        response = svc.model.generate_content(full_prompt)
        result_text = response.text.strip()
        
        # Clean code fences
        if result_text.startswith("```"):
            result_text = result_text.split("```", 2)[1]
            if result_text.startswith("markdown"):
                result_text = result_text[8:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        
        return {
            "status": "success",
            "original": req.text,
            "result": result_text.strip(),
            "action": req.action,
        }
    except Exception as e:
        logger.error(f"AI edit failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI edit failed: {e}")


@router.post("/projects/{project_id}/report-voice-edit")
async def voice_edit_report(project_id: str, req: VoiceEditRequest):
    """Apply a voice command to edit the RICS report using Gemini AI.
    
    Flow:
    1. Load the active version's MD content
    2. Use Gemini to intelligently apply the voice command
    3. If confirmed: save as new version → regenerate PDF → return
    4. If preview: return diff for user review
    """
    from services.voice_report_editor import VoiceReportEditor
    from services.report_versioning import ReportVersioning
    
    # Resolve project path (with storage fallback)
    project_dir, pid, storage_base = await _resolve_project_dir(project_id)
    versioning = ReportVersioning(storage_base=storage_base)
    
    # Load active version content
    active_vid = versioning.get_active_version_id(pid)
    if active_vid:
        content = versioning.get_version_content(pid, active_vid)
    else:
        content = versioning.get_latest_content(pid)
    
    if not content:
        # Fallback: try the latest.md file
        latest_path = os.path.join(project_dir, "rics_report_latest.md")
        if os.path.exists(latest_path):
            with open(latest_path) as f:
                content = f.read()
        else:
            raise HTTPException(status_code=404, detail="No report found. Generate first.")
    
    # Initialize Gemini for intelligent editing
    gemini_model = None
    try:
        from services.gemini_service import GeminiService
        svc = GeminiService()
        gemini_model = svc
        logger.info(f"Voice edit: Gemini activated ({svc.MODEL_NAME})")
    except Exception as e:
        logger.warning(f"Gemini unavailable for voice edit: {e}")
    
    editor = VoiceReportEditor(gemini_service=gemini_model)
    updated_content, edit_info = await editor.apply_edit(
        content, req.voice_text, use_gemini=(gemini_model is not None)
    )
    
    # Generate diff for preview
    diff = ""
    if content != updated_content:
        diff = editor.generate_diff(content, updated_content)
    
    if req.confirm and edit_info.get("applied"):
        # Save as new version
        version = versioning.save_version(
            pid, updated_content,
            label=f"Voice edit: {req.voice_text[:50]}",
            changes_summary=f"Voice command: {req.voice_text}"
        )
        
        # Update latest MD file
        latest_md_path = os.path.join(project_dir, "rics_report_latest.md")
        with open(latest_md_path, "w") as f:
            f.write(updated_content)
        
        # Regenerate PDF via Playwright for the new version
        pdf_path = None
        try:
            import re as _re
            import markdown as _md
            
            css_path = os.path.join(os.path.dirname(os.path.dirname(project_dir)), 
                                     "02_Brain_Cluster", "templates", "rics_style.css")
            if not os.path.exists(css_path):
                css_path = "/app/templates/rics_style.css"
            
            with open(css_path) as f:
                css = f.read()
            
            clean_md = _re.sub(r'^---\s*\n.*?\n---\s*\n', '', updated_content, flags=_re.DOTALL)
            html_body = _md.markdown(clean_md, extensions=['tables', 'fenced_code', 'toc'])
            full_html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><style>{css}</style></head>
<body>{html_body}</body>
</html>"""
            
            from services.playwright_pdf_generator import generate_pdf_playwright
            pdf_output = os.path.join(project_dir, "RICS_Final_Report.pdf")
            pdf_path = await generate_pdf_playwright(full_html, pdf_output, reference="")
            
            # Save PDF to version
            if pdf_path:
                versioning.save_version_pdf(pid, version.version_id, pdf_path)
        except Exception as pdf_err:
            logger.error(f"PDF regen after voice edit failed: {pdf_err}")
        
        edit_info["version"] = version.to_dict()
        edit_info["pdf_regenerated"] = pdf_path is not None
    
    return {
        "status": "success" if edit_info.get("applied") else "preview",
        "edit_info": edit_info,
        "diff": diff,
        "confirmed": req.confirm
    }


@router.get("/projects/{project_id}/report-versions")
async def list_report_versions(project_id: str):
    """List all versions of the RICS report with active version info."""
    from services.report_versioning import ReportVersioning
    
    project_dir, pid, storage_base = await _resolve_project_dir(project_id)
    versioning = ReportVersioning(storage_base=storage_base)
    
    versions = versioning.list_versions(pid)
    active_id = versioning.get_active_version_id(pid)
    
    return {
        "status": "success",
        "versions": versions,
        "active_version_id": active_id,
        "total": len(versions),
        "project_id": project_id
    }


@router.post("/projects/{project_id}/report-mark-final")
async def mark_report_final(project_id: str, req: MarkFinalRequest):
    """Mark a specific version as the final report."""
    from services.report_versioning import ReportVersioning
    
    versioning = ReportVersioning(storage_base="project_data")
    success = versioning.mark_final(project_id, req.version_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Version {req.version_id} not found")
    
    return {
        "status": "success",
        "marked_final": req.version_id,
        "project_id": project_id
    }


@router.get("/projects/{project_id}/report-diff")
async def diff_report_versions(project_id: str, v1: str, v2: str):
    """Get a diff between two report versions."""
    from services.report_versioning import ReportVersioning
    
    versioning = ReportVersioning(storage_base="project_data")
    diff = versioning.diff_versions(project_id, v1, v2)
    
    if diff is None:
        raise HTTPException(status_code=404, detail="One or both versions not found")
    
    return {
        "status": "success",
        "diff": diff,
        "v1": v1,
        "v2": v2,
        "project_id": project_id
    }


@router.get("/projects/{project_id}/report-version/{version_id}/pdf")
async def get_version_pdf(project_id: str, version_id: str):
    """Serve a specific version's PDF file."""
    from services.report_versioning import ReportVersioning
    from fastapi.responses import FileResponse
    
    project_dir = await _resolve_project_semantic_path(project_id)
    if not project_dir:
        raise HTTPException(status_code=404, detail="Project not found")
    
    versioning = ReportVersioning(storage_base=os.path.dirname(project_dir))
    pid = os.path.basename(project_dir)
    pdf_path = versioning.get_version_pdf_path(pid, version_id)
    
    if not pdf_path or not os.path.exists(pdf_path):
        # Fallback: try the main RICS_Final_Report.pdf
        fallback = os.path.join(project_dir, "RICS_Final_Report.pdf")
        if os.path.exists(fallback):
            pdf_path = fallback
        else:
            raise HTTPException(status_code=404, detail=f"PDF not found for {version_id}")
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"RICS_Report_{version_id}.pdf"
    )


@router.put("/projects/{project_id}/report-active-version")
async def set_active_version(project_id: str, req: dict):
    """Set a version as the active (default) for editing."""
    from services.report_versioning import ReportVersioning
    
    version_id = req.get("version_id", "")
    if not version_id:
        raise HTTPException(status_code=400, detail="version_id required")
    
    project_dir = await _resolve_project_semantic_path(project_id)
    if not project_dir:
        raise HTTPException(status_code=404, detail="Project not found")
    
    versioning = ReportVersioning(storage_base=os.path.dirname(project_dir))
    pid = os.path.basename(project_dir)
    success = versioning.set_active_version(pid, version_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Version {version_id} not found")
    
    return {
        "status": "success",
        "active_version_id": version_id,
        "project_id": project_id
    }


# ======================================================================
# ======================================================================
# PHASE: SURVEYOR APPROVAL — Post-generation review workflow
# ======================================================================

class ApprovalRequest(BaseModel):
    """Request body for approving/rejecting a report"""
    version_id: Optional[str] = None  # Which version to approve (latest if None)

class RejectionRequest(BaseModel):
    """Request body for rejecting a report"""
    version_id: Optional[str] = None
    reasons: List[str] = []
    voice_feedback_path: Optional[str] = None


async def _get_approval_path(project_id: str) -> str:
    """Resolve the approval.json path for a project."""
    project_dir, pid, storage_base = await _resolve_project_dir(project_id)
    return os.path.join(project_dir, "approval.json")


@router.post("/projects/{project_id}/report-approve")
async def approve_report(project_id: str, req: ApprovalRequest = None):
    """Surveyor approves the final report — marks version as FINAL and locks it."""
    try:
        from datetime import datetime
        from services.report_versioning import ReportVersioning
        
        approval_path = await _get_approval_path(project_id)
        os.makedirs(os.path.dirname(approval_path), exist_ok=True)
        
        # Resolve project for versioning
        project_dir = await _resolve_project_semantic_path(project_id)
        version_id = req.version_id if req and req.version_id else None
        
        # Mark version as FINAL and lock it
        if project_dir:
            versioning = ReportVersioning(storage_base=os.path.dirname(project_dir))
            pid = os.path.basename(project_dir)
            
            if not version_id:
                version_id = versioning.get_active_version_id(pid)
            
            if version_id:
                versioning.mark_final(pid, version_id)
                logger.info(f"Version {version_id} marked FINAL for {project_id}")
        
        # Build approval record
        revision = 0
        if os.path.exists(approval_path):
            with open(approval_path) as f:
                old = json.load(f)
            revision = old.get("revision_number", 0) + 1
        
        approval = {
            "status": "approved",
            "timestamp": datetime.now().isoformat(),
            "version_id": version_id,
            "surveyor_tag": "SURVEYOR_APPROVED",
            "rejection_reasons": [],
            "voice_feedback": None,
            "revision_number": revision,
            "locked": True,
        }
        
        with open(approval_path, "w") as f:
            json.dump(approval, f, indent=2)
        
        return {"status": "success", "approval": approval}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/report-reject")
async def reject_report(project_id: str, req: RejectionRequest):
    """Surveyor rejects the report — saves reasons and resets locked state."""
    try:
        from datetime import datetime
        
        approval_path = await _get_approval_path(project_id)
        os.makedirs(os.path.dirname(approval_path), exist_ok=True)
        
        revision = 0
        if os.path.exists(approval_path):
            with open(approval_path) as f:
                old = json.load(f)
            revision = old.get("revision_number", 0) + 1
        
        approval = {
            "status": "rejected",
            "timestamp": datetime.now().isoformat(),
            "version_id": req.version_id,
            "surveyor_tag": "SURVEYOR_REJECTED",
            "rejection_reasons": req.reasons,
            "voice_feedback": req.voice_feedback_path,
            "revision_number": revision,
            "locked": False,
        }
        
        with open(approval_path, "w") as f:
            json.dump(approval, f, indent=2)
        
        return {"status": "success", "approval": approval}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/report-approval")
async def get_approval_status(project_id: str):
    """Get current approval status for the project's final report."""
    approval_path = await _get_approval_path(project_id)
    
    if not os.path.exists(approval_path):
        return {
            "status": "pending",
            "timestamp": None,
            "surveyor_tag": None,
            "rejection_reasons": [],
            "revision_number": 0,
            "locked": False,
        }
    
    with open(approval_path) as f:
        return json.load(f)


# ══════════════════════════════════════════════════════════
# PHOTO REORDER — List & reorder evidence photos in report
# ══════════════════════════════════════════════════════════

class PhotoReorderRequest(BaseModel):
    photo_ids: list  # Ordered list of filenames

@router.get("/projects/{project_id}/report-photos")
async def list_report_photos(project_id: str):
    """List all evidence photos for the project, respecting saved order."""
    STORAGE_ROOT = os.environ.get("STORAGE_ROOT", "/app/storage")
    
    # Find photos in UUID directory
    photo_dir = os.path.join(STORAGE_ROOT, "Projects", project_id)
    photos = []
    
    if os.path.exists(photo_dir):
        # Scan all subdirectories for image files
        for root, dirs, files in os.walk(photo_dir):
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    rel_path = os.path.relpath(os.path.join(root, f), photo_dir)
                    full_path = os.path.join(root, f)
                    stat = os.stat(full_path)
                    photos.append({
                        "id": rel_path,
                        "filename": f,
                        "path": f"/storage/Projects/{project_id}/{rel_path}",
                        "size_kb": round(stat.st_size / 1024, 1),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
    
    # Also check semantic path
    project_dir = await _resolve_project_semantic_path(project_id)
    if project_dir and project_dir != photo_dir:
        for root, dirs, files in os.walk(project_dir):
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    rel_path = os.path.relpath(os.path.join(root, f), project_dir)
                    full_path = os.path.join(root, f)
                    stat = os.stat(full_path)
                    pid_entry = {
                        "id": rel_path,
                        "filename": f,
                        "path": f"/storage/Projects/{os.path.basename(project_dir)}/{rel_path}",
                        "size_kb": round(stat.st_size / 1024, 1),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                    # Avoid duplicates
                    if not any(p["filename"] == f for p in photos):
                        photos.append(pid_entry)
    
    # Apply saved order if exists
    order_file = f"project_data/{project_id}/reports/photo_order.json"
    if os.path.exists(order_file):
        with open(order_file) as f:
            saved_order = json.load(f)
        # Sort photos by saved order
        order_map = {pid: i for i, pid in enumerate(saved_order)}
        photos.sort(key=lambda p: order_map.get(p["id"], 999))
    
    return {
        "status": "success",
        "photos": photos,
        "total": len(photos),
        "project_id": project_id,
    }


@router.put("/projects/{project_id}/report-photos/reorder")
async def reorder_report_photos(project_id: str, req: PhotoReorderRequest):
    """Save the new photo order for the report."""
    order_dir = f"project_data/{project_id}/reports"
    os.makedirs(order_dir, exist_ok=True)
    order_file = os.path.join(order_dir, "photo_order.json")
    
    with open(order_file, "w") as f:
        json.dump(req.photo_ids, f, indent=2)
    
    return {
        "status": "success",
        "order": req.photo_ids,
        "total": len(req.photo_ids),
        "project_id": project_id,
    }
