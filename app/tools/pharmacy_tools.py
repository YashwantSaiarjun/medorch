"""
Pharmacy tools — get_medications and get_prescriptions.
These are the ONLY data sources the Pharmacy Agent can access.
"""
from __future__ import annotations
from app.tools.clinical_tools import ToolResult
from app.db.csv_service import get_patient, query_by_patient


def get_medications(patient_id: str) -> ToolResult:
    """Retrieve current medications for a patient."""
    patient = get_patient(patient_id)
    if not patient:
        return ToolResult(
            success=False, data=[], tool_name="get_medications",
            patient_id=patient_id,
            message=f"Patient {patient_id} not found."
        )
    rows = query_by_patient("medications", patient_id)
    return ToolResult(
        success=True, data=rows, tool_name="get_medications",
        patient_id=patient_id,
        message=f"Found {len(rows)} medication record(s) for {patient_id}."
    )


def get_prescriptions(patient_id: str) -> ToolResult:
    """Retrieve prescriptions for a patient."""
    patient = get_patient(patient_id)
    if not patient:
        return ToolResult(
            success=False, data=[], tool_name="get_prescriptions",
            patient_id=patient_id,
            message=f"Patient {patient_id} not found."
        )
    rows = query_by_patient("prescriptions", patient_id)
    return ToolResult(
        success=True, data=rows, tool_name="get_prescriptions",
        patient_id=patient_id,
        message=f"Found {len(rows)} prescription(s) for {patient_id}."
    )