from __future__ import annotations
import time
from app.agents.base_agent import AgentResponse, SourceCitation
from app.llm.client import LLMUnavailableError, call_llm, llm_configured
from app.rag.pharmacy_retriever import PharmacyRetriever

AGENT_ID = "pharmacy"

SYSTEM_PROMPT = """You are the Pharmacy Agent inside MedOrch. Answer ONLY using the
pharmacy documents provided. Your domain covers medication safety, medication-use
processes, medication reconciliation, high-risk medications, and transitions of care.
- Base answers strictly on provided documents.
- Cite document IDs used.
- Do not prescribe or recommend medication for specific patients.
- State clearly if the knowledge base does not cover the question."""

class PharmacyAgent:
    def __init__(self, retriever: PharmacyRetriever | None = None) -> None:
        self._retriever = retriever or PharmacyRetriever()

    def handle(self, query: str, top_k: int = 3) -> AgentResponse:
        start = time.monotonic()
        try:
            results = self._retriever.retrieve(query, top_k=top_k)
        except Exception as exc:
            return AgentResponse(agent_id=AGENT_ID, answer="", error=f"Retrieval failure: {exc}")
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        if not results:
            return AgentResponse(agent_id=AGENT_ID,
                answer="No relevant pharmacy documents found.",
                sources=[], retrieval_metadata={"latency_ms": elapsed_ms, "documents_considered": 0})
        sources = [SourceCitation(doc_id=r.document.doc_id, title=r.document.title,
                                  score=round(r.score, 4)) for r in results]
        return AgentResponse(agent_id=AGENT_ID, answer=self._synthesize(query, results),
            sources=sources, retrieval_metadata={"latency_ms": elapsed_ms, "documents_considered": len(results)})

    def _synthesize(self, query: str, results) -> str:
        context = "\n\n".join(f"[{r.document.doc_id}] {r.document.title}\n{r.document.content}"
                              for r in results)
        if llm_configured():
            try:
                return call_llm(SYSTEM_PROMPT,
                    f"Pharmacy documents:\n{context}\n\nUser question: {query}\n\n"
                    "Answer using only the documents above, cite doc_ids.",
                    max_tokens=500).strip()
            except LLMUnavailableError:
                pass
        top = results[0]
        return f"[Pharmacy Agent]\nBased on '{top.document.title}' ({top.document.doc_id}):\n{top.document.content}"