# MedOrch — Secure Multi-Agent Healthcare AI Orchestration Platform

> **A role-aware, multi-agent healthcare AI proof-of-concept demonstrating secure agent routing, RBAC, isolated knowledge bases, RAG, multi-agent orchestration, and auditability.**

> ⚠️ **Healthcare Disclaimer:** MedOrch is a technical proof-of-concept. All healthcare knowledge used in this project is synthetic and fictional. The system does not process real patient data (PHI), is not a clinical decision-support system, and must not be used for diagnosis, treatment, or real patient care.

---

## 📌 Overview

**MedOrch** is an end-to-end multi-agent AI orchestration platform designed to demonstrate how multiple specialized AI agents can collaborate while maintaining **role-based access control and knowledge isolation**.

The system consists of:

* 🧠 A central **Orchestrator Agent**
* 🩺 A **Clinical Knowledge Agent**
* 🏥 A **Healthcare Operations Agent**
* 🔐 A deterministic **RBAC / Policy Engine**
* 📚 Independent RAG pipelines and knowledge bases
* 🔎 Intent-based agent routing
* 🔗 Multi-agent request orchestration
* 📋 Structured audit logging
* 🧪 Automated security and routing tests

The central design principle is:

> **The LLM can determine which agent is relevant, but it never makes the final authorization decision.**

Authorization is performed by deterministic application logic **before** an agent is executed or its knowledge base is queried.

---

# 🎯 Problem Statement

Healthcare organizations may have multiple AI-powered knowledge systems serving different domains, such as:

* Clinical knowledge
* Healthcare operations
* Insurance
* Patient services
* Pharmacy
* Billing

A centralized AI interface could route user requests to the appropriate specialized agent.

However, this introduces important security and architecture questions:

* Which users are allowed to access each agent?
* How can different knowledge domains remain isolated?
* How can unauthorized retrieval be prevented?
* How can multiple agents collaborate without exposing protected data?
* How can routing and authorization decisions be audited?
* What happens when a user requests information spanning multiple domains?

MedOrch explores these challenges through a secure multi-agent architecture.

---

# 💡 Solution

MedOrch separates **intent detection**, **authorization**, **agent execution**, and **knowledge retrieval** into independent responsibilities.

```text
                         ┌──────────────────┐
                         │       User       │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  FastAPI / UI    │
                         └────────┬─────────┘
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │    MedOrch Orchestrator  │
                    │       LangGraph          │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │     Intent Detection     │
                    │          LLM             │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │   Policy Engine / RBAC   │
                    │    Deterministic Code    │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                 DENIED                    ALLOWED
                    │                         │
                    ▼                         ▼
              Access Denied          Specialized Agent
                                             │
                                  ┌──────────┴──────────┐
                                  │                     │
                                  ▼                     ▼
                           Clinical Agent       Operations Agent
                                  │                     │
                                  ▼                     ▼
                           Clinical KB          Operations KB
                                  │                     │
                                  └──────────┬──────────┘
                                             │
                                             ▼
                                     Result Aggregator
                                             │
                                             ▼
                                        Audit Log
                                             │
                                             ▼
                                       Final Response
```

---

# 🏗️ Architecture

The complete architecture and threat model are available in:

[`architecture/architecture.md`](architecture/architecture.md)

### High-Level Flow

```text
User
  ↓
API / UI
  ↓
MedOrch Orchestrator
  ↓
Intent Detection
  ↓
Policy Engine / RBAC
  ↓
 ┌───────────────────────┐
 │                       │
 ▼                       ▼
DENIED                 ALLOWED
 │                       │
 ▼                       ▼
Access Denied       Specialized Agent
                         │
                ┌────────┴────────┐
                ▼                 ▼
          Clinical Agent   Operations Agent
                │                 │
                ▼                 ▼
          Clinical KB      Operations KB
                │                 │
                └────────┬────────┘
                         ▼
                 Response Aggregator
                         │
                         ▼
                    Audit Logger
                         │
                         ▼
                    Final Response
```

---

# 🔐 Core Security Principle

A critical design decision in MedOrch is:

> **Authorization is performed before agent execution and before knowledge retrieval.**

The LLM is responsible for **intent detection**, not authorization.

### Incorrect approach

```text
User
 ↓
LLM
 ↓
Retrieve from all relevant sources
 ↓
Filter unauthorized information
```

This can expose protected information during retrieval.

### MedOrch approach

```text
User
 ↓
Intent Detection
 ↓
Policy Engine
 ↓
Authorization
 ↓
Agent Execution
 ↓
Knowledge Retrieval
 ↓
Response
```

For example:

```text
User Role: OPERATIONS

Request:
"What is the synthetic hypertension treatment protocol?"

                ↓

Intent Detection
        ↓
Clinical Agent
        ↓
Policy Engine
        ↓
OPERATIONS → CLINICAL = DENIED
        ↓
Clinical Agent NOT executed
        ↓
Clinical KB NOT queried
        ↓
Access Denied
```

The system does **not** fetch protected data and filter it afterward.

---

# 🤖 Specialized Agents

## Agent A — Clinical Knowledge Agent

The Clinical Agent manages the clinical knowledge domain.

Its synthetic knowledge base contains examples such as:

* Clinical guidelines
* Disease information
* Clinical procedures
* Treatment protocols
* Synthetic medication information

Architecture:

```text
Clinical Agent
      ↓
Clinical Retriever
      ↓
clinical_kb
      ↓
Clinical Documents
```

The Clinical Agent has no direct access to the Operations knowledge base.

---

## Agent B — Healthcare Operations Agent

The Operations Agent manages healthcare operational knowledge.

Its synthetic knowledge base contains examples such as:

* Hospital workflows
* Patient admission procedures
* Insurance workflows
* Billing policies
* Administrative processes

Architecture:

```text
Operations Agent
      ↓
Operations Retriever
      ↓
operations_kb
      ↓
Operations Documents
```

The Operations Agent has no direct access to the Clinical knowledge base.

---

# 🔒 Knowledge Isolation

MedOrch maintains separate knowledge boundaries for each specialized agent.

```text
                  MedOrch
              ───────────────
               Never directly
              accesses vector DBs
                    │
           ┌────────┴────────┐
           │                 │
           ▼                 ▼
      Clinical Agent    Operations Agent
           │                 │
           ▼                 ▼
 Clinical Retriever    Operations Retriever
           │                 │
           ▼                 ▼
     clinical_kb        operations_kb
```

Isolation is enforced at multiple layers:

1. **Application layer**
2. **Agent layer**
3. **Retriever layer**
4. **Knowledge-store layer**

The Orchestrator does not directly query the vector stores.

Each specialized agent is responsible for accessing only its own knowledge domain.

Automated isolation tests are implemented in:

```text
tests/test_isolation.py
```

---

# 🔑 RBAC Model

MedOrch uses a centralized deterministic permission matrix.

| Role           | Clinical Agent | Operations Agent |
| -------------- | :------------: | :--------------: |
| **CLINICIAN**  |    ✅ Allowed   |     ❌ Denied     |
| **OPERATIONS** |    ❌ Denied    |     ✅ Allowed    |
| **ADMIN**      |    ✅ Allowed   |     ✅ Allowed    |
| **RESTRICTED** |    ❌ Denied    |     ❌ Denied     |

The permission matrix is maintained in:

```text
app/auth/policy_engine.py
```

### Important

The LLM cannot modify or override these permissions.

The LLM may say:

> "This request appears to require the Clinical Agent."

The Policy Engine independently determines:

> "Is this user's role authorized to access the Clinical Agent?"

---

# 🔄 Multi-Agent Orchestration

MedOrch supports requests that require multiple knowledge domains.

Example:

> "Give me the synthetic clinical hypertension protocol and the corresponding hospital admission workflow."

The Orchestrator identifies:

```text
Clinical requirement
        ↓
Clinical Agent

Operations requirement
        ↓
Operations Agent
```

The Policy Engine independently authorizes each agent.

```text
                    User Request
                         │
                         ▼
                    Orchestrator
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        Clinical Intent       Operations Intent
              │                     │
              ▼                     ▼
        Policy Check          Policy Check
              │                     │
              ▼                     ▼
       Clinical Agent       Operations Agent
              │                     │
              ▼                     ▼
         Clinical KB         Operations KB
              │                     │
              └──────────┬──────────┘
                         ▼
                  Result Aggregator
                         │
                         ▼
                   Final Response
```

If the user is authorized for only one domain, only that domain executes.

---

# 🧠 LangGraph Workflow

The orchestration workflow is implemented using **LangGraph**.

```text
identify_role
      ↓
analyze_intent
      ↓
authorize
   ┌──┴───────────────┐
   │                  │
DENIED              ALLOWED
   │                  │
   ▼                  ▼
access_denied    execute_agents
   │                  │
   │                  ▼
   │           aggregate_results
   │                  │
   └────────┬─────────┘
            ▼
        audit_log
            ↓
           END
```

The workflow supports:

* Single-agent requests
* Multi-agent requests
* Unauthorized requests
* Missing-role scenarios
* Unknown intents
* Agent failures
* Retrieval failures

---

# 📋 Auditability

Every request generates a structured audit record.

Example:

```json
{
  "request_id": "req-001",
  "user_id": "user-001",
  "role": "OPERATIONS",
  "request": "What is the synthetic hypertension treatment protocol?",
  "requested_agents": ["clinical"],
  "authorized_agents": [],
  "denied_agents": ["clinical"],
  "executed_agents": [],
  "status": "DENIED"
}
```

The audit layer records information such as:

* Request ID
* User ID
* User role
* Original request
* Detected intent
* Requested agents
* Authorized agents
* Denied agents
* Executed agents
* Execution status
* Timestamp

Sensitive information should not be unnecessarily written to logs.

---

# 🧪 Demo Scenarios

The following scenarios demonstrate the main capabilities of the platform.

## Scenario 1 — Authorized Clinical Access

**Role**

```text
CLINICIAN
```

**Request**

```text
What are the synthetic clinical guidelines for hypertension management?
```

**Expected**

```text
Intent → Clinical
Authorization → ALLOWED
Agent → Clinical Agent
Result → Successful response
```

---

## Scenario 2 — Authorized Operations Access

**Role**

```text
OPERATIONS
```

**Request**

```text
What is the synthetic hospital admission workflow?
```

**Expected**

```text
Intent → Operations
Authorization → ALLOWED
Agent → Operations Agent
Result → Successful response
```

---

## Scenario 3 — Unauthorized Clinical Access

**Role**

```text
OPERATIONS
```

**Request**

```text
What is the synthetic clinical protocol for hypertension?
```

**Expected**

```text
Intent → Clinical
Authorization → DENIED
Agent → Clinical Agent NOT executed
Knowledge Base → Clinical KB NOT queried
Result → Access denied
```

---

## Scenario 4 — Multi-Agent Request

**Role**

```text
ADMIN
```

**Request**

```text
Give me the synthetic clinical hypertension protocol
and the corresponding hospital admission workflow.
```

**Expected**

```text
Clinical Agent → ALLOWED
Operations Agent → ALLOWED

        ↓

Both agents execute independently

        ↓

Results aggregated

        ↓

Final response returned
```

---

## Scenario 5 — Restricted User

**Role**

```text
RESTRICTED
```

**Request**

```text
Give me information about hypertension.
```

**Expected**

```text
Authorization → DENIED
Clinical Agent → NOT executed
Operations Agent → NOT executed
```

---

# 🧰 Technology Stack

### AI / Agent Architecture

* Python 3.11+
* LangGraph
* LLM-based intent classification
* RAG
* Embeddings

### Backend

* FastAPI
* Pydantic

### Data & Retrieval

* PostgreSQL
* pgvector
* Isolated knowledge bases
* Synthetic JSON knowledge documents
* In-memory vector-store fallback for local development and testing

### Frontend

* Streamlit

### Infrastructure

* Docker
* Docker Compose

### Testing

* pytest

---

# 📁 Project Structure

```text
medorch/
│
├── app/
│   ├── api/
│   │   └── routes.py
│   │
│   ├── agents/
│   │   ├── orchestrator.py
│   │   ├── clinical_agent.py
│   │   ├── operations_agent.py
│   │   └── intent.py
│   │
│   ├── auth/
│   │   ├── models.py
│   │   └── policy_engine.py
│   │
│   ├── rag/
│   │   ├── embeddings.py
│   │   ├── vector_store.py
│   │   ├── clinical_retriever.py
│   │   ├── operations_retriever.py
│   │   └── kb_loader.py
│   │
│   ├── audit/
│   │   ├── models.py
│   │   └── service.py
│   │
│   ├── graph/
│   │   ├── workflow.py
│   │   └── state.py
│   │
│   ├── llm/
│   │   └── client.py
│   │
│   ├── config.py
│   └── main.py
│
├── data/
│   ├── clinical/
│   │   └── documents.json
│   │
│   └── operations/
│       └── documents.json
│
├── tests/
│   ├── test_auth.py
│   ├── test_routing.py
│   ├── test_isolation.py
│   └── test_rag.py
│
├── ui/
│   └── streamlit_app.py
│
├── architecture/
│   └── architecture.md
│
├── scripts/
│   ├── init_db.sql
│   └── load_kb.py
│
├── Dockerfile
├── Dockerfile.ui
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

# 🚀 Getting Started

## Prerequisites

* Python 3.11+
* Docker Desktop — optional for local non-Docker execution
* An LLM API key — optional
* Git

---

## Option 1 — Quick Local Run

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

### Linux / macOS

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

The project can run without an external LLM API using its deterministic fallback mode.

Without `DATABASE_URL`, the application uses the in-memory vector store.

---

# 🐳 Option 2 — Run with Docker

Create the environment file:

```bash
cp .env.example .env
```

Then start the complete stack:

```bash
docker compose up --build
```

This starts:

| Service    | Purpose               |   Port |
| ---------- | --------------------- | -----: |
| `postgres` | PostgreSQL + pgvector | `5432` |
| `api`      | FastAPI backend       | `8000` |
| `ui`       | Streamlit application | `8501` |

Stop the application:

```bash
docker compose down
```

To also remove the PostgreSQL volume:

```bash
docker compose down -v
```

---

# ⚙️ Environment Configuration

Configuration is available in:

```text
.env.example
```

Important variables:

| Variable          | Description                                  |
| ----------------- | -------------------------------------------- |
| `LLM_PROVIDER`    | LLM provider such as `openai` or `anthropic` |
| `LLM_API_KEY`     | API key for the configured provider          |
| `LLM_MODEL`       | Model name                                   |
| `DISABLE_LLM`     | Disables external LLM calls                  |
| `DATABASE_URL`    | PostgreSQL connection string                 |
| `RETRIEVAL_TOP_K` | Number of retrieved documents                |

Example:

```env
LLM_PROVIDER=openai
LLM_API_KEY=
LLM_MODEL=
DISABLE_LLM=true
DATABASE_URL=
RETRIEVAL_TOP_K=3
```

**Never commit `.env` or real API keys to GitHub.**

---

# 🔌 Running the API

Start FastAPI:

```bash
uvicorn app.main:app --reload --port 8000
```

API:

```text
http://localhost:8000
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

---

# 🖥️ Running the Streamlit UI

Start the frontend:

```bash
streamlit run ui/streamlit_app.py
```

The UI can be accessed through the Streamlit URL displayed in the terminal.

If the API is running on another address, configure:

```text
MEDORCH_API_URL
```

---

# 🧪 Testing

Run the complete test suite:

```bash
DISABLE_LLM=true pytest tests/ -v
```

The deterministic test mode does not require an external LLM API key.

The test suite covers:

* RBAC
* All supported roles
* Agent authorization
* Agent routing
* Knowledge isolation
* Unauthorized execution prevention
* RAG behavior
* Single-agent workflows
* Multi-agent workflows
* Demo scenarios

---

# 🔍 Example API Request

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-001",
    "role": "CLINICIAN",
    "message": "What are the synthetic clinical guidelines for hypertension management?"
  }'
```

The response includes structured information such as:

```text
Final response
Request ID
Detected agents
Authorized agents
Citations
Execution status
```

---

# 🛡️ Security Design

MedOrch demonstrates several security principles relevant to multi-agent AI systems.

### 1. Authorization Before Retrieval

Unauthorized agents are blocked before their retrievers execute.

```text
Intent
  ↓
Authorization
  ↓
Agent
  ↓
Retriever
  ↓
Knowledge Base
```

Not:

```text
Intent
  ↓
Retrieve Everything
  ↓
Filter Response
```

---

### 2. Deterministic Authorization

The LLM does not determine whether a user is authorized.

The Policy Engine makes that decision using application code.

---

### 3. Least Privilege

Users receive access only to the knowledge domains required by their role.

---

### 4. Agent Isolation

Each agent has:

* Its own prompt
* Its own retriever
* Its own knowledge domain
* Its own vector-store namespace/table

---

### 5. No Direct Vector Store Access by the Orchestrator

The Orchestrator coordinates agents but does not directly retrieve knowledge.

---

### 6. Auditability

Routing and authorization decisions are recorded for traceability.

---

### 7. Secret Management

Credentials are provided through environment variables rather than source code.

---

# 🧩 Production Considerations

MedOrch is a POC and is **not production-ready or HIPAA compliant**.

A production healthcare implementation would require significantly stronger controls, including:

### Identity & Authentication

* OAuth2 / OIDC
* Enterprise SSO
* MFA
* Session management
* Identity-provider integration

The current POC uses a client-provided role for demonstration purposes only.

---

### Data Protection

* Encryption in transit
* Encryption at rest
* Key management
* Secrets management
* Network isolation
* Private infrastructure where appropriate

---

### Audit & Compliance

* Durable audit storage
* Tamper-evident audit logs
* Centralized observability
* Access reviews
* Compliance controls
* Security monitoring

---

### AI Security

A production implementation would also require controls around:

* Prompt injection
* Indirect prompt injection
* Tool authorization
* Data exfiltration
* Agent-to-agent trust
* Output validation
* Retrieval security
* Model access policies

---

### Healthcare Safety

Before any healthcare AI system is used in real clinical workflows, additional:

* Clinical validation
* Safety review
* Regulatory/compliance review
* Human oversight
* Risk assessment

would be required.

---

# ⚠️ Current Limitations

This project intentionally keeps several components lightweight because it is a proof-of-concept.

### Embeddings

The current implementation uses a lightweight hashing-based embedding approach suitable for the small synthetic demo corpus.

It has not been benchmarked for production-scale retrieval relevance.

### Authentication

There is no real identity provider.

The role is currently supplied by the client/UI and therefore should **not** be considered a production security control.

### Session Management

Session and role information is stored in memory and resets when the API restarts.

### Audit Storage

The audit log is currently local/in-memory rather than a durable enterprise audit platform.

### Synthetic Data

All knowledge-base content is synthetic and fictional.

---

# 🔮 Future Improvements

Potential next steps include:

* Replace demo embeddings with production embedding models
* Add additional specialized agents
* Introduce persistent audit storage
* Add enterprise identity integration using OIDC
* Add centralized secrets management
* Add OpenTelemetry tracing
* Add per-role rate limiting
* Add advanced agent evaluation
* Add prompt-injection defenses
* Add policy-based tool authorization
* Add human-in-the-loop approval workflows
* Add production-grade monitoring
* Add N-way agent isolation

---

# 📊 What This POC Demonstrates

The project demonstrates practical concepts across several areas:

| Area                           | Demonstrated |
| ------------------------------ | ------------ |
| Multi-Agent AI                 | ✅            |
| LLM Orchestration              | ✅            |
| LangGraph                      | ✅            |
| RAG                            | ✅            |
| RBAC                           | ✅            |
| Least Privilege                | ✅            |
| Agent Isolation                | ✅            |
| Knowledge Isolation            | ✅            |
| Authorization Before Retrieval | ✅            |
| Multi-Agent Workflows          | ✅            |
| Audit Logging                  | ✅            |
| FastAPI                        | ✅            |
| Streamlit                      | ✅            |
| PostgreSQL / pgvector          | ✅            |
| Docker                         | ✅            |
| Automated Testing              | ✅            |

---

# 🎯 Key Architectural Takeaway

The primary goal of MedOrch is not simply to demonstrate that an LLM can call multiple agents.

It demonstrates how a multi-agent system can separate:

```text
                 ┌─────────────────────┐
                 │   Intent Detection  │
                 │        LLM          │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │  Authorization      │
                 │  Deterministic RBAC │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │   Agent Execution   │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ Knowledge Retrieval │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │    Audit / Trace    │
                 └─────────────────────┘
```

This separation helps establish clear **trust boundaries, least-privilege access, and knowledge isolation** between specialized AI agents.

---

# ⚠️ Healthcare Disclaimer

**MedOrch is a technical proof-of-concept only.**

All clinical and healthcare operations content used by this project is synthetic and fictional.

MedOrch:

* Does not process real patient data
* Does not contain PHI
* Is not HIPAA compliant
* Is not a clinical decision-support system
* Must not be used for diagnosis
* Must not be used for treatment planning
* Must not be used to guide real patient care

The architecture is intended to demonstrate engineering concepts around **multi-agent AI, orchestration, authorization, RAG, security boundaries, and knowledge isolation**.

---


