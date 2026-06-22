"""
Knowledge extraction engine. Mode 1: LLM (LLM_EXTRACTION_ENABLED=true). Mode 2: rule-based
(default, zero external API keys needed). Rule-based is sufficient for V1.
"""

import json
import logging
from dataclasses import dataclass
import httpx
from core.config import settings
from core.types import KnowledgeType, RelationshipType

logger = logging.getLogger(__name__)

RULE_PATTERNS = {
    KnowledgeType.DECISION.value: ["decided", "we chose", "we will use", "we agreed", "decision:"],
    KnowledgeType.CODE_PATTERN.value: ["pattern", "implementation", "we use", "we implemented", "approach"],
    KnowledgeType.BUG_REPORT.value: ["bug", "fixed", "crash", "error", "fails", "broken"],
    KnowledgeType.REFACTORING.value: ["refactor", "cleanup", "simplified", "improved", "rewrote"],
    KnowledgeType.ARCHITECTURE.value: ["architecture", "system design", "service", "component", "microservice"],
    KnowledgeType.API_SPEC.value: ["api", "endpoint", "interface", "contract", "schema"]
}


@dataclass
class ExtractionResult:
    type: str
    title: str
    content: str
    confidence: float
    tags: list[str]


async def extract_from_messages(messages: list[dict]) -> list[ExtractionResult]:
    """Branch on settings.llm_extraction_enabled + settings.llm_api_key."""
    if settings.LLM_EXTRACTION_ENABLED and settings.LLM_API_KEY:
        return await _llm_extract(messages)
    return await _rule_based_extract(messages)


async def _rule_based_extract(messages: list[dict]) -> list[ExtractionResult]:
    """Per-message keyword scan. Default MEMORY for content >20 chars with no match. De-duplicate."""
    results = []
    seen = set()

    for msg in messages:
        content = msg.get("content") or msg.get("text") or ""
        if not isinstance(content, str):
            continue

        content_stripped = content.strip()
        if not content_stripped:
            continue

        if content_stripped in seen:
            continue

        content_lower = content_stripped.lower()
        matched_type = None

        # Keyword match
        for k_type, patterns in RULE_PATTERNS.items():
            for pattern in patterns:
                if pattern in content_lower:
                    matched_type = k_type
                    break
            if matched_type:
                break

        if matched_type:
            seen.add(content_stripped)
            # Create a simple title
            words = content_stripped.split()
            title = " ".join(words[:5])
            if len(content_stripped) > 30:
                title = f"{title}..."
            results.append(ExtractionResult(
                type=matched_type,
                title=title,
                content=content_stripped,
                confidence=0.8,
                tags=[matched_type]
            ))
        elif len(content_stripped) > 20:
            seen.add(content_stripped)
            words = content_stripped.split()
            title = " ".join(words[:5])
            if len(content_stripped) > 30:
                title = f"{title}..."
            results.append(ExtractionResult(
                type=KnowledgeType.MEMORY.value,
                title=title,
                content=content_stripped,
                confidence=0.5,
                tags=[KnowledgeType.MEMORY.value]
            ))

    return results


async def _llm_extract(messages: list[dict]) -> list[ExtractionResult]:
    """OpenAI-compatible /v1/chat/completions. Prompt: return ONLY JSON array with keys

    type/title/content/confidence/tags. Parse; fallback to rule-based on error.
    """
    base_url = getattr(settings, "LLM_BASE_URL", "https://api.openai.com/v1")
    url = f"{base_url.rstrip('/')}/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json"
    }

    # Format the input messages list as a JSON string to pass in user prompt
    formatted_messages = json.dumps(messages, indent=2)

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a knowledge extraction engine. Extract key knowledge items from the provided "
                    "conversation messages. Return ONLY a valid JSON array of objects with the keys: "
                    "'type', 'title', 'content', 'confidence', 'tags'.\n"
                    "The 'type' MUST be one of: 'memory', 'code_pattern', 'decision', 'api_spec', "
                    "'bug_report', 'refactoring', 'architecture'.\n"
                    "Do not include any introductory or concluding text, no markdown formatting, "
                    "no triple backticks. Just return the raw JSON array."
                )
            },
            {
                "role": "user",
                "content": formatted_messages
            }
        ],
        "temperature": 0.0
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Strip markdown block wrappers if model outputted them
            if content.startswith("```"):
                lines = content.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()

            parsed = json.loads(content)
            results = []
            for item in parsed:
                results.append(ExtractionResult(
                    type=item.get("type", KnowledgeType.MEMORY.value),
                    title=item.get("title", ""),
                    content=item.get("content", ""),
                    confidence=float(item.get("confidence", 0.8)),
                    tags=item.get("tags", [])
                ))
            return results
    except Exception as e:
        logger.error(f"LLM extraction failed, falling back to rule-based: {e}")
        return await _rule_based_extract(messages)


async def infer_relationship(obj1: ExtractionResult, obj2: ExtractionResult) -> dict | None:
    """Infer relationship between two extraction results.

    DECISION + CODE_PATTERN => IMPLEMENTS, confidence 0.7
    Both ARCHITECTURE => RELATED_TO, confidence 0.6
    BUG_REPORT + CODE_PATTERN => RELATED_TO, confidence 0.6
    Otherwise: None
    """
    t1 = obj1.type
    t2 = obj2.type

    if {t1, t2} == {KnowledgeType.DECISION.value, KnowledgeType.CODE_PATTERN.value}:
        return {
            "type": RelationshipType.IMPLEMENTS.value,
            "confidence": 0.7
        }

    if t1 == KnowledgeType.ARCHITECTURE.value and t2 == KnowledgeType.ARCHITECTURE.value:
        return {
            "type": RelationshipType.RELATED_TO.value,
            "confidence": 0.6
        }

    if {t1, t2} == {KnowledgeType.BUG_REPORT.value, KnowledgeType.CODE_PATTERN.value}:
        return {
            "type": RelationshipType.RELATED_TO.value,
            "confidence": 0.6
        }

    return None
