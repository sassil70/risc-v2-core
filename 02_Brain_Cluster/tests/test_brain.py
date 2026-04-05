from fastapi.testclient import TestClient
from main import app
from database import db
import os
import hashlib
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock

# Mock DB Connection
@pytest.fixture(autouse=True)
def mock_db_connection(monkeypatch):
    monkeypatch.setattr(db, "connect", AsyncMock())
    monkeypatch.setattr(db, "disconnect", AsyncMock())

# Global client
client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "Brain Cluster Online", "version": "2.0"}

def test_handshake_time_skew_logic():
    now_utc = datetime.now(timezone.utc).isoformat()
    response = client.post("/api/v2/sync/handshake", json={
        "session_id": "test_valid",
        "package_hash": "dummy_hash",
        "package_size_bytes": 1024,
        "device_timestamp_utc": now_utc
    })
    assert response.status_code == 200
    
    old_time = "2020-01-01T00:00:00Z"
    response_bad = client.post("/api/v2/sync/handshake", json={
        "session_id": "test_invalid",
        "package_hash": "dummy_hash",
        "package_size_bytes": 1024,
        "device_timestamp_utc": old_time
    })
    assert response_bad.status_code == 409

def test_forensic_validator_logic():
    from forensic import ForensicValidator
    test_file = "test_data.bin"
    content = b"SECRET_EVIDENCE_PYTHON"
    with open(test_file, "wb") as f:
        f.write(content)
    
    expected_hex = hashlib.sha256(content).hexdigest()
    calculated = ForensicValidator.calculate_file_hash(test_file)
    assert calculated == expected_hex
    
    if os.path.exists(test_file):
        os.remove(test_file)
