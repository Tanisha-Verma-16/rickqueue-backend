"""
SQLAlchemy Base Class
All models inherit from this
"""

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Models will be imported by alembic/env.py when needed
# Do NOT import models here to avoid circular imports

__all__ = ['Base']