"""
Audit service.

Records one AuditRecord per request: the detected intent, the
authorization decision, and the execution result. This module never logs
full document contents or PHI-equivalent synthetic patient identifiers --
only the request text (already user-supplied), routing metadata, and
outcome flags, per the spec's "do not log sensitive information
unnecessarily" requirement.

Storage: an in-memory store (thread-safe dict) backing GET /audit/{id}
for the lifetime of the process, plus a structured JSON-lines log file on
disk (audit.log) as a durable, appendable audit trail. In the
docker-compose deployment this file can be shipped to any log
aggregator; a Postgres-backed audit table can be swapped in the same way
the vector store is (see app/rag/vector_store.py) without changing any
caller.
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from app.audit.models import AuditRecord

_logger = logging.getLogger("medorch.audit")

_LOG_PATH = Path(__file__).resolve().parents[2] / "audit.log"


class AuditService:
    def __init__(self, log_path: Path | None = None) -> None:
        self._records: dict[str, AuditRecord] = {}
        self._lock = threading.Lock()
        self._log_path = log_path or _LOG_PATH

    def record(self, audit_record: AuditRecord) -> None:
        with self._lock:
            self._records[audit_record.request_id] = audit_record
        _logger.info(
            "audit_event",
            extra={"audit": audit_record.to_dict()},
        )
        try:
            with open(self._log_path, "a") as f:
                f.write(json.dumps(audit_record.to_dict()) + "\n")
        except OSError:
            # Never let audit persistence failures break the request path;
            # the in-memory record and structured log line above still exist.
            _logger.warning("Failed to write audit log to disk", exc_info=True)

    def get(self, request_id: str) -> AuditRecord | None:
        with self._lock:
            return self._records.get(request_id)

    def all(self) -> list[AuditRecord]:
        with self._lock:
            return list(self._records.values())


_singleton: AuditService | None = None


def get_audit_service() -> AuditService:
    global _singleton
    if _singleton is None:
        _singleton = AuditService()
    return _singleton


def reset_audit_service_for_tests() -> None:
    global _singleton
    _singleton = AuditService(log_path=Path("/tmp/medorch_test_audit.log"))
