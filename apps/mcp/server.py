# ==============================================================================
# MENO MCP server. Exposes knowledge graph as MCP tools. Calls the same core functions as the REST API
# — no duplicate logic anywhere.
# ==============================================================================
"""
MENO MCP server. Exposes knowledge graph as MCP tools. Calls the same core functions as the REST API
— no duplicate logic anywhere.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP
from sqlalchemy import select

from db.session import async_session
from db.models.session import Session, SessionMessage
from core.types import KnowledgeType
from knowledge.store import store_knowledge_object
from knowledge.retrieval import retrieve_knowledge, search_by_type
from knowledge.relationships import create_relationship, get_subgraph
from knowledge.context import define_context
from apps.worker.promotion_worker import promote_session
from memory.working.redis_store import create_session_cache, append_message_cache

mcp = FastMCP("meno")

def convert_for_mcp(obj: Any) -> Any:
    """
    recursively convert UUID to str, datetime to str in any structure.
    Also handles Pydantic models and SQLAlchemy models without embedding vector fields.
    """
    if obj is None:
        return None
    
    # Handle Pydantic models
    if hasattr(obj, "model_dump"):
        obj = obj.model_dump()
    # Handle SQLAlchemy models
    elif hasattr(obj, "__table__"):
        attrs = {}
        for col in obj.__table__.columns:
            if col.name == "embedding":
                continue
            name = col.name
            val = getattr(obj, name)
            if name == "metadata_":
                attrs["metadata"] = val
            else:
                attrs[name] = val
        obj = attrs

    if isinstance(obj, dict):
        return {k: convert_for_mcp(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [convert_for_mcp(x) for x in obj]
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj

@mcp.tool()
async def meno_store(
    tenant_id: str,
    user_id: str,
    type: str,
    content: str,
    title: Optional[str] = None,
    source_type: str = "conversation",
    confidence: float = 0.5,
    tags: List[str] = [],
    context_ids: List[str] = []
) -> Dict[str, Any]:
    """Store a knowledge object. Call immediately after: making an architectural
decision, establishing a code pattern, fixing a bug, or learning a durable project fact.
Do NOT call for transient chit-chat. type must be one of: memory, code_pattern, decision,
api_spec, bug_report, refactoring, architecture."""
    try:
        async with async_session() as db:
            result = await store_knowledge_object(
                db=db,
                tenant_id=tenant_id,
                user_id=user_id,
                type=type,
                content=content,
                title=title,
                source_type=source_type,
                confidence=confidence,
                tags=tags,
                context_ids=context_ids
            )
            return convert_for_mcp(result)
    except Exception as e:
        return {"error": str(e), "tool": "meno_store"}

@mcp.tool()
async def meno_retrieve(
    tenant_id: str,
    user_id: str,
    query: str,
    top_k: int = 5,
    knowledge_type: Optional[str] = None,
    context_id: Optional[str] = None,
    expand_relationships: bool = False
) -> Any:
    """Retrieve relevant knowledge before any non-trivial task. Call: at session start,
before implementing something that might already exist, before deriving a decision from scratch."""
    try:
        # Validate knowledge_type
        if knowledge_type and knowledge_type not in [t.value for t in KnowledgeType]:
            raise ValueError(f"Invalid knowledge type: {knowledge_type}")

        async with async_session() as db:
            ctx_uuid = uuid.UUID(context_id) if context_id else None
            result = await retrieve_knowledge(
                db=db,
                tenant_id=tenant_id,
                user_id=user_id,
                query=query,
                top_k=top_k,
                knowledge_type=knowledge_type,
                context_id=ctx_uuid,
                expand_relationships=expand_relationships
            )
            return convert_for_mcp(result)
    except Exception as e:
        return {"error": str(e), "tool": "meno_retrieve"}

@mcp.tool()
async def meno_relate(
    tenant_id: str,
    source_id: str,
    target_id: str,
    relationship_type: str,
    confidence: float = 1.0,
    explanation: Optional[str] = None
) -> Dict[str, Any]:
    """Link two knowledge objects. Use when a pattern implements a decision,
a bug contradicts an assumption, or any meaningful connection exists."""
    try:
        async with async_session() as db:
            result = await create_relationship(
                db=db,
                tenant_id=tenant_id,
                source_id=source_id,
                target_id=target_id,
                relationship_type=relationship_type,
                confidence=confidence,
                explanation=explanation
            )
            return convert_for_mcp(result)
    except Exception as e:
        return {"error": str(e), "tool": "meno_relate"}

@mcp.tool()
async def meno_get_graph(
    object_id: str,
    max_depth: int = 2,
    relationship_types: List[str] = []
) -> Dict[str, Any]:
    """Get the relationship subgraph around an object. Use to understand
what a decision depends on, what implements it, or what it supersedes. max_depth=2 is
sufficient."""
    try:
        async with async_session() as db:
            result = await get_subgraph(
                db=db,
                object_id=object_id,
                max_depth=max_depth,
                relationship_types=relationship_types
            )
            return convert_for_mcp(result)
    except Exception as e:
        return {"error": str(e), "tool": "meno_get_graph"}

@mcp.tool()
async def meno_search_by_type(
    tenant_id: str,
    user_id: str,
    type: str,
    context_id: Optional[str] = None,
    limit: int = 50
) -> Any:
    """Find all objects of a specific type. Use for a full picture of a category
rather than semantic search."""
    try:
        async with async_session() as db:
            ctx_uuid = uuid.UUID(context_id) if context_id else None
            result = await search_by_type(
                db=db,
                tenant_id=tenant_id,
                user_id=user_id,
                knowledge_type=type,
                context_id=ctx_uuid,
                limit=limit
            )
            return convert_for_mcp(result)
    except Exception as e:
        return {"error": str(e), "tool": "meno_search_by_type"}

@mcp.tool()
async def meno_define_context(
    tenant_id: str,
    context_type: str,
    context_id: str,
    metadata: Dict[str, Any] = {}
) -> Dict[str, Any]:
    """Define or retrieve a project/team/org context. Always define at project start
and pass context_id to store/retrieve calls to scope knowledge and prevent mixing projects."""
    try:
        async with async_session() as db:
            result = await define_context(
                db=db,
                tenant_id=tenant_id,
                context_type=context_type,
                context_id_str=context_id,
                metadata=metadata
            )
            return convert_for_mcp(result)
    except Exception as e:
        return {"error": str(e), "tool": "meno_define_context"}

@mcp.tool()
async def meno_create_session(
    tenant_id: str,
    user_id: str
) -> Dict[str, Any]:
    """Create a working memory session at the start of a significant work block."""
    try:
        async with async_session() as db:
            session_row = Session(
                tenant_id=tenant_id,
                user_id=user_id,
                metadata_={}
            )
            db.add(session_row)
            await db.commit()
            await db.refresh(session_row)

            await create_session_cache(
                session_id=session_row.id,
                user_id=session_row.user_id,
                tenant_id=session_row.tenant_id
            )
            return convert_for_mcp(session_row)
    except Exception as e:
        return {"error": str(e), "tool": "meno_create_session"}

@mcp.tool()
async def meno_append_message(
    session_id: str,
    role: str,
    content: str
) -> Dict[str, Any]:
    """Append a message to the session. Log decisions, patterns, bug discoveries.
This material is extracted when the session is promoted."""
    try:
        session_uuid = uuid.UUID(session_id) if isinstance(session_id, str) else session_id
        async with async_session() as db:
            session_stmt = select(Session).where(Session.id == session_uuid)
            session_res = await db.execute(session_stmt)
            session_row = session_res.scalar_one_or_none()
            if not session_row:
                raise ValueError(f"Session with ID {session_id} not found")

            try:
                updated_cache = await append_message_cache(session_uuid, role, content)
            except ValueError:
                msg_stmt = select(SessionMessage).where(SessionMessage.session_id == session_uuid).order_by(SessionMessage.created_at.asc())
                msg_res = await db.execute(msg_stmt)
                db_messages = msg_res.scalars().all()

                formatted_messages = []
                for msg in db_messages:
                    formatted_messages.append({
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.created_at.isoformat()
                    })

                await create_session_cache(
                    session_id=session_uuid,
                    user_id=session_row.user_id,
                    tenant_id=session_row.tenant_id
                )
                for msg in formatted_messages:
                    await append_message_cache(session_uuid, msg["role"], msg["content"])

                updated_cache = await append_message_cache(session_uuid, role, content)

            db_msg = SessionMessage(
                session_id=session_uuid,
                role=role,
                content=content,
                metadata_={}
            )
            db.add(db_msg)

            session_row.last_activity = datetime.utcnow()
            await db.commit()

            return convert_for_mcp(updated_cache)
    except Exception as e:
        return {"error": str(e), "tool": "meno_append_message"}

@mcp.tool()
async def meno_promote_session(
    session_id: str
) -> Dict[str, Any]:
    """Promote session to structured knowledge. Run before ending a long session
or switching tools. Extracts knowledge so the next tool session can retrieve it."""
    try:
        async with async_session() as db:
            result = await promote_session(session_id, db)
            if result is None:
                raise ValueError(f"Session with ID {session_id} not found or already promoted")
            return convert_for_mcp(result)
    except Exception as e:
        return {"error": str(e), "tool": "meno_promote_session"}
