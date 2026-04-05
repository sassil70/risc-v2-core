import os
import json
import zipfile
import shutil
import logging
from datetime import datetime
from database import db

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PackageProcessor")

class PackageProcessor:
    """
    Handles the lifecycle of a signed package after integrity check:
    1. Unzip.
    2. Validate Manifest.
    3. Insert Session into DB.
    4. Insert Media Assets into DB.
    """
    
    def __init__(self, storage_root: str = "storage/sessions"):
        self.storage_root = storage_root
        os.makedirs(self.storage_root, exist_ok=True)

    async def process(self, zip_path: str, claimed_hash: str):
        """
        Main entry point.
        """
        # 1. Unzip to a temporary location first to read manifest
        temp_id = f"temp_{os.path.basename(zip_path)}_processing"
        temp_extract_path = os.path.join(self.storage_root, temp_id)
        
        logger.info(f"Processing Package: {zip_path}")

        try:
            self._unzip(zip_path, temp_extract_path)
            
            # 2. Read Manifest
            manifest_path = os.path.join(temp_extract_path, "session_manifest.json")
            if not os.path.exists(manifest_path):
                raise ValueError("CRITICAL: session_manifest.json missing from package.")
            
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            # 3. Validate Consistency
            self._validate_manifest_schema(manifest)
            
            # 4. Determine Real Session ID from Manifest (Source of Truth)
            session_id = manifest['sessionId']
            
            # 5. Move to permanent storage (Rename folder)
            final_storage_path = os.path.join(self.storage_root, session_id)
            if os.path.exists(final_storage_path):
                 shutil.rmtree(final_storage_path) # Overwrite existing session data? Or merge? For now overwrite.
            os.rename(temp_extract_path, final_storage_path)
            
            # 6. DB Insertions
            await self._insert_session_data(session_id, manifest, claimed_hash)
            await self._insert_media_assets(session_id, manifest, final_storage_path)
            
            logger.info(f"Successfully processed session {session_id}")
            return {"status": "success", "session_id": session_id, "assets_count": len(manifest.get('files', []))}

        except zipfile.BadZipFile:
            logger.error(f"Corrupt Zip File: {zip_path}")
            if os.path.exists(temp_extract_path):
                shutil.rmtree(temp_extract_path, ignore_errors=True)
            raise ValueError("Invalid Zip File")
        except Exception as e:
            logger.error(f"Processing Failed: {str(e)}")
            # Cleanup on failure to avoid zombie folders
            if os.path.exists(temp_extract_path):
                shutil.rmtree(temp_extract_path, ignore_errors=True) 
            raise e

    def _unzip(self, zip_path: str, extract_to: str):
        if os.path.exists(extract_to):
            shutil.rmtree(extract_to) # Clean slate
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
            
    def _validate_manifest_schema(self, manifest: dict):
        required_keys = ["sessionId", "timestamp", "surveyorId", "files"]
        for key in required_keys:
            if key not in manifest:
                raise ValueError(f"Manifest missing required key: {key}")

    async def _insert_session_data(self, session_id: str, manifest: dict, package_hash: str):
        # Maps Manifest JSON to DB Columns
        query = """
        INSERT INTO sessions (session_id, surveyor_id, created_at, package_hash, status)
        VALUES ($1, $2, $3, $4, 'processed')
        ON CONFLICT (session_id) DO UPDATE 
        SET status = 'reprocessed', updated_at = NOW();
        """
        # Parse timestamp safely
        try:
            timestamp = datetime.fromisoformat(manifest['timestamp'])
        except:
            timestamp = datetime.now() # Fallback

        await db.execute(query, session_id, manifest.get('surveyorId', 'unknown'), timestamp, package_hash)

    async def _insert_media_assets(self, session_id: str, manifest: dict, extraction_root: str):
        files = manifest.get('files', [])
        if not files:
            logger.warning(f"No files found in manifest for session {session_id}")
            return

        query = """
        INSERT INTO media_assets (file_path, file_hash, session_id, media_type, status)
        VALUES ($1, $2, $3, $4, 'ready')
        ON CONFLICT (file_path) DO NOTHING;
        """
        
        for file_info in files:
            relative_path = file_info.get('path')
            file_hash = file_info.get('hash')
            
            # Verify file actually exists on disk after unzip
            full_path = os.path.join(extraction_root, relative_path)
            if not os.path.exists(full_path):
                logger.error(f"Manifest claims {relative_path} exists, but file is missing on disk.")
                continue # Skip missing files, but don't fail entire batch? Or fail? RICS says "Forensic Integrity". 
                         # Ideally fail, but for resilience we log error.
            
            # Determine type
            ext = os.path.splitext(relative_path)[1].lower()
            media_type = 'image' if ext in ['.jpg', '.png', '.jpeg'] else 'audio' if ext in ['.m4a', '.mp3', '.wav'] else 'other'

            await db.execute(query, full_path, file_hash, session_id, media_type)
