-- 007_feedback_training.sql
-- Izana Chat: DPO (Direct Preference Optimization) feedback collection,
-- training data pair storage, daily analytics aggregation, and export logging.

CREATE TABLE dpo_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  message_id TEXT,
  score INTEGER CHECK (score IN (0, 1)),
  category TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE dpo_feedback_details (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  message_id TEXT,
  query TEXT,
  response TEXT,
  issues TEXT[] DEFAULT '{}',
  feedback_text TEXT,
  preferred_response TEXT,
  quality_score DECIMAL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE training_data_pairs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chosen TEXT NOT NULL,
  rejected TEXT NOT NULL,
  query TEXT,
  preference_strength DECIMAL,
  source TEXT DEFAULT 'user_feedback',
  validated BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE dpo_analytics_daily (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  date DATE NOT NULL UNIQUE,
  total_feedback INTEGER DEFAULT 0,
  helpful_count INTEGER DEFAULT 0,
  not_helpful_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE training_export_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exported_by TEXT,
  record_count INTEGER,
  format TEXT DEFAULT 'jsonl',
  filters JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);
