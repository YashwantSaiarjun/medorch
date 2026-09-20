-- MedOrch database initialization: separate physical tables per agent
-- knowledge base, enforcing storage-level isolation in addition to the
-- application-level isolation enforced by the retrievers/agents.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS clinical_kb (
    doc_id      TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    metadata    JSONB DEFAULT '{}'::jsonb,
    embedding   vector(256) NOT NULL
);

CREATE TABLE IF NOT EXISTS operations_kb (
    doc_id      TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    metadata    JSONB DEFAULT '{}'::jsonb,
    embedding   vector(256) NOT NULL
);

CREATE INDEX IF NOT EXISTS clinical_kb_embedding_idx
    ON clinical_kb USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);

CREATE INDEX IF NOT EXISTS operations_kb_embedding_idx
    ON operations_kb USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);

-- Audit trail (optional durable store; the app also writes a local
-- audit.log JSON-lines file by default).
CREATE TABLE IF NOT EXISTS audit_logs (
    request_id          TEXT PRIMARY KEY,
    user_id             TEXT NOT NULL,
    role                TEXT NOT NULL,
    ts                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    request_text        TEXT NOT NULL,
    detected_intent     JSONB,
    requested_agents    JSONB,
    authorized_agents   JSONB,
    denied_agents       JSONB,
    executed_agents     JSONB,
    status              TEXT NOT NULL
);
