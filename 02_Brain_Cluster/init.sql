-- Enable Extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Projects Table (Top Level)
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference_number VARCHAR(50) UNIQUE NOT NULL,
    client_name VARCHAR(100),
    site_metadata JSONB DEFAULT '{}', -- ZenRows Data
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Dashboard columns
    status VARCHAR(20) DEFAULT 'active',
    approval_status VARCHAR(20) DEFAULT 'pending',
    address TEXT,
    total_photos INTEGER DEFAULT 0,
    total_elements INTEGER DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    urgent_count INTEGER DEFAULT 0,
    attention_count INTEGER DEFAULT 0,
    surveyor_name VARCHAR(200),
    surveyor_id UUID,
    latest_version VARCHAR(100),
    rics_number VARCHAR(100),
    inspection_date DATE,
    report_date DATE,
    property_type VARCHAR(100)
);

-- 2. Sessions Table (The Digital Parcel)
CREATE TABLE sessions (
    id VARCHAR(100) PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    surveyor_id UUID, -- Link to users table if exists
    title VARCHAR(255),
    status VARCHAR(50),
    data JSONB DEFAULT '{}', -- Full session JSON storage
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,
    is_locked BOOLEAN DEFAULT FALSE
);

-- 3. Media Assets (The Evidence)
CREATE TABLE media_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100) REFERENCES sessions(id),
    
    file_path VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) NOT NULL, -- SHA-256
    asset_type VARCHAR(20) NOT NULL, -- 'image', 'audio'
    
    captured_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    room_tag VARCHAR(100),
    element_tag VARCHAR(100),
    
    -- AI Semantic Search Vector (Gemini 3.0 Embedding - 768 dim)
    embedding vector(768)
);

-- 4. Immutable Audit Log (Forensic Blackbox)
CREATE TABLE immutable_audit_log (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_id TEXT NOT NULL,
    operation VARCHAR(10) NOT NULL, -- INSERT, UPDATE, DELETE
    old_value JSONB,
    new_value JSONB,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    changed_by VARCHAR(50)
);

-- Trigger Function for Audit
CREATE OR REPLACE FUNCTION log_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'DELETE') THEN
        INSERT INTO immutable_audit_log (table_name, record_id, operation, old_value, changed_by)
        VALUES (TG_TABLE_NAME, OLD.id, 'DELETE', row_to_json(OLD), current_user);
        RETURN OLD;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO immutable_audit_log (table_name, record_id, operation, old_value, new_value, changed_by)
        VALUES (TG_TABLE_NAME, NEW.id, 'UPDATE', row_to_json(OLD), row_to_json(NEW), current_user);
        RETURN NEW;
    ELSIF (TG_OP = 'INSERT') THEN
        INSERT INTO immutable_audit_log (table_name, record_id, operation, new_value, changed_by)
        VALUES (TG_TABLE_NAME, NEW.id, 'INSERT', row_to_json(NEW), current_user);
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Apply Triggers
CREATE TRIGGER audit_media_assets
AFTER INSERT OR UPDATE OR DELETE ON media_assets
FOR EACH ROW EXECUTE FUNCTION log_changes();

CREATE TRIGGER audit_sessions
AFTER INSERT OR UPDATE OR DELETE ON sessions
FOR EACH ROW EXECUTE FUNCTION log_changes();

-- 5. Users Table (Authentication)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200),
    role VARCHAR(50) DEFAULT 'surveyor',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Access Events Table (Login Audit Trail)
CREATE TABLE IF NOT EXISTS access_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Seed Default Users (password: risc2026, bcrypt hashed)
INSERT INTO users (username, password_hash, full_name, role)
VALUES 
    ('admin', '$2b$12$jcEzfOyhfrCNyEAwx/8KPOhJ2vgDh7QZ5xtPdVswAYd5WHNFkaEMu', 'System Administrator', 'admin'),
    ('surveyor', '$2b$12$cH/oqMHimal7SWnjVeWIvucCxA8m89vpPSjAY/2Chao.POHeTs386', 'RICS Surveyor', 'surveyor')
ON CONFLICT (username) DO NOTHING;
