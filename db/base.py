# SQLAlchemy DeclarativeBase. All models inherit from Base. Never redefine elsewhere.
"""
SQLAlchemy DeclarativeBase. All models inherit from Base. Never redefine elsewhere.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
