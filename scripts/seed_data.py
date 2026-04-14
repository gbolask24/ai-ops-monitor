#!/usr/bin/env python3
"""
Realistic seed data generator for AI Operations Monitoring Dashboard.

Generates 300-400 rows across chat_events, workflow_runs, and ai_requests
with realistic time patterns, failure rates, and operational behaviour.

Usage:
    python seed_data.py              # Truncate tables first, then seed
    python seed_data.py --append     # Append without truncating
"""

import argparse
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

import psycopg2

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL = os.environ["DATABASE_URL_HOST"]

NUM_CONVERSATIONS = 50
NUM_WORKFLOW_RUNS = 150
NUM_AI_REQUESTS = 160
DAYS_BACK = 7

# Provider/model definitions with latency and cost profiles
MODELS = [
    {"provider": "anthropic", "model": "claude-sonnet-4-5", "weight": 0.30,
     "latency_base": 600, "latency_range": 600, "cost_per_1k_input": 0.003, "cost_per_1k_output": 0.015},
    {"provider": "anthropic", "model": "claude-haiku-4-5", "weight": 0.28,
     "latency_base": 180, "latency_range": 220, "cost_per_1k_input": 0.0008, "cost_per_1k_output": 0.004},
    {"provider": "openai", "model": "gpt-4o", "weight": 0.18,
     "latency_base": 500, "latency_range": 700, "cost_per_1k_input": 0.0025, "cost_per_1k_output": 0.01},
    {"provider": "openai", "model": "gpt-4o-mini", "weight": 0.16,
     "latency_base": 200, "latency_range": 200, "cost_per_1k_input": 0.00015, "cost_per_1k_output": 0.0006},
    {"provider": "gemini", "model": "gemini-2.0-flash", "weight": 0.08,
     "latency_base": 190, "latency_range": 210, "cost_per_1k_input": 0.0001, "cost_per_1k_output": 0.0004},
]

WORKFLOWS = [
    {"name": "customer-onboarding", "base_duration": 2500, "duration_range": 2000, "failure_rate": 0.08},
    {"name": "ticket-classification", "base_duration": 300, "duration_range": 400, "failure_rate": 0.05},
    {"name": "sentiment-analysis", "base_duration": 400, "duration_range": 300, "failure_rate": 0.06},
    {"name": "auto-response", "base_duration": 800, "duration_range": 600, "failure_rate": 0.07},
    {"name": "escalation-handler", "base_duration": 1500, "duration_range": 2500, "failure_rate": 0.20},
    {"name": "feedback-collector", "base_duration": 500, "duration_range": 400, "failure_rate": 0.04},
    {"name": "invoice-processor", "base_duration": 4000, "duration_range": 4000, "failure_rate": 0.20},
    {"name": "knowledge-sync", "base_duration": 2000, "duration_range": 3000, "failure_rate": 0.10},
]

INBOXES = ["website", "email", "whatsapp", "api"]

ERROR_TYPES_WORKFLOW = ["timeout", "connection_error", "validation_error", "rate_limit", "internal_error"]
ERROR_TYPES_AI = ["timeout", "rate_limit", "context_length_exceeded", "provider_error", "invalid_response"]

# Incident bursts: (days_ago, hour, duration_minutes)
INCIDENT_BURSTS = [
    (2, 14, 45),   # 2 days ago at 2pm, lasting 45 min
    (4, 10, 30),   # 4 days ago at 10am, lasting 30 min
    (6, 16, 60),   # 6 days ago at 4pm, lasting 60 min
]

# ---------------------------------------------------------------------------
# Time generation
# ---------------------------------------------------------------------------

def generate_timestamp(days_back: int = DAYS_BACK) -> datetime:
    """Generate a realistic timestamp with business-hour and weekday weighting."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days_back)

    while True:
        # Pick a random point in the time range
        offset_seconds = random.randint(0, int(days_back * 86400))
        ts = start + timedelta(seconds=offset_seconds)

        hour = ts.hour
        weekday = ts.weekday()  # 0=Monday, 6=Sunday

        # Business hours (9-18) get 3x weight
        if 9 <= hour <= 18:
            weight = 0.9
        elif 7 <= hour <= 21:
            weight = 0.4
        else:
            weight = 0.15

        # Weekdays get 2x weight over weekends
        if weekday >= 5:
            weight *= 0.5

        if random.random() < weight:
            return ts


def is_during_incident(ts: datetime) -> bool:
    """Check if a timestamp falls within an incident burst window."""
    now = datetime.now(timezone.utc)
    for days_ago, burst_hour, duration_min in INCIDENT_BURSTS:
        burst_start = (now - timedelta(days=days_ago)).replace(
            hour=burst_hour, minute=0, second=0, microsecond=0
        )
        burst_end = burst_start + timedelta(minutes=duration_min)
        if burst_start <= ts <= burst_end:
            return True
    return False


# ---------------------------------------------------------------------------
# Data generators
# ---------------------------------------------------------------------------

def pick_model() -> dict:
    """Pick a model based on configured weights."""
    r = random.random()
    cumulative = 0.0
    for m in MODELS:
        cumulative += m["weight"]
        if r <= cumulative:
            return m
    return MODELS[-1]


def generate_conversations() -> list[dict]:
    """Generate chat_events for realistic conversation lifecycles."""
    events = []
    conversation_ids = [f"conv-{uuid.uuid4().hex[:8]}" for _ in range(NUM_CONVERSATIONS)]

    for conv_id in conversation_ids:
        inbox = random.choice(INBOXES)
        contact_id = f"contact-{uuid.uuid4().hex[:8]}"
        base_ts = generate_timestamp()

        # Every conversation starts with creation
        events.append({
            "timestamp": base_ts,
            "conversation_id": conv_id,
            "event_type": "conversation_created",
            "agent_type": "system",
            "inbox": inbox,
            "contact_id": contact_id,
        })

        # AI replies (1-3)
        num_replies = random.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]
        current_ts = base_ts
        for i in range(num_replies):
            current_ts = current_ts + timedelta(minutes=random.randint(1, 10))
            events.append({
                "timestamp": current_ts,
                "conversation_id": conv_id,
                "event_type": "ai_reply_sent",
                "agent_type": "ai",
                "inbox": inbox,
                "contact_id": contact_id,
            })

        # ~12% get human handoff
        is_handoff = random.random() < 0.12
        if is_handoff:
            current_ts = current_ts + timedelta(minutes=random.randint(2, 15))
            events.append({
                "timestamp": current_ts,
                "conversation_id": conv_id,
                "event_type": "human_handoff",
                "agent_type": "system",
                "inbox": inbox,
                "contact_id": contact_id,
            })
            current_ts = current_ts + timedelta(minutes=random.randint(1, 5))
            events.append({
                "timestamp": current_ts,
                "conversation_id": conv_id,
                "event_type": "agent_assigned",
                "agent_type": "human",
                "inbox": inbox,
                "contact_id": contact_id,
            })

        # ~90% get resolved
        if random.random() < 0.90:
            current_ts = current_ts + timedelta(minutes=random.randint(5, 60))
            resolver = "human" if is_handoff else "ai"
            events.append({
                "timestamp": current_ts,
                "conversation_id": conv_id,
                "event_type": "conversation_resolved",
                "agent_type": resolver,
                "inbox": inbox,
                "contact_id": contact_id,
            })

    return events


def generate_workflow_runs() -> list[dict]:
    """Generate workflow_runs with realistic status and duration patterns."""
    runs = []

    for _ in range(NUM_WORKFLOW_RUNS):
        wf = random.choice(WORKFLOWS)
        ts = generate_timestamp()
        incident = is_during_incident(ts)

        # Determine status — higher failure during incidents
        failure_rate = wf["failure_rate"] * (3.0 if incident else 1.0)
        failure_rate = min(failure_rate, 0.6)

        r = random.random()
        if r < failure_rate:
            status = "failed"
            error_type = random.choice(ERROR_TYPES_WORKFLOW)
        elif r < failure_rate + 0.05:
            status = "retry"
            error_type = random.choice(["timeout", "rate_limit"])
        else:
            status = "success"
            error_type = None

        # Duration: failures and retries tend to be longer
        base = wf["base_duration"]
        rng = wf["duration_range"]
        duration = base + random.randint(0, rng)
        if status == "failed":
            duration = int(duration * random.uniform(1.5, 3.0))
        elif status == "retry":
            duration = int(duration * random.uniform(1.2, 2.0))
        if incident:
            duration = int(duration * random.uniform(1.3, 2.0))

        retry_count = 0
        if status == "retry":
            retry_count = random.randint(1, 3)

        runs.append({
            "timestamp": ts,
            "workflow_name": wf["name"],
            "execution_id": f"exec-{uuid.uuid4().hex[:12]}",
            "status": status,
            "duration_ms": duration,
            "retry_count": retry_count,
            "error_type": error_type,
        })

    return runs


def generate_ai_requests(conversations: list[dict]) -> list[dict]:
    """Generate ai_requests correlated with conversation events."""
    requests = []

    # Get conversation IDs that had AI replies
    ai_reply_events = [e for e in conversations if e["event_type"] == "ai_reply_sent"]
    # Get conversation IDs that had handoffs (these should correlate with escalations)
    handoff_conv_ids = {e["conversation_id"] for e in conversations if e["event_type"] == "human_handoff"}

    for i in range(NUM_AI_REQUESTS):
        model_info = pick_model()
        ts = generate_timestamp()
        incident = is_during_incident(ts)

        # Link some requests to conversation AI replies
        conv_id = None
        is_escalated = False
        if i < len(ai_reply_events):
            event = ai_reply_events[i]
            ts = event["timestamp"]
            conv_id = event["conversation_id"]
            is_escalated = conv_id in handoff_conv_ids
        elif random.random() < 0.6:
            conv_id = f"conv-{uuid.uuid4().hex[:8]}"

        # Latency
        latency = model_info["latency_base"] + random.randint(0, model_info["latency_range"])
        if incident:
            latency = int(latency * random.uniform(2.0, 5.0))

        # Tokens
        input_tokens = random.randint(200, 2000)
        output_tokens = random.randint(50, 800)
        total_tokens = input_tokens + output_tokens

        # Cost
        cost = (
            (input_tokens / 1000) * model_info["cost_per_1k_input"]
            + (output_tokens / 1000) * model_info["cost_per_1k_output"]
        )
        cost = round(cost, 6)

        # Schema validity: ~92% valid, higher failure during incidents
        schema_fail_rate = 0.20 if incident else 0.08
        schema_valid = random.random() > schema_fail_rate

        # Fallback: ~8%, higher during incidents
        fallback_rate = 0.25 if incident else 0.08
        fallback_used = random.random() < fallback_rate

        # Error type: linked to fallback or incident
        error_type = None
        if fallback_used:
            error_type = random.choice(ERROR_TYPES_AI)
        elif incident and random.random() < 0.3:
            error_type = random.choice(["timeout", "provider_error"])

        # Escalation: ~5% base, correlated with handoff conversations
        escalated = is_escalated or (random.random() < 0.05)

        requests.append({
            "timestamp": ts,
            "request_id": f"req-{uuid.uuid4().hex[:12]}",
            "conversation_id": conv_id,
            "provider": model_info["provider"],
            "model": model_info["model"],
            "latency_ms": latency,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost": cost,
            "schema_valid": schema_valid,
            "fallback_used": fallback_used,
            "escalated": escalated,
            "error_type": error_type,
        })

    return requests


# ---------------------------------------------------------------------------
# Database insertion
# ---------------------------------------------------------------------------

def insert_chat_events(cur, events: list[dict]) -> int:
    """Insert chat events into Postgres. Returns count inserted."""
    sql = """
        INSERT INTO chat_events (timestamp, conversation_id, event_type, agent_type, inbox, contact_id)
        VALUES (%(timestamp)s, %(conversation_id)s, %(event_type)s, %(agent_type)s, %(inbox)s, %(contact_id)s)
    """
    for event in events:
        cur.execute(sql, event)
    return len(events)


def insert_workflow_runs(cur, runs: list[dict]) -> int:
    """Insert workflow runs into Postgres. Returns count inserted."""
    sql = """
        INSERT INTO workflow_runs (timestamp, workflow_name, execution_id, status, duration_ms, retry_count, error_type)
        VALUES (%(timestamp)s, %(workflow_name)s, %(execution_id)s, %(status)s, %(duration_ms)s, %(retry_count)s, %(error_type)s)
    """
    for run in runs:
        cur.execute(sql, run)
    return len(runs)


def insert_ai_requests(cur, requests: list[dict]) -> int:
    """Insert AI requests into Postgres. Returns count inserted."""
    sql = """
        INSERT INTO ai_requests (
            timestamp, request_id, conversation_id, provider, model,
            latency_ms, input_tokens, output_tokens, total_tokens, estimated_cost,
            schema_valid, fallback_used, escalated, error_type
        ) VALUES (
            %(timestamp)s, %(request_id)s, %(conversation_id)s, %(provider)s, %(model)s,
            %(latency_ms)s, %(input_tokens)s, %(output_tokens)s, %(total_tokens)s, %(estimated_cost)s,
            %(schema_valid)s, %(fallback_used)s, %(escalated)s, %(error_type)s
        )
    """
    for req in requests:
        cur.execute(sql, req)
    return len(requests)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Seed realistic monitoring data")
    parser.add_argument("--append", action="store_true", help="Append data without truncating existing rows")
    args = parser.parse_args()

    print("Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    if not args.append:
        print("Truncating existing data...")
        cur.execute("TRUNCATE chat_events, workflow_runs, ai_requests RESTART IDENTITY")
        conn.commit()

    print("Generating conversation data...")
    chat_events = generate_conversations()

    print("Generating workflow runs...")
    workflow_runs = generate_workflow_runs()

    print("Generating AI requests...")
    ai_requests = generate_ai_requests(chat_events)

    print("Inserting chat events...")
    chat_count = insert_chat_events(cur, chat_events)

    print("Inserting workflow runs...")
    workflow_count = insert_workflow_runs(cur, workflow_runs)

    print("Inserting AI requests...")
    ai_count = insert_ai_requests(cur, ai_requests)

    conn.commit()
    cur.close()
    conn.close()

    total = chat_count + workflow_count + ai_count
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=DAYS_BACK)

    print(f"\n{'='*50}")
    print(f"Seed complete!")
    print(f"{'='*50}")
    print(f"  chat_events:   {chat_count:>6} rows")
    print(f"  workflow_runs:  {workflow_count:>6} rows")
    print(f"  ai_requests:   {ai_count:>6} rows")
    print(f"  {'-'*30}")
    print(f"  total:         {total:>6} rows")
    print(f"  time range:    {start.strftime('%Y-%m-%d %H:%M')} -> {now.strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
