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

import os
import uuid

import requests
import streamlit as st

API_URL = os.getenv("MEDORCH_API_URL", "http://localhost:8000")

st.set_page_config(page_title="MedOrch", page_icon="🏥", layout="centered")

st.title("MedOrch — Secure Multi-Agent Healthcare AI")
st.caption(
    "Proof-of-concept using **synthetic data only**. Not intended for clinical "
    "decision-making or real patient care."
)

if "user_id" not in st.session_state:
    st.session_state.user_id = f"user-{uuid.uuid4().hex[:8]}"
if "role" not in st.session_state:
    st.session_state.role = None
if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.subheader("Session")
    st.text(f"User ID: {st.session_state.user_id}")

    role_choice = st.radio(
        "Select your role",
        options=["Clinician", "Operations", "Admin", "Restricted"],
        index=None if st.session_state.role is None else
        ["CLINICIAN", "OPERATIONS", "ADMIN", "RESTRICTED"].index(st.session_state.role),
    )
    if role_choice:
        st.session_state.role = role_choice.upper()

    st.divider()
    st.markdown("**Access matrix (demo)**")
    st.markdown(
        "- **Clinician** → Agent A only\n"
        "- **Operations** → Agent B only\n"
        "- **Admin** → Agent A + Agent B\n"
        "- **Restricted** → no access"
    )

    st.divider()
    if st.button("Clear conversation"):
        st.session_state.history = []
        st.rerun()

st.divider()

for turn in st.session_state.history:
    with st.chat_message("user"):
        st.write(turn["request"])
    with st.chat_message("assistant"):
        st.markdown(f"**Detected Domain(s):** {', '.join(turn['agents_considered']) or 'none'}")
        auth_line = f"**Authorization Decision:** {turn['status']}"
        if turn["denied_agents"]:
            auth_line += f" (denied: {', '.join(turn['denied_agents'])})"
        st.markdown(auth_line)
        st.markdown(f"**Agent(s) Executed:** {', '.join(turn['executed_agents']) or 'none'}")

        if turn["status"] == "DENIED":
            st.error(turn["final_response"])
        elif turn["status"] == "NEEDS_ROLE":
            st.warning(turn["final_response"])
        else:
            st.markdown("**Answer:**")
            st.write(turn["final_response"])

        if turn["citations"]:
            with st.expander("Sources"):
                for c in turn["citations"]:
                    st.markdown(f"- `[{c['agent']}]` **{c['title']}** ({c['doc_id']}) — relevance {c['score']:.3f}")

message = st.chat_input("Ask MedOrch a question (synthetic clinical or operations knowledge)…")

if message:
    with st.chat_message("user"):
        st.write(message)

    payload = {"user_id": st.session_state.user_id, "message": message}
    if st.session_state.role:
        payload["role"] = st.session_state.role

    try:
        resp = requests.post(f"{API_URL}/chat", json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        st.error(f"Could not reach MedOrch API at {API_URL}: {exc}")
        st.stop()

    st.session_state.history.append(
        {
            "request": message,
            "agents_considered": data.get("agents_considered", []),
            "status": data.get("status"),
            "denied_agents": data.get("denied_agents", []),
            "executed_agents": data.get("executed_agents", []),
            "final_response": data.get("final_response", ""),
            "citations": data.get("citations", []),
        }
    )
    st.rerun()
