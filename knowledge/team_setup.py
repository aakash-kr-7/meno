# ==============================================================================
# (a) What this file is: Team onboarding helper.
# (b) What it does: Idempotent get-or-create for project context. First teammate creates it; subsequent teammates discover and reuse it without resetting metadata.
# (c) How it fits into the MENO system: Provides team context initialization and sharing utilities.
# ==============================================================================

from sqlalchemy.ext.asyncio import AsyncSession
from db.models.context import KnowledgeContext
from knowledge.context import get_context, define_context

async def get_or_create_team_context(
    db: AsyncSession,
    tenant_id: str,
    project_name: str
) -> KnowledgeContext:
    """
    Idempotently retrieves or creates a project-level context.
    Avoids overwriting existing metadata if the context already exists.
    """
    result = await get_context(db, tenant_id, "project", project_name)
    if result:
        return result  # return existing — do NOT call define_context() again, would reset metadata
    return await define_context(db, tenant_id, "project", project_name, metadata={})
