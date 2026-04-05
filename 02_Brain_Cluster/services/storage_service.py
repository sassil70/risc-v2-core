import os
import logging

logger = logging.getLogger("StorageService")

class StorageService:
    def __init__(self, storage_root: str):
        self.storage_root = os.path.abspath(storage_root)
        os.makedirs(self.storage_root, exist_ok=True)
        logger.info(f"StorageService initialized at: {self.storage_root}")

    async def get_session_path(self, session_id: str) -> str:
        """
        [RADICAL FIX] Uses DB to dynamically construct Semantic Storage paths.
        Format: Storage/Projects/[Reference]_[Client]/[YYYY-MM-DD]_Session/
        """
        # Late import to prevent circular dependency at startup
        from database import db
        import datetime
        
        # Handle draft pseudo-sessions from Voice Architect tests
        if session_id.startswith("draft_"):
           path = os.path.join(self.storage_root, "Drafts", session_id)
           os.makedirs(path, exist_ok=True)
           return path
           
        try:
            query = """
                SELECT p.reference_number, p.client_name, s.started_at 
                FROM sessions s 
                LEFT JOIN projects p ON s.project_id = p.id 
                WHERE s.id = $1
            """
            row = await db.fetchrow(query, session_id)
            if row:
                ref = row['reference_number'] or "UNKNOWN_REF"
                client = row['client_name'] or "Unknown_Client"
                
                # Clean strings for filesystem safety
                safe_ref = str(ref).replace("/", "-").replace("\\", "-").replace(" ", "_")
                safe_client = str(client).replace("/", "-").replace("\\", "-").replace(" ", "_")
                
                started_at = row['started_at'] or datetime.datetime.now(datetime.timezone.utc)
                date_str = started_at.strftime("%Y-%m-%d")
                
                project_folder = f"{safe_ref}_{safe_client}"
                session_folder = f"{date_str}_Session_{session_id[:8]}"
                
                path = os.path.join(self.storage_root, "Projects", project_folder, session_folder)
                os.makedirs(path, exist_ok=True)
                return path
        except Exception as e:
            logger.error(f"Failed to lookup semantic path for {session_id}: {e}")
            
        # Fallback if DB fails or session not found
        path = os.path.join(self.storage_root, "Projects", "Orphaned_Sessions", session_id)
        os.makedirs(path, exist_ok=True)
        return path

    async def get_reports_path(self, session_id: str) -> str:
        path = os.path.join(await self.get_session_path(session_id), "reports")
        os.makedirs(path, exist_ok=True)
        return path

    async def get_media_path(self, session_id: str) -> str:
        path = os.path.join(await self.get_session_path(session_id), "evidence")
        os.makedirs(path, exist_ok=True)
        return path

    def get_log_path(self, user_id: str) -> str:
        path = os.path.join(self.storage_root, "users", user_id, "logs")
        os.makedirs(path, exist_ok=True)
        return path

# Global singleton or inject as needed
def get_storage_service():
    """
    Independent calculation of STORAGE_ROOT to avoid circular imports.
    """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    EXTERNAL_STORAGE = os.path.abspath(os.path.join(BASE_DIR, "..", "storage"))
    INTERNAL_STORAGE = os.path.join(BASE_DIR, "storage")
    STORAGE_ROOT = EXTERNAL_STORAGE if os.path.exists(EXTERNAL_STORAGE) else INTERNAL_STORAGE
    
    return StorageService(STORAGE_ROOT)
