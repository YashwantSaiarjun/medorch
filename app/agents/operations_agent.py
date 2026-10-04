from __future__ import annotations
import time
from app.agents.base_agent import AgentResponse, SourceCitation
from app.llm.client import LLMUnavailableError, call_llm, llm_configured
from app.rag.operations_retriever import OperationsRetriever
from app.tools.operations_tools import get_appointments, get_admission_status
from app.tools.clinical_tools import get_patient_info
from app.agents.intent import classify_query_type

AGENT_ID = "operations"

SYSTEM_PROMPT = """You are the Operations Agent inside MedOrch for XYZ Hospital.
You answer using ONLY the patient operational data or reference documents provided.
Rules:
  - Give clear, natural answers in plain English.
  - Never add citation markers like 【】, [], or footnotes.
  - Never say "based on the data provided" or "according to the records".
  - Just answer the question directly and naturally.
  - Never invent information not present in the provided data."""


class OperationsAgent:
    def __init__(self, retriever: OperationsRetriever | None = None) -> None:
        self._retriever = retriever or OperationsRetriever()

    def handle(self, query: str, top_k: int = 3,
               patient_id: str | None = None) -> AgentResponse:
        start      = time.monotonic()
        query_type = classify_query_type(query)

        if patient_id and query_type == "patient_data":
            return self._handle_patient_query(query, patient_id, start)

        return self._handle_rag_query(query, top_k, start)

    def _handle_patient_query(self, query: str,
                               patient_id: str, start: float) -> AgentResponse:
        info_result = get_patient_info(patient_id)
        appt_result = get_appointments(patient_id)
        adm_result  = get_admission_status(patient_id)

        tools_called = [
            info_result.tool_name,
            appt_result.tool_name,
            adm_result.tool_name,
        ]
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)

        # No records found at all
        if (not info_result.success and
                not appt_result.data and
                not adm_result.data):
            return AgentResponse(
                agent_id=AGENT_ID,
                answer=f"Patient {patient_id} was not found in the system.",
                sources=[],
                retrieval_metadata={
                    "latency_ms":   elapsed_ms,
                    "tools_called": tools_called,
                    "patient_id":   patient_id,
                },
            )

        # Patient exists but no operations records
        if not appt_result.data and not adm_result.data:
            patient_name = ""
            if info_result.data:
                p = info_result.data[0]
                patient_name = f"{p['first_name']} {p['last_name']}"
            return AgentResponse(
                agent_id=AGENT_ID,
                answer=(
                    f"{patient_name} ({patient_id}) has no appointments "
                    f"or admission records on file."
                ),
                sources=[],
                retrieval_metadata={
                    "latency_ms":   elapsed_ms,
                    "tools_called": tools_called,
                    "patient_id":   patient_id,
                },
            )

        context = self._format_patient_context(
            patient_id,
            info_result.data,
            appt_result.data,
            adm_result.data,
        )
        answer = self._synthesize_from_tools(query, context, patient_id)

        return AgentResponse(
            agent_id=AGENT_ID,
            answer=answer,
            sources=[],
            retrieval_metadata={
                "latency_ms":   elapsed_ms,
                "tools_called": tools_called,
                "patient_id":   patient_id,
            },
        )

    def _handle_rag_query(self, query: str,
                           top_k: int, start: float) -> AgentResponse:
        try:
            results = self._retriever.retrieve(query, top_k=top_k)
        except Exception as exc:
            return AgentResponse(
                agent_id=AGENT_ID,
                answer="",
                error=f"Retrieval failure: {exc}"
            )

        elapsed_ms = round((time.monotonic() - start) * 1000, 2)

        if not results:
            return AgentResponse(
                agent_id=AGENT_ID,
                answer="No relevant operations documents found.",
                sources=[],
                retrieval_metadata={
                    "latency_ms":          elapsed_ms,
                    "documents_considered": 0,
                },
            )

        sources = [
            SourceCitation(
                doc_id=r.document.doc_id,
                title=r.document.title,
                score=round(r.score, 4)
            )
            for r in results
        ]
        answer = self._synthesize_from_rag(query, results)
        return AgentResponse(
            agent_id=AGENT_ID,
            answer=answer,
            sources=sources,
            retrieval_metadata={
                "latency_ms":          elapsed_ms,
                "documents_considered": len(results),
            },
        )

    def _format_patient_context(self, patient_id: str,
                                 patient_info: list,
                                 appointments: list,
                                 admissions: list) -> str:
        lines = []

        if patient_info:
            p = patient_info[0]
            lines.append("PATIENT INFORMATION:")
            lines.append(f"  Name:       {p['first_name']} {p['last_name']}")
            lines.append(f"  Patient ID: {p['patient_id']}")
            lines.append(f"  DOB:        {p['dob']}")
            lines.append(f"  Gender:     {p['gender']}")
            lines.append(f"  Blood Type: {p['blood_type']}")

        if appointments:
            lines.append("\nAPPOINTMENTS:")
            for a in appointments:
                lines.append(
                    f"  - {a['appointment_type']} with {a['provider']} "
                    f"| Date: {a['date']} {a['time']} "
                    f"| Status: {a['status']}"
                )
        else:
            lines.append("\nAPPOINTMENTS: None on record")

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
        else:
            lines.append("\nADMISSIONS: None on record")

        return "\n".join(lines)

    def _synthesize_from_tools(self, query: str,
                            context: str,
                            patient_id: str) -> str:
        if llm_configured():
            try:
                return call_llm(
                    SYSTEM_PROMPT,
                    f"Patient operations data:\n{context}\n\n"
                    f"User question: {query}\n\n"
                    "Answer naturally in plain English using proper markdown:\n"
                    "- Use ## for section headings\n"
                    "- Format tables with each row on its own line\n"
                    "- Never show raw data labels like 'PATIENT INFORMATION:'\n"
                    "- Start with a brief patient introduction\n"
                    "- Then show appointments and admissions in clean tables",
                    max_tokens=700
                ).strip()
            except Exception as e:
                print(f"DEBUG operations LLM error: {type(e).__name__}: {e}")

        print("DEBUG: falling back to template")
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
                    f"Operations reference documents:\n{context}\n\n"
                    f"User question: {query}\n\n"
                    "Answer using only the documents above.",
                    max_tokens=500
                ).strip()
            except LLMUnavailableError:
                pass
        top = results[0]
        return (
            f"Based on '{top.document.title}' "
            f"({top.document.doc_id}):\n{top.document.content}"
        )