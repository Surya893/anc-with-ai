"""
Database Models for ANC Platform
SQLAlchemy ORM models for all entities
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

db = SQLAlchemy()


def generate_uuid():
    """Generate UUID string"""
    return str(uuid.uuid4())


class User(db.Model):
    """User model for authentication"""
    __tablename__ = 'users'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    api_key = Column(String(64), unique=True, index=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    audio_sessions = relationship('AudioSession', back_populates='user', cascade='all, delete-orphan')
    api_requests = relationship('APIRequest', back_populates='user', cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)

    def generate_api_key(self):
        """Generate new API key"""
        self.api_key = generate_uuid().replace('-', '')
        return self.api_key

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class AudioSession(db.Model):
    """Audio processing session"""
    __tablename__ = 'audio_sessions'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False, index=True)
    session_type = Column(String(50))  # 'live', 'batch', 'test'
    status = Column(String(20), default='active')  # 'active', 'paused', 'completed', 'error'

    # Audio parameters
    sample_rate = Column(Integer, default=44100)
    channels = Column(Integer, default=1)
    chunk_size = Column(Integer, default=1024)

    # ANC parameters
    anc_enabled = Column(Boolean, default=False)
    anc_algorithm = Column(String(50), default='lms')  # 'lms', 'nlms', 'rls', 'freq_domain'
    anc_intensity = Column(Float, default=1.0)
    filter_length = Column(Integer, default=512)

    # Processing metrics
    total_chunks_processed = Column(Integer, default=0)
    average_latency_ms = Column(Float, default=0.0)
    average_cancellation_db = Column(Float, default=0.0)

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship('User', back_populates='audio_sessions')
    noise_detections = relationship('NoiseDetection', back_populates='session', cascade='all, delete-orphan')
    processing_metrics = relationship('ProcessingMetric', back_populates='session', cascade='all, delete-orphan')

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_type': self.session_type,
            'status': self.status,
            'anc_enabled': self.anc_enabled,
            'anc_algorithm': self.anc_algorithm,
            'anc_intensity': self.anc_intensity,
            'total_chunks_processed': self.total_chunks_processed,
            'average_latency_ms': self.average_latency_ms,
            'average_cancellation_db': self.average_cancellation_db,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'created_at': self.created_at.isoformat()
        }


class NoiseDetection(db.Model):
    """Detected noise events"""
    __tablename__ = 'noise_detections'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey('audio_sessions.id'), nullable=False, index=True)

    # Detection details
    noise_type = Column(String(50), index=True)  # 'traffic', 'office', 'construction', etc.
    confidence = Column(Float)
    is_emergency = Column(Boolean, default=False)

    # Audio characteristics
    intensity_db = Column(Float)
    frequency_peak_hz = Column(Float)
    duration_seconds = Column(Float)

    # Features (stored as JSON)
    audio_features = Column(JSON)

    # Timestamps
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship('AudioSession', back_populates='noise_detections')

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'noise_type': self.noise_type,
            'confidence': self.confidence,
            'is_emergency': self.is_emergency,
            'intensity_db': self.intensity_db,
            'frequency_peak_hz': self.frequency_peak_hz,
            'duration_seconds': self.duration_seconds,
            'detected_at': self.detected_at.isoformat(),
            'created_at': self.created_at.isoformat()
        }


class ProcessingMetric(db.Model):
    """Real-time processing metrics"""
    __tablename__ = 'processing_metrics'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey('audio_sessions.id'), nullable=False, index=True)

    # Performance metrics
    latency_ms = Column(Float)
    throughput_chunks_per_sec = Column(Float)
    cpu_usage_percent = Column(Float)
    memory_usage_mb = Column(Float)

    # ANC metrics
    cancellation_db = Column(Float)
    snr_improvement_db = Column(Float)
    residual_noise_db = Column(Float)

    # Timestamp
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    session = relationship('AudioSession', back_populates='processing_metrics')

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'latency_ms': self.latency_ms,
            'cancellation_db': self.cancellation_db,
            'snr_improvement_db': self.snr_improvement_db,
            'recorded_at': self.recorded_at.isoformat()
        }


class NoiseProfile(db.Model):
    """Stored noise profiles for training"""
    __tablename__ = 'noise_profiles'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(50), index=True)
    description = Column(Text)

    # Audio file reference
    audio_file_path = Column(String(255))
    duration_seconds = Column(Float)
    sample_rate = Column(Integer)

    # Characteristics
    frequency_range_low_hz = Column(Float)
    frequency_range_high_hz = Column(Float)
    typical_intensity_db = Column(Float)

    # Features for classification
    feature_vector = Column(JSON)

    # Usage statistics
    detection_count = Column(Integer, default=0)
    last_detected_at = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'duration_seconds': self.duration_seconds,
            'frequency_range': {
                'low': self.frequency_range_low_hz,
                'high': self.frequency_range_high_hz
            },
            'typical_intensity_db': self.typical_intensity_db,
            'detection_count': self.detection_count,
            'created_at': self.created_at.isoformat()
        }


class APIRequest(db.Model):
    """API request logging for analytics"""
    __tablename__ = 'api_requests'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey('users.id'), index=True)

    # Request details
    method = Column(String(10))
    endpoint = Column(String(255), index=True)
    status_code = Column(Integer, index=True)
    response_time_ms = Column(Float)

    # Request metadata
    ip_address = Column(String(45))
    user_agent = Column(String(255))

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship('User', back_populates='api_requests')

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'method': self.method,
            'endpoint': self.endpoint,
            'status_code': self.status_code,
            'response_time_ms': self.response_time_ms,
            'created_at': self.created_at.isoformat()
        }


class SystemMetric(db.Model):
    """System-wide metrics"""
    __tablename__ = 'system_metrics'

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Metric details
    metric_name = Column(String(100), index=True)
    metric_value = Column(Float)
    metric_unit = Column(String(20))

    # Metadata
    tags = Column(JSON)  # Additional context as key-value pairs

    # Timestamp
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'metric_unit': self.metric_unit,
            'tags': self.tags,
            'recorded_at': self.recorded_at.isoformat()
        }
