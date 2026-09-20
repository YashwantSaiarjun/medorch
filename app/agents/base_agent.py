"""
Shared response contract for specialized agents.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceCitation:
    doc_id: str
    title: str
    score: float


@dataclass(frozen=True)
class AgentResponse:
    agent_id: str
    answer: str
    sources: list[SourceCitation] = field(default_factory=list)
    retrieval_metadata: dict = field(default_factory=dict)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None
