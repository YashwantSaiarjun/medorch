"""
Core RBAC data models.

These are plain, deterministic Python types. Nothing in this module ever
calls an LLM -- roles and agent identifiers are fixed, closed enumerations
so that authorization decisions are fully deterministic and testable.
"""
from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    CLINICIAN = "CLINICIAN"
    OPERATIONS = "OPERATIONS"
    ADMIN = "ADMIN"
    RESTRICTED = "RESTRICTED"

    @classmethod
    def values(cls) -> list[str]:
        return [r.value for r in cls]


class AgentId(str, Enum):
    CLINICAL = "clinical"
    OPERATIONS = "operations"

    @classmethod
    def values(cls) -> list[str]:
        return [a.value for a in cls]


class AuthDecision(str, Enum):
    ALLOWED = "ALLOWED"
    DENIED = "DENIED"
