"""
Operations tools — get_appointments and get_admission_status.
These are the ONLY data sources the Operations Agent can access.
"""
from __future__ import annotations
from app.tools.clinical_tools import ToolResult
from app.db.csv_service import get_patient, query_by_patient


def get_appointments(patient_id: str) -> ToolResult:
    """Retrieve appointments for a patient."""
    patient = get_patient(patient_id)
    if not patient:
        return ToolResult(
            success=False, data=[], tool_name="get_appointments",
            patient_id=patient_id,
            message=f"Patient {patient_id} not found."
        )
    rows = query_by_patient("appointments", patient_id)
    return ToolResult(
        success=True, data=rows, tool_name="get_appointments",
        patient_id=patient_id,
        message=f"Found {len(rows)} appointment(s) for {patient_id}."
    )


def get_admission_status(patient_id: str) -> ToolResult:
    """Retrieve admission records for a patient."""
    patient = get_patient(patient_id)
    if not patient:
        return ToolResult(
            success=False, data=[], tool_name="get_admission_status",
            patient_id=patient_id,
            message=f"Patient {patient_id} not found."
        )
    rows = query_by_patient("admissions", patient_id)
    active = [r for r in rows if r.get("status") == "Current"]
    return ToolResult(
        success=True, data=rows, tool_name="get_admission_status",
        patient_id=patient_id,
        message=f"Found {len(rows)} admission record(s). Currently admitted: {len(active)}."
    )