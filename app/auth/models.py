from __future__ import annotations
from enum import Enum

class Role(str, Enum):
    CLINICIAN        = "CLINICIAN"
    PHARMACIST       = "PHARMACIST"
    OPERATIONS_STAFF = "OPERATIONS_STAFF"

    @classmethod
    def values(cls) -> list[str]:
        return [r.value for r in cls]

class AgentId(str, Enum):
    CLINICAL   = "clinical"
    PHARMACY   = "pharmacy"
    OPERATIONS = "operations"

    @classmethod
    def values(cls) -> list[str]:
        return [a.value for a in cls]

class AuthDecision(str, Enum):
    ALLOWED = "ALLOWED"
    DENIED  = "DENIED"