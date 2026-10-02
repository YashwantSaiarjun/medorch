from __future__ import annotations
import time
from app.agents.base_agent import AgentResponse, SourceCitation
from app.llm.client import LLMUnavailableError, call_llm, llm_configured
from app.rag.operations_retriever import OperationsRetriever
from app.tools.operations_tools import get_appointments, get_admission_status

AGENT_ID = "operations"

SYSTEM_PROMPT = """You are the Operations Agent inside MedOrch for XYZ Hospital.
You answer using ONLY the data provided — either patient operational records or
hospital operations reference documents. Always:
  - Base your answer strictly on the provided data.
  - If patient data is provided, focus your answer on that patient.
  - Cite your source (tool name or document ID).
  - Never invent appointment slots, admission decisions, or hospital policies."""


class OperationsAgent:
    def __init__(self, retriever: OperationsRetriever | None = None) -> None:
        self._retriever = retriever or OperationsRetriever()

    def handle(self, query: str, top_k: int = 3,
               patient_id: str | None = None) -> AgentResponse:
        start = time.monotonic()

        if patient_id:
            return self._handle_patient_query(query, patient_id, start)
        return self._handle_rag_query(query, top_k, start)

    def _handle_patient_query(self, query: str,
                               patient_id: str, start: float) -> AgentResponse:
        appt_result = get_appointments(patient_id)
        adm_result  = get_admission_status(patient_id)

        tools_called = [appt_result.tool_name, adm_result.tool_name]
        elapsed_ms   = round((time.monotonic() - start) * 1000, 2)

        if not appt_result.success and not adm_result.success:
            return AgentResponse(
                agent_id=AGENT_ID,
                answer=f"Patient {patient_id} not found in operations records.",
                sources=[],
                retrieval_metadata={"latency_ms": elapsed_ms,
                                    "tools_called": tools_called,
                                    "patient_id": patient_id},
            )

        context = self._format_patient_context(
            patient_id, appt_result.data, adm_result.data)
        answer  = self._synthesize_from_tools(query, context, patient_id)

        return AgentResponse(
            agent_id=AGENT_ID, answer=answer, sources=[],
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
                answer="No relevant operations documents found.",
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
                                 appointments: list, admissions: list) -> str:
        lines = [f"Patient ID: {patient_id}\n"]

        if appointments:
            lines.append("APPOINTMENTS:")
            for a in appointments:
                lines.append(
                    f"  - {a['appointment_type']} with {a['provider']} "
                    f"| Date: {a['date']} {a['time']} "
                    f"| Status: {a['status']}"
                )

        if admissions:
            lines.append("\nADMISSIONS:")
            for a in admissions:
                discharged = a['discharged_date'] or "Currently admitted"
                lines.append(
                    f"  - Ward: {a['ward']} "
                    f"| Reason: {a['reason']} "
                    f"| Admitted: {a['admitted_date']} "
                    f"| Discharged: {discharged} "
                    f"| Status: {a['status']}"
                )

        return "\n".join(lines)

    def _synthesize_from_tools(self, query: str,
                                context: str, patient_id: str) -> str:
        if llm_configured():
            try:
                return call_llm(
                    SYSTEM_PROMPT,
                    f"Patient operations data:\n{context}\n\n"
                    f"User question: {query}\n\n"
                    "Answer based on the patient data above.",
                    max_tokens=600
                ).strip()
            except LLMUnavailableError:
                pass
        return f"[Operations Data for {patient_id}]\n{context}"

    def _synthesize_from_rag(self, query: str, results) -> str:
        context = "\n\n".join(
            f"[{r.document.doc_id}] {r.document.title}\n{r.document.content}"
            for r in results
        )
        if llm_configured():
            try:
                return call_llm(
                    SYSTEM_PROMPT,
                    f"Operations reference documents:\n{context}\n\n"
                    f"User question: {query}\n\n"
                    "Answer using only the documents above, cite doc_ids.",
                    max_tokens=500
                ).strip()
            except LLMUnavailableError:
                pass
        top = results[0]
        return (f"Based on '{top.document.title}' "
                f"({top.document.doc_id}):\n{top.document.content}")