import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from core.config import settings
from db.models.knowledge_object import KnowledgeObject
from core.embeddings import embedding_service

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    async with async_session() as session:
        # Check all knowledge objects currently in the DB
        stmt = select(KnowledgeObject)
        res = await session.execute(stmt)
        objs = res.scalars().all()
        print(f"Total objects in DB: {len(objs)}")
        for o in objs:
            print(f"ID: {o.id}, Tenant: {o.tenant_id}, User: {o.user_id}, Type: {o.type}, Content: {o.content[:30]}")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
