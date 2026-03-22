CREATE TABLE chat_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  chapter_id UUID REFERENCES chapters(id),
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  message_type TEXT DEFAULT 'text' CHECK (message_type IN (
    'text', 'checkin_card', 'plan_card', 'summary_card',
    'transition_card', 'partner_card', 'celebration_card',
    'bloodwork_card', 'content_card', 'plan_status_card',
    'week_summary_card'
  )),
  card_data JSONB,
  week_number INTEGER,
  retain BOOLEAN DEFAULT false,
  sources JSONB DEFAULT '[]',
  suggested_followups TEXT[] DEFAULT '{}',
  message_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE chat_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their chat logs" ON chat_logs FOR ALL USING (auth.uid() = user_id);
CREATE INDEX idx_chat_logs_user ON chat_logs(user_id, created_at DESC);
CREATE INDEX idx_chat_logs_chapter ON chat_logs(chapter_id, week_number);
CREATE INDEX idx_chat_logs_message_id ON chat_logs(message_id);

CREATE TABLE chat_summaries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  chapter_id UUID REFERENCES chapters(id),
  session_id TEXT,
  summary_text TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE chat_summaries ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their summaries" ON chat_summaries FOR ALL USING (auth.uid() = user_id);

CREATE TABLE chat_logs_archive (LIKE chat_logs INCLUDING ALL);
ALTER TABLE chat_logs_archive ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their archived logs" ON chat_logs_archive FOR ALL USING (auth.uid() = user_id);

CREATE TABLE chapter_summaries_weekly (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chapter_id UUID NOT NULL REFERENCES chapters(id),
  week_number INTEGER NOT NULL,
  summary_text TEXT,
  stats JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(chapter_id, week_number)
);
