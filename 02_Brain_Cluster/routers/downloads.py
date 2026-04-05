"""
Downloads Router — 3-Tier Download Center for Surveyor Dashboard.

Tier 1: Full Report (PDF + DOCX)
Tier 2: Room Partial Reports (PDF + DOCX)
Tier 3: Raw Data ZIP (photos + audio + JSON)
"""

import os
import io
import json
import glob
import zipfile
import tempfile
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from database import db

logger = logging.getLogger("downloads")
router = APIRouter()


# ─── Helper: Resolve project path ───
async def _resolve_project_path(project_id: str) -> str:
    """Find the project's storage folder."""
    from routers.projects import _resolve_project_semantic_path
    path = await _resolve_project_semantic_path(project_id)
    if not path or not os.path.exists(path):
        raise HTTPException(404, "Project not found")
    return path


def _get_storage_root() -> str:
    """Get the storage root path."""
    from services.storage_service import get_storage_service
    return get_storage_service().storage_root


# ═══════════════════════════════════════════
# TIER 1: FULL REPORT
# ═══════════════════════════════════════════

@router.get("/projects/{project_id}/download/pdf")
async def download_full_pdf(project_id: str):
    """Download the full RICS report as PDF."""
    project_dir = await _resolve_project_path(project_id)

    # Search for PDF
    candidates = [
        os.path.join(project_dir, "RICS_Final_Report.pdf"),
        os.path.join(project_dir, "reports", "RICS_Final_Report.pdf"),
        os.path.join(project_dir, "reports", "RICS_Final_Report_v2.pdf"),
    ]

    # Also check report_versions for latest
    ver_dir = os.path.join(project_dir, "report_versions")
    if os.path.isdir(ver_dir):
        pdfs = sorted([f for f in os.listdir(ver_dir) if f.endswith('.pdf')])
        if pdfs:
            candidates.insert(0, os.path.join(ver_dir, pdfs[-1]))

    pdf_path = None
    for c in candidates:
        if os.path.exists(c):
            pdf_path = c
            break

    if not pdf_path:
        raise HTTPException(404, "PDF not found. Generate the report first.")

    # Get reference for filename
    ref = await _get_project_ref(project_id)
    filename = f"RICS_Report_{ref}.pdf"

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/projects/{project_id}/download/docx")
async def download_full_docx(project_id: str):
    """Download the full RICS report as Word DOCX with embedded images."""
    project_dir = await _resolve_project_path(project_id)
    ref = await _get_project_ref(project_id)

    # Find the HTML source
    html_candidates = [
        os.path.join(project_dir, "rics_report_latest.html"),
        os.path.join(project_dir, "RICS_Final_Report.html"),
        os.path.join(project_dir, "reports", "RICS_Final_Report.html"),
        os.path.join(project_dir, "reports", "RICS_Final_Report_v2.html"),
    ]

    html_path = None
    for c in html_candidates:
        if os.path.exists(c):
            html_path = c
            break

    if not html_path:
        raise HTTPException(404, "HTML report not found. Generate the report first.")

    # Generate DOCX
    output_path = os.path.join(project_dir, f"RICS_Report_{ref}.docx")

    try:
        from services.docx_builder import build_docx_from_html
        build_docx_from_html(
            html_path=html_path,
            output_path=output_path,
            reference=ref,
            storage_root=_get_storage_root(),
        )
    except Exception as e:
        logger.error(f"DOCX generation failed: {e}")
        raise HTTPException(500, f"DOCX generation failed: {str(e)}")

    filename = f"RICS_Report_{ref}.docx"
    return FileResponse(
        path=output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ═══════════════════════════════════════════
# TIER 2: ROOM PARTIAL REPORTS
# ═══════════════════════════════════════════

@router.get("/projects/{project_id}/download/rooms")
async def list_downloadable_rooms(project_id: str):
    """List all rooms that have partial reports available for download."""
    project_dir = await _resolve_project_path(project_id)

    rooms = []
    # Find all partial_report.json files across sessions
    for pr_path in glob.glob(os.path.join(project_dir, "**/partial_report.json"), recursive=True):
        try:
            with open(pr_path, "r") as f:
                data = json.load(f)
            room_id = data.get("room_id", "")
            room_name = data.get("room_name", room_id)
            room_folder = os.path.dirname(pr_path)

            # Count photos and audio
            photo_count = 0
            audio_count = 0
            contexts = []
            for ctx_name in sorted(os.listdir(room_folder)):
                ctx_path = os.path.join(room_folder, ctx_name)
                if os.path.isdir(ctx_path) and ctx_name.startswith("Context_"):
                    ctx_label = ctx_name.replace("Context_", "").replace("_", " ")
                    ctx_photos = len([f for f in os.listdir(ctx_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
                    ctx_audio = len([f for f in os.listdir(ctx_path) if f.lower().endswith(('.m4a', '.mp3', '.wav', '.aac'))])
                    photo_count += ctx_photos
                    audio_count += ctx_audio
                    contexts.append({
                        "name": ctx_label,
                        "photos": ctx_photos,
                        "audio": ctx_audio,
                    })

            elements_count = len(data.get("elements", []))
            urgent = sum(1 for e in data.get("elements", []) if e.get("condition_rating", 0) == 3)
            attention = sum(1 for e in data.get("elements", []) if e.get("condition_rating", 0) == 2)

            rooms.append({
                "room_id": room_id,
                "room_name": room_name,
                "floor": data.get("floor_level", ""),
                "elements": elements_count,
                "urgent": urgent,
                "attention": attention,
                "photos": photo_count,
                "audio": audio_count,
                "contexts": contexts,
                "partial_report_path": pr_path,
                "room_folder": room_folder,
            })
        except Exception as e:
            logger.warning(f"Failed to parse {pr_path}: {e}")

    return {"rooms": rooms}


@router.get("/projects/{project_id}/download/room/{room_id}/docx")
async def download_room_docx(project_id: str, room_id: str):
    """Download a single room report as DOCX with photos."""
    project_dir = await _resolve_project_path(project_id)
    ref = await _get_project_ref(project_id)

    # Find the room's partial_report.json
    pr_path, room_folder = _find_room_files(project_dir, room_id)

    if not pr_path:
        raise HTTPException(404, f"Room {room_id} not found")

    output_path = os.path.join(tempfile.gettempdir(), f"Room_{room_id}_{ref}.docx")

    try:
        from services.docx_builder import build_room_docx
        build_room_docx(
            partial_report_path=pr_path,
            room_folder=room_folder,
            output_path=output_path,
            reference=ref,
            storage_root=_get_storage_root(),
        )
    except Exception as e:
        logger.error(f"Room DOCX generation failed: {e}")
        raise HTTPException(500, f"Room DOCX generation failed: {str(e)}")

    # Get room name for filename
    with open(pr_path, 'r') as f:
        room_name = json.load(f).get("room_name", room_id)
    safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in room_name)
    filename = f"Room_{safe_name}_{ref}.docx"

    return FileResponse(
        path=output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/projects/{project_id}/download/room/{room_id}/pdf")
async def download_room_pdf(project_id: str, room_id: str):
    """Download a single room report as PDF."""
    project_dir = await _resolve_project_path(project_id)
    ref = await _get_project_ref(project_id)

    pr_path, room_folder = _find_room_files(project_dir, room_id)
    if not pr_path:
        raise HTTPException(404, f"Room {room_id} not found")

    # Generate DOCX first, then convert using the room report
    # Actually, build HTML and use Playwright for PDF
    output_pdf = os.path.join(tempfile.gettempdir(), f"Room_{room_id}_{ref}.pdf")

    try:
        # Build a simple HTML from partial report for PDF
        html = _build_room_html(pr_path, room_folder, ref, _get_storage_root())

        from services.playwright_pdf_generator import generate_pdf_playwright
        import asyncio
        await generate_pdf_playwright(html, output_pdf, ref)
    except Exception as e:
        logger.error(f"Room PDF generation failed: {e}")
        raise HTTPException(500, f"Room PDF generation failed: {str(e)}")

    with open(pr_path, 'r') as f:
        room_name = json.load(f).get("room_name", room_id)
    safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in room_name)
    filename = f"Room_{safe_name}_{ref}.pdf"

    return FileResponse(
        path=output_pdf,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ═══════════════════════════════════════════
# TIER 3: RAW DATA ZIP
# ═══════════════════════════════════════════

@router.get("/projects/{project_id}/download/raw-zip")
async def download_raw_zip(project_id: str):
    """
    Download all raw project data as a ZIP archive.
    Includes: photos, audio recordings, JSON files, organized by room/context.
    """
    project_dir = await _resolve_project_path(project_id)
    ref = await _get_project_ref(project_id)

    # Create ZIP in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(project_dir):
            # Skip report_versions folder (too large, user has direct access)
            if 'report_versions' in root:
                continue

            for fname in files:
                full_path = os.path.join(root, fname)
                ext = fname.lower().split('.')[-1] if '.' in fname else ''

                # Include: photos, audio, JSON, reports
                include_exts = {'jpg', 'jpeg', 'png', 'gif',  # photos
                                'm4a', 'mp3', 'wav', 'aac', 'opus',  # audio
                                'json',  # data
                                'html', 'md', 'pdf',  # reports
                                }

                if ext in include_exts:
                    # Create a clean relative path
                    rel_path = os.path.relpath(full_path, project_dir)
                    arcname = f"{ref}/{rel_path}"
                    try:
                        zf.write(full_path, arcname)
                    except Exception as e:
                        logger.warning(f"Failed to add {full_path} to ZIP: {e}")

    zip_buffer.seek(0)
    zip_size_mb = len(zip_buffer.getvalue()) / (1024 * 1024)
    logger.info(f"RAW ZIP generated: {zip_size_mb:.1f}MB for {ref}")

    filename = f"RICS_RawData_{ref}_{datetime.now().strftime('%Y%m%d')}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ═══════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════

async def _get_project_ref(project_id: str) -> str:
    """Get the project reference number."""
    try:
        row = await db.fetchrow("SELECT reference_number FROM projects WHERE id = $1", project_id)
        if row and row['reference_number']:
            # Clean the reference for use in filenames
            ref = row['reference_number'].strip()
            return "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in ref)
    except:
        pass
    return project_id[:8]


def _find_room_files(project_dir: str, room_id: str):
    """Find partial_report.json and folder for a specific room."""
    for pr_path in glob.glob(os.path.join(project_dir, f"**/{room_id}/partial_report.json"), recursive=True):
        return pr_path, os.path.dirname(pr_path)
    return None, None


def _build_room_html(pr_path: str, room_folder: str, ref: str, storage_root: str) -> str:
    """Build HTML for a room report for Playwright PDF rendering."""
    with open(pr_path, 'r') as f:
        report = json.load(f)

    room_name = report.get('room_name', 'Unknown Room')
    floor = report.get('floor_level', 'N/A')
    summary = report.get('inspection_summary', '')

    html_parts = [f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #231F20; margin: 40px; }}
h1 {{ color: #4D2D69; border-bottom: 3px solid #D4A843; padding-bottom: 8px; }}
h2 {{ color: #4D2D69; margin-top: 24px; }}
h3 {{ color: #231F20; margin-top: 16px; }}
.meta {{ color: #6B7280; font-size: 14px; margin-bottom: 20px; }}
.cr1 {{ color: #4CAF50; font-weight: bold; }}
.cr2 {{ color: #FF9800; font-weight: bold; }}
.cr3 {{ color: #F44336; font-weight: bold; }}
.defect {{ background: #FFF3E0; border-left: 4px solid #FF9800; padding: 8px 12px; margin: 8px 0; }}
img {{ max-width: 100%; height: auto; margin: 8px 0; border-radius: 4px; border: 1px solid #ddd; }}
.photo-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 12px 0; }}
</style>
</head><body>
<h1>Room Report: {room_name}</h1>
<div class="meta">Reference: {ref} | Floor: {floor}</div>
"""]

    if summary:
        html_parts.append(f"<h2>Inspection Summary</h2><p>{summary}</p>")

    for el in report.get('elements', []):
        cr = el.get('condition_rating', 0)
        cr_class = f"cr{cr}" if cr in (1, 2, 3) else ""
        cr_label = {1: 'CR1 — No repair', 2: 'CR2 — Repair needed', 3: 'CR3 — Urgent'}.get(cr, f'CR{cr}')

        html_parts.append(f"""
        <h3>{el.get('rics_element', el.get('name', ''))}</h3>
        <p class="{cr_class}">Condition Rating: {cr_label}</p>
        <p>{el.get('condition_description', '')}</p>
        """)

        for d in el.get('defects_identified', []):
            html_parts.append(f"""
            <div class="defect">
                <strong>⚠ {d.get('defect_type', 'Defect')}</strong>
                {f"<br>Severity: {d['severity']}" if d.get('severity') else ''}
                {f"<br>Location: {d['location']}" if d.get('location') else ''}
                {f"<br>Action: {d['recommended_action']}" if d.get('recommended_action') else ''}
            </div>""")

        # Evidence photos
        photos = el.get('evidence_photos', [])
        if photos:
            html_parts.append('<div class="photo-grid">')
            for photo_url in photos:
                abs_path = photo_url.replace("/storage/", f"{storage_root}/")
                if os.path.exists(abs_path):
                    html_parts.append(f'<img src="file://{abs_path}" />')
            html_parts.append('</div>')

    # Context photos
    if os.path.isdir(room_folder):
        html_parts.append('<div style="page-break-before: always;"></div>')
        html_parts.append('<h2>All Context Photos</h2>')
        for ctx_name in sorted(os.listdir(room_folder)):
            ctx_path = os.path.join(room_folder, ctx_name)
            if os.path.isdir(ctx_path) and ctx_name.startswith("Context_"):
                label = ctx_name.replace("Context_", "").replace("_", " ")
                imgs = sorted([f for f in os.listdir(ctx_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
                if imgs:
                    html_parts.append(f'<h3>📷 {label}</h3><div class="photo-grid">')
                    for img in imgs:
                        html_parts.append(f'<img src="file://{os.path.join(ctx_path, img)}" />')
                    html_parts.append('</div>')

    html_parts.append("</body></html>")
    return "\n".join(html_parts)
