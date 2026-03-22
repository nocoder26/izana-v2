CREATE TABLE personalized_plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  nutrition_plan JSONB NOT NULL DEFAULT '{}',
  exercise_plan JSONB NOT NULL DEFAULT '{}',
  mental_health_plan JSONB NOT NULL DEFAULT '{}',
  exercise_content_ids UUID[] DEFAULT '{}',
  meditation_content_ids UUID[] DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'PENDING_NUTRITIONIST' CHECK (status IN (
    'GENERATING', 'PENDING_NUTRITIONIST', 'IN_REVIEW',
    'APPROVED', 'MODIFIED', 'REJECTED', 'EXPIRED'
  )),
  source TEXT DEFAULT 'ai_generated' CHECK (source IN ('ai_generated', 'nutritionist_modified')),
  parent_plan_id UUID REFERENCES personalized_plans(id),
  version INTEGER DEFAULT 1,
  treatment_type TEXT,
  phase TEXT,
  generation_context JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE personalized_plans ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their plans" ON personalized_plans FOR ALL USING (auth.uid() = user_id);

ALTER TABLE chapters ADD CONSTRAINT fk_chapters_plan
  FOREIGN KEY (plan_snapshot_id) REFERENCES personalized_plans(id);

CREATE TABLE approval_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id UUID NOT NULL REFERENCES personalized_plans(id),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'ASSIGNED', 'IN_REVIEW', 'COMPLETED')),
  priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('normal', 'urgent_phase_change', 'positive_outcome')),
  assigned_to UUID,
  adaptation_context JSONB,
  deadline TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_approval_queue_status_priority ON approval_queue(status, priority, created_at);

CREATE TABLE plan_modifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id UUID NOT NULL REFERENCES personalized_plans(id),
  section TEXT NOT NULL,
  field_path TEXT NOT NULL,
  ai_original TEXT,
  human_modified TEXT,
  reason TEXT,
  category TEXT,
  severity TEXT CHECK (severity IN ('minor', 'moderate', 'major', 'critical')),
  could_cause_harm BOOLEAN DEFAULT false,
  training_eligible BOOLEAN DEFAULT true,
  reviewer_id UUID,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE plan_review_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id UUID NOT NULL REFERENCES personalized_plans(id),
  action TEXT NOT NULL,
  reviewer_id UUID,
  details JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE meal_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  meal_type TEXT NOT NULL,
  description TEXT,
  followed_plan BOOLEAN,
  satisfaction INTEGER CHECK (satisfaction BETWEEN 1 AND 5),
  offline_sync BOOLEAN DEFAULT false,
  logged_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, meal_type, (logged_at::date))
);
ALTER TABLE meal_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their meal logs" ON meal_logs FOR ALL USING (auth.uid() = user_id);

CREATE TABLE activity_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  activity_type TEXT NOT NULL,
  content_id UUID,
  duration_minutes INTEGER,
  completion_pct DECIMAL DEFAULT 100,
  offline_sync BOOLEAN DEFAULT false,
  logged_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their activity logs" ON activity_logs FOR ALL USING (auth.uid() = user_id);

CREATE TABLE admin_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'NUTRITIONIST' CHECK (role IN ('NUTRITIONIST', 'ADMIN')),
  password_hash TEXT,
  is_active BOOLEAN DEFAULT true,
  last_login_at TIMESTAMPTZ,
  plans_reviewed_count INTEGER DEFAULT 0,
  avg_review_minutes DECIMAL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
