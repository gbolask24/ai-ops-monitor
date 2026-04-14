#!/usr/bin/env python3
"""Insert a single chat event into Postgres.

Usage:
    python ingest_chat_event.py '{"conversation_id": "conv-123", "event_type": "ai_reply_sent", "agent_type": "ai"}'
"""

import json
import os
import sys

import psycopg2

DATABASE_URL = os.environ["DATABASE_URL_HOST"]

KNOWN_FIELDS = {"timestamp", "conversation_id", "event_type", "agent_type", "inbox", "contact_id"}
REQUIRED_FIELDS = {"conversation_id", "event_type", "agent_type"}


SQL = """
    INSERT INTO chat_events (timestamp, conversation_id, event_type, agent_type, inbox, contact_id, metadata)
    VALUES (%(timestamp)s, %(conversation_id)s, %(event_type)s, %(agent_type)s, %(inbox)s, %(contact_id)s, %(metadata)s)
    RETURNING id
"""


def ingest(payload: dict) -> int:
    """Insert a chat event. Returns the inserted row ID."""
    missing = REQUIRED_FIELDS - payload.keys()
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    metadata = {}
    params = {"timestamp": None, "conversation_id": None, "event_type": None,
              "agent_type": None, "inbox": None, "contact_id": None}
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
    print(f"Inserted chat_event id={row_id}")
