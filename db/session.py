# Async session factory. get_db() FastAPI dependency yields AsyncSession per request.
"""
Async session factory. get_db() FastAPI dependency yields AsyncSession per request.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from core.config import settings

import sys
from sqlalchemy.pool import NullPool
from core.config import settings

# Use NullPool during testing/pytest to prevent cross-loop connection pooling issues
is_testing = "pytest" in sys.modules or settings.APP_ENV == "test"

if is_testing:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
else:
    engine = create_async_engine(settings.DATABASE_URL)

async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
