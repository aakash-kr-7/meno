"""
Type-aware ranking. Different types age at different rates. Decisions half-life=180d, code_pattern=60d,
memory=7d. Formula: 0.5*sim + 0.2*recency + 0.15*confidence + 0.1*context_match + 0.05*access
"""

import math
from dataclasses import dataclass
from datetime import datetime
from core.types import KnowledgeType

HALF_LIVES = {
    KnowledgeType.DECISION.value: 180,
    KnowledgeType.CODE_PATTERN.value: 60,
    KnowledgeType.ARCHITECTURE.value: 180,
    KnowledgeType.API_SPEC.value: 90,
    KnowledgeType.BUG_REPORT.value: 30,
    KnowledgeType.REFACTORING.value: 60,
    KnowledgeType.MEMORY.value: 7
}


@dataclass
class RankInput:
    similarity: float
    knowledge_type: str
    created_at: datetime
    access_count: int
    confidence: float = 0.5
    in_query_context: bool = True


@dataclass
class RankResult:
    score: float
    breakdown: dict


def rank(r: RankInput, now: datetime = None) -> RankResult:
    # Resolve datetime offset naive vs aware mismatch if any
    if now is None:
        now = datetime.now(r.created_at.tzinfo)
    else:
        if r.created_at.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=r.created_at.tzinfo)
        elif r.created_at.tzinfo is None and now.tzinfo is not None:
            now = now.replace(tzinfo=None)

    age_days = (now - r.created_at).total_seconds() / 86400.0
    if age_days < 0:
        age_days = 0.0

    # Ensure knowledge_type is a string key
    k_type = r.knowledge_type
    if hasattr(k_type, "value"):
        k_type = k_type.value

    half_life = HALF_LIVES.get(k_type, 14)
    recency = math.exp(-0.693 * age_days / half_life)  # correct half-life formula
    access = min(r.access_count, 20) / 20.0
    context_match = 1.0 if r.in_query_context else 0.5

    score = (
        0.5 * r.similarity
        + 0.2 * recency
        + 0.15 * r.confidence
        + 0.1 * context_match
        + 0.05 * access
    )

    return RankResult(
        score=round(score, 4),
        breakdown={
            "similarity": r.similarity,
            "recency": recency,
            "confidence": r.confidence,
            "context_match": context_match,
            "access": access,
            "age_days": age_days,
            "half_life": half_life
        }
    )


def rank_many(inputs: list[RankInput], now: datetime = None) -> list[tuple[int, RankResult]]:
    """Returns sorted list of (original_index, RankResult) descending by score."""
    results = []
    for i, r in enumerate(inputs):
        res = rank(r, now)
        results.append((i, res))
    # Sort descending by score
    results.sort(key=lambda x: x[1].score, reverse=True)
    return results
