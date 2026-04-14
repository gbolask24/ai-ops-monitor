"""
Thin webhook ingestion service for AI Operations Monitoring Dashboard.

Accepts structured events from Chatwoot, n8n, and AI services,
maps known fields into Postgres tables, stores remaining fields in JSONB metadata.
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import asyncpg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]

# ---------------------------------------------------------------------------
# Pydantic models — required fields only, everything else goes to metadata
# ---------------------------------------------------------------------------

class ChatEventPayload(BaseModel):
    conversation_id: str
    event_type: str
    agent_type: str
    timestamp: Optional[datetime] = None
    inbox: Optional[str] = None
    contact_id: Optional[str] = None

    class Config:
        extra = "allow"


class WorkflowRunPayload(BaseModel):
    workflow_name: str
    execution_id: str
    status: str
    timestamp: Optional[datetime] = None
    duration_ms: Optional[int] = None
    retry_count: Optional[int] = None
    error_type: Optional[str] = None

    class Config:
        extra = "allow"


class AIRequestPayload(BaseModel):
    request_id: str
    provider: str
    model: str
    timestamp: Optional[datetime] = None
    conversation_id: Optional[str] = None
    latency_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    estimated_cost: Optional[float] = None
    schema_valid: Optional[bool] = None
    fallback_used: Optional[bool] = None
    escalated: Optional[bool] = None
    error_type: Optional[str] = None

    class Config:
        extra = "allow"


# ---------------------------------------------------------------------------
# App lifecycle — connection pool
# ---------------------------------------------------------------------------

pool: Optional[asyncpg.Pool] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    yield
    await pool.close()


app = FastAPI(
    title="AI Operations Webhook Receiver",
    description="Thin ingestion layer for monitoring telemetry",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Helper: extract known fields + dump extras to metadata
# ---------------------------------------------------------------------------

def split_payload(payload: BaseModel, known_fields: set[str]) -> tuple[dict, dict]:
    """Split payload into known columns and metadata extras."""
    data = payload.model_dump(exclude_none=True)
    columns = {}
    metadata = {}
    for key, value in data.items():
        if key in known_fields:
            columns[key] = value
        else:
            metadata[key] = value
    return columns, metadata


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/ingest/chat-event")
async def ingest_chat_event(payload: ChatEventPayload):
    known = {"timestamp", "conversation_id", "event_type", "agent_type", "inbox", "contact_id"}
    columns, metadata = split_payload(payload, known)

    try:
        async with pool.acquire() as conn:
            row_id = await conn.fetchval(
                """
                INSERT INTO chat_events (conversation_id, event_type, agent_type, inbox, contact_id, metadata, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, COALESCE($7, NOW()))
                RETURNING id
                """,
                columns["conversation_id"],
                columns["event_type"],
                columns["agent_type"],
                columns.get("inbox"),
                columns.get("contact_id"),
                json.dumps(metadata),
                columns.get("timestamp"),
            )
    except Exception as e:
        logger.exception("Ingestion failed")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"status": "ok", "id": row_id}


@app.post("/ingest/workflow-run")
async def ingest_workflow_run(payload: WorkflowRunPayload):
    known = {"timestamp", "workflow_name", "execution_id", "status", "duration_ms", "retry_count", "error_type"}
    columns, metadata = split_payload(payload, known)

    try:
        async with pool.acquire() as conn:
            row_id = await conn.fetchval(
                """
                INSERT INTO workflow_runs (workflow_name, execution_id, status, duration_ms, retry_count, error_type, metadata, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7, COALESCE($8, NOW()))
                RETURNING id
                """,
                columns["workflow_name"],
                columns["execution_id"],
                columns["status"],
                columns.get("duration_ms"),
                columns.get("retry_count", 0),
                columns.get("error_type"),
                json.dumps(metadata),
                columns.get("timestamp"),
            )
    except Exception as e:
        logger.exception("Ingestion failed")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"status": "ok", "id": row_id}


@app.post("/ingest/ai-request")
async def ingest_ai_request(payload: AIRequestPayload):
    known = {
        "timestamp", "request_id", "conversation_id", "provider", "model",
        "latency_ms", "input_tokens", "output_tokens", "total_tokens", "estimated_cost",
        "schema_valid", "fallback_used", "escalated", "error_type",
    }
    columns, metadata = split_payload(payload, known)

    try:
        async with pool.acquire() as conn:
            row_id = await conn.fetchval(
                """
                INSERT INTO ai_requests (
                    request_id, conversation_id, provider, model,
                    latency_ms, input_tokens, output_tokens, total_tokens, estimated_cost,
                    schema_valid, fallback_used, escalated, error_type, metadata, timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, COALESCE($15, NOW()))
                RETURNING id
                """,
                columns["request_id"],
                columns.get("conversation_id"),
                columns["provider"],
                columns["model"],
                columns.get("latency_ms"),
                columns.get("input_tokens"),
                columns.get("output_tokens"),
                columns.get("total_tokens"),
                columns.get("estimated_cost"),
                columns.get("schema_valid"),
                columns.get("fallback_used", False),
                columns.get("escalated", False),
                columns.get("error_type"),
                json.dumps(metadata),
                columns.get("timestamp"),
            )
    except Exception as e:
        logger.exception("Ingestion failed")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"status": "ok", "id": row_id}
