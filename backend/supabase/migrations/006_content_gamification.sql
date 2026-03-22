-- 006_content_gamification.sql
-- Izana Chat: Wellness content library, user progress tracking, ratings,
-- gamification (points, levels, streaks, badges), and couple goals.

CREATE TABLE wellness_content (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT,
  content_type TEXT NOT NULL CHECK (content_type IN ('exercise_video', 'meditation_audio', 'breathing_exercise', 'yoga_video', 'article', 'audio_guide')),
  duration_seconds INTEGER,
  cloudflare_stream_id TEXT,
  thumbnail_url TEXT,
  intensity TEXT CHECK (intensity IN ('gentle', 'light', 'moderate', 'active')),
  plan_eligible BOOLEAN DEFAULT false,
  treatment_phases TEXT[] DEFAULT '{}',
  treatment_types TEXT[] DEFAULT '{}',
  contraindications TEXT[] DEFAULT '{}',
  categories TEXT[] DEFAULT '{}',
  partner_suitable BOOLEAN DEFAULT false,
  grief_appropriate BOOLEAN DEFAULT false,
  early_pregnancy_safe BOOLEAN DEFAULT false,
  translations JSONB DEFAULT '{}',
  is_active BOOLEAN DEFAULT true,
  sort_order INTEGER DEFAULT 0,
  version INTEGER DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE content_progress (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  content_id UUID NOT NULL REFERENCES wellness_content(id),
  progress_pct DECIMAL DEFAULT 0,
  position_seconds INTEGER DEFAULT 0,
  completed BOOLEAN DEFAULT false,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, content_id)
);
ALTER TABLE content_progress ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their progress" ON content_progress FOR ALL USING (auth.uid() = user_id);

CREATE TABLE content_ratings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  content_id UUID NOT NULL REFERENCES wellness_content(id),
  rating INTEGER CHECK (rating BETWEEN 1 AND 5),
  feedback TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, content_id)
);
ALTER TABLE content_ratings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their ratings" ON content_ratings FOR ALL USING (auth.uid() = user_id);

CREATE TABLE user_gamification (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  total_points INTEGER DEFAULT 0,
  level INTEGER DEFAULT 1,
  level_name TEXT DEFAULT 'Beginner',
  current_streak INTEGER DEFAULT 0,
  longest_streak INTEGER DEFAULT 0,
  couple_streak INTEGER DEFAULT 0,
  level_progress DECIMAL DEFAULT 0,
  version INTEGER DEFAULT 1,
  updated_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE user_gamification ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their gamification" ON user_gamification FOR ALL USING (auth.uid() = user_id);

CREATE TABLE badges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  category TEXT NOT NULL,
  criteria JSONB NOT NULL,
  icon TEXT,
  sort_order INTEGER DEFAULT 0
);

CREATE TABLE user_badges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  badge_id UUID NOT NULL REFERENCES badges(id),
  earned_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, badge_id)
);
ALTER TABLE user_badges ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their badges" ON user_badges FOR ALL USING (auth.uid() = user_id);

CREATE TABLE couple_goals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  primary_user_id UUID NOT NULL REFERENCES auth.users(id),
  partner_user_id UUID REFERENCES auth.users(id),
  goal_type TEXT NOT NULL,
  target INTEGER NOT NULL,
  progress_primary INTEGER DEFAULT 0,
  progress_partner INTEGER DEFAULT 0,
  deadline DATE,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);
