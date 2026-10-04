from __future__ import annotations
import time

from app.agents.base_agent import AgentResponse, SourceCitation
from app.agents.intent import classify_query_type
from app.llm.client import LLMUnavailableError, call_llm, llm_configured
from app.rag.pharmacy_retriever import PharmacyRetriever
from app.tools.clinical_tools import get_patient_info
from app.tools.pharmacy_tools import get_medications, get_prescriptions

AGENT_ID = "pharmacy"

SYSTEM_PROMPT = """You are the Pharmacy Agent inside MedOrch for XYZ Hospital.
You answer using ONLY the patient medication data or pharmacy documents provided.
Rules:
  - Give clear, natural answers in plain English.
  - Use proper markdown formatting:
    * Use ## for section headings
    * Always put each table row on its own separate line
    * Never compress a table onto one line
    * Use bullet points for simple lists
  - Never add citation markers like 【】, [], or footnotes.
  - Never say "based on the data provided" or "according to the records".
  - Just answer the question directly and naturally.
  - Never invent information not present in the provided data.

Correct table format:
## Medications
| Medication | Dose | Frequency | Status |
|------------|------|-----------|--------|
| Aspirin    | 75mg | Once daily| Active |"""


class PharmacyAgent:
    def __init__(self, retriever: PharmacyRetriever | None = None) -> None:
        self._retriever = retriever or PharmacyRetriever()

    def handle(self, query: str, top_k: int = 3,
               patient_id: str | None = None) -> AgentResponse:
        start = time.monotonic()
        query_type = classify_query_type(query)

        if patient_id and query_type == "patient_data":
            return self._handle_patient_query(query, patient_id, start)

        return self._handle_rag_query(query, top_k, start)

    def _handle_patient_query(self, query, patient_id, start):
        info_result = get_patient_info(patient_id)
        med_result = get_medications(patient_id)
        rx_result = get_prescriptions(patient_id)

        tools_called = [info_result.tool_name,
                        med_result.tool_name,
                        rx_result.tool_name]
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)

        context = self._format_patient_context(
            patient_id, info_result.data, med_result.data, rx_result.data)
        answer = self._synthesize_from_tools(query, context, patient_id)

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
                answer="No relevant pharmacy documents found.",
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

    def _format_patient_context(self, patient_id, patient_info,
                               medications, prescriptions):
        lines = []

        if patient_info:
            p = patient_info[0]
            lines.append("PATIENT INFORMATION:")
            lines.append(f"  Name:       {p['first_name']} {p['last_name']}")
            lines.append(f"  Patient ID: {p['patient_id']}")
            lines.append(f"  DOB:        {p['dob']}")
            lines.append(f"  Gender:     {p['gender']}")
            lines.append(f"  Blood Type: {p['blood_type']}")

        if medications:
            lines.append("\nCURRENT MEDICATIONS:")
            for m in medications:
                lines.append(
                    f"  - {m['medication_name']} {m['dose']} "
                    f"| Frequency: {m['frequency']} "
                    f"| Prescriber: {m['prescriber']} "
                    f"| Status: {m['status']}"
                )

        if prescriptions:
            lines.append("\nPRESCRIPTIONS:")
            for p in prescriptions:
                lines.append(
                    f"  - {p['drug_name']} {p['dose']} "
                    f"| Qty: {p['quantity']} "
                    f"| Prescribed: {p['prescribed_date']} "
                    f"| Status: {p['status']}"
                )

        return "\n".join(lines)

    def _synthesize_from_tools(self, query: str,
                            context: str, patient_id: str) -> str:
        if llm_configured():
            try:
                return call_llm(
                    SYSTEM_PROMPT,
                    f"Patient pharmacy data:\n{context}\n\n"
                    f"User question: {query}\n\n"
                    "Answer naturally. Use ## headings for sections. "
                    "Format tables with each row on a new line. "
                    "Do not compress tables onto one line.",
                    max_tokens=600,
                ).strip()
            except Exception as e:
                import logging
                logging.getLogger("medorch").error(f"LLM call failed: {e}")
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
                    f"Pharmacy reference documents:\n{context}\n\n"
                    f"User question: {query}\n\n"
                    "Answer using only the documents above, cite doc_ids.",
                    max_tokens=500,
                ).strip()
            except LLMUnavailableError:
                pass
        top = results[0]
        return (f"Based on '{top.document.title}' "
                f"({top.document.doc_id}):\n{top.document.content}")