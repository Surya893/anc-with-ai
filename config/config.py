"""
Configuration Management for ANC Platform
Supports multiple environments: development, staging, production
"""

import os
from datetime import timedelta
from pathlib import Path


class Config:
    """Base configuration"""
    # Application
    APP_NAME = "ANC Platform"
    APP_VERSION = "1.0.0"
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Paths
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / 'data'
    MODELS_DIR = BASE_DIR / 'models'
    UPLOAD_DIR = BASE_DIR / 'uploads'
    LOG_DIR = BASE_DIR / 'logs'

    # Create directories
    for directory in [DATA_DIR, MODELS_DIR, UPLOAD_DIR, LOG_DIR]:
        directory.mkdir(exist_ok=True)

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{BASE_DIR}/anc_platform.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # Redis
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    REDIS_CACHE_TTL = 300  # 5 minutes

    # Celery
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TIMEZONE = 'UTC'
    CELERY_ENABLE_UTC = True

    # Flask
    JSON_SORT_KEYS = False
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size

    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')

    # Authentication
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    API_KEY_HEADER = 'X-API-Key'

    # Rate Limiting
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_DEFAULT = '100 per minute'
    RATE_LIMIT_STORAGE_URL = REDIS_URL

    # Audio Processing
    AUDIO_SAMPLE_RATE = 44100
    AUDIO_CHUNK_SIZE = 1024
    AUDIO_CHANNELS = 1
    AUDIO_FORMAT = 'float32'

    # ANC Algorithms
    ANC_FILTER_LENGTH = 512
    ANC_STEP_SIZE = 0.01
    ANC_FORGETTING_FACTOR = 0.99
    ANC_FFT_SIZE = 1024

    # Machine Learning
    ML_MODEL_PATH = MODELS_DIR / 'noise_classifier_sklearn.joblib'
    ML_SCALER_PATH = MODELS_DIR / 'scaler_sklearn.joblib'
    ML_EMERGENCY_MODEL_PATH = MODELS_DIR / 'emergency_classifier.joblib'
    ML_BATCH_SIZE = 32
    ML_CONFIDENCE_THRESHOLD = 0.7

    # WebSocket
    WEBSOCKET_PING_INTERVAL = 25
    WEBSOCKET_PING_TIMEOUT = 5
    WEBSOCKET_MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10MB

    # Monitoring
    PROMETHEUS_ENABLED = True
    METRICS_PORT = 9090

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = LOG_DIR / 'anc_platform.log'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True
    LOG_LEVEL = 'DEBUG'


class StagingConfig(Config):
    """Staging configuration"""
    DEBUG = False
    TESTING = False
    LOG_LEVEL = 'INFO'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    LOG_LEVEL = 'WARNING'

    # Production security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Rate limiting - more strict
    RATE_LIMIT_DEFAULT = '60 per minute'


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'staging': StagingConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env=None):
    """Get configuration based on environment"""
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
