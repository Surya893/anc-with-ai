# Database Layer

## Overview

This layer handles all data persistence for the ANC Platform using PostgreSQL.

## Architecture

```
database/
├── models.py           # SQLAlchemy ORM models
├── schema.sql          # Raw SQL schema
├── migrations/         # Alembic migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── seeds/              # Seed data
│   ├── users.sql
│   └── test_data.sql
├── schemas/            # JSON schemas
│   └── api_schemas.json
└── README.md
```

## Database Schema

### Tables

1. **users** - User accounts and authentication
2. **audio_sessions** - Audio processing sessions
3. **noise_detections** - ML classification results
4. **processing_metrics** - Performance metrics
5. **api_requests** - API request logs
6. **device_calibrations** - Hardware calibration data
7. **emergency_events** - Safety-critical emergency detections

## Entity Relationship

```
users (1) ──── (M) audio_sessions
              │
              ├──── (M) noise_detections
              └──── (M) processing_metrics

users (1) ──── (M) api_requests
users (1) ──── (M) device_calibrations
audio_sessions (1) ──── (M) emergency_events
```

## Models

### User
- id (UUID, PK)
- username (String, unique)
- email (String, unique)
- password_hash (String)
- api_key (String, unique)
- is_active (Boolean)
- is_admin (Boolean)
- created_at (DateTime)
- updated_at (DateTime)

### AudioSession
- id (UUID, PK)
- user_id (UUID, FK → users)
- session_type (String: 'live', 'batch', 'test')
- status (String: 'active', 'paused', 'completed', 'error')
- sample_rate (Integer)
- channels (Integer)
- chunk_size (Integer)
- anc_enabled (Boolean)
- anc_algorithm (String)
- anc_intensity (Float)
- total_chunks_processed (Integer)
- average_latency_ms (Float)
- average_cancellation_db (Float)
- started_at (DateTime)
- ended_at (DateTime)
- created_at (DateTime)

### NoiseDetection
- id (UUID, PK)
- session_id (UUID, FK → audio_sessions)
- noise_type (String)
- confidence (Float)
- timestamp (DateTime)
- features (JSON)

### ProcessingMetric
- id (UUID, PK)
- session_id (UUID, FK → audio_sessions)
- latency_ms (Float)
- cancellation_db (Float)
- cpu_usage (Float)
- memory_usage (Float)
- timestamp (DateTime)

### EmergencyEvent
- id (UUID, PK)
- session_id (UUID, FK → audio_sessions)
- emergency_type (String)
- confidence (Float)
- action_taken (String)
- timestamp (DateTime)

## Setup

### Initialize Database

```bash
# Create PostgreSQL database
createdb anc_system

# Or with psql
psql -U postgres -c "CREATE DATABASE anc_system;"

# Create user
psql -U postgres -c "CREATE USER anc_user WITH PASSWORD 'anc_password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE anc_system TO anc_user;"
```

### Run Migrations

```bash
# Initialize Alembic
alembic init migrations

# Create migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head
```

### Seed Data

```bash
# Load seed data
psql -U anc_user -d anc_system -f database/seeds/users.sql
```

## Queries

### Common Queries

```sql
-- Get user's recent sessions
SELECT * FROM audio_sessions
WHERE user_id = 'user-uuid'
ORDER BY created_at DESC
LIMIT 10;

-- Get session metrics
SELECT
    s.id,
    s.anc_algorithm,
    AVG(m.latency_ms) as avg_latency,
    AVG(m.cancellation_db) as avg_cancellation
FROM audio_sessions s
JOIN processing_metrics m ON s.id = m.session_id
WHERE s.id = 'session-uuid'
GROUP BY s.id, s.anc_algorithm;

-- Get noise type distribution
SELECT
    noise_type,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence
FROM noise_detections
GROUP BY noise_type
ORDER BY count DESC;

-- Get emergency events
SELECT * FROM emergency_events
WHERE timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
```

## Backup & Restore

### Backup

```bash
# Full backup
pg_dump -U anc_user anc_system > backup.sql

# Schema only
pg_dump -U anc_user --schema-only anc_system > schema.sql

# Data only
pg_dump -U anc_user --data-only anc_system > data.sql
```

### Restore

```bash
# Restore from backup
psql -U anc_user anc_system < backup.sql
```

## Performance

### Indexes

```sql
-- User indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_api_key ON users(api_key);

-- Session indexes
CREATE INDEX idx_audio_sessions_user_id ON audio_sessions(user_id);
CREATE INDEX idx_audio_sessions_created_at ON audio_sessions(created_at);

-- Metric indexes
CREATE INDEX idx_processing_metrics_session_id ON processing_metrics(session_id);
CREATE INDEX idx_processing_metrics_timestamp ON processing_metrics(timestamp);

-- Noise detection indexes
CREATE INDEX idx_noise_detections_session_id ON noise_detections(session_id);
CREATE INDEX idx_noise_detections_noise_type ON noise_detections(noise_type);
```

### Partitioning

For large datasets, consider partitioning:

```sql
-- Partition processing_metrics by timestamp
CREATE TABLE processing_metrics (
    -- columns
) PARTITION BY RANGE (timestamp);

CREATE TABLE processing_metrics_2024_01 PARTITION OF processing_metrics
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

## Monitoring

```sql
-- Database size
SELECT pg_size_pretty(pg_database_size('anc_system'));

-- Table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Active connections
SELECT * FROM pg_stat_activity WHERE datname = 'anc_system';
```

## Security

- All passwords are hashed using bcrypt
- API keys are randomly generated UUIDs
- Database connections use SSL in production
- Least privilege access control
- Regular backups to S3
