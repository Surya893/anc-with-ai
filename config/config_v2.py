"""
Secure Configuration Management v2.0

This module provides secure configuration management with:
- Environment variable validation
- Secrets Manager integration
- No hardcoded secrets
- Type checking
- CORS restrictions
- Rate limiting
- Request size limits

Version: 2.0.0
Date: 2025-11-19
"""

import os
import logging
from typing import Optional, List
from dataclasses import dataclass
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid"""
    pass


@dataclass
class SecurityConfig:
    """Security configuration"""
    # CORS - FIXED: No wildcard, use specific origins
    allowed_origins: List[str]
    allowed_methods: List[str] = None
    allowed_headers: List[str] = None
    max_age: int = 3600

    # Rate limiting - FIXED: Added request size limits
    max_requests_per_minute: int = 60
    max_requests_per_hour: int = 1000
    max_request_size_bytes: int = 1048576  # 1 MB
    max_audio_size_bytes: int = 262144  # 256 KB

    # JWT
    jwt_algorithm: str = 'HS256'
    jwt_expiration_seconds: int = 3600

    # API keys
    require_api_key: bool = True
    api_key_header: str = 'X-API-Key'

    def __post_init__(self):
        if self.allowed_methods is None:
            self.allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
        if self.allowed_headers is None:
            self.allowed_headers = [
                'Content-Type',
                'Authorization',
                'X-API-Key',
                'X-Request-ID'
            ]

        # FIXED: Validate no wildcard in CORS
        if '*' in self.allowed_origins:
            raise ConfigurationError("Wildcard CORS origin not allowed in production")


@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str
    port: int
    database: str
    username: str
    password_secret_arn: str  # FIXED: Store password in Secrets Manager
    ssl_mode: str = 'require'
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600


@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str
    port: int = 6379
    auth_token_secret_arn: str  # FIXED: Store auth token in Secrets Manager
    db: int = 0
    ssl: bool = True
    socket_timeout: int = 5
    socket_connect_timeout: int = 2
    retry_on_timeout: bool = True
    max_connections: int = 50


@dataclass
class AWSConfig:
    """AWS service configuration"""
    region: str
    s3_bucket_raw_audio: str
    s3_bucket_processed_audio: str
    s3_bucket_ml_models: str
    dynamodb_connections_table: str
    dynamodb_sessions_table: str
    sqs_processing_queue_url: str
    sqs_output_queue_url: str
    sagemaker_endpoint_classifier: str
    sagemaker_endpoint_emergency: str

    # FIXED: Proper timeout configuration
    boto3_connect_timeout: int = 10
    boto3_read_timeout: int = 30


@dataclass
class ANCConfig:
    """ANC processing configuration"""
    algorithm: str = 'hybrid_nlms_rls'
    filter_length: int = 512
    sample_rate: int = 48000
    num_channels: int = 1

    # Algorithm parameters
    nlms_step_size: float = 0.5
    nlms_epsilon: float = 1e-8  # FIXED: Added epsilon
    rls_forgetting_factor: float = 0.99
    rls_delta: float = 1.0

    # Performance
    max_latency_ms: float = 10.0
    enable_spatial_audio: bool = True
    enable_adaptive_learning: bool = True


class SecureConfigManager:
    """
    Secure configuration manager with Secrets Manager integration

    SECURITY IMPROVEMENTS:
    - No hardcoded secrets
    - Secrets Manager integration
    - Environment variable validation
    - Type checking
    - Fail-safe defaults
    """

    def __init__(self, environment: str = 'prod'):
        self.environment = environment
        self.secrets_client = boto3.client('secretsmanager')

        # Validate required environment variables
        self._validate_environment()

        # Load configuration
        self.security = self._load_security_config()
        self.database = self._load_database_config()
        self.redis = self._load_redis_config()
        self.aws = self._load_aws_config()
        self.anc = self._load_anc_config()

        logger.info(f"Loaded secure configuration for environment: {environment}")

    def _validate_environment(self):
        """Validate required environment variables are set"""
        required_vars = [
            'AWS_REGION',
            'ENVIRONMENT',
            'DB_HOST',
            'REDIS_HOST',
            'S3_BUCKET_RAW_AUDIO',
            'S3_BUCKET_PROCESSED_AUDIO',
            'DYNAMODB_CONNECTIONS_TABLE',
            'SQS_PROCESSING_QUEUE_URL'
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

    def _get_secret(self, secret_arn: str) -> str:
        """
        Retrieve secret from AWS Secrets Manager

        Args:
            secret_arn: ARN of the secret

        Returns:
            Secret value

        Raises:
            ConfigurationError: If secret cannot be retrieved
        """
        try:
            response = self.secrets_client.get_secret_value(SecretId=secret_arn)
            return response['SecretString']
        except ClientError as e:
            logger.error(f"Failed to retrieve secret {secret_arn}: {e}")
            raise ConfigurationError(f"Failed to retrieve secret: {e}")

    def _load_security_config(self) -> SecurityConfig:
        """Load security configuration"""
        # FIXED: Use specific origins from environment variable
        allowed_origins_str = os.getenv('ALLOWED_CORS_ORIGINS', '')

        if not allowed_origins_str:
            raise ConfigurationError("ALLOWED_CORS_ORIGINS environment variable not set")

        allowed_origins = [origin.strip() for origin in allowed_origins_str.split(',')]

        return SecurityConfig(
            allowed_origins=allowed_origins,
            max_requests_per_minute=int(os.getenv('MAX_REQUESTS_PER_MINUTE', '60')),
            max_requests_per_hour=int(os.getenv('MAX_REQUESTS_PER_HOUR', '1000')),
            max_request_size_bytes=int(os.getenv('MAX_REQUEST_SIZE_BYTES', '1048576')),
            max_audio_size_bytes=int(os.getenv('MAX_AUDIO_SIZE_BYTES', '262144')),
            jwt_expiration_seconds=int(os.getenv('JWT_EXPIRATION_SECONDS', '3600')),
            require_api_key=os.getenv('REQUIRE_API_KEY', 'true').lower() == 'true'
        )

    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration"""
        password_secret_arn = os.getenv('DB_PASSWORD_SECRET_ARN')

        if not password_secret_arn:
            raise ConfigurationError("DB_PASSWORD_SECRET_ARN not set")

        return DatabaseConfig(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT', '5432')),
            database=os.getenv('DB_NAME', 'ancdb'),
            username=os.getenv('DB_USERNAME', 'ancadmin'),
            password_secret_arn=password_secret_arn,
            ssl_mode=os.getenv('DB_SSL_MODE', 'require'),
            pool_size=int(os.getenv('DB_POOL_SIZE', '10')),
            max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '20'))
        )

    def _load_redis_config(self) -> RedisConfig:
        """Load Redis configuration"""
        auth_token_secret_arn = os.getenv('REDIS_AUTH_TOKEN_SECRET_ARN')

        if not auth_token_secret_arn:
            raise ConfigurationError("REDIS_AUTH_TOKEN_SECRET_ARN not set")

        return RedisConfig(
            host=os.getenv('REDIS_HOST'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            auth_token_secret_arn=auth_token_secret_arn,
            db=int(os.getenv('REDIS_DB', '0')),
            ssl=os.getenv('REDIS_SSL', 'true').lower() == 'true',
            max_connections=int(os.getenv('REDIS_MAX_CONNECTIONS', '50'))
        )

    def _load_aws_config(self) -> AWSConfig:
        """Load AWS configuration"""
        return AWSConfig(
            region=os.getenv('AWS_REGION'),
            s3_bucket_raw_audio=os.getenv('S3_BUCKET_RAW_AUDIO'),
            s3_bucket_processed_audio=os.getenv('S3_BUCKET_PROCESSED_AUDIO'),
            s3_bucket_ml_models=os.getenv('S3_BUCKET_ML_MODELS'),
            dynamodb_connections_table=os.getenv('DYNAMODB_CONNECTIONS_TABLE'),
            dynamodb_sessions_table=os.getenv('DYNAMODB_SESSIONS_TABLE'),
            sqs_processing_queue_url=os.getenv('SQS_PROCESSING_QUEUE_URL'),
            sqs_output_queue_url=os.getenv('SQS_OUTPUT_QUEUE_URL'),
            sagemaker_endpoint_classifier=os.getenv('SAGEMAKER_ENDPOINT_CLASSIFIER'),
            sagemaker_endpoint_emergency=os.getenv('SAGEMAKER_ENDPOINT_EMERGENCY'),
            boto3_connect_timeout=int(os.getenv('BOTO3_CONNECT_TIMEOUT', '10')),
            boto3_read_timeout=int(os.getenv('BOTO3_READ_TIMEOUT', '30'))
        )

    def _load_anc_config(self) -> ANCConfig:
        """Load ANC processing configuration"""
        return ANCConfig(
            algorithm=os.getenv('ANC_ALGORITHM', 'hybrid_nlms_rls'),
            filter_length=int(os.getenv('ANC_FILTER_LENGTH', '512')),
            sample_rate=int(os.getenv('ANC_SAMPLE_RATE', '48000')),
            num_channels=int(os.getenv('ANC_NUM_CHANNELS', '1')),
            nlms_step_size=float(os.getenv('ANC_NLMS_STEP_SIZE', '0.5')),
            nlms_epsilon=float(os.getenv('ANC_NLMS_EPSILON', '1e-8')),
            rls_forgetting_factor=float(os.getenv('ANC_RLS_FORGETTING_FACTOR', '0.99')),
            max_latency_ms=float(os.getenv('ANC_MAX_LATENCY_MS', '10.0')),
            enable_spatial_audio=os.getenv('ANC_ENABLE_SPATIAL_AUDIO', 'true').lower() == 'true',
            enable_adaptive_learning=os.getenv('ANC_ENABLE_ADAPTIVE_LEARNING', 'true').lower() == 'true'
        )

    def get_database_password(self) -> str:
        """Get database password from Secrets Manager"""
        return self._get_secret(self.database.password_secret_arn)

    def get_redis_auth_token(self) -> str:
        """Get Redis auth token from Secrets Manager"""
        return self._get_secret(self.redis.auth_token_secret_arn)

    def get_jwt_secret(self) -> str:
        """Get JWT secret from Secrets Manager"""
        jwt_secret_arn = os.getenv('JWT_SECRET_ARN')
        if not jwt_secret_arn:
            raise ConfigurationError("JWT_SECRET_ARN not set")
        return self._get_secret(jwt_secret_arn)


# Global configuration instance
_config: Optional[SecureConfigManager] = None


def get_config() -> SecureConfigManager:
    """Get global configuration instance"""
    global _config

    if _config is None:
        environment = os.getenv('ENVIRONMENT', 'prod')
        _config = SecureConfigManager(environment)

    return _config


# Environment-specific configurations
def get_env_config_template(environment: str) -> str:
    """
    Get environment configuration template

    Returns a template .env file for the specified environment
    """
    if environment == 'prod':
        return """
# Production Environment Configuration

# AWS
AWS_REGION=us-east-1
ENVIRONMENT=prod

# Database (PostgreSQL)
DB_HOST=anc-db-prod.xxxxxxxx.us-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=ancdb
DB_USERNAME=ancadmin
DB_PASSWORD_SECRET_ARN=arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:anc/db/password-prod
DB_SSL_MODE=require
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# Redis (ElastiCache)
REDIS_HOST=anc-redis-prod.xxxxxx.0001.use1.cache.amazonaws.com
REDIS_PORT=6379
REDIS_AUTH_TOKEN_SECRET_ARN=arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:anc/redis/auth-token-prod
REDIS_SSL=true
REDIS_DB=0
REDIS_MAX_CONNECTIONS=100

# S3 Buckets
S3_BUCKET_RAW_AUDIO=anc-ai-raw-audio-prod
S3_BUCKET_PROCESSED_AUDIO=anc-ai-processed-audio-prod
S3_BUCKET_ML_MODELS=anc-ai-ml-models-prod

# DynamoDB Tables
DYNAMODB_CONNECTIONS_TABLE=anc-ai-connections-prod
DYNAMODB_SESSIONS_TABLE=anc-ai-sessions-prod

# SQS Queues
SQS_PROCESSING_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/ACCOUNT/anc-ai-audio-processing-prod
SQS_OUTPUT_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/ACCOUNT/anc-ai-audio-output-prod

# SageMaker Endpoints
SAGEMAKER_ENDPOINT_CLASSIFIER=anc-ai-noise-classifier-prod
SAGEMAKER_ENDPOINT_EMERGENCY=anc-ai-emergency-detector-prod

# Security
ALLOWED_CORS_ORIGINS=https://anc.example.com,https://app.anc.example.com
MAX_REQUESTS_PER_MINUTE=120
MAX_REQUESTS_PER_HOUR=5000
MAX_REQUEST_SIZE_BYTES=1048576
MAX_AUDIO_SIZE_BYTES=262144
JWT_SECRET_ARN=arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:anc/jwt/secret-prod
JWT_EXPIRATION_SECONDS=3600
REQUIRE_API_KEY=true

# ANC Configuration
ANC_ALGORITHM=hybrid_nlms_rls
ANC_FILTER_LENGTH=512
ANC_SAMPLE_RATE=48000
ANC_NUM_CHANNELS=2
ANC_NLMS_STEP_SIZE=0.5
ANC_NLMS_EPSILON=1e-8
ANC_RLS_FORGETTING_FACTOR=0.99
ANC_MAX_LATENCY_MS=10.0
ANC_ENABLE_SPATIAL_AUDIO=true
ANC_ENABLE_ADAPTIVE_LEARNING=true

# Timeouts
BOTO3_CONNECT_TIMEOUT=10
BOTO3_READ_TIMEOUT=30

# Logging
LOG_LEVEL=INFO
"""
    elif environment == 'dev':
        return """
# Development Environment Configuration

# AWS
AWS_REGION=us-east-1
ENVIRONMENT=dev

# Database (Local PostgreSQL or RDS)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ancdb_dev
DB_USERNAME=ancdev
DB_PASSWORD_SECRET_ARN=arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:anc/db/password-dev
DB_SSL_MODE=prefer
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# Redis (Local or ElastiCache)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_AUTH_TOKEN_SECRET_ARN=arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:anc/redis/auth-token-dev
REDIS_SSL=false
REDIS_DB=0
REDIS_MAX_CONNECTIONS=20

# S3 Buckets
S3_BUCKET_RAW_AUDIO=anc-ai-raw-audio-dev
S3_BUCKET_PROCESSED_AUDIO=anc-ai-processed-audio-dev
S3_BUCKET_ML_MODELS=anc-ai-ml-models-dev

# DynamoDB Tables
DYNAMODB_CONNECTIONS_TABLE=anc-ai-connections-dev
DYNAMODB_SESSIONS_TABLE=anc-ai-sessions-dev

# SQS Queues
SQS_PROCESSING_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/ACCOUNT/anc-ai-audio-processing-dev
SQS_OUTPUT_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/ACCOUNT/anc-ai-audio-output-dev

# SageMaker Endpoints
SAGEMAKER_ENDPOINT_CLASSIFIER=anc-ai-noise-classifier-dev
SAGEMAKER_ENDPOINT_EMERGENCY=anc-ai-emergency-detector-dev

# Security (More relaxed for dev)
ALLOWED_CORS_ORIGINS=http://localhost:3000,http://localhost:8080
MAX_REQUESTS_PER_MINUTE=1000
MAX_REQUESTS_PER_HOUR=50000
MAX_REQUEST_SIZE_BYTES=2097152
MAX_AUDIO_SIZE_BYTES=524288
JWT_SECRET_ARN=arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:anc/jwt/secret-dev
JWT_EXPIRATION_SECONDS=7200
REQUIRE_API_KEY=false

# ANC Configuration
ANC_ALGORITHM=hybrid_nlms_rls
ANC_FILTER_LENGTH=256
ANC_SAMPLE_RATE=48000
ANC_NUM_CHANNELS=1
ANC_NLMS_STEP_SIZE=0.6
ANC_NLMS_EPSILON=1e-8
ANC_RLS_FORGETTING_FACTOR=0.99
ANC_MAX_LATENCY_MS=20.0
ANC_ENABLE_SPATIAL_AUDIO=false
ANC_ENABLE_ADAPTIVE_LEARNING=true

# Timeouts
BOTO3_CONNECT_TIMEOUT=10
BOTO3_READ_TIMEOUT=30

# Logging
LOG_LEVEL=DEBUG
"""
    else:
        raise ValueError(f"Unknown environment: {environment}")


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Get configuration
    try:
        config = get_config()
        print(f"Loaded configuration for environment: {config.environment}")
        print(f"Security - Allowed origins: {config.security.allowed_origins}")
        print(f"Security - Max request size: {config.security.max_request_size_bytes} bytes")
        print(f"ANC - Algorithm: {config.anc.algorithm}")
        print(f"ANC - Filter length: {config.anc.filter_length}")
    except ConfigurationError as e:
        print(f"Configuration error: {e}")
