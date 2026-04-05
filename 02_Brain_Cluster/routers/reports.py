from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
import os
import json
from datetime import datetime

router = APIRouter()

from services.storage_service import get_storage_service

# --- Storage Logic ---
storage_service = get_storage_service()

@router.get("/reports/{session_id}", response_class=HTMLResponse)
async def generate_report_html(session_id: str):
    """
    Generates a RICS-compliant HTML Report for the session.
    User can Print-to-PDF from browser.
    """
    session_dir = await storage_service.get_session_path(session_id)
    init_file = os.path.join(session_dir, "session_init.json")
    
    if not os.path.exists(init_file):
        raise HTTPException(status_code=404, detail="Session Data Not Found")
        
    try:
        with open(init_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Corrupt Data: {e}")
        
    title = data.get("title", f"Inspection {session_id}")
    address = data.get("address", {}).get("full_address", "Unknown Address")
    date_str = datetime.now().strftime("%d %B %Y")
    
    floor_plan = data.get("floor_plan", {})
    rooms = floor_plan.get("rooms", []) if "rooms" in floor_plan else []
    
    external_rooms = [r for r in rooms if r.get('type') == 'external']
    service_rooms = [r for r in rooms if r.get('type') == 'services']
    standard_rooms = [r for r in rooms if r.get('type') not in ['external', 'services']]
    
    floors = {}
    for r in standard_rooms:
        f_num = r.get('floor', 0)
        if f_num not in floors: floors[f_num] = []
        floors[f_num].append(r)
    sorted_floors = sorted(floors.keys())

    def render_room(room):
        room_id = room.get("id")
        room_dir = os.path.join(session_dir, room_id)
        image_html = ""
        if os.path.exists(room_dir):
            for root, dirs, files in os.walk(room_dir):
                for f in files:
                    if f.lower().endswith(('.jpg', '.png', '.jpeg')):
                        abs_file = os.path.abspath(os.path.join(root, f))
                        try:
                            rel_to_storage = os.path.relpath(abs_file, storage_service.storage_root)
                            img_url = "/storage/" + rel_to_storage.replace("\\", "/")
                            image_html += f"""
                            <div class="evidence-item">
                                <img src="{img_url}" loading="lazy">
                                <p>{f}</p>
                            </div>
                            """
                        except ValueError:
                            continue
        
        return f"""
        <div class="room-block">
            <h3>{room.get('name', 'Unnamed Room')}</h3>
            <div class="meta-tags">
                <span class="tag">{room.get('type', 'General')}</span>
                <span class="tag">{len(room.get('contexts', []))} Items Checked</span>
            </div>
            <div class="gallery">{image_html}</div>
            <div class="notes"><h4>Forensic Analysis</h4><div class="analysis-box"><p>No specific forensic notes recorded for this element.</p></div></div>
        </div>
        """

    html_content = ""
    if external_rooms:
        html_content += """<div class="section page-break"><h2>Section D: Outside the Property</h2>"""
        for r in external_rooms: html_content += render_room(r)
        html_content += "</div>"
    if sorted_floors:
        html_content += """<div class="section page-break"><h2>Section E: Inside the Property</h2>"""
        for f_num in sorted_floors:
            floor_name = {0: "Ground Floor", 1: "First Floor"}.get(f_num, f"Floor {f_num}")
            html_content += f"""<div class="floor-header"><h3>{floor_name}</h3></div>"""
            for r in floors[f_num]: html_content += render_room(r)
        html_content += "</div>"
    if service_rooms:
        html_content += """<div class="section page-break"><h2>Section F: Services</h2>"""
        for r in service_rooms: html_content += render_room(r)
        html_content += "</div>"

    html = f"""
    <!DOCTYPE html><html><head><title>RICS Report - {title}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Merriweather:wght@300;400;700&family=Open+Sans:wght@400;600&display=swap');
        body {{ font-family: 'Open Sans', sans-serif; padding: 0; margin: 0; color: #333; background: #eef2f5; }}
        .container {{ max-width: 210mm; margin: 0 auto; background: white; padding: 40px; min-height: 297mm; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        .title-page {{ text-align: center; padding-top: 100px; padding-bottom: 200px; page-break-after: always; }}
        .title-page h1 {{ font-family: 'Merriweather', serif; font-size: 3em; color: #2c3e50; margin-bottom: 20px; }}
        .section {{ margin-top: 40px; }}
        h2 {{ color: #c0392b; border-bottom: 2px solid #c0392b; padding-bottom: 10px; font-family: 'Merriweather', serif; }}
        .gallery {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 15px 0; }}
        .evidence-item img {{ width: 100%; height: 160px; object-fit: cover; border-radius: 4px; }}
        .analysis-box {{ background: #f9f9f9; padding: 15px; border-radius: 4px; border-left: 3px solid #ccc; font-style: italic; }}
        .page-break {{ page-break-before: always; }}
        @media print {{ body {{ background: white; }} .container {{ box-shadow: none; margin: 0; width: 100%; max-width: 100%; padding: 0; }} }}
        .print-btn {{ position: fixed; bottom: 20px; right: 20px; padding: 15px 30px; background: #c0392b; color: white; border-radius: 30px; cursor: pointer; }}
    </style></head>
    <body><button class="print-btn" onclick="window.print()">🖨️ Print RICS Report</button>
    <div class="container">
        <div class="title-page"><h1>Building Survey Report</h1><p><strong>Property:</strong> {address}</p><p><strong>Date:</strong> {date_str}</p></div>
        {html_content}
        <div class="section page-break"><h2>I. Risks & Regulations</h2><div class="analysis-box"><p><strong>Damp & Timber:</strong> AI Analysis required.</p></div></div>
    </div></body></html>"""
    return html

from forensic_engine import analyze_session, generate_partial_room_report, voice_edit_partial_report

@router.post("/reports/{session_id}/generate_ai")
async def generate_ai_report(session_id: str):
    """
    Triggers the Gemini Forensic Analysis for the session.
    """
    session_dir = await storage_service.get_session_path(session_id)
    init_file = os.path.join(session_dir, "session_init.json")
    if not os.path.exists(init_file): raise HTTPException(status_code=404, detail="Session Data Not Found")
        
    try:
        with open(init_file, 'r') as f: data = json.load(f)
        report = await analyze_session(session_id, data)
        report_path = os.path.join(session_dir, "forensic_report_v1.json")
        with open(report_path, "w", encoding="utf-8") as f: json.dump(report, f, indent=2)
        return {"status": "success", "report": report}
    except Exception as e:
        print(f"AI Generation Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reports/{session_id}/generate_partial")
async def generate_partial_report(session_id: str, payload: dict):
    """
    Triggers Gemini 3.1 chunked generation for a specific room.
    Expects payload: {"room_id": "..."}
    """
    room_id = payload.get("room_id")
    if not room_id:
        raise HTTPException(status_code=400, detail="room_id is required")

    session_dir = await storage_service.get_session_path(session_id)
    init_file = os.path.join(session_dir, "session_init.json")
    if not os.path.exists(init_file): raise HTTPException(status_code=404, detail="Session Data Not Found")
        
    try:
        with open(init_file, 'r') as f: data = json.load(f)
        report_chunk = await generate_partial_room_report(session_id, room_id, data)
        
        # Save the partial state
        room_dir = os.path.join(session_dir, room_id)
        os.makedirs(room_dir, exist_ok=True)
        chunk_path = os.path.join(room_dir, "partial_report.json")
        with open(chunk_path, "w", encoding="utf-8") as f: json.dump(report_chunk, f, indent=2)
            
        return {"status": "success", "room_id": room_id, "report_chunk": report_chunk}
    except Exception as e:
        print(f"Partial AI Generation Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reports/{session_id}/voice_edit_partial")
async def apply_voice_edit(session_id: str, payload: dict):
    """
    Applies surgical voice edits to a specific room's chunk using Gemini 3.1.
    Expects payload: {"room_id": "...", "edit_instruction": "..."}
    """
    room_id = payload.get("room_id")
    edit_instruction = payload.get("edit_instruction")
    if not room_id or not edit_instruction:
        raise HTTPException(status_code=400, detail="room_id and edit_instruction are required")

    session_dir = await storage_service.get_session_path(session_id)
    room_dir = os.path.join(session_dir, room_id)
    chunk_path = os.path.join(room_dir, "partial_report.json")
    
    if not os.path.exists(chunk_path): 
        raise HTTPException(status_code=404, detail="Partial report chunk not found. Generate it first.")
        
    try:
        with open(chunk_path, 'r') as f: current_chunk = json.load(f)
        updated_chunk = await voice_edit_partial_report(current_chunk, edit_instruction)
        
        # Overwrite the partial state with the edited version
        with open(chunk_path, "w", encoding="utf-8") as f: json.dump(updated_chunk, f, indent=2)
            
        return {"status": "success", "room_id": room_id, "report_chunk": updated_chunk}
    except Exception as e:
        print(f"Voice Edit API Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
