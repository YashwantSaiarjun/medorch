"""
MedOrch Streamlit UI.

A simple, professional chat UI that talks to the MedOrch FastAPI backend
over HTTP. It shows the full decision trail for every request: detected
domain(s), authorization decision, agent(s) executed, the answer, and
sources -- so the security boundary is visible, not just the answer.

Run with:
    streamlit run ui/streamlit_app.py

Configure the backend URL via the MEDORCH_API_URL environment variable
(defaults to http://localhost:8000).
"""
from __future__ import annotations
import os, uuid
import requests
import streamlit as st

API_URL = os.getenv("MEDORCH_API_URL", "http://localhost:8000")

st.set_page_config(page_title="MedOrch — XYZ Hospital", page_icon="🏥", layout="centered")
st.title("MedOrch — XYZ Hospital AI")
st.caption("Secure multi-agent healthcare platform. Reference use only.")

if "user_id" not in st.session_state:
    st.session_state.user_id = f"user-{uuid.uuid4().hex[:8]}"
if "role" not in st.session_state:
    st.session_state.role = None
if "patient_id" not in st.session_state:
    st.session_state.patient_id = None
if "history" not in st.session_state:
    st.session_state.history = []

_ROLE_OPTIONS = ["Clinician", "Pharmacist", "Operations Staff"]
_ROLE_VALUES  = ["CLINICIAN", "PHARMACIST", "OPERATIONS_STAFF"]

# Load patient IDs for dropdown
@st.cache_data
def load_patient_ids():
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from app.db.csv_service import get_all_patient_ids
        return get_all_patient_ids()
    except Exception:
        return [f"P{1000+i}" for i in range(1, 2001)]

patient_ids = load_patient_ids()

with st.sidebar:
    st.subheader("Session")
    st.text(f"User: {st.session_state.user_id}")

    st.divider()

    # Role selector
    current_idx = _ROLE_VALUES.index(st.session_state.role) \
                  if st.session_state.role in _ROLE_VALUES else 0
    role_choice = st.radio("Select your role", _ROLE_OPTIONS, index=current_idx)
    st.session_state.role = _ROLE_VALUES[_ROLE_OPTIONS.index(role_choice)]

    st.divider()

    # Patient ID dropdown
    st.subheader("Patient")
    patient_choice = st.selectbox(
        "Select Patient ID",
        options=["-- Select a patient --"] + patient_ids,
        index=0
    )
    if patient_choice != "-- Select a patient --":
        st.session_state.patient_id = patient_choice

    st.divider()
    st.markdown("**Access**")
    st.markdown(
        "- **Clinician** → diagnoses, lab results\n"
        "- **Pharmacist** → medications, prescriptions\n"
        "- **Operations** → appointments, admissions"
    )

    if st.button("Clear chat"):
        st.session_state.history = []
        st.rerun()

st.divider()

# Show selected patient prominently
if st.session_state.patient_id:
    st.info(f"📋 Active patient: **{st.session_state.patient_id}** | Role: **{st.session_state.role}**")
else:
    st.warning("Please select a patient from the sidebar to begin.")

# Chat history
for turn in st.session_state.history:
    with st.chat_message("user"):
        st.write(turn["request"])
    with st.chat_message("assistant"):
        st.markdown(f"**Detected Domain(s):** {', '.join(turn['agents_considered']) or 'none'}")
        auth_line = f"**Authorization:** {turn['status']}"
        if turn["denied_agents"]:
            auth_line += f" — denied: {', '.join(turn['denied_agents'])}"
        st.markdown(auth_line)
        if turn.get("tools_called"):
            st.markdown(f"**Tools called:** {', '.join(turn['tools_called'])}")
        st.markdown(f"**Agents executed:** {', '.join(turn['executed_agents']) or 'none'}")

        if turn["status"] in ("DENIED", "NEEDS_ROLE"):
            st.error(turn["final_response"])
        else:
            st.markdown("**Answer:**")
            st.write(turn["final_response"])

        if turn["citations"]:
            with st.expander("Sources"):
                for c in turn["citations"]:
                    st.markdown(f"- `[{c['agent']}]` **{c['title']}** ({c['doc_id']}) — {c['score']:.3f}")

# Chat input
message = st.chat_input("Ask about the selected patient...")

if message:
    if not st.session_state.patient_id:
        st.error("Please select a patient first.")
        st.stop()

    with st.chat_message("user"):
        st.write(message)

    payload = {
        "user_id":    st.session_state.user_id,
        "role":       st.session_state.role,
        "patient_id": st.session_state.patient_id,
        "message":    message,
    }

    try:
        resp = requests.post(f"{API_URL}/chat", json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        st.error(f"API error: {exc}")
        st.stop()

    st.session_state.history.append({
        "request":          message,
        "agents_considered":data.get("agents_considered", []),
        "status":           data.get("status"),
        "denied_agents":    data.get("denied_agents", []),
        "executed_agents":  data.get("executed_agents", []),
        "tools_called":     data.get("tools_called", []),
        "final_response":   data.get("final_response", ""),
        "citations":        data.get("citations", []),
    })
    st.rerun()