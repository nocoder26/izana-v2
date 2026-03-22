CREATE TABLE symptom_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  symptoms TEXT[] NOT NULL,
  date DATE NOT NULL DEFAULT CURRENT_DATE,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, date)
);
ALTER TABLE symptom_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their symptom logs" ON symptom_logs FOR ALL USING (auth.uid() = user_id);

CREATE TABLE emotion_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  mood TEXT NOT NULL CHECK (mood IN ('great', 'good', 'okay', 'low', 'struggling')),
  anxiety INTEGER CHECK (anxiety BETWEEN 1 AND 5),
  hope INTEGER CHECK (hope BETWEEN 1 AND 5),
  energy INTEGER CHECK (energy BETWEEN 1 AND 5),
  overwhelm INTEGER CHECK (overwhelm BETWEEN 1 AND 5),
  date DATE NOT NULL DEFAULT CURRENT_DATE,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, date)
);
ALTER TABLE emotion_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their emotion logs" ON emotion_logs FOR ALL USING (auth.uid() = user_id);

CREATE TABLE phase_symptoms (
  id SERIAL PRIMARY KEY,
  phase TEXT NOT NULL,
  category TEXT NOT NULL,
  symptom TEXT NOT NULL,
  severity_default TEXT DEFAULT 'mild',
  UNIQUE(phase, symptom)
);

CREATE TABLE phase_content (
  id SERIAL PRIMARY KEY,
  phase TEXT NOT NULL,
  day_in_phase INTEGER,
  content_type TEXT DEFAULT 'tip',
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  treatment_type TEXT,
  language TEXT DEFAULT 'en'
);

CREATE TABLE population_insights (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phase TEXT NOT NULL,
  day_in_phase INTEGER,
  insight_type TEXT NOT NULL,
  insight_text TEXT NOT NULL,
  sample_size INTEGER,
  percentage DECIMAL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE partner_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  primary_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  partner_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  invite_code TEXT UNIQUE,
  invite_expires_at TIMESTAMPTZ,
  visibility_settings JSONB DEFAULT '{"mood": true, "phase": true, "symptoms": false, "plan_adherence": false}',
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE partner_links ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users see their partner links" ON partner_links
  FOR ALL USING (auth.uid() = primary_user_id OR auth.uid() = partner_user_id);

CREATE TABLE recovery_phrases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  phrase_hash TEXT NOT NULL,
  salt TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id)
);

CREATE TABLE recovery_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pseudonym TEXT NOT NULL,
  ip_address TEXT,
  attempted_at TIMESTAMPTZ DEFAULT now(),
  success BOOLEAN DEFAULT false
);
