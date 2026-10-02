from __future__ import annotations
import time
from app.agents.base_agent import AgentResponse, SourceCitation
from app.llm.client import LLMUnavailableError, call_llm, llm_configured
from app.rag.clinical_retriever import ClinicalRetriever
from app.tools.clinical_tools import get_diagnoses, get_lab_results

AGENT_ID = "clinical"

SYSTEM_PROMPT = """You are the Clinical Agent inside MedOrch for XYZ Hospital.
You answer using ONLY the data provided to you — either patient records or
clinical reference documents. Always:
  - Base your answer strictly on the provided data.
  - If patient data is provided, focus your answer on that patient.
  - Cite which source you used (tool name or document ID).
  - Never invent diagnoses, treatments, or clinical recommendations.
  - State clearly if the data does not cover the question."""


class ClinicalAgent:
    def __init__(self, retriever: ClinicalRetriever | None = None) -> None:
        self._retriever = retriever or ClinicalRetriever()

    def handle(self, query: str, top_k: int = 3,
               patient_id: str | None = None) -> AgentResponse:
        start = time.monotonic()

        # ── PATH 1: Patient-specific → use tools ──────────────────────────
        if patient_id:
            return self._handle_patient_query(query, patient_id, start)

        # ── PATH 2: General question → use RAG ────────────────────────────
        return self._handle_rag_query(query, top_k, start)

    def _handle_patient_query(self, query: str,
                               patient_id: str, start: float) -> AgentResponse:
        dx_result  = get_diagnoses(patient_id)
        lab_result = get_lab_results(patient_id)

        tools_called = [dx_result.tool_name, lab_result.tool_name]
        elapsed_ms   = round((time.monotonic() - start) * 1000, 2)

        if not dx_result.success and not lab_result.success:
            return AgentResponse(
                agent_id=AGENT_ID,
                answer=f"Patient {patient_id} not found in clinical records.",
                sources=[],
                retrieval_metadata={"latency_ms": elapsed_ms,
                                    "tools_called": tools_called,
                                    "patient_id": patient_id},
            )

        context = self._format_patient_context(
            patient_id, dx_result.data, lab_result.data)
        answer  = self._synthesize_from_tools(query, context, patient_id)

        return AgentResponse(
            agent_id=AGENT_ID,
            answer=answer,
            sources=[],
            retrieval_metadata={"latency_ms": elapsed_ms,
                                "tools_called": tools_called,
                                "patient_id": patient_id},
        )

    def _handle_rag_query(self, query: str,
                           top_k: int, start: float) -> AgentResponse:
        try:
            results = self._retriever.retrieve(query, top_k=top_k)
        except Exception as exc:
            return AgentResponse(agent_id=AGENT_ID, answer="",
                                 error=f"Retrieval failure: {exc}")

        elapsed_ms = round((time.monotonic() - start) * 1000, 2)

        if not results:
            return AgentResponse(
                agent_id=AGENT_ID,
                answer="No relevant clinical documents found.",
                sources=[],
                retrieval_metadata={"latency_ms": elapsed_ms,
                                    "documents_considered": 0},
            )

        sources = [
            SourceCitation(doc_id=r.document.doc_id,
                           title=r.document.title,
                           score=round(r.score, 4))
            for r in results
        ]
        answer = self._synthesize_from_rag(query, results)
        return AgentResponse(
            agent_id=AGENT_ID, answer=answer, sources=sources,
            retrieval_metadata={"latency_ms": elapsed_ms,
                                "documents_considered": len(results)},
        )

    def _format_patient_context(self, patient_id: str,
                                 diagnoses: list, labs: list) -> str:
        lines = [f"Patient ID: {patient_id}\n"]

        if diagnoses:
            lines.append("DIAGNOSES:")
            for d in diagnoses:
                lines.append(
                    f"  - {d['description']} (ICD: {d['icd_code']}) "
                    f"| Date: {d['diagnosed_date']} "
                    f"| Clinician: {d['clinician']} "
                    f"| Status: {d['status']}"
                )

        if labs:
            lines.append("\nLAB RESULTS:")
            for l in labs:
                lines.append(
                    f"  - {l['test_name']}: {l['result']} {l['unit']} "
                    f"(Normal: {l['normal_range']}) "
                    f"| Status: {l['status']} "
                    f"| Date: {l['date']}"
                )

        return "\n".join(lines)

    def _synthesize_from_tools(self, query: str,
                                context: str, patient_id: str) -> str:
        if llm_configured():
            try:
                return call_llm(
                    SYSTEM_PROMPT,
                    f"Patient clinical data:\n{context}\n\n"
                    f"User question: {query}\n\n"
                    "Answer based on the patient data above.",
                    max_tokens=600
                ).strip()
            except LLMUnavailableError:
                pass
        return f"[Clinical Data for {patient_id}]\n{context}"

    def _synthesize_from_rag(self, query: str, results) -> str:
        context = "\n\n".join(
            f"[{r.document.doc_id}] {r.document.title}\n{r.document.content}"
            for r in results
        )
        if llm_configured():
            try:
                return call_llm(
                    SYSTEM_PROMPT,
                    f"Clinical reference documents:\n{context}\n\n"
                    f"User question: {query}\n\n"
                    "Answer using only the documents above, cite doc_ids.",
                    max_tokens=500
                ).strip()
            except LLMUnavailableError:
                pass
        top = results[0]
        return (f"Based on '{top.document.title}' "
                f"({top.document.doc_id}):\n{top.document.content}")