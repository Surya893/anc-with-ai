# Configuration Directory

All configuration files for the ANC Platform.

## Directory Structure

```
config/
├── config.py           # Main configuration module
├── nginx/              # Nginx configuration
│   └── nginx.conf     # Nginx reverse proxy config
└── README.md          # This file
```

---

## Python Configuration

### `config.py`

**Purpose:** Centralized configuration management for Python application.

**Usage:**
```python
from config.config import get_config

config = get_config()  # Automatically detects environment
print(config.DATABASE_URL)
print(config.SECRET_KEY)
```

**Environments:**
- `development` - Local development
- `testing` - Test environment
- `production` - Production deployment

**Configuration from Environment:**
```python
import os
os.environ['FLASK_ENV'] = 'production'

config = get_config()  # Returns ProductionConfig
```

### Configuration Classes

**BaseConfig** - Shared settings
- Debug mode
- Testing mode
- Secret key
- Database URLs
- Redis configuration
- Celery configuration
- AWS settings

**DevelopmentConfig** - Development settings
- Debug enabled
- Local database
- Relaxed CORS
- Verbose logging

**ProductionConfig** - Production settings
- Debug disabled
- Production database
- Strict CORS
- Error logging only
- Security headers enabled

**TestingConfig** - Test settings
- Testing enabled
- In-memory database
- Mocked external services

---

## Nginx Configuration

### `nginx/nginx.conf`

**Purpose:** Reverse proxy configuration for production deployment.

**Features:**
- Load balancing across Gunicorn workers
- WebSocket proxy support
- Static file serving
- Gzip compression
- SSL/TLS termination
- Security headers
- Rate limiting

**Usage:**

**Development (local testing):**
```bash
nginx -c config/nginx/nginx.conf -t  # Test configuration
nginx -c config/nginx/nginx.conf      # Start nginx
```

**Production (Docker):**
```yaml
# docker-compose.yml
services:
  nginx:
    image: nginx:latest
    volumes:
      - ./config/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
      - "443:443"
```

**Production (systemd):**
```bash
# Copy to nginx config directory
sudo cp config/nginx/nginx.conf /etc/nginx/sites-available/anc-platform
sudo ln -s /etc/nginx/sites-available/anc-platform /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Nginx Configuration Details

**Upstream servers:**
```nginx
upstream anc_backend {
    server 127.0.0.1:5000;
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
}
```

**WebSocket support:**
```nginx
location /ws/ {
    proxy_pass http://anc_backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

**Static files:**
```nginx
location /static/ {
    alias /path/to/anc-with-ai/static/;
    expires 30d;
}
```

**Security headers:**
```nginx
add_header X-Frame-Options "SAMEORIGIN";
add_header X-Content-Type-Options "nosniff";
add_header X-XSS-Protection "1; mode=block";
```

---

## Environment Variables

### Required Variables

Create a `.env` file in the project root:

```bash
# Application
FLASK_ENV=production
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://user:password@localhost/anc_platform
REDIS_URL=redis://localhost:6379/0

# AWS (for production)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
S3_BUCKET=anc-platform-audio

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Audio
SAMPLE_RATE=48000
CHUNK_SIZE=512

# ML Models
MODEL_PATH=models/
MODEL_VERSION=1.0.0

# Security
JWT_SECRET_KEY=your-jwt-secret
JWT_EXPIRATION_HOURS=24

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/anc-platform.log
```

### Optional Variables

```bash
# Feature Flags
ENABLE_EMERGENCY_DETECTION=true
ENABLE_CLOUD_STORAGE=true
ENABLE_METRICS_COLLECTION=true

# Performance
MAX_WORKERS=4
WORKER_TIMEOUT=30
MAX_UPLOAD_SIZE_MB=10

# External Services
SENTRY_DSN=https://...@sentry.io/...
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

---

## Loading Configuration

### From Python Code

```python
from config.config import get_config

# Get configuration object
config = get_config()

# Access settings
db_url = config.DATABASE_URL
secret = config.SECRET_KEY
debug = config.DEBUG
```

### From Flask App

```python
from flask import Flask
from config.config import get_config

app = Flask(__name__)
app.config.from_object(get_config())

# Access via app.config
db_url = app.config['DATABASE_URL']
```

### From Environment

```bash
# Set environment
export FLASK_ENV=production

# Run application
python wsgi.py
```

---

## Configuration Validation

### Check Configuration

```python
from config.config import get_config

config = get_config()

# Validate required settings
required_settings = [
    'DATABASE_URL',
    'SECRET_KEY',
    'REDIS_URL'
]

for setting in required_settings:
    if not hasattr(config, setting):
        raise ValueError(f"Missing required setting: {setting}")
    if not getattr(config, setting):
        raise ValueError(f"Empty value for required setting: {setting}")
```

### Test Nginx Configuration

```bash
# Validate nginx config
nginx -c config/nginx/nginx.conf -t

# Should output:
# nginx: the configuration file config/nginx/nginx.conf syntax is ok
# nginx: configuration file config/nginx/nginx.conf test is successful
```

---

## Security Best Practices

### Secret Key Management

**❌ Don't:**
```python
SECRET_KEY = "my-secret-key"  # Hardcoded secret
```

**✅ Do:**
```python
import os
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable not set")
```

### Database Credentials

**❌ Don't:**
```python
DATABASE_URL = "postgresql://user:password@localhost/db"
```

**✅ Do:**
```python
DATABASE_URL = os.environ.get('DATABASE_URL')
```

### Environment Files

**❌ Don't:**
- Commit `.env` files to git
- Share `.env` files publicly
- Use same secrets across environments

**✅ Do:**
- Use `.env.example` as a template
- Keep `.env` in `.gitignore`
- Use different secrets for dev/prod
- Use secrets management (AWS Secrets Manager, Vault)

---

## Troubleshooting

### Configuration Not Loading

**Problem:** Settings not being applied

**Solution:**
```python
import os
print(os.environ.get('FLASK_ENV'))  # Check environment
print(config.__class__.__name__)     # Check config class
```

### Nginx Configuration Errors

**Problem:** Nginx fails to start

**Solution:**
```bash
# Check syntax
nginx -c config/nginx/nginx.conf -t

# Check error log
tail -f /var/log/nginx/error.log

# Verify paths
ls -la config/nginx/nginx.conf
```

### Environment Variables Not Set

**Problem:** Missing environment variables

**Solution:**
```bash
# Load .env file
export $(cat .env | xargs)

# Verify loaded
echo $DATABASE_URL
echo $SECRET_KEY
```

---

## See Also

- [Production Deployment Guide](../docs/deployment/PRODUCTION_DEPLOYMENT.md) - Production setup
- [Local Execution Guide](../docs/guides/LOCAL_EXECUTION_GUIDE.md) - Local development
- [Docker Compose](../docker-compose.yml) - Container configuration
- [Environment Example](../.env.example) - Environment template

---

**Last Updated:** 2025-11-16
**Maintained by:** ANC Platform Team
