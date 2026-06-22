# /knowledge/store and /knowledge/retrieve are the two most-called endpoints in MENO.
"""
/knowledge/store and /knowledge/retrieve are the two most-called endpoints in MENO.
"""

import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from apps.api.dependencies import get_db
from apps.api.schemas import (
    StoreRequest,
    StoreResponse,
    RetrieveRequest,
    RetrieveResponse,
    SearchByTypeRequest
)
from db.models.knowledge_object import KnowledgeObject
from knowledge.store import store_knowledge_object, get_knowledge_object
from knowledge.retrieval import retrieve_knowledge, search_by_type
from knowledge.relationships import get_relationships

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/store", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
async def store_object(request: StoreRequest, db: AsyncSession = Depends(get_db)):
    try:
        obj = await store_knowledge_object(
            db=db,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            type=request.type,
            content=request.content,
            title=request.title,
            source_type=request.source_type,
            source_id=request.source_id,
            source_context=request.source_context or {},
            confidence=request.confidence or 0.5,
            tags=request.tags or [],
            metadata=request.metadata or {},
            context_ids=request.context_ids or []
        )
        return obj
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_objects(request: RetrieveRequest, db: AsyncSession = Depends(get_db)):
    results = await retrieve_knowledge(
        db=db,
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        query=request.query,
        top_k=request.top_k or 5,
        knowledge_type=request.knowledge_type,
        context_id=request.context_id,
        expand_relationships=request.expand_relationships or False,
        relationship_types=request.relationship_types or []
    )
    return {"results": results}


@router.post("/search/structured", response_model=List[StoreResponse])
async def search_objects(request: SearchByTypeRequest, db: AsyncSession = Depends(get_db)):
    objs = await search_by_type(
        db=db,
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        knowledge_type=request.knowledge_type,
        context_id=request.context_id,
        limit=request.limit or 50
    )
    return objs


@router.get("/{object_id}", response_model=Dict[str, Any])
async def get_object_by_id(object_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await get_knowledge_object(db, object_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge object with id {object_id} not found"
        )

    relationships = await get_relationships(db, object_id, direction="both")

    return {
        "id": obj.id,
        "tenant_id": obj.tenant_id,
        "user_id": obj.user_id,
        "type": obj.type,
        "title": obj.title,
        "content": obj.content,
        "source_type": obj.source_type,
        "source_id": obj.source_id,
        "source_context": obj.source_context,
        "confidence": obj.confidence,
        "tags": obj.tags,
        "metadata": obj.metadata_,
        "created_at": obj.created_at,
        "relationships": relationships
    }


@router.delete("/{object_id}", status_code=status.HTTP_200_OK)
async def delete_object_by_id(object_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await get_knowledge_object(db, object_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge object with id {object_id} not found"
        )

    stmt = delete(KnowledgeObject).where(KnowledgeObject.id == object_id)
    await db.execute(stmt)
    await db.commit()
    return {"success": True}
