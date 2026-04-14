#!/usr/bin/env python3
"""Insert a single workflow run into Postgres.

Usage:
    python ingest_workflow_run.py '{"workflow_name": "auto-response", "execution_id": "exec-abc", "status": "success", "duration_ms": 1200}'
"""

import json
import os
import sys

import psycopg2

DATABASE_URL = os.environ["DATABASE_URL_HOST"]

KNOWN_FIELDS = {"timestamp", "workflow_name", "execution_id", "status", "duration_ms", "retry_count", "error_type"}
REQUIRED_FIELDS = {"workflow_name", "execution_id", "status"}


SQL = """
    INSERT INTO workflow_runs (timestamp, workflow_name, execution_id, status, duration_ms, retry_count, error_type, metadata)
    VALUES (%(timestamp)s, %(workflow_name)s, %(execution_id)s, %(status)s, %(duration_ms)s, %(retry_count)s, %(error_type)s, %(metadata)s)
    RETURNING id
"""


def ingest(payload: dict) -> int:
    """Insert a workflow run. Returns the inserted row ID."""
    missing = REQUIRED_FIELDS - payload.keys()
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    metadata = {}
    params = {"timestamp": None, "workflow_name": None, "execution_id": None,
              "status": None, "duration_ms": None, "retry_count": None, "error_type": None}
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
    print(f"Inserted workflow_run id={row_id}")
