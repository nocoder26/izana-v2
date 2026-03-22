-- 010_chat_traces.sql
-- Izana Chat: Observability layer (Decision 10) for per-swarm call logging,
-- debugging, and cost tracking across the AI agent swarm architecture.

-- Chat traces for per-swarm call logging, debugging, cost tracking
CREATE TABLE chat_traces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trace_id UUID NOT NULL,
  message_id TEXT,
  swarm_id TEXT NOT NULL,
  input_text TEXT,
  output_text TEXT,
  model TEXT,
  tokens_in INTEGER,
  tokens_out INTEGER,
  latency_ms INTEGER,
  error TEXT,
  retry_count INTEGER DEFAULT 0,
  fallback_used BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_chat_traces_trace ON chat_traces(trace_id);
CREATE INDEX idx_chat_traces_message ON chat_traces(message_id);
CREATE INDEX idx_chat_traces_swarm ON chat_traces(swarm_id, created_at DESC);
