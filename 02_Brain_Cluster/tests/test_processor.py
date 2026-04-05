import unittest
import os
import shutil
import json
import zipfile
import asyncio
from unittest.mock import MagicMock, AsyncMock

# Mock DB before importing processor
import sys
sys.modules['database'] = MagicMock()
sys.modules['database'].db = AsyncMock()

from processor import PackageProcessor

class TestPackageProcessor(unittest.TestCase):
    
    TEST_DIR = "test_storage"
    ZIP_PATH = "test_package.zip"
    SESSION_ID = "test_session_123"

    def setUp(self):
        # Create Dummy Zip
        os.makedirs(self.TEST_DIR, exist_ok=True)
        
        self.manifest = {
            "sessionId": self.SESSION_ID,
            "timestamp": "2026-01-06T12:00:00Z",
            "surveyorId": "SURVEYOR_01",
            "files": [
                {"path": "image1.jpg", "hash": "dummyhash123"}
            ]
        }
        
        # Write Manifest and Dummy Image
        with open("session_manifest.json", "w") as f:
            json.dump(self.manifest, f)
        with open("image1.jpg", "w") as f:
            f.write("dummy image content")
            
        # Zip it
        with zipfile.ZipFile(self.ZIP_PATH, 'w') as zf:
            zf.write("session_manifest.json")
            zf.write("image1.jpg")
            
        # Clean temp files
        os.remove("session_manifest.json")
        os.remove("image1.jpg")

    def tearDown(self):
        if os.path.exists(self.ZIP_PATH):
            os.remove(self.ZIP_PATH)
        if os.path.exists(self.TEST_DIR):
            shutil.rmtree(self.TEST_DIR)

    def test_process_success(self):
        """Scenario A: Successful Processing"""
        processor = PackageProcessor(storage_root=self.TEST_DIR)
        
        # Async run
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(processor.process(self.ZIP_PATH, "pkg_hash_123"))
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['session_id'], self.SESSION_ID)
        
        # Check if files extracted
        extracted_manifest = os.path.join(self.TEST_DIR, self.SESSION_ID, "session_manifest.json")
        self.assertTrue(os.path.exists(extracted_manifest))

    def test_missing_manifest(self):
        """Scenario C: Zip valid but missing manifest"""
        # Create zip without manifest
        bad_zip = "bad.zip"
        with zipfile.ZipFile(bad_zip, 'w') as zf:
            zf.writestr("random.txt", "content")
            
        processor = PackageProcessor(storage_root=self.TEST_DIR)
        loop = asyncio.new_event_loop()
        
        with self.assertRaises(ValueError) as cm:
            loop.run_until_complete(processor.process(bad_zip, "hash"))
        
        self.assertIn("session_manifest.json missing", str(cm.exception))
        os.remove(bad_zip)

    def test_corrupt_zip(self):
        """Scenario B: Not a zip file"""
        with open("fake.zip", "w") as f:
            f.write("This is not a zip")
            
        processor = PackageProcessor(storage_root=self.TEST_DIR)
        loop = asyncio.new_event_loop()
        
        with self.assertRaises(ValueError) as cm:
             loop.run_until_complete(processor.process("fake.zip", "hash"))
             
        self.assertIn("Invalid Zip File", str(cm.exception))
        os.remove("fake.zip")

if __name__ == '__main__':
    unittest.main()
