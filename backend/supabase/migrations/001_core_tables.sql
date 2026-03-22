-- Profiles (extends Supabase auth.users)
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  pseudonym TEXT UNIQUE NOT NULL,
  gender TEXT NOT NULL CHECK (gender IN ('Male', 'Female')),
  treatment_path TEXT,
  language TEXT DEFAULT 'en',
  avatar TEXT DEFAULT 'Phoenix',
  timezone TEXT DEFAULT 'UTC',
  consent_timestamp TIMESTAMPTZ,
  consent_version TEXT DEFAULT '2.0',
  core_fertility_json JSONB DEFAULT '{}',
  extended_bloodwork_json JSONB DEFAULT '{}',
  bloodwork_analysis_json JSONB DEFAULT '[]',
  report_history JSONB DEFAULT '[]',
  age_range TEXT,
  health_conditions TEXT[] DEFAULT '{}',
  height_cm DECIMAL,
  weight_kg DECIMAL,
  bmi DECIMAL,
  fitness_level TEXT,
  smoking_status TEXT,
  alcohol_consumption TEXT,
  sleep_duration TEXT,
  sleep_quality TEXT,
  stress_level TEXT,
  hydration TEXT,
  digestion_issues TEXT[] DEFAULT '{}',
  allergies TEXT[] DEFAULT '{}',
  dietary_restrictions TEXT[] DEFAULT '{}',
  food_preferences TEXT[] DEFAULT '{}',
  food_dislikes TEXT,
  exercise_time_minutes INTEGER,
  exercise_preferences TEXT[] DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their profile" ON profiles FOR ALL USING (auth.uid() = id);

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profiles_updated_at BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
