from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class AuditRecord:
    request_id:        str
    user_id:           str
    role:              str
    timestamp:         str
    request_text:      str
    patient_id:        str | None         # ← NEW
    detected_intent:   list[str]
    requested_agents:  list[str]
    authorized_agents: list[str]
    denied_agents:     list[str]
    executed_agents:   list[str]
    tools_called:      list[str]          # ← NEW
    status:            str

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "request_id":        self.request_id,
            "user_id":           self.user_id,
            "role":              self.role,
            "timestamp":         self.timestamp,
            "patient_id":        self.patient_id,
            "request":           self.request_text,
            "detected_intent":   self.detected_intent,
            "requested_agents":  self.requested_agents,
            "authorized_agents": self.authorized_agents,
            "denied_agents":     self.denied_agents,
            "executed_agents":   self.executed_agents,
            "tools_called":      self.tools_called,
            "status":            self.status,
        }