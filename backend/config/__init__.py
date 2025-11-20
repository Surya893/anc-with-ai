"""
Backend Configuration Module
"""

from .settings import Config, get_config
from .database import db, init_db

__all__ = ['Config', 'get_config', 'db', 'init_db']
