-- Smoke test seed data: 15 rows to validate schema on startup.
-- Timestamps use NOW() - INTERVAL for relative freshness.

-- ============================================================
-- chat_events: one mini conversation lifecycle
-- ============================================================
INSERT INTO chat_events (timestamp, conversation_id, event_type, agent_type, inbox, contact_id) VALUES
(NOW() - INTERVAL '6 hours', 'conv-seed-001', 'conversation_created', 'system', 'website', 'contact-001'),
(NOW() - INTERVAL '5 hours 50 minutes', 'conv-seed-001', 'ai_reply_sent', 'ai', 'website', 'contact-001'),
(NOW() - INTERVAL '5 hours 30 minutes', 'conv-seed-001', 'human_handoff', 'system', 'website', 'contact-001'),
(NOW() - INTERVAL '5 hours', 'conv-seed-001', 'agent_assigned', 'human', 'website', 'contact-001'),
(NOW() - INTERVAL '4 hours', 'conv-seed-001', 'conversation_resolved', 'human', 'website', 'contact-001');

-- ============================================================
-- workflow_runs: 3 success, 1 failed, 1 retry
-- ============================================================
INSERT INTO workflow_runs (timestamp, workflow_name, execution_id, status, duration_ms, retry_count, error_type) VALUES
(NOW() - INTERVAL '3 hours', 'ticket-classification', 'exec-seed-001', 'success', 450, 0, NULL),
(NOW() - INTERVAL '2 hours 30 minutes', 'auto-response', 'exec-seed-002', 'success', 1200, 0, NULL),
(NOW() - INTERVAL '2 hours', 'customer-onboarding', 'exec-seed-003', 'success', 3400, 0, NULL),
(NOW() - INTERVAL '1 hour 30 minutes', 'invoice-processor', 'exec-seed-004', 'failed', 8500, 0, 'timeout'),
(NOW() - INTERVAL '1 hour', 'invoice-processor', 'exec-seed-005', 'retry', 9200, 1, 'timeout');

-- ============================================================
-- ai_requests: varying providers, one fallback, one schema failure
-- ============================================================
INSERT INTO ai_requests (timestamp, request_id, conversation_id, provider, model, latency_ms, input_tokens, output_tokens, total_tokens, estimated_cost, schema_valid, fallback_used, escalated) VALUES
(NOW() - INTERVAL '5 hours 50 minutes', 'req-seed-001', 'conv-seed-001', 'anthropic', 'claude-sonnet-4-5', 680, 1200, 350, 1550, 0.004650, TRUE, FALSE, FALSE),
(NOW() - INTERVAL '4 hours', 'req-seed-002', 'conv-seed-002', 'openai', 'gpt-4o', 920, 800, 420, 1220, 0.006100, TRUE, FALSE, FALSE),
(NOW() - INTERVAL '3 hours', 'req-seed-003', 'conv-seed-003', 'anthropic', 'claude-haiku-4-5', 210, 600, 150, 750, 0.000375, TRUE, FALSE, FALSE),
(NOW() - INTERVAL '2 hours', 'req-seed-004', 'conv-seed-004', 'openai', 'gpt-4o-mini', 340, 900, 280, 1180, 0.000590, FALSE, FALSE, FALSE),
(NOW() - INTERVAL '1 hour', 'req-seed-005', 'conv-seed-005', 'anthropic', 'claude-sonnet-4-5', 2800, 1500, 0, 1500, 0.004500, NULL, TRUE, TRUE);
