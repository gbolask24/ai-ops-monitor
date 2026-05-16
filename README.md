# AI Operations Monitoring Dashboard

A lightweight observability layer for AI operations, monitoring chat activity, AI service performance, and workflow execution through structured telemetry flowing into Grafana.

This project demonstrates how AI operations can be monitored in real-time, providing visibility into latency, cost, workflow reliability, and escalation behaviour.

## Architecture

```
Chat platform webhooks ──┐
Workflow engine events ──┤──→ FastAPI webhook receiver ──→ Postgres ──→ Grafana
AI service telemetry ────┘         (port 8001)            (port 5432)    (port 3000)
```

**Ingestion:** Chat platform webhooks, workflow engine events, and AI service telemetry flow into a lightweight FastAPI webhook receiver. Python ingestion and seed scripts support local testing and demo data generation.

**Storage:** Postgres acts as the central metrics store across three core tables: `chat_events`, `workflow_runs`, and `ai_requests`.

**Visualization:** Grafana connects to Postgres as a provisioned datasource, with dashboards authored in the UI, exported, and committed for reproducible provisioning.

**Runtime:** Docker Compose runs Postgres, Grafana, and the webhook receiver. The full stack starts with a single command.

## Key Design Decisions

- **Thin ingestion layer** — the webhook receiver is intentionally simple: accept JSON, map to table, insert, done. No auth, queues, retries, or business logic.
- **Postgres as metrics store** — simple, queryable, sufficient for MVP. Avoids Prometheus/Loki/Tempo complexity.
- **Grafana for operational visibility** — dashboards authored visually, exported as JSON, provisioned automatically on startup.

## Features

- **Conversation monitoring** — track volume, AI replies, agent handoffs, resolution rates
- **AI latency and cost tracking** — avg/p95 latency, token usage, estimated cost by model
- **Workflow health** — success/failure rates, top failing workflows, duration analysis
- **Escalation visibility** — escalation and fallback trends over time
- **Validation quality** — schema pass rate and error tracking
- **Incident table** — unified view of recent failures across all systems
- **Operational optimization** — slowest workflows and most expensive models

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for seed script)

### Setup

```bash
# 1. Clone and configure
git clone <repo-url>
cd ai-operations-monitoring-dashboard
cp .env.example .env

# 2. Start infrastructure
docker compose up -d

# 3. Seed realistic demo data
pip install -r scripts/requirements.txt
python scripts/seed_data.py

# 4. Open Grafana
# http://localhost:3000  (login: admin / admin)
```

The database schema and a small smoke test seed (`db/seed.sql`) load automatically on first startup. The `seed_data.py` script adds 300-400 rows of realistic operational data spread over the last 7 days.

## Dashboard Walkthrough

The main dashboard contains 8 panels across 3 rows:

### Overview Row
| Panel | What it answers |
|---|---|
| **Conversation Overview** | How many conversations are we handling? How many go to AI vs human agents? |
| **AI Response Latency** | What's our avg and p95 latency? Any degradation trends? |
| **Workflow Health** | Are our workflows running reliably? Which ones fail most? |

### Analysis Row
| Panel | What it answers |
|---|---|
| **Token & Cost Usage** | How much are we spending on LLM calls? Which models cost most? |
| **Escalation & Fallback** | Are escalation and fallback rates trending up or down? |
| **Validation Quality** | Are our AI responses schema-valid? Where are errors appearing? |

### Operations Row
| Panel | What it answers |
|---|---|
| **Recent Incidents** | What just went wrong? Unified view across chat, workflow, and AI systems. |
| **Slowest & Most Expensive** | Where should we optimize? Top workflows by duration, models by cost. |

Dashboard variables (provider, model, workflow, inbox, status) allow filtering across all panels.

## Connecting Real Systems

The webhook receiver accepts generic JSON payloads, making it compatible with chat platform webhooks, workflow engine callbacks, or direct AI service telemetry without requiring strict schemas.

### Chat Platform

Configure a webhook in your chat platform pointing at:

```
http://<host>:8001/ingest/chat-event
```

Payload example:

```json
{
  "conversation_id": "12345",
  "event_type": "ai_reply_sent",
  "agent_type": "ai",
  "inbox": "website"
}
```

### Workflow Engine

Add an HTTP request step at the end of workflows:

```
POST http://<host>:8001/ingest/workflow-run

{
  "workflow_name": "auto-response",
  "execution_id": "exec-abc-123",
  "status": "success",
  "duration_ms": 1500
}
```

### AI Service Telemetry

After each LLM call, POST telemetry:

```python
import httpx

httpx.post("http://<host>:8001/ingest/ai-request", json={
    "request_id": "req-abc-123",
    "provider": "anthropic",
    "model": "claude-sonnet-4-5",
    "latency_ms": 650,
    "input_tokens": 1200,
    "output_tokens": 350,
    "estimated_cost": 0.00465,
    "schema_valid": True,
})
```

Any fields not matching known columns are stored in the JSONB `metadata` column.

## Data Model

| Table | Purpose | Key fields |
|---|---|---|
| `chat_events` | Conversation activity from chat platforms | `conversation_id`, `event_type`, `agent_type`, `inbox` |
| `workflow_runs` | Workflow execution telemetry | `workflow_name`, `execution_id`, `status`, `duration_ms` |
| `ai_requests` | LLM / AI service metrics | `provider`, `model`, `latency_ms`, `estimated_cost`, `schema_valid` |

Full schema: [`db/init.sql`](db/init.sql)

## Tech Stack

| Layer | Technology |
|---|---|
| **Infrastructure** | Docker Compose, Postgres 16 |
| **Backend** | Python 3.11+, FastAPI, asyncpg, psycopg2 |
| **Observability** | Grafana 11 |

## Limitations

This is an MVP. Current limitations:

- Event ingestion is simplified — no batching, buffering, or guaranteed delivery
- No alerting rules configured
- No distributed tracing (no trace/span IDs)
- No authentication on the webhook receiver
- Seed data is synthetic (but realistically distributed)
- Single Grafana dashboard (no drill-down views)

## Future Improvements

- **Alerting** — Grafana alerting rules for latency spikes, failure rate thresholds, cost anomalies
- **Prometheus/Loki** — Complementary metrics and log aggregation alongside Postgres
- **Anomaly detection** — Statistical anomaly detection on latency and failure trends
- **Multi-dashboard** — Separate dashboards for incident detail, cost analysis, workflow deep-dive
- **Auth** — API key or token authentication on the webhook receiver
- **Rate limiting** — Protect the ingestion endpoint from abuse
- **Batch ingestion** — Accept arrays of events for higher throughput
- **Real-time** — WebSocket or SSE for live dashboard updates

## Project Structure

```
ai-operations-monitoring-dashboard/
├── docker-compose.yml          # Orchestrates Postgres, Grafana, webhook receiver
├── .env.example                # Environment variable template
├── README.md
├── db/
│   ├── init.sql                # Database schema and indexes
│   └── seed.sql                # Smoke test seed data (15 rows)
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── postgres.yml    # Auto-configure Postgres datasource
│   │   └── dashboards/
│   │       └── dashboards.yml  # Auto-discover dashboard JSON
│   └── dashboards/
│       └── ai_operations_dashboard.json
├── scripts/
│   ├── requirements.txt
│   ├── seed_data.py            # Realistic demo data generator
│   ├── ingest_chat_event.py    # Insert single chat event
│   ├── ingest_workflow_run.py  # Insert single workflow run
│   └── ingest_ai_request.py   # Insert single AI request
└── app/
    ├── Dockerfile
    ├── requirements.txt
    └── webhook_receiver.py     # FastAPI ingestion service
```
