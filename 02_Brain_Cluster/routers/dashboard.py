"""
Dashboard API — Surveyor Control Panel
Provides endpoints for the dashboard SPA (overview, filtered projects, status management).
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from database import db
import os, json, glob, logging

logger = logging.getLogger("dashboard")
router = APIRouter()


# ═══════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════

class StatusUpdate(BaseModel):
    status: str  # 'active', 'completed', 'archived'


# ═══════════════════════════════════════════
# GET /dashboard/overview  — KPI + project list
# ═══════════════════════════════════════════

@router.get("/dashboard/overview")
async def dashboard_overview(user_id: Optional[str] = None):
    """Returns KPI counts and full project list for the dashboard."""
    
    base_where = ""
    params = []
    if user_id:
        base_where = "WHERE p.surveyor_id = $1"
        params = [user_id]
    
    # KPI counts
    counts = await db.fetchrow(f"""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'active' OR status IS NULL) as active,
            COUNT(*) FILTER (WHERE status = 'completed') as completed,
            COUNT(*) FILTER (WHERE status = 'archived') as archived
        FROM projects p {base_where}
    """, *params)
    
    # Project list (most recent first)
    projects = await db.fetch(f"""
        SELECT 
            p.id, p.reference_number, p.client_name, p.address,
            p.status, p.approval_status, p.created_at,
            p.total_photos, p.total_elements, p.urgent_count, p.attention_count,
            p.latest_version, p.surveyor_name, p.rics_number,
            p.inspection_date, p.report_date, p.property_type,
            p.site_metadata
        FROM projects p 
        {base_where}
        ORDER BY p.created_at DESC
    """, *params)
    
    project_list = []
    for p in projects:
        meta = p.get("site_metadata") or {}
        if isinstance(meta, str):
            meta = json.loads(meta)
        
        # Extract address from metadata if not in column
        addr = p.get("address") or ""
        if not addr and meta:
            addr_obj = meta.get("address", {})
            if isinstance(addr_obj, dict):
                addr = addr_obj.get("full_address", "")
            elif isinstance(addr_obj, str):
                addr = addr_obj
        
        project_list.append({
            "id": str(p["id"]),
            "reference": p.get("reference_number", ""),
            "client_name": p.get("client_name", ""),
            "address": addr,
            "status": p.get("status") or "active",
            "approval_status": p.get("approval_status") or "pending",
            "created_at": p["created_at"].isoformat() if p.get("created_at") else "",
            "inspection_date": str(p.get("inspection_date") or ""),
            "report_date": str(p.get("report_date") or ""),
            "total_photos": p.get("total_photos") or 0,
            "total_elements": p.get("total_elements") or 0,
            "urgent_count": p.get("urgent_count") or 0,
            "attention_count": p.get("attention_count") or 0,
            "latest_version": p.get("latest_version") or "",
            "surveyor_name": p.get("surveyor_name") or "",
            "property_type": p.get("property_type") or "",
        })
    
    return {
        "kpi": {
            "total": counts["total"],
            "active": counts["active"],
            "completed": counts["completed"],
            "archived": counts["archived"],
        },
        "projects": project_list,
    }


# ═══════════════════════════════════════════
# GET /dashboard/projects?status=active
# ═══════════════════════════════════════════

@router.get("/dashboard/projects")
async def dashboard_projects(
    status: Optional[str] = Query(None, description="Filter: active, completed, archived"),
    search: Optional[str] = Query(None, description="Search by address or reference"),
):
    """Returns filtered project list."""
    conditions = []
    params = []
    idx = 1
    
    if status:
        conditions.append(f"(p.status = ${idx} OR (${idx} = 'active' AND p.status IS NULL))")
        params.append(status)
        idx += 1
    
    if search:
        conditions.append(f"(p.address ILIKE ${idx} OR p.reference_number ILIKE ${idx} OR p.client_name ILIKE ${idx})")
        params.append(f"%{search}%")
        idx += 1
    
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    projects = await db.fetch(f"""
        SELECT id, reference_number, client_name, address, status, 
               approval_status, created_at, total_photos, total_elements,
               urgent_count, attention_count, latest_version, 
               surveyor_name, inspection_date, property_type, site_metadata
        FROM projects p {where}
        ORDER BY created_at DESC
    """, *params)
    
    result = []
    for p in projects:
        meta = p.get("site_metadata") or {}
        if isinstance(meta, str):
            meta = json.loads(meta)
        addr = p.get("address") or ""
        if not addr and meta:
            addr_obj = meta.get("address", {})
            addr = addr_obj.get("full_address", "") if isinstance(addr_obj, dict) else str(addr_obj)
        
        result.append({
            "id": str(p["id"]),
            "reference": p.get("reference_number", ""),
            "client_name": p.get("client_name", ""),
            "address": addr,
            "status": p.get("status") or "active",
            "approval_status": p.get("approval_status") or "pending",
            "created_at": p["created_at"].isoformat() if p.get("created_at") else "",
            "inspection_date": str(p.get("inspection_date") or ""),
            "total_photos": p.get("total_photos") or 0,
            "total_elements": p.get("total_elements") or 0,
            "urgent_count": p.get("urgent_count") or 0,
            "attention_count": p.get("attention_count") or 0,
            "latest_version": p.get("latest_version") or "",
            "surveyor_name": p.get("surveyor_name") or "",
            "property_type": p.get("property_type") or "",
        })
    
    return {"projects": result, "total": len(result)}


# ═══════════════════════════════════════════
# PUT /projects/{id}/status  — change project lifecycle
# ═══════════════════════════════════════════

@router.put("/projects/{project_id}/status")
async def update_project_status(project_id: str, body: StatusUpdate):
    """Change project status: active → completed → archived."""
    valid = {"active", "completed", "archived"}
    if body.status not in valid:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid}")
    
    result = await db.execute(
        "UPDATE projects SET status = $1 WHERE id = $2",
        body.status, project_id
    )
    
    return {"status": "success", "new_status": body.status}


# ═══════════════════════════════════════════
# GET /projects/{id}/summary  — full project summary
# ═══════════════════════════════════════════

@router.get("/projects/{project_id}/summary")
async def project_summary(project_id: str):
    """Returns comprehensive project summary for the detail page."""
    
    p = await db.fetchrow(
        "SELECT * FROM projects WHERE id = $1", project_id
    )
    if not p:
        raise HTTPException(404, "Project not found")
    
    meta = p.get("site_metadata") or {}
    if isinstance(meta, str):
        meta = json.loads(meta)
    
    addr = p.get("address") or ""
    if not addr:
        addr_obj = meta.get("address", {})
        addr = addr_obj.get("full_address", "") if isinstance(addr_obj, dict) else str(addr_obj or "")
    
    # Find project folder on disk
    from routers.projects import _resolve_project_semantic_path
    project_dir = await _resolve_project_semantic_path(project_id)
    
    # Get version info
    versions = []
    if project_dir:
        ver_dir = os.path.join(project_dir, "report_versions")
        if os.path.isdir(ver_dir):
            for f in sorted(os.listdir(ver_dir)):
                if f.endswith(".md"):
                    vid = f.replace(".md", "")
                    pdf_exists = os.path.exists(os.path.join(ver_dir, f"{vid}.pdf"))
                    stat = os.stat(os.path.join(ver_dir, f))
                    versions.append({
                        "version_id": vid,
                        "created_at": stat.st_mtime,
                        "size_bytes": stat.st_size,
                        "has_pdf": pdf_exists,
                    })
    
    # Check for final report files
    has_report = False
    report_html_url = ""
    report_pdf_url = ""
    if project_dir:
        if os.path.exists(os.path.join(project_dir, "rics_report_latest.html")):
            has_report = True
            # Build URL relative to storage
            from services.storage_service import get_storage_service
            storage = get_storage_service()
            try:
                rel = os.path.relpath(project_dir, storage.storage_root)
                report_html_url = f"/storage/{rel}/rics_report_latest.html"
                report_pdf_url = f"/storage/{rel}/RICS_Final_Report.pdf"
            except:
                pass
    
    # Photo preview (first 6)
    photo_previews = []
    if project_dir:
        patterns = ["**/*.jpg", "**/*.jpeg", "**/*.png"]
        seen = set()
        for pat in patterns:
            for img_path in glob.glob(os.path.join(project_dir, pat), recursive=True):
                if "report_versions" in img_path:
                    continue
                if img_path not in seen:
                    seen.add(img_path)
                    try:
                        from services.storage_service import get_storage_service
                        storage = get_storage_service()
                        rel = os.path.relpath(img_path, storage.storage_root)
                        photo_previews.append(f"/storage/{rel}")
                    except:
                        pass
                if len(photo_previews) >= 6:
                    break
            if len(photo_previews) >= 6:
                break
    
    # Count total photos
    total_photos_on_disk = 0
    if project_dir:
        for pat in ["**/*.jpg", "**/*.jpeg", "**/*.png"]:
            total_photos_on_disk += len([
                f for f in glob.glob(os.path.join(project_dir, pat), recursive=True)
                if "report_versions" not in f
            ])
    
    # Sessions
    sessions = await db.fetch(
        "SELECT id, title, status, started_at FROM sessions WHERE project_id = $1 ORDER BY started_at DESC",
        project_id
    )
    
    return {
        "project": {
            "id": str(p["id"]),
            "reference": p.get("reference_number", ""),
            "client_name": p.get("client_name", ""),
            "address": addr,
            "status": p.get("status") or "active",
            "approval_status": p.get("approval_status") or "pending",
            "created_at": p["created_at"].isoformat() if p.get("created_at") else "",
            "inspection_date": str(p.get("inspection_date") or ""),
            "report_date": str(p.get("report_date") or ""),
            "surveyor_name": p.get("surveyor_name") or meta.get("surveyor_name", ""),
            "rics_number": p.get("rics_number") or "",
            "property_type": p.get("property_type") or "",
            "total_photos": total_photos_on_disk,
            "total_elements": p.get("total_elements") or 0,
            "urgent_count": p.get("urgent_count") or 0,
            "attention_count": p.get("attention_count") or 0,
            "latest_version": p.get("latest_version") or (versions[-1]["version_id"] if versions else ""),
        },
        "has_report": has_report,
        "report_html_url": report_html_url,
        "report_pdf_url": report_pdf_url,
        "versions": versions,
        "photo_previews": photo_previews,
        "total_photos_on_disk": total_photos_on_disk,
        "sessions": [
            {
                "id": s["id"],
                "title": s.get("title", ""),
                "status": s.get("status", ""),
                "started_at": s["started_at"].isoformat() if s.get("started_at") else "",
            }
            for s in sessions
        ],
    }
