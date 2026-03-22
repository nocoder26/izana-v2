-- 009_fie_schema.sql
-- Izana Chat: Fertility Insights Engine (FIE) schema for anonymized
-- feature extraction, ML training data, generated insights,
-- model registry, and data export audit logging.

CREATE SCHEMA IF NOT EXISTS fie;

CREATE TABLE fie.feature_store (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  anonymous_cycle_id TEXT UNIQUE NOT NULL,
  treatment_type TEXT NOT NULL,
  cycle_number INTEGER,
  features_demographic JSONB,
  features_biomarker JSONB,
  features_behavioral JSONB,
  features_treatment JSONB,
  outcome TEXT,
  outcome_binary INTEGER,
  cycle_completed BOOLEAN DEFAULT false,
  data_quality_score DECIMAL,
  extracted_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE fie.training_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  anonymous_cycle_id TEXT NOT NULL,
  feature_vector JSONB NOT NULL,
  target_outcome INTEGER NOT NULL,
  treatment_type TEXT NOT NULL,
  quality_score DECIMAL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE fie.insights (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  insight_type TEXT NOT NULL CHECK (insight_type IN (
    'adherence_outcome_correlation', 'biomarker_behavior_correlation',
    'phase_duration_outcome', 'lifestyle_factor_impact',
    'plan_modification_pattern', 'symptom_outcome_predictor',
    'content_engagement_impact'
  )),
  treatment_type TEXT,
  phase TEXT,
  description TEXT NOT NULL,
  statistical_significance DECIMAL,
  effect_size DECIMAL,
  sample_size INTEGER,
  confidence TEXT CHECK (confidence IN ('low', 'medium', 'high')),
  actionable BOOLEAN DEFAULT false,
  insight_data JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE fie.model_registry (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_name TEXT NOT NULL,
  model_version TEXT NOT NULL,
  treatment_type TEXT,
  algorithm TEXT,
  features_used TEXT[],
  training_samples INTEGER,
  metrics JSONB,
  model_artifact_path TEXT,
  is_active BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE fie.export_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exported_by TEXT NOT NULL,
  record_count INTEGER NOT NULL,
  treatment_type_filter TEXT,
  quality_threshold DECIMAL,
  format TEXT DEFAULT 'jsonl',
  created_at TIMESTAMPTZ DEFAULT now()
);
