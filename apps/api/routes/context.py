# REST router for context management. Scopes knowledge to projects/teams. Define a context first, then store knowledge linked to it.
"""
REST router for context management. Scopes knowledge to projects/teams. Define a context first, then store knowledge linked to it.
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from apps.api.schemas import ContextDefineRequest, ContextResponse, StoreResponse
from knowledge.context import define_context, get_context, get_knowledge_in_context

router = APIRouter(prefix="/context", tags=["context"])


@router.post("/", response_model=ContextResponse, status_code=status.HTTP_201_CREATED)
async def define_new_context(
    request: ContextDefineRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        ctx = await define_context(
            db=db,
            tenant_id=request.tenant_id,
            context_type=request.context_type,
            context_id_str=request.context_id,
            metadata=request.metadata or {}
        )
        return ctx
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{context_type}/{context_id}", response_model=ContextResponse)
async def get_existing_context(
    context_type: str,
    context_id: str,
    tenant_id: str,
    db: AsyncSession = Depends(get_db)
):
    ctx = await get_context(
        db=db,
        tenant_id=tenant_id,
        context_type=context_type,
        context_id_str=context_id
    )
    if not ctx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Context not found"
        )
    return ctx


@router.get("/{context_uuid}/knowledge", response_model=List[StoreResponse])
async def get_context_knowledge(
    context_uuid: uuid.UUID,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    objs = await get_knowledge_in_context(
        db=db,
        context_uuid=context_uuid,
        limit=limit
    )
    return objs
