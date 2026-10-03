"""
Patient-level authorization.

Determines which patients each user is permitted to access.
This is deterministic Python code — no LLM is involved.

In production this would query a database. For this POC
we use a static mapping that can be easily extended.
"""
from __future__ import annotations
from app.auth.models import Role

# User → permitted patient IDs mapping
# In production: query the users/patient_assignments table
_PATIENT_ACCESS_MAP: dict[str, list[str]] = {
    "user-001": [f"P{1000+i}" for i in range(1, 201)],    # Dr. Sarah Smith  P1001-P1200
    "user-002": [f"P{1000+i}" for i in range(201, 401)],  # Dr. James Patel  P1201-P1400
    "user-003": [f"P{1000+i}" for i in range(401, 601)],  # Dr. Aisha Nkosi  P1401-P1600
    "user-004": ["*"],                                      # Mary Johnson     ALL patients
    "user-005": ["*"],   # Tom Williams — all patients (operations manages whole hospital)
    "admin-001": ["*"],                                     # Admin            ALL patients
}
def is_patient_authorized(user_id: str, patient_id: str,
                           role: str | None = None) -> bool:
    """
    Check if a user is permitted to access a specific patient.
    Pharmacists have access to all patients for medication/prescription data.
    """
    # Pharmacists can access any patient
    if role and role.upper() == Role.PHARMACIST.value:
        return True

    permitted = _PATIENT_ACCESS_MAP.get(user_id, [])

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