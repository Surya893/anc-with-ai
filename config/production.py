"""Production configuration for ANC Platform"""

import os
from datetime import timedelta

class ProductionConfig:
    """Production environment configuration"""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DEBUG = False
    TESTING = False
    
    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://user:pass@localhost/anc_production')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = 20
    SQLALCHEMY_MAX_OVERFLOW = 40
    
    # Redis
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = REDIS_URL
    
    # ANC System
    SAMPLE_RATE = int(os.environ.get('SAMPLE_RATE', 44100))
    CHUNK_SIZE = int(os.environ.get('CHUNK_SIZE', 1024))
    FILTER_LENGTH = int(os.environ.get('FILTER_LENGTH', 512))
    ALGORITHM = os.environ.get('ALGORITHM', 'nlms')
    
    # Feature Extraction
    MFCC_COEFFICIENTS = int(os.environ.get('MFCC_COEFFICIENTS', 13))
    N_FFT = int(os.environ.get('N_FFT', 2048))
    HOP_LENGTH = int(os.environ.get('HOP_LENGTH', 512))
    
    # ML Models
    MODEL_PATH = os.environ.get('MODEL_PATH', '/models/noise_classifier_sklearn.joblib')
    SCALER_PATH = os.environ.get('SCALER_PATH', '/models/scaler_sklearn.joblib')
    EMERGENCY_MODEL_PATH = os.environ.get('EMERGENCY_MODEL_PATH', '/models/emergency_classifier.joblib')
    
    # API
    API_RATE_LIMIT = os.environ.get('API_RATE_LIMIT', '100/minute')
    API_TIMEOUT = int(os.environ.get('API_TIMEOUT', 30))
    
    # Security
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    JWT_ALGORITHM = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Monitoring
    PROMETHEUS_ENABLED = True
    METRICS_PORT = int(os.environ.get('METRICS_PORT', 9090))
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = 'json'
    LOG_FILE = '/var/log/anc/application.log'
    
    # Performance
    MAX_CONCURRENT_SESSIONS = int(os.environ.get('MAX_CONCURRENT_SESSIONS', 100))
    WORKER_TIMEOUT = int(os.environ.get('WORKER_TIMEOUT', 120))
    WORKER_PROCESSES = int(os.environ.get('WORKER_PROCESSES', 4))
    
    # Storage
    STORAGE_BACKEND = os.environ.get('STORAGE_BACKEND', 's3')
    S3_BUCKET = os.environ.get('S3_BUCKET', 'anc-platform-models')
    S3_REGION = os.environ.get('S3_REGION', 'us-east-1')
    
    # Feature Flags
    ENABLE_EMERGENCY_DETECTION = os.environ.get('ENABLE_EMERGENCY_DETECTION', 'true').lower() == 'true'
    ENABLE_ADVANCED_ALGORITHMS = os.environ.get('ENABLE_ADVANCED_ALGORITHMS', 'true').lower() == 'true'
    ENABLE_MULTI_CHANNEL = os.environ.get('ENABLE_MULTI_CHANNEL', 'false').lower() == 'true'


class StagingConfig(ProductionConfig):
    """Staging environment configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class DevelopmentConfig(ProductionConfig):
    """Development environment configuration"""
    DEBUG = True
    TESTING = True
    LOG_LEVEL = 'DEBUG'
    DATABASE_URL = 'sqlite:///anc_dev.db'
    REDIS_URL = 'redis://localhost:6379/1'


config = {
    'production': ProductionConfig,
    'staging': StagingConfig,
    'development': DevelopmentConfig,
    'default': DevelopmentConfig
}
