"""
Patient-level authorization.

Determines which patients each user is permitted to access.
This is deterministic Python code — no LLM is involved.

In production this would query a database. For this POC
we use a static mapping that can be easily extended.
"""
from __future__ import annotations

# User → permitted patient IDs mapping
# In production: query the users/patient_assignments table
_PATIENT_ACCESS_MAP: dict[str, list[str]] = {
    "user-001": ["P1001", "P1002", "P1003", "P1004", "P1005"],
    "user-002": ["P1006", "P1007", "P1008", "P1009", "P1010"],
    "user-003": ["P1001", "P1011", "P1012", "P1013", "P1014"],
    "user-004": ["P1015", "P1016", "P1017", "P1018", "P1019"],
    "user-005": ["P1020", "P1021", "P1022", "P1023", "P1024"],
    # Admin users get access to all patients
    "admin-001": ["*"],
}


def is_patient_authorized(user_id: str, patient_id: str) -> bool:
    """
    Check if a user is permitted to access a specific patient.
    Returns True if authorized, False if denied.
    """
    permitted = _PATIENT_ACCESS_MAP.get(user_id, [])

    # "*" means access to all patients (admin only)
    if "*" in permitted:
        return True

    return patient_id in permitted


def get_permitted_patients(user_id: str) -> list[str]:
    """Return the list of patient IDs this user can access."""
    permitted = _PATIENT_ACCESS_MAP.get(user_id, [])
    if "*" in permitted:
        return ["ALL"]
    return permitted


def get_denial_message(user_id: str, patient_id: str) -> str:
    return (
        f"Access denied. You are not authorized to access "
        f"patient {patient_id}. Contact your administrator "
        f"if you believe this is an error."
    )