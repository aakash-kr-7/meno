# Manual trigger endpoints for the promotion worker. Useful for testing and orchestration.
"""
Manual trigger endpoints for the promotion worker. Useful for testing and orchestration.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from apps.worker.promotion_worker import promote_session, check_and_promote_eligible

router = APIRouter(prefix="/worker", tags=["worker"])


@router.post("/promote/{session_id}")
async def trigger_promote_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger promotion of a specific session.
    """
    result = await promote_session(session_id, db)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or already promoted"
        )
    return result


@router.post("/promote-all")
async def trigger_promote_all(
    db: AsyncSession = Depends(get_db)
):
    """
    Manually check and promote all eligible sessions.
    """
    return await check_and_promote_eligible(db)
