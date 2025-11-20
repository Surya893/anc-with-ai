-- ANC Platform Database Schema
-- PostgreSQL 14+

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    api_key VARCHAR(64) UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_api_key ON users(api_key);

-- Audio sessions table
CREATE TABLE IF NOT EXISTS audio_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_type VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',
    sample_rate INTEGER DEFAULT 44100,
    channels INTEGER DEFAULT 1,
    chunk_size INTEGER DEFAULT 1024,
    anc_enabled BOOLEAN DEFAULT FALSE,
    anc_algorithm VARCHAR(50) DEFAULT 'lms',
    anc_intensity FLOAT DEFAULT 1.0,
    filter_length INTEGER DEFAULT 512,
    total_chunks_processed INTEGER DEFAULT 0,
    average_latency_ms FLOAT DEFAULT 0.0,
    average_cancellation_db FLOAT DEFAULT 0.0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audio_sessions_user_id ON audio_sessions(user_id);
CREATE INDEX idx_audio_sessions_created_at ON audio_sessions(created_at);
CREATE INDEX idx_audio_sessions_status ON audio_sessions(status);

-- Noise detections table
CREATE TABLE IF NOT EXISTS noise_detections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES audio_sessions(id) ON DELETE CASCADE,
    noise_type VARCHAR(50),
    confidence FLOAT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    features JSONB
);

CREATE INDEX idx_noise_detections_session_id ON noise_detections(session_id);
CREATE INDEX idx_noise_detections_noise_type ON noise_detections(noise_type);
CREATE INDEX idx_noise_detections_timestamp ON noise_detections(timestamp);

-- Processing metrics table
CREATE TABLE IF NOT EXISTS processing_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES audio_sessions(id) ON DELETE CASCADE,
    latency_ms FLOAT,
    cancellation_db FLOAT,
    cpu_usage FLOAT,
    memory_usage FLOAT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_processing_metrics_session_id ON processing_metrics(session_id);
CREATE INDEX idx_processing_metrics_timestamp ON processing_metrics(timestamp);

-- API requests table
CREATE TABLE IF NOT EXISTS api_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    endpoint VARCHAR(255),
    method VARCHAR(10),
    status_code INTEGER,
    response_time_ms FLOAT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_api_requests_user_id ON api_requests(user_id);
CREATE INDEX idx_api_requests_timestamp ON api_requests(timestamp);
CREATE INDEX idx_api_requests_endpoint ON api_requests(endpoint);

-- Device calibrations table
CREATE TABLE IF NOT EXISTS device_calibrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(100) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    calibration_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_device_calibrations_device_id ON device_calibrations(device_id);
CREATE INDEX idx_device_calibrations_user_id ON device_calibrations(user_id);

-- Emergency events table
CREATE TABLE IF NOT EXISTS emergency_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES audio_sessions(id) ON DELETE CASCADE,
    emergency_type VARCHAR(50),
    confidence FLOAT,
    action_taken VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_emergency_events_session_id ON emergency_events(session_id);
CREATE INDEX idx_emergency_events_timestamp ON emergency_events(timestamp);
CREATE INDEX idx_emergency_events_type ON emergency_events(emergency_type);

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_device_calibrations_updated_at BEFORE UPDATE ON device_calibrations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
