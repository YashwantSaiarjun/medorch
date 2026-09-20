"""
Agent A -- Clinical Knowledge Agent.

Owns its own system prompt and its own retriever (ClinicalRetriever, bound
to the clinical_kb namespace only). This agent is only ever constructed and
invoked by the orchestrator AFTER the policy engine has authorized the
"clinical" agent for the requesting role -- see app/graph/workflow.py.
"""
from __future__ import annotations

import time

from app.agents.base_agent import AgentResponse, SourceCitation
from app.llm.client import LLMUnavailableError, call_llm, llm_configured
from app.rag.clinical_retriever import ClinicalRetriever

AGENT_ID = "clinical"

SYSTEM_PROMPT = """You are Agent A, the Clinical Knowledge Agent inside MedOrch, a \
healthcare orchestration proof-of-concept. You answer ONLY using the synthetic clinical \
documents provided to you as context. All content is fictional/synthetic demo data, never \
real medical advice. Always:
  - Base your answer strictly on the provided synthetic documents.
  - Cite which synthetic document(s) you used.
  - If the provided documents don't cover the question, say so plainly.
  - Include a brief reminder that this is a synthetic demo, not clinical guidance, when \
appropriate.
Do not invent information beyond the provided synthetic documents."""


class ClinicalAgent:
    def __init__(self, retriever: ClinicalRetriever | None = None) -> None:
        self._retriever = retriever or ClinicalRetriever()

    def handle(self, query: str, top_k: int = 3) -> AgentResponse:
        start = time.monotonic()
        try:
            results = self._retriever.retrieve(query, top_k=top_k)
        except Exception as exc:  # retrieval failure path
            return AgentResponse(agent_id=AGENT_ID, answer="", error=f"Retrieval failure: {exc}")

        elapsed_ms = round((time.monotonic() - start) * 1000, 2)

        if not results:
            return AgentResponse(
                agent_id=AGENT_ID,
                answer="No relevant synthetic clinical documents were found for this request.",
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
                    f"Synthetic clinical documents:\n{context_block}\n\n"
                    f"User question: {query}\n\n"
                    "Answer using only the documents above, and cite doc_ids."
                )
                return call_llm(SYSTEM_PROMPT, user_prompt, max_tokens=500).strip()
            except LLMUnavailableError:
                pass

        # Deterministic fallback: template-based summarization, no LLM required.
        top = results[0]
        snippet = top.document.content
        return (
            f"[Synthetic demo answer -- not real clinical guidance]\n"
            f"Based on synthetic document '{top.document.title}' ({top.document.doc_id}):\n"
            f"{snippet}"
        )
