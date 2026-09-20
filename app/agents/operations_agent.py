"""
Agent B -- Healthcare Operations Knowledge Agent.

Owns its own system prompt and its own retriever (OperationsRetriever,
bound to the operations_kb namespace only). Mirrors ClinicalAgent's
structure but is completely independent -- it cannot reach clinical_kb.
"""
from __future__ import annotations

import time

from app.agents.base_agent import AgentResponse, SourceCitation
from app.llm.client import LLMUnavailableError, call_llm, llm_configured
from app.rag.operations_retriever import OperationsRetriever

AGENT_ID = "operations"

SYSTEM_PROMPT = """You are Agent B, the Healthcare Operations Knowledge Agent inside \
MedOrch, a healthcare orchestration proof-of-concept. You answer ONLY using the synthetic \
operations documents provided to you as context (hospital workflows, admissions, \
scheduling, insurance, billing, administration). All content is fictional/synthetic demo \
data. Always:
  - Base your answer strictly on the provided synthetic documents.
  - Cite which synthetic document(s) you used.
  - If the provided documents don't cover the question, say so plainly.
Do not invent information beyond the provided synthetic documents. Do not answer clinical \
medical questions -- that is outside your domain."""


class OperationsAgent:
    def __init__(self, retriever: OperationsRetriever | None = None) -> None:
        self._retriever = retriever or OperationsRetriever()

    def handle(self, query: str, top_k: int = 3) -> AgentResponse:
        start = time.monotonic()
        try:
            results = self._retriever.retrieve(query, top_k=top_k)
        except Exception as exc:
            return AgentResponse(agent_id=AGENT_ID, answer="", error=f"Retrieval failure: {exc}")

        elapsed_ms = round((time.monotonic() - start) * 1000, 2)

        if not results:
            return AgentResponse(
                agent_id=AGENT_ID,
                answer="No relevant synthetic operations documents were found for this request.",
                sources=[],
                retrieval_metadata={"latency_ms": elapsed_ms, "documents_considered": 0},
            )

        sources = [
            SourceCitation(doc_id=r.document.doc_id, title=r.document.title, score=round(r.score, 4))
            for r in results
        ]
        answer = self._synthesize_answer(query, results)

        return AgentResponse(
            agent_id=AGENT_ID,
            answer=answer,
            sources=sources,
            retrieval_metadata={"latency_ms": elapsed_ms, "documents_considered": len(results)},
        )

    def _synthesize_answer(self, query: str, results) -> str:
        context_block = "\n\n".join(f"[{r.document.doc_id}] {r.document.title}\n{r.document.content}" for r in results)

        if llm_configured():
            try:
                user_prompt = (
                    f"Synthetic operations documents:\n{context_block}\n\n"
                    f"User question: {query}\n\n"
                    "Answer using only the documents above, and cite doc_ids."
                )
                return call_llm(SYSTEM_PROMPT, user_prompt, max_tokens=500).strip()
            except LLMUnavailableError:
                pass

        top = results[0]
        snippet = top.document.content
        return (
            f"[Synthetic demo answer]\n"
            f"Based on synthetic document '{top.document.title}' ({top.document.doc_id}):\n"
            f"{snippet}"
        )
