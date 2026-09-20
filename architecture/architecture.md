# MedOrch Architecture

> **Disclaimer**: MedOrch is a technical proof-of-concept. All knowledge base
> content is synthetic/fictional. This system is **not** intended for
> clinical decision-making and does not process real patient data (PHI).

## 1. System Architecture

```
                          ┌─────────────────────┐
                          │        User          │
                          │ (Streamlit UI / API)  │
                          └──────────┬───────────┘
                                     │  message + role
                                     ▼
                          ┌─────────────────────┐
                          │   FastAPI  /chat     │
                          └──────────┬───────────┘
                                     ▼
                     ┌───────────────────────────────┐
                     │     MedOrch Orchestrator        │
                     │   (LangGraph state machine)     │
                     │                                 │
                     │  identify_role                  │
                     │       │                          │
                     │  analyze_intent  (LLM suggestion)│
                     │       │                          │
                     │  authorize   <-- Policy Engine   │
                     │       │      (deterministic,     │
                     │       │       no LLM involved)   │
                     │   ┌───┴────┐                     │
                     │ DENIED  ALLOWED/PARTIAL           │
                     │   │        │                      │
                     │   │   execute_agents               │
                     │   │        │                      │
                     │   │  aggregate_results             │
                     │   └───┬────┘                      │
                     │     audit_log                      │
                     └───────────────────────────────┘
                        │                         │
             (only if authorized)      (only if authorized)
                        ▼                         ▼
              ┌──────────────────┐      ┌──────────────────────┐
              │  Agent A          │      │  Agent B               │
              │  Clinical         │      │  Operations            │
              │  Knowledge Agent  │      │  Knowledge Agent       │
              └─────────┬────────┘      └───────────┬──────────┘
                        │                             │
              ┌─────────▼────────┐      ┌────────────▼──────────┐
              │ ClinicalRetriever │      │ OperationsRetriever    │
              │ (clinical_kb only)│      │ (operations_kb only)   │
              └─────────┬────────┘      └────────────┬──────────┘
                        │                             │
              ┌─────────▼────────┐      ┌────────────▼──────────┐
              │   clinical_kb      │      │   operations_kb        │
              │ (synthetic docs)   │      │ (synthetic docs)       │
              └───────────────────┘      └────────────────────────┘
```

## 2. Component Architecture

| Component | Responsibility | Location |
|---|---|---|
| FastAPI routes | HTTP surface, request validation, session role storage | `app/api/routes.py` |
| Orchestration graph | State machine wiring the request lifecycle | `app/graph/workflow.py` |
| Intent classifier | LLM (or heuristic) *suggestion* of relevant domain(s) | `app/agents/intent.py` |
| Policy engine | Deterministic RBAC authorization -- the security boundary | `app/auth/policy_engine.py` |
| Agent A | Clinical knowledge agent, own prompt/retriever | `app/agents/clinical_agent.py` |
| Agent B | Operations knowledge agent, own prompt/retriever | `app/agents/operations_agent.py` |
| Retrievers | Namespace-bound retrieval, one per agent | `app/rag/clinical_retriever.py`, `app/rag/operations_retriever.py` |
| Vector store | Storage backend (in-memory or Postgres/pgvector) | `app/rag/vector_store.py` |
| Audit service | Structured audit trail per request | `app/audit/logger.py` |

## 3. Agent Boundaries

Agent A and Agent B are isolated at three independent layers, so a bug in
any one layer alone cannot cause a cross-domain leak:

1. **Application layer** -- `ClinicalAgent` only ever constructs a
   `ClinicalRetriever`; `OperationsAgent` only ever constructs an
   `OperationsRetriever`. Neither agent class imports or references the
   other's retriever.
2. **Retriever layer** -- `ClinicalRetriever.retrieve()` and
   `OperationsRetriever.retrieve()` take no `namespace` argument. The
   namespace (`clinical_kb` / `operations_kb`) is a module-level constant
   baked into each retriever class, not a parameter that could be
   mis-supplied at a call site.
3. **Storage layer** -- in the Postgres/pgvector deployment, `clinical_kb`
   and `operations_kb` are two separate physical tables (see
   `scripts/init_db.sql`). In the in-memory dev/test store, they are two
   separate dict entries keyed by namespace string. Either way, a query
   against one namespace can structurally never return rows from the
   other.

The Orchestrator never queries a vector store directly -- it only ever
calls `agent.handle(message)` on an already-authorized agent instance,
which is the only thing capable of reaching a retriever.

## 4. Data Flow

```
message ─► identify_role ─► analyze_intent ─► authorize ─► execute_agents ─► aggregate_results ─► audit_log ─► response
```

At `execute_agents`, the loop iterates **only** over
`state["authorized_agents"]` -- the output of the policy engine. There is
no code path in the graph that invokes an agent id that is not present in
that list.

## 5. Authorization Flow

```
User request + role
        │
        ▼
 LLM / heuristic intent classification
        │  (untrusted suggestion: e.g. ["clinical", "operations"])
        ▼
 Policy Engine (app/auth/policy_engine.py)
        │  role x requested_agents -> (authorized_agents, denied_agents)
        │  PURE FUNCTION, no side effects, no LLM call
        ▼
   authorized_agents  ──►  execute_agents  ──►  retrievers  ──►  knowledge bases
   denied_agents      ──►  access_denied node (no agent/retriever/KB touched)
```

**Authorization occurs before agent execution and before knowledge
retrieval.** Concretely: the `execute_agents` graph node is only reached
via the `authorize` -> `_route_after_authorize` conditional edge when at
least one agent was authorized, and even then it only loops over
`authorized_agents`. A denied agent's retriever object is never
instantiated and its knowledge base is never queried -- not "queried then
filtered," genuinely never queried.

## 6. Multi-Agent Flow

For a request like *"Give me the synthetic clinical hypertension protocol
and the corresponding hospital admission workflow"*:

1. `analyze_intent` suggests `["clinical", "operations"]`.
2. `authorize` checks both against the requester's role independently.
   - ADMIN: both allowed → both execute.
   - CLINICIAN: only `clinical` allowed → only Agent A executes; the
     response notes that the operations domain was withheld.
3. `execute_agents` invokes each authorized agent independently (each
   agent only ever touches its own retriever/KB).
4. `aggregate_results` merges the per-agent answers into clearly labeled
   sections ("Clinical Knowledge Agent (Agent A): ...", "Healthcare
   Operations Agent (Agent B): ...") with per-agent source citations.

## 7. Threat Model

| Threat | Mitigation |
|---|---|
| LLM hallucinated/manipulated intent grants access to an unauthorized domain | Intent output is only ever compared against the static policy matrix in code; the LLM cannot set `authorized_agents` itself. |
| Prompt injection inside a user message tricks the LLM into claiming a different role or "admin override" | Role is sourced from the request/session field validated against a closed enum server-side (`app/auth/models.py::Role`), never parsed out of the free-text `message`. The system prompt explicitly tells the LLM it has no authorization authority. |
| Prompt injection inside a *retrieved document* tries to get the LLM to leak the other KB or change behavior | Each agent only ever receives documents from its own retriever; there is no code path where Agent A's context window can contain Agent B's documents. |
| Retrieve-then-filter data leakage (fetching restricted data and hiding it in the response) | Structurally impossible here: the retriever for a denied agent is never constructed, so there is no unauthorized data in memory to filter in the first place. |
| Cross-domain data leakage via shared vector store namespace confusion | Retrievers hard-bind to a single namespace constant; Postgres deployment uses physically separate tables (see `test_isolation.py`). |
| Sensitive data in audit logs | Audit records only store routing/authorization metadata and the (already user-supplied) request text -- not retrieved document contents. |
| Secrets in source control | No API keys are hard-coded; all secrets come from environment variables (`.env`, gitignored). `.env.example` ships only placeholders. |

## 8. Trust Boundaries

```
 ┌───────────────────────────── Untrusted ─────────────────────────────┐
 │  User input (message, claimed role in request body)                  │
 │  LLM output (intent suggestion, synthesized answer text)             │
 └───────────────────────────────────────────────────────────────────────┘
                                   │
                     validated / authorized against
                                   │
 ┌───────────────────────────── Trusted ───────────────────────────────┐
 │  Role enum validation (app/auth/models.py)                           │
 │  Policy engine permission matrix (app/auth/policy_engine.py)         │
 │  Graph routing logic (app/graph/workflow.py)                         │
 │  Retriever namespace binding (app/rag/*_retriever.py)                │
 └───────────────────────────────────────────────────────────────────────┘
```

The LLM sits entirely on the untrusted side of this boundary for
authorization purposes -- its only trusted-side effect is which *label*
(`"clinical"` / `"operations"`) gets passed to the policy engine, and the
policy engine treats that as just another user-influenced input to be
checked, not a command to obey.

## 9. Data Isolation Strategy

- Two independent knowledge domains, each with its own JSON source
  documents (`data/clinical/documents.json`, `data/operations/documents.json`).
- Two independent vector namespaces (`clinical_kb`, `operations_kb`),
  implemented as either two dict entries (in-memory store) or two physical
  Postgres tables (pgvector store) -- selected by `DATABASE_URL`.
- Two independent retriever classes, each hard-bound to one namespace with
  no parameter that could redirect it.
- Automated tests (`tests/test_isolation.py`) assert that adversarial
  cross-domain queries issued directly against one retriever never return
  the other domain's documents.

## 10. Audit Architecture

Every request produces exactly one `AuditRecord`
(`app/audit/models.py`) containing: `request_id`, `user_id`, `role`,
`timestamp`, the original request text, `detected_intent`,
`requested_agents`, `authorized_agents`, `denied_agents`,
`executed_agents`, and final `status`. Records are:

- kept in-memory for the life of the process (backing `GET
  /audit/{request_id}`), and
- appended as JSON lines to `audit.log` on disk for durability /
  downstream log shipping.

The audit service deliberately does not log retrieved document content or
full LLM-synthesized answers -- only routing/authorization metadata and
the user's own request text, per the "do not log sensitive information
unnecessarily" requirement.

## 11. Why This Is Not "the LLM pretending to route"

The `authorize` and `execute_agents` graph nodes are ordinary,
unit-tested Python functions with no LLM call anywhere inside them (see
`app/graph/workflow.py`). `tests/test_auth.py` and `tests/test_routing.py`
exercise them directly and via the compiled graph, proving that:

- a denied role genuinely never reaches `execute_agents` for the denied
  domain (its retriever object is never even constructed), and
- swapping out the intent classifier for a hostile/broken one (see the
  heuristic fallback path) cannot change what the policy engine allows --
  it can only change what gets *requested*, not what gets *authorized*.
