"""
Report Versioning System — Enhanced for PDF-per-version storage.
Tracks versions of RICS reports with MD + PDF, active version,
diff, and mark-final capabilities.

Each version stores:
- v{N}.md — Markdown source
- v{N}.pdf — Generated PDF (via Playwright)
- manifest.json — Version metadata with active_version_id
"""

import os
import json
import shutil
import logging
import difflib
from datetime import datetime
from typing import List, Optional, Dict

logger = logging.getLogger("report_versioning")


class ReportVersion:
    """Metadata for one version of a report"""
    def __init__(self, version_id: str, label: str, timestamp: str,
                 md_path: str, pdf_path: Optional[str] = None,
                 is_final: bool = False, changes_summary: str = "",
                 page_count: int = 0, pdf_size_kb: int = 0,
                 photo_count: int = 0):
        self.version_id = version_id
        self.label = label
        self.timestamp = timestamp
        self.md_path = md_path
        self.pdf_path = pdf_path
        self.is_final = is_final
        self.changes_summary = changes_summary
        self.page_count = page_count
        self.pdf_size_kb = pdf_size_kb
        self.photo_count = photo_count
    
    def to_dict(self) -> dict:
        return {
            "version_id": self.version_id,
            "label": self.label,
            "timestamp": self.timestamp,
            "md_path": self.md_path,
            "pdf_path": self.pdf_path,
            "is_final": self.is_final,
            "changes_summary": self.changes_summary,
            "page_count": self.page_count,
            "pdf_size_kb": self.pdf_size_kb,
            "photo_count": self.photo_count,
        }


class ReportVersioning:
    """Manages versioned RICS report storage with MD + PDF per version."""
    
    def __init__(self, storage_base: str):
        self.storage_base = storage_base
    
    def _versions_dir(self, project_id: str) -> str:
        d = os.path.join(self.storage_base, project_id, "report_versions")
        os.makedirs(d, exist_ok=True)
        return d
    
    def _manifest_path(self, project_id: str) -> str:
        return os.path.join(self._versions_dir(project_id), "manifest.json")
    
    def _load_manifest(self, project_id: str) -> dict:
        """Load manifest with versions list and active_version_id."""
        path = self._manifest_path(project_id)
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            # Migration: handle old list-only format
            if isinstance(data, list):
                data = {
                    "active_version_id": data[-1]["version_id"] if data else None,
                    "versions": data
                }
            return data
        return {"active_version_id": None, "versions": []}
    
    def _save_manifest(self, project_id: str, manifest: dict):
        with open(self._manifest_path(project_id), "w") as f:
            json.dump(manifest, f, indent=2)
    
    def save_version(
        self, project_id: str, md_content: str,
        label: str = "", changes_summary: str = "",
        photo_count: int = 0
    ) -> ReportVersion:
        """Save a new version of the report (MD only — PDF added separately)."""
        manifest = self._load_manifest(project_id)
        versions = manifest.get("versions", [])
        version_num = len(versions) + 1
        version_id = f"v{version_num}"
        
        if not label:
            label = f"Version {version_num}"
        
        timestamp = datetime.now().isoformat()
        
        # Save MD file
        md_filename = f"{version_id}.md"
        md_path = os.path.join(self._versions_dir(project_id), md_filename)
        with open(md_path, "w") as f:
            f.write(md_content)
        
        version = ReportVersion(
            version_id=version_id,
            label=label,
            timestamp=timestamp,
            md_path=md_filename,
            is_final=False,
            changes_summary=changes_summary,
            photo_count=photo_count,
        )
        
        versions.append(version.to_dict())
        manifest["versions"] = versions
        manifest["active_version_id"] = version_id  # Latest is always active
        self._save_manifest(project_id, manifest)
        
        logger.info(f"Saved version {version_id} for project {project_id}")
        return version
    
    def save_version_pdf(
        self, project_id: str, version_id: str, pdf_source_path: str
    ) -> Optional[str]:
        """
        Copy/link a generated PDF to the version's storage.
        Returns the stored PDF path.
        """
        manifest = self._load_manifest(project_id)
        versions = manifest.get("versions", [])
        
        for v in versions:
            if v["version_id"] == version_id:
                pdf_filename = f"{version_id}.pdf"
                pdf_dest = os.path.join(self._versions_dir(project_id), pdf_filename)
                
                # Copy PDF to versioned storage
                if os.path.exists(pdf_source_path):
                    shutil.copy2(pdf_source_path, pdf_dest)
                    v["pdf_path"] = pdf_filename
                    
                    # Update metadata
                    v["pdf_size_kb"] = os.path.getsize(pdf_dest) // 1024
                    try:
                        import fitz
                        doc = fitz.open(pdf_dest)
                        v["page_count"] = len(doc)
                        doc.close()
                    except Exception:
                        pass
                    
                    self._save_manifest(project_id, manifest)
                    logger.info(f"Saved PDF for {version_id}: {pdf_filename} ({v['pdf_size_kb']}KB)")
                    return pdf_dest
                else:
                    logger.warning(f"PDF source not found: {pdf_source_path}")
        
        return None
    
    def get_version_pdf_path(self, project_id: str, version_id: str) -> Optional[str]:
        """Get the absolute path to a version's PDF file."""
        manifest = self._load_manifest(project_id)
        for v in manifest.get("versions", []):
            if v["version_id"] == version_id and v.get("pdf_path"):
                return os.path.join(self._versions_dir(project_id), v["pdf_path"])
        return None
    
    def list_versions(self, project_id: str) -> List[dict]:
        """List all versions for a project."""
        manifest = self._load_manifest(project_id)
        return manifest.get("versions", [])
    
    def get_active_version_id(self, project_id: str) -> Optional[str]:
        """Get the currently active version ID for editing."""
        manifest = self._load_manifest(project_id)
        return manifest.get("active_version_id")
    
    def set_active_version(self, project_id: str, version_id: str) -> bool:
        """Set a version as the active (default) version for editing."""
        manifest = self._load_manifest(project_id)
        versions = manifest.get("versions", [])
        
        # Verify version exists
        if not any(v["version_id"] == version_id for v in versions):
            return False
        
        manifest["active_version_id"] = version_id
        self._save_manifest(project_id, manifest)
        logger.info(f"Set active version to {version_id} for {project_id}")
        return True
    
    def get_version_content(self, project_id: str, version_id: str) -> Optional[str]:
        """Get the MD content of a specific version."""
        manifest = self._load_manifest(project_id)
        for v in manifest.get("versions", []):
            if v["version_id"] == version_id:
                md_path = os.path.join(self._versions_dir(project_id), v["md_path"])
                if os.path.exists(md_path):
                    with open(md_path) as f:
                        return f.read()
        return None
    
    def mark_final(self, project_id: str, version_id: str) -> bool:
        """Mark a version as the final report."""
        manifest = self._load_manifest(project_id)
        versions = manifest.get("versions", [])
        
        # Unmark all previous finals
        for v in versions:
            v["is_final"] = False
        
        # Mark the selected version
        for v in versions:
            if v["version_id"] == version_id:
                v["is_final"] = True
                if "FINAL" not in v["label"]:
                    v["label"] = f"FINAL — {v['label']}"
                manifest["active_version_id"] = version_id
                self._save_manifest(project_id, manifest)
                logger.info(f"Marked {version_id} as FINAL for {project_id}")
                return True
        
        return False
    
    def get_final_version(self, project_id: str) -> Optional[dict]:
        """Get the version marked as final."""
        manifest = self._load_manifest(project_id)
        for v in manifest.get("versions", []):
            if v.get("is_final"):
                return v
        return None
    
    def diff_versions(
        self, project_id: str, v1_id: str, v2_id: str
    ) -> Optional[str]:
        """Generate a diff between two versions."""
        content1 = self.get_version_content(project_id, v1_id)
        content2 = self.get_version_content(project_id, v2_id)
        
        if content1 is None or content2 is None:
            return None
        
        diff = difflib.unified_diff(
            content1.splitlines(keepends=True),
            content2.splitlines(keepends=True),
            fromfile=v1_id,
            tofile=v2_id,
            n=3
        )
        
        return "".join(diff)
    
    def get_latest_content(self, project_id: str) -> Optional[str]:
        """Get the active version's content (or most recent)."""
        manifest = self._load_manifest(project_id)
        active_id = manifest.get("active_version_id")
        
        if active_id:
            content = self.get_version_content(project_id, active_id)
            if content:
                return content
        
        # Fallback: most recent
        versions = manifest.get("versions", [])
        if versions:
            latest = versions[-1]
            return self.get_version_content(project_id, latest["version_id"])
        return None
