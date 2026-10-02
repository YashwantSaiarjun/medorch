"""
Clinical tools — get_diagnoses and get_lab_results.
These are the ONLY data sources the Clinical Agent can access.
"""
from __future__ import annotations
from dataclasses import dataclass
from app.db.csv_service import get_patient, query_by_patient


@dataclass
class ToolResult:
    success: bool
    data: list[dict]
    message: str
    tool_name: str
    patient_id: str


def get_diagnoses(patient_id: str) -> ToolResult:
    """Retrieve diagnoses for a patient."""
    patient = get_patient(patient_id)
    if not patient:
        return ToolResult(
            success=False, data=[], tool_name="get_diagnoses",
            patient_id=patient_id,
            message=f"Patient {patient_id} not found."
        )
    rows = query_by_patient("diagnoses", patient_id)
    return ToolResult(
        success=True, data=rows, tool_name="get_diagnoses",
        patient_id=patient_id,
        message=f"Found {len(rows)} diagnosis record(s) for {patient_id}."
    )


def get_lab_results(patient_id: str) -> ToolResult:
    """Retrieve lab results for a patient."""
    patient = get_patient(patient_id)
    if not patient:
        return ToolResult(
            success=False, data=[], tool_name="get_lab_results",
            patient_id=patient_id,
            message=f"Patient {patient_id} not found."
        )
    rows = query_by_patient("lab_results", patient_id)
    return ToolResult(
        success=True, data=rows, tool_name="get_lab_results",
        patient_id=patient_id,
        message=f"Found {len(rows)} lab result(s) for {patient_id}."
    )