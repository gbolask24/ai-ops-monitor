-- AI Operations Monitoring Dashboard — Database Schema
-- Three independent event stream tables for telemetry ingestion.

-- ============================================================
-- chat_events: Chatwoot customer service activity
-- ============================================================
CREATE TABLE chat_events (
    id              SERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    conversation_id TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    agent_type      TEXT NOT NULL,
    inbox           TEXT,
    contact_id      TEXT,
    metadata        JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_chat_events_timestamp ON chat_events (timestamp);
CREATE INDEX idx_chat_events_conversation_id ON chat_events (conversation_id);
CREATE INDEX idx_chat_events_event_type ON chat_events (event_type);

-- ============================================================
-- workflow_runs: n8n workflow and agent execution
-- ============================================================
CREATE TABLE workflow_runs (
    id              SERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    workflow_name   TEXT NOT NULL,
    execution_id    TEXT NOT NULL UNIQUE,
    status          TEXT NOT NULL,
    duration_ms     INTEGER,
    retry_count     INTEGER DEFAULT 0,
    error_type      TEXT,
    metadata        JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_workflow_runs_timestamp ON workflow_runs (timestamp);
CREATE INDEX idx_workflow_runs_workflow_name ON workflow_runs (workflow_name);
CREATE INDEX idx_workflow_runs_status ON workflow_runs (status);
CREATE INDEX idx_workflow_runs_error_type ON workflow_runs (error_type);

-- ============================================================
-- ai_requests: LLM and chatbot level metrics
-- ============================================================
CREATE TABLE ai_requests (
    id              SERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    request_id      TEXT NOT NULL UNIQUE,
    conversation_id TEXT,
    provider        TEXT NOT NULL,
    model           TEXT NOT NULL,
    latency_ms      INTEGER,
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    total_tokens    INTEGER,
    estimated_cost  NUMERIC(10, 6),
    schema_valid    BOOLEAN,
    fallback_used   BOOLEAN DEFAULT FALSE,
    escalated       BOOLEAN DEFAULT FALSE,
    error_type      TEXT,
    metadata        JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_ai_requests_timestamp ON ai_requests (timestamp);
CREATE INDEX idx_ai_requests_conversation_id ON ai_requests (conversation_id);
CREATE INDEX idx_ai_requests_provider ON ai_requests (provider);
CREATE INDEX idx_ai_requests_model ON ai_requests (model);
CREATE INDEX idx_ai_requests_error_type ON ai_requests (error_type);
