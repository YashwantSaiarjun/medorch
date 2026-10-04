"""
MedOrch Streamlit UI — XYZ Hospital
"""
from __future__ import annotations
import os
import requests
import streamlit as st

API_URL = os.getenv("MEDORCH_API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="MedOrch — XYZ Hospital",
    page_icon="🏥",
    layout="centered"
)
st.title("🏥 MedOrch — XYZ Hospital AI")
st.caption("Secure multi-agent healthcare platform. Reference use only. Not for clinical decision-making.")

# ── Staff directory ────────────────────────────────────────────────────────
# Maps display name → (user_id, role)
STAFF_DIRECTORY = {
    "Dr. Sarah Smith (Clinician)":        ("user-001", "CLINICIAN"),
    "Dr. James Patel (Clinician)":        ("user-002", "CLINICIAN"),
    "Dr. Aisha Nkosi (Clinician)":        ("user-003", "CLINICIAN"),
    "Mary Johnson (Pharmacist)":          ("user-004", "PHARMACIST"),
    "Tom Williams (Pharmacist)":          ("user-005", "PHARMACIST"),
    "Admin — Full Access":                ("admin-001", "CLINICIAN"),
}

STAFF_NAMES = list(STAFF_DIRECTORY.keys())

# ── Session state ──────────────────────────────────────────────────────────
if "staff_name" not in st.session_state:
    st.session_state.staff_name = STAFF_NAMES[0]
if "user_id" not in st.session_state:
    st.session_state.user_id = "user-001"
if "role" not in st.session_state:
    st.session_state.role = "CLINICIAN"
if "patient_id" not in st.session_state:
    st.session_state.patient_id = None
if "history" not in st.session_state:
    st.session_state.history = []

# ── Load patient IDs ───────────────────────────────────────────────────────
@st.cache_data
def load_patient_ids() -> list[str]:
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from app.db.csv_service import get_all_patient_ids
        return get_all_patient_ids()
    except Exception:
        return [f"P{1000+i}" for i in range(1, 2001)]


@st.cache_data
def get_permitted_for(user_id: str) -> list[str]:
    try:
        from app.auth.patient_auth import get_permitted_patients
        return get_permitted_patients(user_id)
    except Exception:
        return []


patient_ids = load_patient_ids()

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("👤 Staff Login")

    staff_choice = st.selectbox(
        "Select Staff Member",
        options=STAFF_NAMES,
        index=STAFF_NAMES.index(st.session_state.staff_name)
              if st.session_state.staff_name in STAFF_NAMES else 0
    )

    # Auto-fill user_id and role from staff selection
    selected_user_id, selected_role = STAFF_DIRECTORY[staff_choice]
    st.session_state.staff_name = staff_choice
    st.session_state.user_id    = selected_user_id
    st.session_state.role       = selected_role

    # Show role badge
    role_display = {
        "CLINICIAN":       "🩺 Clinician",
        "PHARMACIST":      "💊 Pharmacist",
        "OPERATIONS_STAFF":"🏥 Operations Staff",
    }
    st.info(f"Role: {role_display.get(st.session_state.role, st.session_state.role)}")

    # Show permitted patients
    permitted = get_permitted_for(st.session_state.user_id)
    if permitted == ["ALL"]:
        st.caption("🔓 Patient access: ALL")
    else:
        st.caption(f"🔒 Permitted patients: {', '.join(permitted)}")

    st.divider()

    st.subheader("🧑 Patient")
    patient_choice = st.selectbox(
        "Select Patient ID",
        options=["-- Select a patient --"] + patient_ids,
        index=0
    )
    if patient_choice != "-- Select a patient --":
        st.session_state.patient_id = patient_choice
    else:
        st.session_state.patient_id = None

    st.divider()

    st.markdown("**🔐 Access Matrix**")
    st.markdown(
        "- **Clinician** → diagnoses, lab results\n"
        "- **Pharmacist** → medications, prescriptions\n"
        "- **Operations** → appointments, admissions"
    )

    st.divider()

    if st.button("🗑️ Clear chat"):
        st.session_state.history = []
        st.rerun()

# ── Active session banner ──────────────────────────────────────────────────
st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    # Show only the name part, not the role in brackets
    display_name = st.session_state.staff_name.split("(")[0].strip()
    st.metric("Staff", display_name)
with col2:
    st.metric("Role", role_display.get(st.session_state.role, st.session_state.role))
with col3:
    st.metric("Patient", st.session_state.patient_id or "None")

st.divider()

if not st.session_state.patient_id:
    st.warning("⚠️ Please select a patient from the sidebar to begin.")

# ── Chat history ───────────────────────────────────────────────────────────
for turn in st.session_state.history:
    with st.chat_message("user"):
        st.write(turn["request"])

    with st.chat_message("assistant"):

        status = turn["status"]
        if status == "ALLOWED":
            st.success(f"✅ Authorization: {status}")
        elif status == "PARTIAL":
            st.warning(f"⚠️ Authorization: {status}")
        else:
            st.error(f"❌ Authorization: {status}")

        if turn["agents_considered"]:
            st.markdown(
                f"**🔍 Detected Domain(s):** "
                f"`{'`, `'.join(turn['agents_considered'])}`"
            )

        if turn["denied_agents"]:
            st.markdown(
                f"**🚫 Denied:** "
                f"`{'`, `'.join(turn['denied_agents'])}`"
            )

        if turn.get("tools_called"):
            st.markdown(
                f"**🔧 Tools Called:** "
                f"`{'`, `'.join(turn['tools_called'])}`"
            )

        if turn["executed_agents"]:
            st.markdown(
                f"**🤖 Agent(s) Executed:** "
                f"`{'`, `'.join(turn['executed_agents'])}`"
            )

        st.divider()

        if status in ("DENIED", "NEEDS_ROLE", "PATIENT_DENIED"):
            st.error(turn["final_response"])
        else:
            st.markdown("**💬 Answer:**")
            st.write(turn["final_response"])

        if turn.get("citations"):
            with st.expander("📚 Sources"):
                for c in turn["citations"]:
                    st.markdown(
                        f"- `[{c['agent']}]` **{c['title']}** "
                        f"({c['doc_id']}) — relevance: {c['score']:.3f}"
                    )

# ── Chat input ─────────────────────────────────────────────────────────────
message = st.chat_input("Ask about the selected patient...")

if message:
    if not st.session_state.patient_id:
        st.error("⚠️ Please select a patient first.")
        st.stop()

    with st.chat_message("user"):
        st.write(message)

    payload = {
        "user_id":    st.session_state.user_id,
        "role":       st.session_state.role,
        "patient_id": st.session_state.patient_id,
        "message":    message,
    }

    with st.spinner("Processing..."):
        try:
            resp = requests.post(f"{API_URL}/chat", json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            st.error(f"❌ API error: {exc}")
            st.stop()


    st.session_state.history.append({
        "request":           message,
        "agents_considered": data.get("agents_considered", []),
        "status":            data.get("status"),
        "denied_agents":     data.get("denied_agents", []),
        "executed_agents":   data.get("executed_agents", []),
        "tools_called":      data.get("tools_called", []),
        "final_response":    data.get("final_response", ""),
        "citations":         data.get("citations", []),
    })
    st.rerun()