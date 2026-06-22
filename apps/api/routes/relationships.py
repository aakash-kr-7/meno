# REST router for relationship graph.
"""
REST router for relationship graph.
"""

import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from apps.api.schemas import (
    RelateRequest,
    RelateResponse,
    SubgraphResponse
)
from knowledge.relationships import (
    create_relationship,
    get_relationships,
    get_subgraph
)

router = APIRouter(prefix="/knowledge", tags=["relationships"])


@router.post("/relate", response_model=RelateResponse, status_code=status.HTTP_201_CREATED)
async def relate_objects(request: RelateRequest, db: AsyncSession = Depends(get_db)):
    try:
        rel = await create_relationship(
            db=db,
            tenant_id=request.tenant_id,
            source_id=request.source_id,
            target_id=request.target_id,
            relationship_type=request.relationship_type,
            confidence=request.confidence or 1.0,
            explanation=request.explanation,
            inferred=request.inferred or False
        )
        return rel
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/graph/{object_id}", response_model=SubgraphResponse)
async def get_graph(
    object_id: uuid.UUID,
    max_depth: int = Query(default=2, ge=1, le=5),
    relationship_types: List[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db)
):
    subgraph = await get_subgraph(
        db=db,
        object_id=object_id,
        max_depth=max_depth,
        relationship_types=relationship_types
    )
    return subgraph


@router.get("/{object_id}/relationships", response_model=Dict[str, Any])
async def get_object_relationships(
    object_id: uuid.UUID,
    direction: str = Query(default="both"),
    relationship_types: List[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db)
):
    if direction not in ("outgoing", "incoming", "both"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Direction must be 'outgoing', 'incoming', or 'both'"
        )

    rels = await get_relationships(
        db=db,
        object_id=object_id,
        direction=direction,
        relationship_types=relationship_types
    )
    return rels
