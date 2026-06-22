# All API dependencies including database session retrieval.
"""
All API dependencies including database session retrieval.
"""

from db.session import get_db

__all__ = ["get_db"]
