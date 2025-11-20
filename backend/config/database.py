"""
Database Configuration and Connection
"""

from flask_sqlalchemy import SQLAlchemy
import logging

logger = logging.getLogger(__name__)

# Create SQLAlchemy instance
db = SQLAlchemy()


def init_db():
    """Initialize database - create all tables"""
    try:
        # Import all models to ensure they're registered
        from database.models import (
            User, AudioSession, NoiseDetection,
            ProcessingMetric, APIRequest, DeviceCalibration,
            EmergencyEvent
        )

        # Create all tables
        db.create_all()
        logger.info("Database tables created successfully")

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


def drop_db():
    """Drop all database tables - USE WITH CAUTION"""
    db.drop_all()
    logger.warning("All database tables dropped")


def reset_db():
    """Reset database - drop and recreate all tables"""
    drop_db()
    init_db()
    logger.info("Database reset complete")
