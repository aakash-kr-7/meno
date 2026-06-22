# Knowledge extraction pipeline. Extracts typed objects (memories, patterns, decisions, bugs) from conversation messages. Infers relationships between objects. Links to project contexts mentioned in conversation.
"""
Knowledge extraction pipeline. Extracts typed objects (memories, patterns, decisions, bugs) from conversation messages. Infers relationships between objects. Links to project contexts mentioned in conversation.
"""

import re
from typing import List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from core.types import ContextType, RelationshipType, KnowledgeType
from core.llm import extract_from_messages, infer_relationship
from knowledge.store import store_knowledge_object
from knowledge.context import define_context, link_to_context
from knowledge.relationships import create_relationship
from db.models.knowledge_object import KnowledgeObject
from db.models.context import KnowledgeContext


async def extract_and_store_from_session(
    db: AsyncSession,
    session_id: Any,
    user_id: str,
    tenant_id: str,
    messages: List[dict]
) -> List[KnowledgeObject]:
    """
    Extracts knowledge objects from messages, stores them, infers relationships,
    scans for project mentions, and links them to relevant contexts.
    """
    # 1. Call extract_from_messages(messages) from core/llm.py
    extraction_results = await extract_from_messages(messages)
    if not extraction_results:
        return []

    # 2. For each ExtractionResult: call store_knowledge_object(db, ..., source_type='session', source_id=session_id)
    stored_objects: List[KnowledgeObject] = []
    for res in extraction_results:
        obj = await store_knowledge_object(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            type=res.type,
            content=res.content,
            title=res.title,
            source_type='session',
            source_id=str(session_id),
            confidence=res.confidence,
            tags=res.tags
        )
        stored_objects.append(obj)

    # 3. Pairwise infer_relationship() on all extracted pairs.
    # If result not None and confidence > 0.6: call create_relationship()
    from itertools import combinations
    for (res1, ko1), (res2, ko2) in combinations(zip(extraction_results, stored_objects), 2):
        rel_dict = await infer_relationship(res1, res2)
        if rel_dict is not None and rel_dict.get("confidence", 0.0) > 0.6:
            # Determine relationship direction: if IMPLEMENTS, CODE_PATTERN implements DECISION
            if rel_dict["type"] == RelationshipType.IMPLEMENTS.value:
                if ko1.type == KnowledgeType.CODE_PATTERN.value:
                    src_id, tgt_id = ko1.id, ko2.id
                else:
                    src_id, tgt_id = ko2.id, ko1.id
            else:
                src_id, tgt_id = ko1.id, ko2.id

            await create_relationship(
                db=db,
                tenant_id=tenant_id,
                source_id=src_id,
                target_id=tgt_id,
                relationship_type=rel_dict["type"],
                confidence=rel_dict["confidence"],
                inferred=True
            )

    # 4. Scan message content for project context mentions:
    # Look for patterns like "project:", "in sol", "for <name>".
    # Call get_or_create_context_from_mention() then link_to_context() for each object.
    mentions = set()
    pattern = re.compile(r"(project:\w+|in\s+\w+|for\s+\w+)", re.IGNORECASE)
    for msg in messages:
        content = msg.get("content") or msg.get("text") or ""
        if isinstance(content, str):
            for match in pattern.finditer(content):
                mentions.add(match.group(1))

    for mention in mentions:
        context = await get_or_create_context_from_mention(db, tenant_id, mention)
        if context is not None:
            for ko in stored_objects:
                await link_to_context(db, knowledge_object_id=ko.id, context_uuid=context.id)

    # 5. Return list of stored KnowledgeObject instances.
    return stored_objects


async def get_or_create_context_from_mention(
    db: AsyncSession,
    tenant_id: str,
    mention: str
) -> Optional[KnowledgeContext]:
    """
    Parse mention, e.g. "project:meno", "in sol", "for meno".
    context_type=PROJECT, context_id=mention.strip().lower()
    Call define_context(). Return context.
    """
    mention_lower = mention.strip().lower()
    if mention_lower.startswith("project:"):
        context_id = mention_lower.split(":", 1)[1].strip()
    elif mention_lower.startswith("in "):
        context_id = mention_lower[3:].strip()
    elif mention_lower.startswith("for "):
        context_id = mention_lower[4:].strip()
    else:
        context_id = mention_lower

    if not context_id:
        return None

    # Filter out common English stop words to avoid noise contexts
    stop_words = {"the", "a", "an", "this", "that", "these", "those", "my", "your", "his", "her", "its", "our", "their", "here", "there", "it", "them", "us", "him", "her", "you", "me"}
    if context_id in stop_words and not mention_lower.startswith("project:"):
        return None

    context = await define_context(
        db=db,
        tenant_id=tenant_id,
        context_type=ContextType.PROJECT.value,
        context_id_str=context_id
    )
    return context
