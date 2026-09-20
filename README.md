# MedOrch — Secure Multi-Agent Healthcare Orchestration Platform

> **Healthcare disclaimer**: MedOrch is a technical proof-of-concept that
> demonstrates secure, role-aware multi-agent orchestration architecture.
> **All knowledge base content is synthetic/fictional.** MedOrch does not
> process real patient data (PHI), is **not** a clinical decision-support
> tool, and must not be used to guide real patient care. See
> [Security Considerations](#17-security-considerations) for what would be
> required for a production healthcare deployment.

---

## 1. Project Overview

MedOrch is a proof-of-concept multi-agent AI platform for healthcare that
shows how to build a system where **the LLM is never the final authority
on access control**. A central orchestrator (built as a LangGraph state
machine) classifies user requests, but a separate, deterministic policy
engine — plain Python code — decides which specialized agent(s) may
actually execute and which knowledge base may actually be queried.

## 2. Problem Statement

Naively bolting RAG onto an LLM router creates a real risk: if the LLM
alone decides "this looks like a clinical question, let me fetch clinical
data," then a prompt injection, a hallucination, or a bug can leak
sensitive domain data to an unauthorized user. MedOrch solves this by
putting a deterministic authorization gate **between** intent detection
and knowledge retrieval, and by giving every knowledge domain its own
isolated agent, retriever, and knowledge base.

## 3. Architecture

See [`architecture/architecture.md`](architecture/architecture.md) for the
full write-up (component architecture, threat model, trust boundaries,
data isolation strategy, audit architecture). Summary diagram:

```
User ─► FastAPI /chat ─► Orchestrator (LangGraph)
                              │
                    identify_role ─► analyze_intent (LLM, untrusted)
                              │
                    authorize (deterministic Policy Engine)
                         │                  │
                      DENIED             ALLOWED
                         │                  │
                  access_denied      execute_agents
                                             │
                              ┌──────────────┴──────────────┐
                              ▼                              ▼
                      Agent A (Clinical)             Agent B (Operations)
                      ClinicalRetriever               OperationsRetriever
                      clinical_kb                      operations_kb
                              │                              │
                              └──────────► aggregate_results ◄┘
                                             │
                                          audit_log ─► response
```


User
  ↓
API / UI
  ↓
Orchestrator
  ↓
Intent Detection
  ↓
Policy Engine / RBAC
  ↓
 ┌──────────────┬──────────────┐
 ↓              ↓
Agent A        Agent B
Clinical       Operations
 ↓              ↓
KB A           KB B
 ↓              ↓
Vector DB A    Vector DB B
 └───────┬──────┘
         ↓
   Response Aggregator
         ↓
      Audit Log
## 4. Security Model

- **RBAC** enforced by a centralized, deterministic policy engine
  (`app/auth/policy_engine.py`) — not by prompt instructions.
- **Authorization before retrieval**: a denied agent's retriever is never
  constructed and its knowledge base is never queried. Data is never
  fetched and then filtered after the fact.
- **Agent + knowledge-base isolation**: each agent is hard-bound to its
  own retriever and namespace; see [Knowledge Isolation Model](#7-knowledge-isolation-model).
- **Auditability**: every request produces a structured audit record
  capturing the routing, authorization, and execution outcome.
- **No secrets in source**: all credentials come from environment
  variables; `.env.example` ships placeholders only.

Full threat model and trust boundaries: see
[`architecture/architecture.md`](architecture/architecture.md).

## 5. Multi-Agent Workflow

The orchestrator is implemented as a LangGraph state machine
(`app/graph/workflow.py`) with these nodes:

```
identify_role → analyze_intent → authorize ─┬─► access_denied ─► audit_log ─► END
                                              └─► execute_agents → aggregate_results → audit_log → END
```

It supports single-agent requests, multi-agent requests (independently
authorizing and invoking each requested agent), unauthorized requests,
missing-role prompts, unknown intent, and agent/retrieval failures.

## 6. RBAC Model

| Role | Agent A (Clinical) | Agent B (Operations) |
|---|---|---|
| CLINICIAN | ✅ ALLOWED | ❌ DENIED |
| OPERATIONS | ❌ DENIED | ✅ ALLOWED |
| ADMIN | ✅ ALLOWED | ✅ ALLOWED |
| RESTRICTED | ❌ DENIED | ❌ DENIED |

This matrix lives in exactly one place:
`app/auth/policy_engine.py::_PERMISSION_MATRIX`.

## 7. Knowledge Isolation Model

```
      MedOrch (never touches a vector store directly)
         │
   ------------------------
   │                      │
Agent A                Agent B
   │                      │
ClinicalRetriever    OperationsRetriever
(clinical_kb only)   (operations_kb only)
   │                      │
clinical_kb            operations_kb
```

Enforced at three layers (application, retriever, storage) — see
[`architecture/architecture.md §3`](architecture/architecture.md#3-agent-boundaries).
Proven by `tests/test_isolation.py`.

## 8. Technology Stack

- Python 3.11+
- FastAPI + Pydantic
- LangGraph (orchestration state machine)
- PostgreSQL + pgvector (production vector store) — with an in-memory
  vector store fallback for zero-infra local dev/CI, behind the same
  interface (`app/rag/vector_store.py`)
- Streamlit (UI)
- Docker / Docker Compose
- pytest

## 9. Project Structure

```
medorch/
├── app/
│   ├── api/routes.py               # FastAPI endpoints
│   ├── agents/                     # orchestrator, Agent A, Agent B, intent
│   ├── auth/                       # RBAC models + deterministic policy engine
│   ├── rag/                        # embeddings, vector store, retrievers, kb loader
│   ├── audit/                      # audit record model + service
│   ├── graph/                      # LangGraph workflow + state
│   ├── llm/                        # thin LLM client wrapper
│   ├── config.py
│   └── main.py
├── data/{clinical,operations}/documents.json   # synthetic knowledge bases
├── tests/                          # test_auth, test_routing, test_isolation, test_rag
├── ui/streamlit_app.py
├── architecture/architecture.md
├── scripts/{init_db.sql,load_kb.py}
├── docker-compose.yml, Dockerfile, Dockerfile.ui
├── requirements.txt, .env.example, .gitignore
└── README.md
```

## 10. Setup Instructions

### Option A — quick local run (no Docker, no Postgres)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # optionally set LLM_API_KEY; leave blank to run fully offline
```

Without `DATABASE_URL` set, MedOrch automatically uses the in-memory
vector store — nothing else to configure.

### Option B — full stack with Docker

```bash
cp .env.example .env    # optionally set LLM_API_KEY
docker compose up --build
```

## 11. Docker Instructions

`docker compose up --build` starts three services:

- `postgres` — Postgres + pgvector, initialized with `scripts/init_db.sql`
  (creates the `clinical_kb` and `operations_kb` tables).
- `api` — the FastAPI backend on `:8000`.
- `ui` — the Streamlit UI on `:8501`, pointed at the `api` service.

Stop with `docker compose down` (add `-v` to also drop the Postgres
volume).

## 12. Environment Configuration

See [`.env.example`](.env.example) for the full list. Key variables:

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `anthropic` or `openai` |
| `LLM_API_KEY` | Leave blank to run fully offline with deterministic heuristics |
| `LLM_MODEL` | Model name for the configured provider |
| `DISABLE_LLM` | Force-disable LLM calls even if a key is set |
| `DATABASE_URL` | Set to use Postgres/pgvector; unset = in-memory store |
| `RETRIEVAL_TOP_K` | Number of documents each agent retrieves per query |

## 13. Running the API

```bash
uvicorn app.main:app --reload --port 8000
```

Interactive docs at `http://localhost:8000/docs`.

## 14. Running Streamlit

```bash
streamlit run ui/streamlit_app.py
```

Set `MEDORCH_API_URL` if the API isn't on `http://localhost:8000`.

## 15. Test Instructions

```bash
DISABLE_LLM=true pytest tests/ -v
```

`DISABLE_LLM=true` makes the suite fully deterministic and offline (no
API key required); the policy engine and knowledge isolation are always
deterministic regardless of this flag. 26 tests covering RBAC (all 4
roles × both agents), knowledge isolation, orchestration/routing
(including every demo scenario below), and RAG-layer behavior.

## 16. Example Requests

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user-001","role":"CLINICIAN","message":"What are the synthetic clinical guidelines for hypertension management?"}'
```

### Demo Scenarios

| # | Role | Question | Expected |
|---|---|---|---|
| 1 | CLINICIAN | "What are the synthetic clinical guidelines for hypertension management?" | Agent A executes |
| 2 | OPERATIONS | "What is the synthetic hospital admission workflow?" | Agent B executes |
| 3 | OPERATIONS | "What is the synthetic clinical protocol for hypertension?" | **Access denied**; Agent A does not execute |
| 4 | ADMIN | "Give me the synthetic clinical hypertension protocol and the corresponding hospital admission workflow." | Agent A **and** Agent B execute |
| 5 | RESTRICTED | "Give me information about hypertension." | **Access denied**; no agent executes |

Each is covered by an automated regression test in `tests/test_routing.py`.

## 17. Security Considerations

- Authorization is evaluated **before** any agent is invoked or any
  knowledge base is queried (never "fetch then filter").
- The LLM's intent output is treated as untrusted input to the policy
  engine, never as an authorization decision itself.
- No PHI or real patient data is present anywhere in this repository.
- No secrets are hard-coded; see `.env.example`.
- The in-memory session/role store in `app/api/routes.py` is POC-scope
  only (no persistence, no real authentication) — see Limitations.

**This POC is not HIPAA compliant and makes no such claim.** A production
healthcare deployment would additionally require, at minimum:

- Real authentication/identity provider (OAuth2/OIDC/SSO) instead of a
  client-supplied `role` field, plus MFA for privileged roles.
- Encryption at rest and in transit for all data stores, and a signed/
  tamper-evident audit log (not a plain JSON-lines file).
- A Business Associate Agreement (BAA) with any third-party LLM provider,
  and a private/VPC-isolated model deployment if PHI is ever involved.
- Formal access reviews, session expiry, rate limiting, and centralized
  secrets management (e.g. a vault service).
- A clinical safety/compliance review before any output is used to
  inform real care decisions — this system is explicitly not designed or
  validated for that purpose.

## 18. Limitations

- Retrieval uses a lightweight hashing-based embedding (no external
  embedding API required) — adequate for this synthetic demo corpus, not
  benchmarked for production-scale relevance.
- Session/role storage is in-memory and resets on API restart.
- No real user authentication — `role` is a client-supplied POC
  convenience, not a security control on its own (do not deploy this
  as-is on an untrusted network).
- Audit log is a local file + in-memory store, not a durable/queryable
  audit database.

## 19. Future Improvements

- Swap the hashing embedding for a real embedding model/service behind
  the same `VectorStore` interface.
- Add a third/fourth specialized agent to demonstrate N-way isolation.
- Persist sessions and audit records in Postgres (`audit_logs` table is
  already scaffolded in `scripts/init_db.sql`).
- Add per-role rate limiting and structured request tracing (OpenTelemetry).
- Real identity provider integration (OIDC) replacing the demo role
  selector.

## 20. Healthcare Disclaimer

MedOrch is a technical proof-of-concept only. All clinical and
operations content in its knowledge bases is synthetic and fictional. It
is **not** intended for, and must not be used for, clinical
decision-making, diagnosis, treatment planning, or any form of real
patient care. It does not process real patient data (PHI) and is not
represented as HIPAA compliant.
