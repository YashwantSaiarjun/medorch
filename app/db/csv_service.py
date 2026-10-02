"""
CSV data service for XYZ Hospital patient data.

This is the ONLY module that reads patient CSV files.
Agents never access CSVs directly — they go through tools,
which go through this service.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "patients"


def _read_csv(filename: str) -> list[dict]:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def _load_all() -> dict[str, list[dict]]:
    """Load all CSVs once into memory at startup."""
    return {
        "patients":      _read_csv("patients.csv"),
        "diagnoses":     _read_csv("diagnoses.csv"),
        "lab_results":   _read_csv("lab_results.csv"),
        "medications":   _read_csv("medications.csv"),
        "prescriptions": _read_csv("prescriptions.csv"),
        "appointments":  _read_csv("appointments.csv"),
        "admissions":    _read_csv("admissions.csv"),
    }


def get_patient(patient_id: str) -> dict | None:
    """Check patient exists."""
    data = _load_all()
    matches = [r for r in data["patients"] if r["patient_id"] == patient_id]
    return matches[0] if matches else None


def query_by_patient(table: str, patient_id: str) -> list[dict]:
    """Return all rows for a patient from a specific table."""
    data = _load_all()
    if table not in data:
        raise ValueError(f"Unknown table: {table}")
    return [r for r in data[table] if r["patient_id"] == patient_id]


def get_all_patient_ids() -> list[str]:
    """Return all patient IDs for the UI dropdown."""
    data = _load_all()
    return sorted({r["patient_id"] for r in data["patients"]})