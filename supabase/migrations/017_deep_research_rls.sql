-- Enable RLS
ALTER TABLE deep_research_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE deep_research_sessions ENABLE ROW LEVEL SECURITY;

-- Users can read their own deep research results
CREATE POLICY deep_research_user_read
  ON deep_research_results FOR SELECT
  USING (auth.uid() = user_id);

-- Users can create their own research results
CREATE POLICY deep_research_user_insert
  ON deep_research_results FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can read their own sessions
CREATE POLICY deep_research_session_user_read
  ON deep_research_sessions FOR SELECT
  USING (auth.uid() = user_id);

-- Users can insert their own sessions
CREATE POLICY deep_research_session_user_insert
  ON deep_research_sessions FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can update their own sessions
CREATE POLICY deep_research_session_user_update
  ON deep_research_sessions FOR UPDATE
  USING (auth.uid() = user_id);
