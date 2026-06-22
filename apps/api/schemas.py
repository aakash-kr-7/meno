# All Pydantic v2 request/response schemas. Public API contracts.
"""
All Pydantic v2 request/response schemas. Public API contracts.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class StoreRequest(BaseModel):
    tenant_id: str
    user_id: str
    type: str
    content: str
    title: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    source_context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    confidence: Optional[float] = 0.5
    tags: Optional[List[str]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    context_ids: Optional[List[uuid.UUID]] = Field(default_factory=list)


class StoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    tenant_id: str
    user_id: str
    type: str
    content: str
    title: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    source_context: Dict[str, Any] = Field(default_factory=dict)
    confidence: float
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime


class RetrieveRequest(BaseModel):
    tenant_id: str
    user_id: str
    query: str
    top_k: Optional[int] = 5
    knowledge_type: Optional[str] = None
    context_id: Optional[uuid.UUID] = None
    expand_relationships: Optional[bool] = False
    relationship_types: Optional[List[str]] = Field(default_factory=list)


class RetrieveResult(BaseModel):
    id: uuid.UUID
    type: str
    title: Optional[str] = None
    content: str
    score: float
    breakdown: Dict[str, Any]
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    source_context: Dict[str, Any]
    confidence: float
    tags: List[str]
    created_at: str
    relationships: Optional[Dict[str, Any]] = None


class RetrieveResponse(BaseModel):
    results: List[RetrieveResult]


class RelateRequest(BaseModel):
    tenant_id: Optional[str] = None
    source_id: uuid.UUID
    target_id: uuid.UUID
    relationship_type: str
    confidence: Optional[float] = 1.0
    explanation: Optional[str] = None
    inferred: Optional[bool] = False


class RelateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: Optional[str] = None
    source_id: uuid.UUID
    target_id: uuid.UUID
    relationship_type: str
    confidence: float
    explanation: Optional[str] = None
    inferred: bool
    created_at: datetime


class SubgraphResponse(BaseModel):
    root: uuid.UUID
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class ContextDefineRequest(BaseModel):
    tenant_id: str
    context_type: str
    context_id: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ContextResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    tenant_id: str
    context_type: str
    context_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class SearchByTypeRequest(BaseModel):
    tenant_id: str
    user_id: str
    knowledge_type: str
    context_id: Optional[uuid.UUID] = None
    limit: Optional[int] = 50


class SessionCreateRequest(BaseModel):
    tenant_id: str
    user_id: str
    context_id: Optional[uuid.UUID] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    user_id: str
    context_id: Optional[uuid.UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class MessageAppendRequest(BaseModel):
    content: str
    role: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SessionMessagesResponse(BaseModel):
    session_id: uuid.UUID
    messages: List[Dict[str, Any]]


class BehaviorProfileRequest(BaseModel):
    tenant_id: str
    user_id: str


class BehaviorProfileResponse(BaseModel):
    user_id: str
    profile_data: Dict[str, Any]


class BehaviorProfilePatchRequest(BaseModel):
    preferred_language: Optional[str] = None
    tone: Optional[str] = None
    context_size: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None
