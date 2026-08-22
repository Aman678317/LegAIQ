-- Deep research events for streaming
CREATE TABLE IF NOT EXISTS deep_research_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID NOT NULL REFERENCES deep_research_sessions(id) ON DELETE CASCADE,
  event_type VARCHAR(100) NOT NULL, -- step.created, message.created, reasoning, etc.
  event_data JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deep_research_events_session ON deep_research_events(session_id);

ALTER TABLE deep_research_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY deep_research_events_user_read
  ON deep_research_events FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM deep_research_sessions s
      WHERE s.id = session_id AND s.user_id = auth.uid()
    )
  );

CREATE POLICY deep_research_events_user_insert
  ON deep_research_events FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM deep_research_sessions s
      WHERE s.id = session_id AND s.user_id = auth.uid()
    )
  );
