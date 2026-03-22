-- 008_system_tables.sql
-- Izana Chat: Core system infrastructure tables including vector search (pgvector),
-- admin prompt management, knowledge gap tracking, citation/compliance/swarm-health
-- logging, push notifications, nudge queue, provider share links with PHI audit,
-- bloodwork snapshots, and questionnaire state management.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content TEXT NOT NULL,
  embedding vector(384),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(384),
  match_threshold FLOAT,
  match_count INT
)
RETURNS TABLE (id UUID, content TEXT, metadata JSONB, similarity FLOAT)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT documents.id, documents.content, documents.metadata,
    1 - (documents.embedding <=> query_embedding) AS similarity
  FROM documents
  WHERE 1 - (documents.embedding <=> query_embedding) > match_threshold
  ORDER BY documents.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

CREATE TABLE admin_prompts (
  id SERIAL PRIMARY KEY,
  swarm_id TEXT UNIQUE NOT NULL,
  swarm_name TEXT NOT NULL,
  prompt_text TEXT NOT NULL,
  version INTEGER DEFAULT 1,
  updated_at TIMESTAMPTZ DEFAULT now(),
  updated_by TEXT
);

CREATE TABLE knowledge_gaps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  gap_type TEXT NOT NULL,
  query TEXT NOT NULL,
  context JSONB,
  status TEXT DEFAULT 'open' CHECK (status IN ('open', 'reviewed', 'addressed', 'dismissed')),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE citation_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id TEXT,
  document_id UUID REFERENCES documents(id),
  relevance_score DECIMAL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE compliance_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id TEXT,
  checks JSONB NOT NULL,
  passed BOOLEAN,
  fix_attempts INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE swarm_health_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  swarm_id TEXT NOT NULL,
  call_count INTEGER DEFAULT 0,
  error_count INTEGER DEFAULT 0,
  avg_latency_ms DECIMAL,
  p95_latency_ms DECIMAL,
  status TEXT DEFAULT 'healthy',
  recorded_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE push_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  subscription JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their subscriptions" ON push_subscriptions FOR ALL USING (auth.uid() = user_id);

CREATE TABLE nudge_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  nudge_type TEXT NOT NULL,
  channel TEXT NOT NULL DEFAULT 'push' CHECK (channel IN ('push', 'email', 'in_app', 'chat_card')),
  scheduled_for TIMESTAMPTZ NOT NULL,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'cancelled')),
  message_template TEXT,
  message_data JSONB,
  sent_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  type TEXT,
  read BOOLEAN DEFAULT false,
  data JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their notifications" ON notifications FOR ALL USING (auth.uid() = user_id);

CREATE TABLE provider_shares (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  token TEXT UNIQUE NOT NULL,
  include_bloodwork BOOLEAN DEFAULT true,
  include_checkins BOOLEAN DEFAULT true,
  include_timeline BOOLEAN DEFAULT true,
  include_adherence BOOLEAN DEFAULT true,
  valid_days INTEGER DEFAULT 7,
  max_views INTEGER DEFAULT 10,
  current_views INTEGER DEFAULT 0,
  expires_at TIMESTAMPTZ NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE phi_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  share_token TEXT,
  action TEXT NOT NULL,
  ip_address TEXT,
  user_agent TEXT,
  accessed_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE bloodwork_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  biomarkers JSONB NOT NULL,
  trend_data JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE bloodwork_snapshots ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their snapshots" ON bloodwork_snapshots FOR ALL USING (auth.uid() = user_id);

CREATE TABLE questionnaire_states (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  current_step TEXT NOT NULL,
  responses JSONB DEFAULT '{}',
  started_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ,
  UNIQUE(user_id)
);
ALTER TABLE questionnaire_states ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their questionnaire" ON questionnaire_states FOR ALL USING (auth.uid() = user_id);
