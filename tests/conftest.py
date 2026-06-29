import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import delete
from sqlalchemy.pool import NullPool
from httpx import AsyncClient, ASGITransport

from core.config import settings
from apps.api.main import app
from db.session import engine as app_engine
from db.models import KnowledgeObject, KnowledgeRelationship, KnowledgeContext, KnowledgeInContext, BehavioralProfile

@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_engine():
    # Use NullPool to ensure connections are not cached and reused across different event loops
    return create_async_engine(settings.DATABASE_URL, poolclass=NullPool)

@pytest.fixture
async def cleanup(test_engine):
    yield
    # Cleanup database tables in correct dependency order after the test runs
    async_session = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        class_=AsyncSession
    )
    async with async_session() as session:
        await session.execute(delete(KnowledgeInContext))
        await session.execute(delete(KnowledgeRelationship))
        await session.execute(delete(KnowledgeContext))
        await session.execute(delete(KnowledgeObject))
        await session.execute(delete(BehavioralProfile))
        await session.commit()
    
    # Dispose of both engines to clear connection pools between tests
    await app_engine.dispose()
    await test_engine.dispose()

@pytest.fixture
async def db_session(test_engine, cleanup) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        class_=AsyncSession
    )
    async with async_session() as session:
        yield session

@pytest.fixture
async def client(cleanup) -> AsyncGenerator[AsyncClient, None]:
    # No dependency overrides needed! Both client and test connect to the same DB.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture(scope="session", autouse=True)
def warmup_embeddings():
    from core.embeddings import embedding_service
    _ = embedding_service.embed("warmup")

