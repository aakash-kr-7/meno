"""
Pydantic models returned by the MENO SDK. Clean, minimal data structures.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class KnowledgeObject(BaseModel):
    id: str
    type: str
    title: Optional[str] = None
    content: str
    score: Optional[float] = None
    breakdown: Dict[str, Any] = {}
    source_type: Optional[str] = None
    source_context: Dict[str, Any] = {}
    confidence: float
    tags: List[str] = []
    created_at: str
    relationships: Optional[Dict[str, Any]] = None


class StoreResult(BaseModel):
    id: str
    type: str
    title: Optional[str] = None
    content: str
    created_at: str
    confidence: float
    tags: List[str] = []


class RelationshipResult(BaseModel):
    id: str
    source_id: str
    target_id: str
    relationship_type: str
    confidence: float
    explanation: Optional[str] = None
    created_at: str


class SubgraphResult(BaseModel):
    root: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class ContextResult(BaseModel):
    id: str
    tenant_id: str
    context_type: str
    context_id: str
    metadata: Dict[str, Any] = {}
    created_at: str


class SessionInfo(BaseModel):
    id: str
    user_id: str
    tenant_id: str
    created_at: str
