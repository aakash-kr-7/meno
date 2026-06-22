"""
MENO Python SDK. Sync + async variants. tenant_id defaults to 'default' for single-tenant setups.
"""
from typing import Optional, List, Dict, Any
import httpx

from meno.models import (
    KnowledgeObject,
    StoreResult,
    RelationshipResult,
    SubgraphResult,
    ContextResult,
    SessionInfo,
)


class MenoError(Exception):
    def __init__(self, message: str, status_code: int = 0):
        self.status_code = status_code
        super().__init__(message)


class Meno:
    def __init__(self, api_key: str = "", base_url: str = "http://localhost:8000", tenant_id: str = "default"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.tenant_id = tenant_id

        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        self.client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=30.0
        )
        self.aclient = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=30.0
        )

    # --- Sync methods (httpx.Client, timeout=30) -------------------

    def store(
        self,
        user_id: str,
        content: str,
        type: str = "memory",
        title: Optional[str] = None,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        source_context: dict = {},
        confidence: float = 0.5,
        tags: list = [],
        context_ids: list = []
    ) -> StoreResult:
        payload = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "type": type,
            "content": content,
            "title": title,
            "source_type": source_type,
            "source_id": source_id,
            "source_context": source_context,
            "confidence": confidence,
            "tags": tags,
            "context_ids": context_ids
        }
        resp = self.client.post("/knowledge/store", json=payload)
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return StoreResult(**resp.json())

    def retrieve(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        knowledge_type: Optional[str] = None,
        context_id: Optional[str] = None,
        expand_relationships: bool = False,
        relationship_types: list = []
    ) -> List[KnowledgeObject]:
        payload = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "query": query,
            "top_k": top_k,
            "knowledge_type": knowledge_type,
            "context_id": context_id,
            "expand_relationships": expand_relationships,
            "relationship_types": relationship_types
        }
        resp = self.client.post("/knowledge/retrieve", json=payload)
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return [KnowledgeObject(**item) for item in resp.json().get("results", [])]

    def search_by_type(
        self,
        user_id: str,
        object_type: str,
        context_id: Optional[str] = None,
        limit: int = 50
    ) -> List[StoreResult]:
        payload = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "knowledge_type": object_type,
            "context_id": context_id,
            "limit": limit
        }
        resp = self.client.post("/knowledge/search/structured", json=payload)
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return [StoreResult(**item) for item in resp.json()]

    def get_object(self, object_id: str) -> KnowledgeObject:
        resp = self.client.get(f"/knowledge/{object_id}")
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return KnowledgeObject(**resp.json())

    def relate(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        confidence: float = 1.0,
        explanation: Optional[str] = None
    ) -> RelationshipResult:
        payload = {
            "tenant_id": self.tenant_id,
            "source_id": source_id,
            "target_id": target_id,
            "relationship_type": relationship_type,
            "confidence": confidence,
            "explanation": explanation
        }
        resp = self.client.post("/knowledge/relate", json=payload)
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return RelationshipResult(**resp.json())

    def get_graph(
        self,
        object_id: str,
        max_depth: int = 2,
        relationship_types: list = []
    ) -> SubgraphResult:
        params = {"max_depth": max_depth}
        if relationship_types:
            params["relationship_types"] = relationship_types
        resp = self.client.get(f"/knowledge/graph/{object_id}", params=params)
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return SubgraphResult(**resp.json())

    def define_context(
        self,
        context_type: str,
        context_id: str,
        metadata: dict = {}
    ) -> ContextResult:
        payload = {
            "tenant_id": self.tenant_id,
            "context_type": context_type,
            "context_id": context_id,
            "metadata": metadata
        }
        resp = self.client.post("/context/", json=payload)
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return ContextResult(**resp.json())

    def create_session(self, user_id: str) -> SessionInfo:
        payload = {
            "tenant_id": self.tenant_id,
            "user_id": user_id
        }
        resp = self.client.post("/sessions/", json=payload)
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return SessionInfo(**resp.json())

    def append_message(self, session_id: str, role: str, content: str) -> dict:
        payload = {
            "role": role,
            "content": content
        }
        resp = self.client.post(f"/sessions/{session_id}/messages", json=payload)
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return resp.json()

    def get_session(self, session_id: str) -> dict:
        resp = self.client.get(f"/sessions/{session_id}")
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return resp.json()

    def get_extracted_from_session(self, session_id: str) -> List[StoreResult]:
        resp = self.client.get(f"/sessions/{session_id}/extracted")
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return [StoreResult(**item) for item in resp.json()]

    def promote_session(self, session_id: str) -> dict:
        resp = self.client.post(f"/worker/promote/{session_id}")
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return resp.json()

    # --- Async methods (httpx.AsyncClient, timeout=30, a-prefix) ---

    async def astore(
        self,
        user_id: str,
        content: str,
        type: str = "memory",
        title: Optional[str] = None,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        source_context: dict = {},
        confidence: float = 0.5,
        tags: list = [],
        context_ids: list = []
    ) -> StoreResult:
        payload = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "type": type,
            "content": content,
            "title": title,
            "source_type": source_type,
            "source_id": source_id,
            "source_context": source_context,
            "confidence": confidence,
            "tags": tags,
            "context_ids": context_ids
        }
        resp = await self.aclient.post("/knowledge/store", json=payload)
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return StoreResult(**resp.json())

    async def aretrieve(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        knowledge_type: Optional[str] = None,
        context_id: Optional[str] = None,
        expand_relationships: bool = False,
        relationship_types: list = []
    ) -> List[KnowledgeObject]:
        payload = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "query": query,
            "top_k": top_k,
            "knowledge_type": knowledge_type,
            "context_id": context_id,
            "expand_relationships": expand_relationships,
            "relationship_types": relationship_types
        }
        resp = await self.aclient.post("/knowledge/retrieve", json=payload)
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return [KnowledgeObject(**item) for item in resp.json().get("results", [])]

    async def asearch_by_type(
        self,
        user_id: str,
        object_type: str,
        context_id: Optional[str] = None,
        limit: int = 50
    ) -> List[StoreResult]:
        payload = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "knowledge_type": object_type,
            "context_id": context_id,
            "limit": limit
        }
        resp = await self.aclient.post("/knowledge/search/structured", json=payload)
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return [StoreResult(**item) for item in resp.json()]

    async def aget_object(self, object_id: str) -> KnowledgeObject:
        resp = await self.aclient.get(f"/knowledge/{object_id}")
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return KnowledgeObject(**resp.json())

    async def arelate(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        confidence: float = 1.0,
        explanation: Optional[str] = None
    ) -> RelationshipResult:
        payload = {
            "tenant_id": self.tenant_id,
            "source_id": source_id,
            "target_id": target_id,
            "relationship_type": relationship_type,
            "confidence": confidence,
            "explanation": explanation
        }
        resp = await self.aclient.post("/knowledge/relate", json=payload)
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return RelationshipResult(**resp.json())

    async def aget_graph(
        self,
        object_id: str,
        max_depth: int = 2,
        relationship_types: list = []
    ) -> SubgraphResult:
        params = {"max_depth": max_depth}
        if relationship_types:
            params["relationship_types"] = relationship_types
        resp = await self.aclient.get(f"/knowledge/graph/{object_id}", params=params)
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return SubgraphResult(**resp.json())

    async def adefine_context(
        self,
        context_type: str,
        context_id: str,
        metadata: dict = {}
    ) -> ContextResult:
        payload = {
            "tenant_id": self.tenant_id,
            "context_type": context_type,
            "context_id": context_id,
            "metadata": metadata
        }
        resp = await self.aclient.post("/context/", json=payload)
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return ContextResult(**resp.json())

    async def acreate_session(self, user_id: str) -> SessionInfo:
        payload = {
            "tenant_id": self.tenant_id,
            "user_id": user_id
        }
        resp = await self.aclient.post("/sessions/", json=payload)
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return SessionInfo(**resp.json())

    async def aappend_message(self, session_id: str, role: str, content: str) -> dict:
        payload = {
            "role": role,
            "content": content
        }
        resp = await self.aclient.post(f"/sessions/{session_id}/messages", json=payload)
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return resp.json()

    async def aget_session(self, session_id: str) -> dict:
        resp = await self.aclient.get(f"/sessions/{session_id}")
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return resp.json()

    async def aget_extracted_from_session(self, session_id: str) -> List[StoreResult]:
        resp = await self.aclient.get(f"/sessions/{session_id}/extracted")
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return [StoreResult(**item) for item in resp.json()]

    async def apromote_session(self, session_id: str) -> dict:
        resp = await self.aclient.post(f"/worker/promote/{session_id}")
        if resp.status_code < 200 or resp.status_code >= 300:
            raise MenoError(resp.text, resp.status_code)
        return resp.json()
