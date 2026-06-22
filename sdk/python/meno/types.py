"""
SDK type enums. Mirrors core/types.py. Import these to avoid magic strings.
"""
from enum import Enum


class KnowledgeType(str, Enum):
    MEMORY = "memory"
    CODE_PATTERN = "code_pattern"
    DECISION = "decision"
    API_SPEC = "api_spec"
    BUG_REPORT = "bug_report"
    REFACTORING = "refactoring"
    ARCHITECTURE = "architecture"


class RelationshipType(str, Enum):
    SUPERSEDES = "supersedes"
    IMPLEMENTS = "implements"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"
    CONTRADICTS = "contradicts"
    EXTENDS = "extends"
    IS_INSTANCE_OF = "is_instance_of"
    MENTIONED_IN = "mentioned_in"


class ContextType(str, Enum):
    PROJECT = "project"
    TEAM = "team"
    ORGANIZATION = "organization"
    CODEBASE = "codebase"
