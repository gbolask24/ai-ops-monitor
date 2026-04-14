#!/usr/bin/env python3
"""Insert a single AI request into Postgres.

Usage:
    python ingest_ai_request.py '{"request_id": "req-abc", "provider": "anthropic", "model": "claude-sonnet-4-5", "latency_ms": 650}'
"""

import json
import os
import sys

import psycopg2

DATABASE_URL = os.environ["DATABASE_URL_HOST"]

KNOWN_FIELDS = {
    "timestamp", "request_id", "conversation_id", "provider", "model",
    "latency_ms", "input_tokens", "output_tokens", "total_tokens", "estimated_cost",
    "schema_valid", "fallback_used", "escalated", "error_type",
}
REQUIRED_FIELDS = {"request_id", "provider", "model"}


SQL = """
    INSERT INTO ai_requests (
        timestamp, request_id, conversation_id, provider, model,
        latency_ms, input_tokens, output_tokens, total_tokens, estimated_cost,
        schema_valid, fallback_used, escalated, error_type, metadata
    ) VALUES (
        %(timestamp)s, %(request_id)s, %(conversation_id)s, %(provider)s, %(model)s,
        %(latency_ms)s, %(input_tokens)s, %(output_tokens)s, %(total_tokens)s, %(estimated_cost)s,
        %(schema_valid)s, %(fallback_used)s, %(escalated)s, %(error_type)s, %(metadata)s
    )
    RETURNING id
"""


def ingest(payload: dict) -> int:
    """Insert an AI request. Returns the inserted row ID."""
    missing = REQUIRED_FIELDS - payload.keys()
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    metadata = {}
    params = {
        "timestamp": None, "request_id": None, "conversation_id": None,
        "provider": None, "model": None, "latency_ms": None,
        "input_tokens": None, "output_tokens": None, "total_tokens": None,
        "estimated_cost": None, "schema_valid": None, "fallback_used": None,
        "escalated": None, "error_type": None,
    }
    for key, value in payload.items():
        if key in KNOWN_FIELDS:
            params[key] = value
        else:
            metadata[key] = value

    params["metadata"] = json.dumps(metadata)

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(SQL, params)
    row_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return row_id


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} '<json_payload>'")
        sys.exit(1)

    payload = json.loads(sys.argv[1])
    row_id = ingest(payload)
    print(f"Inserted ai_request id={row_id}")
