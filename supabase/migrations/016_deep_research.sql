-- Deep research results storage
CREATE TABLE IF NOT EXISTS deep_research_results (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  question TEXT NOT NULL,
  model VARCHAR(50) NOT NULL,
  max_tool_calls INT DEFAULT 0,
  report_content TEXT NOT NULL,
  citations JSONB DEFAULT '[]'::jsonb,
  usage JSONB DEFAULT '{}'::jsonb,
  elapsed_seconds FLOAT DEFAULT 0.0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deep_research_case ON deep_research_results(case_id);
CREATE INDEX IF NOT EXISTS idx_deep_research_user ON deep_research_results(user_id);

-- Research sessions for streaming state
CREATE TABLE IF NOT EXISTS deep_research_sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  task_id UUID NOT NULL UNIQUE,
  question TEXT NOT NULL,
  model VARCHAR(50) NOT NULL,
  max_tool_calls INT DEFAULT 0,
  status VARCHAR(20) DEFAULT 'PENDING', -- PENDING | RUNNING | SUCCESS | FAILURE
  last_event_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deep_research_session_case ON deep_research_sessions(case_id);
CREATE INDEX IF NOT EXISTS idx_deep_research_session_task ON deep_research_sessions(task_id);
