CREATE TABLE cycles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  treatment_type TEXT NOT NULL,
  cycle_number INTEGER NOT NULL DEFAULT 1,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  outcome TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE cycles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their cycles" ON cycles FOR ALL USING (auth.uid() = user_id);
CREATE INDEX idx_cycles_user ON cycles(user_id);

CREATE TABLE treatment_journeys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  cycle_id UUID REFERENCES cycles(id),
  treatment_type TEXT NOT NULL,
  phase TEXT NOT NULL,
  stim_day INTEGER,
  is_active BOOLEAN DEFAULT true,
  started_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  cycle_start_date DATE,
  expected_retrieval_date DATE,
  expected_transfer_date DATE,
  outcome TEXT,
  outcome_date DATE,
  outcome_emotions TEXT[],
  outcome_notes TEXT
);
ALTER TABLE treatment_journeys ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their journeys" ON treatment_journeys FOR ALL USING (auth.uid() = user_id);

CREATE TABLE chapters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  journey_id UUID REFERENCES treatment_journeys(id),
  cycle_id UUID REFERENCES cycles(id),
  phase TEXT NOT NULL,
  day_count INTEGER DEFAULT 1,
  week_count INTEGER DEFAULT 1,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at TIMESTAMPTZ,
  expected_duration_days INTEGER,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'grief', 'positive')),
  plan_snapshot_id UUID,
  summary_text TEXT,
  grief_mode BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE chapters ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their chapters" ON chapters FOR ALL USING (auth.uid() = user_id);
CREATE INDEX idx_chapters_user_active ON chapters(user_id) WHERE status = 'active';
CREATE INDEX idx_chapters_user ON chapters(user_id);

CREATE TABLE phase_durations (
  id SERIAL PRIMARY KEY,
  treatment_type TEXT NOT NULL,
  phase TEXT NOT NULL,
  avg_days INTEGER NOT NULL,
  min_days INTEGER NOT NULL,
  max_days INTEGER NOT NULL,
  transition_prompt_template TEXT,
  soft_checkin_pct DECIMAL DEFAULT 0.8,
  transition_prompt_pct DECIMAL DEFAULT 1.0,
  followup_interval_days INTEGER DEFAULT 2,
  UNIQUE(treatment_type, phase)
);
