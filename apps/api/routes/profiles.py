"""
REST router for behavioral profiles. context_size controls how many related objects expand during retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from apps.api.dependencies import get_db
from apps.api.schemas import BehaviorProfileResponse, BehaviorProfilePatchRequest
from db.models.behavioral_profile import BehavioralProfile

router = APIRouter(prefix="/profile", tags=["profiles"])

@router.get("/{user_id}", response_model=BehaviorProfileResponse)
async def get_profile(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(BehavioralProfile).where(BehavioralProfile.user_id == user_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if profile is None:
        return BehaviorProfileResponse(
            user_id=user_id,
            profile_data={
                "preferred_language": None,
                "tone": None,
                "context_size": 10,
                "extra": {}
            }
        )

    return BehaviorProfileResponse(
        user_id=user_id,
        profile_data={
            "preferred_language": profile.preferred_language,
            "tone": profile.tone,
            "context_size": profile.context_size,
            "extra": profile.extra
        }
    )

@router.patch("/{user_id}", response_model=BehaviorProfileResponse)
async def update_profile(
    user_id: str,
    body: BehaviorProfilePatchRequest,
    db: AsyncSession = Depends(get_db)
):
    # Prepare insert/update mappings
    insert_values = {"user_id": user_id}
    update_values = {}

    if body.preferred_language is not None:
        insert_values["preferred_language"] = body.preferred_language
        update_values["preferred_language"] = body.preferred_language

    if body.tone is not None:
        insert_values["tone"] = body.tone
        update_values["tone"] = body.tone

    if body.context_size is not None:
        insert_values["context_size"] = body.context_size
        update_values["context_size"] = body.context_size

    if body.extra is not None:
        insert_values["extra"] = body.extra
        update_values["extra"] = body.extra

    stmt = insert(BehavioralProfile).values(**insert_values)
    if update_values:
        update_values["updated_at"] = text("now()")
        stmt = stmt.on_conflict_do_update(
            index_elements=[BehavioralProfile.user_id],
            set_=update_values
        )
    else:
        # If no updates, insert if new, do nothing if already exists
        stmt = stmt.on_conflict_do_nothing(index_elements=[BehavioralProfile.user_id])

    await db.execute(stmt)
    await db.commit()

    # Retrieve updated row to return
    stmt = select(BehavioralProfile).where(BehavioralProfile.user_id == user_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if profile is None:
        return BehaviorProfileResponse(
            user_id=user_id,
            profile_data={
                "preferred_language": body.preferred_language,
                "tone": body.tone,
                "context_size": body.context_size if body.context_size is not None else 10,
                "extra": body.extra if body.extra is not None else {}
            }
        )

    return BehaviorProfileResponse(
        user_id=user_id,
        profile_data={
            "preferred_language": profile.preferred_language,
            "tone": profile.tone,
            "context_size": profile.context_size,
            "extra": profile.extra
        }
    )
