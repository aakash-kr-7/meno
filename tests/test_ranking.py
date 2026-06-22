"""
Unit tests for type-aware ranking. No DB or network required.
"""

from datetime import datetime, timedelta
from core.ranking import rank, rank_many, RankInput
from core.types import KnowledgeType


def test_decision_ages_slower_than_memory() -> None:
    """Both at 30d old, same similarity 0.8. Assert decision.score > memory.score."""
    now = datetime.utcnow()
    created_at = now - timedelta(days=30)

    decision_input = RankInput(
        similarity=0.8,
        knowledge_type=KnowledgeType.DECISION.value,
        created_at=created_at,
        access_count=0,
        confidence=0.5,
        in_query_context=True
    )

    memory_input = RankInput(
        similarity=0.8,
        knowledge_type=KnowledgeType.MEMORY.value,
        created_at=created_at,
        access_count=0,
        confidence=0.5,
        in_query_context=True
    )

    decision_res = rank(decision_input, now=now)
    memory_res = rank(memory_input, now=now)

    assert decision_res.score > memory_res.score


def test_context_penalty() -> None:
    """Same object in_query_context True vs False. Assert in > out."""
    now = datetime.utcnow()
    created_at = now - timedelta(days=2)

    in_context_input = RankInput(
        similarity=0.8,
        knowledge_type=KnowledgeType.DECISION.value,
        created_at=created_at,
        access_count=5,
        confidence=0.7,
        in_query_context=True
    )

    out_context_input = RankInput(
        similarity=0.8,
        knowledge_type=KnowledgeType.DECISION.value,
        created_at=created_at,
        access_count=5,
        confidence=0.7,
        in_query_context=False
    )

    in_res = rank(in_context_input, now=now)
    out_res = rank(out_context_input, now=now)

    assert in_res.score > out_res.score


def test_score_range() -> None:
    """All scores in [0,1]."""
    now = datetime.utcnow()
    inputs = [
        RankInput(
            similarity=1.0,
            knowledge_type=KnowledgeType.DECISION.value,
            created_at=now,
            access_count=100,
            confidence=1.0,
            in_query_context=True
        ),
        RankInput(
            similarity=0.0,
            knowledge_type=KnowledgeType.MEMORY.value,
            created_at=now - timedelta(days=365),
            access_count=0,
            confidence=0.0,
            in_query_context=False
        )
    ]
    for r in inputs:
        res = rank(r, now=now)
        assert 0.0 <= res.score <= 1.0


def test_rank_many_sorted() -> None:
    """3 inputs, assert output is descending."""
    now = datetime.utcnow()
    inputs = [
        RankInput(
            similarity=0.3,
            knowledge_type=KnowledgeType.MEMORY.value,
            created_at=now - timedelta(days=5),
            access_count=1,
            confidence=0.3,
            in_query_context=False
        ),
        RankInput(
            similarity=0.9,
            knowledge_type=KnowledgeType.DECISION.value,
            created_at=now,
            access_count=10,
            confidence=0.9,
            in_query_context=True
        ),
        RankInput(
            similarity=0.6,
            knowledge_type=KnowledgeType.CODE_PATTERN.value,
            created_at=now - timedelta(days=2),
            access_count=5,
            confidence=0.6,
            in_query_context=True
        )
    ]

    ranked = rank_many(inputs, now=now)
    assert len(ranked) == 3
    # Check descending order by score
    assert ranked[0][1].score >= ranked[1][1].score
    assert ranked[1][1].score >= ranked[2][1].score
