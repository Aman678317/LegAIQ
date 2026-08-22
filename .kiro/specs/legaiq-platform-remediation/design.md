# Design: LegAIQ Legal Intelligence Platform Remediation

**Feature**: legaiq-platform-remediation  
**Version**: 1.0  
**Date**: 2025-04-05  
**Status**: DESIGN

---

## 1. Overview

This design document addresses three categories of critical issues in the LegAIQ Legal Intelligence Platform:

### Priority 1: Integration Failures (BLOCKING)
- Deep Research Streamlit isolation
- Document viewer authentication failures  
- BSA Section 63 cryptographic hashing missing

### Priority 2: Feature Enhancements
- OCR bilingual document handling
- Entity resolution for Indian date formats
- Celery worker caching

### Priority 3: Production Hardening
- Multi-agent orchestration
- BigLaw bench schema alignment

This design maintains the existing architecture while implementing targeted enhancements.

---

## 2. Architecture Overview

### Current State
```
FastAPI Backend (26+ routers)
├── Supabase PostgreSQL (15 migrations)
├── Celery Workers (stateless)
├── LLM Providers (Groq, NVIDIA, OpenAI, Anthropic, Ollama)
└── Storage (Supabase case-documents bucket)

Frontend (Next.js 15 App Router)
├── Cases, Chat, Contracts, Workflows modules
└── Document Viewer component

AI Modules
├── indic_ocr.py (13 languages)
├── bharatiya_sakshya.py (evidence models)
└── document_parser.py
```

### Target State
```
Enhanced FastAPI Backend
├── Deep Research API endpoints (FR-1)
├── Pre-signed URL generation (FR-2)
├── BSA certificate generation (FR-3)
├── Redis cache layer (FR-6)
├── Multi-agent orchestration (FR-7)
└── Schema validation middleware (FR-8)

Frontend Enhancements
├── Deep Research panel component (FR-1.4)
├── Document viewer token forwarding (FR-2.3)
└── Certificate download integration (FR-3.3)

New Dependencies
├── Redis (already in docker-compose.yml)
└── OpenAI API (for Deep Research)
```

---

## 3. Deep Research Integration (FR-1)

### 3.1 Backend API Endpoint

**File**: `backend/app/api/deep_research.py` (NEW)

```python
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

router = APIRouter(prefix="/api/v1/cases/{case_id}/deep-research", tags=["deep_research"])

class DeepResearchRequest(BaseModel):
    question: str
    model: str = "o4-mini-deep-research"  # o4-mini-deep-research | o3-deep-research
    max_tool_calls: int = 0

class DeepResearchResponse(BaseModel):
    task_id: UUID
    status: str = "PENDING"
```

**Endpoint**: `POST /api/v1/cases/{case_id}/deep-research`

**Request**:
```json
{
  "question": "What are the recent developments in Indian property law?",
  "model": "o4-mini-deep-research",
  "max_tool_calls": 5
}
```

**Response**: `202 Accepted`
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PENDING"
}
```

**Response**: `404 Not Found` (case doesn't exist or user lacks access)

**Details**:
- Integrates with OpenAI Deep Research API
- Streams events via SSE to `/api/v1/cases/{case_id}/deep-research/stream/{task_id}`
- Stores results in `deep_research_results` table
- Implements authentication via existing `get_case_access` dependency

---

## 4. Database Schema (FR-1.2)

### 4.1 Migration: `016_deep_research.sql` (NEW)

**File**: `supabase/migrations/016_deep_research.sql`

```sql
-- Deep research results storage
CREATE TABLE deep_research_results (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  question TEXT NOT NULL,
  model VARCHAR(50) NOT NULL,
  max_tool_calls INT DEFAULT 0,
  report_content TEXT NOT NULL,
  citations JSONB,
  usage JSONB,
  elapsed_seconds FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_deep_research_case ON deep_research_results(case_id);
CREATE INDEX idx_deep_research_user ON deep_research_results(user_id);

-- Research sessions for streaming state
CREATE TABLE deep_research_sessions (
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

CREATE INDEX idx_deep_research_session_case ON deep_research_sessions(case_id);
CREATE INDEX idx_deep_research_session_task ON deep_research_sessions(task_id);
```

### 4.2 RLS Policies

**File**: `supabase/migrations/017_deep_research_rls.sql` (NEW)

```sql
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

-- Admins can read all
CREATE POLICY deep_research_admin_read
  ON deep_research_results FOR SELECT
  USING (is_admin());
```

---

## 5. Celery Task Integration (FR-1.3)

### 5.1 Task Definition

**File**: `backend/app/workers/tasks.py` (MODIFIED)

```python
from celery.exceptions import Retry
from app.workers.celery_app import celery_app
from supabase import create_client
from app.config import get_settings
from datetime import datetime, timezone

settings = get_settings()

def _db():
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    try:
        return create_client(url, key)
    except Exception:
        return None

@celery_app.task(bind=True, name="tasks.deep_research", max_retries=3, default_retry_delay=30)
def deep_research_task(self, case_id: str, user_id: str, question: str, 
                      model: str = "o4-mini-deep-research", 
                      max_tool_calls: int = 0):
    """Run deep research on OpenAI and stream results."""
    from openai import OpenAI
    import json
    
    db = _db()
    if not db:
        raise ValueError("Database connection failed")
    
    # Verify case access
    case = db.table("cases").select("id, user_id").eq("id", case_id).single().execute()
    if not case.data:
        raise ValueError(f"Case {case_id} not found")
    
    # Create session for streaming
    session = db.table("deep_research_sessions").insert({
        "case_id": case_id,
        "user_id": user_id,
        "task_id": self.request.id,
        "question": question,
        "model": model,
        "max_tool_calls": max_tool_calls,
        "status": "RUNNING"
    }).execute()
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Create thread for research
        thread = client.beta.threads.create()
        
        # Add user message
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=question
        )
        
        # Run with tool (web_search)
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=settings.DEEP_RESEARCH_ASSISTANT_ID,
            tools=[{"type": "web_search"}],
            tool_resources={
                "file_search": {
                    "vector_store_ids": []
                }
            },
            model=model,
            max_tool_calls=max_tool_calls if max_tool_calls > 0 else None
        )
        
        # Stream events
        events = client.beta.threads.runs.steps.list(
            thread_id=thread.id,
            run_id=run.id,
            limit=100,
            order="asc"
        )
        
        # Process events and stream
        for event in events:
            # Stream event to frontend
            db.table("deep_research_events").upsert({
                "session_id": session.data[0]["id"],
                "event_type": event.type,
                "event_data": json.dumps(event.model_dump()),
                "created_at": datetime.now(timezone.utc)
            }).execute()
        
        # Get final message
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        final_message = messages.data[0]
        
        # Store result
        db.table("deep_research_results").insert({
            "case_id": case_id,
            "user_id": user_id,
            "question": question,
            "model": model,
            "max_tool_calls": max_tool_calls,
            "report_content": final_message.content[0].text.value,
            "citations": json.dumps([]),  # Parse citations from response
            "usage": json.dumps({}),  # Add token usage
            "elapsed_seconds": 0.0  # Calculate elapsed time
        }).execute()
        
        # Update session status
        db.table("deep_research_sessions").update({
            "status": "SUCCESS",
            "updated_at": datetime.now(timezone.utc)
        }).eq("id", session.data[0]["id"]).execute()
        
        return {"task_id": self.request.id, "status": "SUCCESS"}
        
    except Exception as e:
        # Update session status
        db.table("deep_research_sessions").update({
            "status": "FAILURE",
            "updated_at": datetime.now(timezone.utc)
        }).eq("id", session.data[0]["id"]).execute()
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        raise ValueError(f"Deep research failed: {str(e)}")
```

### 5.2 Event Storage

**File**: `supabase/migrations/018_deep_research_events.sql` (NEW)

```sql
-- Deep research events for streaming
CREATE TABLE deep_research_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID NOT NULL REFERENCES deep_research_sessions(id) ON DELETE CASCADE,
  event_type VARCHAR(100) NOT NULL, -- step.created, message.created, etc.
  event_data JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_deep_research_events_session ON deep_research_events(session_id);
```

---

## 6. Frontend Integration (FR-1.4)

### 6.1 Deep Research Panel Component

**File**: `frontend/components/deep-research/DeepResearchPanel.tsx` (NEW)

```typescript
"use client";

import { useState, useEffect, useCallback } from "react";
import { Terminal, Download, Play, X, Loader2 } from "lucide-react";
import Markdown from "react-markdown";

interface DeepResearchEvent {
  id: string;
  event_type: string;
  event_data: any;
  created_at: string;
}

interface DeepResearchResult {
  id: string;
  question: string;
  report_content: string;
  citations: any[];
  created_at: string;
}

interface DeepResearchPanelProps {
  caseId: string;
  onClose?: () => void;
}

export function DeepResearchPanel({ caseId, onClose }: DeepResearchPanelProps) {
  const [question, setQuestion] = useState("");
  const [model, setModel] = useState("o4-mini-deep-research");
  const [maxToolCalls, setMaxToolCalls] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [events, setEvents] = useState<DeepResearchEvent[]>([]);
  const [result, setResult] = useState<DeepResearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`/api/v1/cases/${caseId}/deep-research`);
      if (res.ok) {
        const history = await res.json();
        // Set last result as default
        if (history.length > 0) {
          setResult(history[0]);
        }
      }
    } catch (err) {
      setError("Failed to load research history");
    }
  }, [caseId]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleRunResearch = async () => {
    if (!question.trim()) {
      setError("Please enter a research question");
      return;
    }

    setIsRunning(true);
    setError(null);
    setEvents([]);
    setResult(null);

    try {
      const res = await fetch(`/api/v1/cases/${caseId}/deep-research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          model,
          max_tool_calls: maxToolCalls
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to start research");
      }

      const { task_id } = await res.json();
      connectToStream(task_id);
    } catch (err) {
      setError(err.message);
      setIsRunning(false);
    }
  };

  const connectToStream = (taskId: string) => {
    const eventSource = new EventSource(
      `/api/v1/cases/${caseId}/deep-research/stream/${taskId}`
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "event") {
        setEvents(prev => [...prev, data.event]);
      } else if (data.type === "complete") {
        eventSource.close();
        setResult(data.result);
        setIsRunning(false);
      }
    };

    eventSource.onerror = (err) => {
      console.error("EventSource failed:", err);
      eventSource.close();
      setIsRunning(false);
      setError("Connection to research service lost");
    };
  };

  const handleDownload = () => {
    if (!result) return;
    const blob = new Blob([result.report_content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `deep-research-${new Date().toISOString().split("T")[0]}.md`;
    a.click();
  };

  const examples = [
    "What are the most important developments in Indian property law since 2023?",
    "Summarize recent case law on RERA disputes in Maharashtra.",
    "Compare how Indian and US regulations handle title insurance."
  ];

  return (
    <div className="deep-research-panel space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Terminal size={20} />
          Deep Research
        </h3>
        {onClose && (
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        )}
      </div>

      {/* Configuration */}
      <div className="space-y-3 p-4 bg-gray-50 rounded-lg border">
        <div>
          <label className="block text-sm font-medium mb-1">Question</label>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            className="w-full p-2 border rounded-md min-h-[80px]"
            placeholder="Enter your research question..."
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium mb-1">Model</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full p-2 border rounded-md"
            >
              <option value="o4-mini-deep-research">o4-mini-deep-research (Fast)</option>
              <option value="o3-deep-research">o3-deep-research (Deep)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              Max Tool Calls ({maxToolCalls === 0 ? "Auto" : maxToolCalls})
            </label>
            <input
              type="range"
              min="0"
              max="10"
              value={maxToolCalls}
              onChange={(e) => setMaxToolCalls(parseInt(e.target.value))}
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">
              Higher = More thorough but slower and more expensive
            </p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Examples</label>
          <div className="space-y-2">
            {examples.map((ex, i) => (
              <button
                key={i}
                onClick={() => setQuestion(ex)}
                className="w-full text-left text-sm p-2 hover:bg-gray-200 rounded"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleRunResearch}
          disabled={isRunning || !question.trim()}
          className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white p-3 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isRunning ? <Loader2 className="animate-spin" /> : <Play size={18} />}
          {isRunning ? "Running Research..." : "Run Research"}
        </button>
      </div>

      {/* Events Feed */}
      {events.length > 0 && (
        <div className="events-feed bg-gray-900 rounded-lg overflow-hidden">
          <div className="bg-gray-800 px-4 py-2 text-sm font-medium">
            Activity Feed
          </div>
          <div className="max-h-[200px] overflow-y-auto p-4 space-y-2 font-mono text-sm">
            {events.map((event) => (
              <div key={event.id} className="flex gap-2">
                <span className="text-gray-400">
                  {new Date(event.created_at).toLocaleTimeString()}
                </span>
                <span className="text-blue-400">{event.event_type}</span>
                <span className="text-gray-300">
                  {event.event_data?.type === "step_completed" && 
                   event.event_data?.step?.type === "tool_calls" 
                   ? `Tool: ${event.event_data?.step?.tool_calls?.[0]?.function?.name}`
                   : JSON.stringify(event.event_data, null, 2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Final Report */}
      {result && (
        <div className="report-section space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="font-semibold">Final Report</h4>
            <button
              onClick={handleDownload}
              className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700"
            >
              <Download size={16} />
              Download Markdown
            </button>
          </div>
          <div className="report-content p-4 bg-white rounded-lg border">
            <Markdown>{result.report_content}</Markdown>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-600 text-sm">
          {error}
        </div>
      )}
    </div>
  );
}
```

### 6.2 API Client Enhancements

**File**: `frontend/lib/api.ts` (MODIFIED)

```typescript
export async function startDeepResearch(
  caseId: string,
  question: string,
  model: string = "o4-mini-deep-research",
  maxToolCalls: number = 0
): Promise<{ task_id: string; status: string }> {
  const res = await fetch(`/api/v1/cases/${caseId}/deep-research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      model,
      max_tool_calls: maxToolCalls
    })
  });
  
  if (!res.ok) {
    throw new Error(`Deep research failed: ${res.statusText}`);
  }
  
  return res.json();
}

export function subscribeToDeepResearch(
  caseId: string,
  taskId: string,
  onEvent: (event: any) => void,
  onComplete: (result: any) => void,
  onError: (error: any) => void
): EventSource {
  const source = new EventSource(
    `${process.env.NEXT_PUBLIC_API_URL}/api/v1/cases/${caseId}/deep-research/stream/${taskId}`
  );
  
  source.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "event") {
      onEvent(data.event);
    } else if (data.type === "complete") {
      onComplete(data.result);
      source.close();
    }
  };
  
  source.onerror = (err) => {
    onError(err);
    source.close();
  };
  
  return source;
}

export async function listDeepResearch(caseId: string): Promise<any[]> {
  const res = await fetch(`/api/v1/cases/${caseId}/deep-research`);
  if (!res.ok) {
    throw new Error(`Failed to list research: ${res.statusText}`);
  }
  return res.json();
}
```

---

## 7. Document Viewer Authentication (FR-2)

### 7.1 Pre-Signed URL Generation

**File**: `backend/app/api/documents.py` (MODIFIED)

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from supabase import create_client
from app.config import get_settings
from app.security.auth import get_current_user, get_case_access
from datetime import datetime, timedelta, timezone
from typing import Optional
import urllib.parse
import hashlib

router = APIRouter(prefix="/api/v1/cases/{case_id}/documents", tags=["documents"])

settings = get_settings()

def _db():
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    try:
        return create_client(url, key)
    except Exception:
        raise HTTPException(status_code=500, detail="Database connection failed")

@router.get("/{document_id}/download-url")
async def download_url(
    document_id: str,
    case_id: str,
    user = Depends(get_case_access),
    expires_in: int = 3600  # Default 1 hour
):
    """Generate pre-signed URL for document download with token forwarding."""
    db = _db()
    
    # Verify document exists and belongs to case
    doc = db.table("documents").select("id, case_id, storage_path, file_type").eq("id", document_id).single().execute()
    if not doc.data:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Verify case ownership/access
    case = db.table("cases").select("id, user_id").eq("id", case_id).single().execute()
    if not case.data:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Check user access
    if str(user.id) != str(case.data["user_id"]) and not db.table("case_members").select("id").eq("case_id", case_id).eq("user_id", user.id).single().execute().data:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Generate pre-signed URL with forwarded auth token
    storage = db.storage.from_("case-documents")
    
    # Forward user's JWT token in the request
    user_token = user.access_token  # Supabase Auth token from request headers
    
    # Create signed URL with token forwarded
    signed_url = storage.create_signed_url(
        doc.data["storage_path"],
        expires_in,
        http_method="GET",
        headers={
            "Authorization": f"Bearer {user_token}"
        }
    )
    
    if not signed_url.data:
        raise HTTPException(status_code=500, detail="Failed to generate signed URL")
    
    return {
        "url": signed_url.data.signed_url,
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat(),
        "content_type": doc.data["file_type"],
        "cache_control": "private, max-age=3600"
    }
```

### 7.2 RLS Policy Configuration

**File**: `supabase/migrations/019_storage_policies.sql` (NEW)

```sql
-- Storage bucket policies for case-documents
CREATE POLICY authenticated_users_can_read_case_documents
  ON storage.objects FOR SELECT
  USING (
    bucket_id = 'case-documents'
    AND (
      -- Owner can access
      auth.uid() = storage.filename(name)::UUID
      -- Or case member can access via function
      OR case_member(auth.uid(), storage.foldername(name)[1]::UUID)
    )
  );

CREATE POLICY authenticated_users_can_insert_case_documents
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'case-documents'
    AND auth.uid() = storage.foldername(name)[1]::UUID
  );

CREATE POLICY authenticated_users_can_update_case_documents
  ON storage.objects FOR UPDATE
  USING (
    bucket_id = 'case-documents'
    AND auth.uid() = storage.foldername(name)[1]::UUID
  );

CREATE POLICY authenticated_users_can_delete_case_documents
  ON storage.objects FOR DELETE
  USING (
    bucket_id = 'case-documents'
    AND auth.uid() = storage.foldername(name)[1]::UUID
  );

-- Function to check case membership
CREATE OR REPLACE FUNCTION case_member(user_id UUID, case_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM case_members
    WHERE case_id = $2 AND user_id = $1
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if user is admin
CREATE OR REPLACE FUNCTION is_admin()
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM auth.users
    WHERE id = auth.uid() AND raw_user_meta_data->>'role' = 'admin'
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

## 8. Frontend Token Forwarding (FR-2.3)

### 8.1 Document Viewer Enhancements

**File**: `frontend/components/document-viewer/DocumentViewer.tsx` (MODIFIED)

```typescript
import { createClient } from "@supabase/supabase-js";

// ... existing imports ...

export function DocumentViewer({
  documents,
  initialActive,
  active,
  onActiveChange,
  renderers = [],
  requestOptions,
  theme,
  showSidebar = true,
  watermark = false,
  className = "",
  style,
}: DocumentViewerProps) {
  // ... existing state ...

  // Get auth token from Supabase
  const supabase = useMemo(() => {
    if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
      return null;
    }
    return createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    );
  }, []);

  // Get current auth token
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);

  useEffect(() => {
    const loadAuth = async () => {
      try {
        const { data: { session } } = await supabase?.auth.getSession() || { data: { session: null } };
        setAuthToken(session?.access_token || null);
      } catch (err) {
        console.error("Failed to load auth:", err);
      } finally {
        setIsAuthLoading(false);
      }
    };
    
    loadAuth();
    
    const { data: { subscription } } = supabase?.auth.onAuthStateChange((_event, session) => {
      setAuthToken(session?.access_token || null);
    }) || { data: { subscription: null } };
    
    return () => subscription?.unsubscribe();
  }, [supabase]);

  // ... existing code ...

  /** Configured fetch for document bytes — used by text/csv/docx/xlsx renderers. */
  const request = useCallback(async () => {
    if (!activeDocument) throw new Error("No active document");
    if (activeDocument.file) return new Response(activeDocument.file);
    
    // Build init with auth token
    const init = resolveInit(requestOptions?.requestInit, activeDocument);
    
    // Add auth token if available
    if (authToken && !init.headers?.["Authorization"]) {
      init.headers = {
        ...(init.headers || {}),
        "Authorization": `Bearer ${authToken}`
      };
    }
    
    // Handle requestFile callback
    if (requestOptions?.requestFile) {
      return requestOptions.requestFile(activeDocument, init);
    }
    
    // Handle regular fetch with auth
    return fetch(source, init);
  }, [activeDocument, authToken, requestOptions, source]);

  // ... existing inspection and rendering code ...
}
```

### 8.2 Request Options Interface

**File**: `frontend/components/document-viewer/types.ts` (MODIFIED)

```typescript
export interface RequestOptions {
  /** Custom request headers for fetching document bytes. */
  requestInit?: RequestInit | ((doc: ViewerDocument) => RequestInit);
  
  /** Function to override request creation (for authenticated requests). */
  requestFile?: (doc: ViewerDocument, init: RequestInit) => Promise<Response>;
  
  /** Method to use for inspection (HEAD or GET). */
  inspectMethod?: "HEAD" | "GET";
  
  /** Custom headers for inspection requests. */
  inspectInit?: RequestInit | ((doc: ViewerDocument) => RequestInit);
  
  /** Cache mode for requests. */
  cacheMode?: "default" | "no-cache" | "reload" | "force-cache" | "only-if-cached";
}
```

---

## 9. BSA Section 63 Certification (FR-3)

### 9.1 SHA-256 Hash Generation

**File**: `backend/app/ai/bsa_certificates.py` (NEW)

```python
"""
BSA Section 63 Electronic Evidence Certification

Implements cryptographic hashing and certificate generation for electronic
records as required by Indian Evidence Act Section 63.
"""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm


class EvidenceHasher:
    """Cryptographically secure hashing for electronic records."""
    
    @staticmethod
    def generate_file_hash(file_bytes: bytes, filename: str = None, 
                          timestamp: datetime = None) -> str:
        """
        Generate SHA-256 hash for file with metadata inclusion.
        
        Format: {filename}|{size}|{timestamp}|{content_hash}
        """
        content_hash = hashlib.sha256(file_bytes).hexdigest()
        
        # Build metadata string
        filename_part = filename or "unknown"
        size_part = str(len(file_bytes))
        timestamp_part = timestamp or datetime.now(timezone.utc)
        
        metadata = f"{filename_part}|{size_part}|{timestamp_part.isoformat()}"
        
        # Final hash includes metadata
        combined = f"{metadata}|{content_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    @staticmethod
    def generate_incremental_hash(file_path: str, chunk_size: int = 8192) -> str:
        """Generate hash for large files using incremental processing."""
        sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                sha256.update(data)
        
        return sha256.hexdigest()
    
    @staticmethod
    def verify_hash(file_bytes: bytes, expected_hash: str, 
                   filename: str = None) -> bool:
        """Verify file integrity against stored hash."""
        generated_hash = EvidenceHasher.generate_file_hash(
            file_bytes, filename
        )
        return generated_hash == expected_hash


class CertificateGenerator:
    """Generate court-admissible Section 63 electronic evidence certificates."""
    
    @staticmethod
    def generate_section63_certificate(
        evidence: Dict[str, Any],
        custodian: Dict[str, Any],
        include_hash: bool = True,
        include_qr_code: bool = False
    ) -> bytes:
        """
        Generate PDF certificate for electronic evidence.
        
        Certificate Structure:
        1. Header with statutory declaration
        2. Evidence identification (file name, hash, algorithm)
        3. System parameters (computer generated, regular use, integrity)
        4. Custodian declaration and signature
        5. Timestamp and verification info
        """
        # Generate hash if not provided
        if include_hash and "hash_value" not in evidence:
            hasher = EvidenceHasher()
            evidence["hash_value"] = hasher.generate_file_hash(
                evidence.get("file_bytes", b""),
                evidence.get("filename", "unknown")
            )
        
        # Create PDF
        buffer = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        buffer.close()
        
        c = canvas.Canvas(buffer.name, pagesize=A4)
        width, height = A4
        
        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2, height - 2*cm, 
                           "SECTION 63 ELECTRONIC EVIDENCE CERTIFICATE")
        
        c.setFont("Helvetica", 10)
        c.drawCentredString(width / 2, height - 3*cm,
                           "Under the Indian Evidence Act, 1872")
        
        # Separator
        c.line(2*cm, height - 4*cm, width - 2*cm, height - 4*cm)
        
        # Evidence Identification
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2*cm, height - 5*cm, "1. EVIDENCE IDENTIFICATION")
        
        c.setFont("Helvetica", 10)
        y_pos = height - 6*cm
        
        c.drawString(2.5*cm, y_pos, f"File Name: {evidence.get('filename', 'N/A')}")
        y_pos -= 1*cm
        
        c.drawString(2.5*cm, y_pos, f"File Size: {evidence.get('file_size', 'N/A')} bytes")
        y_pos -= 1*cm
        
        c.drawString(2.5*cm, y_pos, f"File Type: {evidence.get('mime_type', 'N/A')}")
        y_pos -= 1*cm
        
        c.drawString(2.5*cm, y_pos, f"SHA-256 Hash: {evidence.get('hash_value', 'N/A')}")
        y_pos -= 1.5*cm
        
        # System Parameters
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2*cm, y_pos, "2. SYSTEM PARAMETERS")
        
        c.setFont("Helvetica", 10)
        y_pos -= 1*cm
        
        c.drawString(2.5*cm, y_pos, "Computer System: Automated Document Processing System")
        y_pos -= 0.8*cm
        
        c.drawString(2.5*cm, y_pos, "Regularly Used: Yes - System is regularly used for document processing")
        y_pos -= 0.8*cm
        
        c.drawString(2.5*cm, y_pos, "Integrity Verified: Yes - SHA-256 hash verification enabled")
        y_pos -= 0.8*cm
        
        c.drawString(2.5*cm, y_pos, "Access Controls: Role-based access with audit logging")
        y_pos -= 1.5*cm
        
        # Statutory Declaration
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2*cm, y_pos, "3. STATUTORY DECLARATION")
        
        c.setFont("Helvetica", 10)
        y_pos -= 1*cm
        
        declaration = (
            "I, the undersigned, being the custodian of the above electronic record, "
            "do hereby declare that:"
        )
        c.drawString(2.5*cm, y_pos, declaration)
        y_pos -= 1.5*cm
        
        declarations = [
            "1. The electronic record is a printout or other output showing an original "
            "electronic record produced by a computer during the period when it was "
            "used regularly to store or process information.",
            "2. The information contained in the electronic record reproduces or is "
            "derived from the information supplied to the computer during its normal "
            "course of operation.",
            "3. The computer was functioning properly during the period when the "
            "electronic record was stored or processed.",
            "4. The electronic record has not been altered since it was last stored "
            "or processed, except for normal use and in accordance with the "
            "computer's normal operation.",
            "5. The SHA-256 hash provided constitutes a reliable integrity check "
            "for the electronic record."
        ]
        
        for decl in declarations:
            c.drawString(2.5*cm, y_pos, decl)
            y_pos -= 0.8*cm
        
        y_pos -= 1*cm
        
        # Custodian Information
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2*cm, y_pos, "4. CUSTODIAN INFORMATION")
        
        c.setFont("Helvetica", 10)
        y_pos -= 1*cm
        
        c.drawString(2.5*cm, y_pos, f"Name: {custodian.get('name', 'N/A')}")
        y_pos -= 0.8*cm
        
        c.drawString(2.5*cm, y_pos, f"Position: {custodian.get('position', 'N/A')}")
        y_pos -= 0.8*cm
        
        c.drawString(2.5*cm, y_pos, f"Organization: {custodian.get('organization', 'N/A')}")
        y_pos -= 1*cm
        
        # Signature Area
        c.setFont("Helvetica-Bold", 10)
        c.drawString(2.5*cm, y_pos, "Signature: _________________________")
        y_pos -= 2*cm
        
        c.setFont("Helvetica", 10)
        c.drawString(2.5*cm, y_pos, f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        y_pos -= 1*cm
        
        # Verification Info
        c.setFont("Helvetica", 8)
        c.drawCentredString(width / 2, 2*cm,
                          "Certificate ID: CERT-" + evidence.get("document_id", "N/A"))
        c.drawCentredString(width / 2, 1.5*cm,
                          "Generated by LegAIQ Legal Intelligence Platform")
        
        c.save()
        
        # Read PDF bytes
        with open(buffer.name, 'rb') as f:
            pdf_bytes = f.read()
        
        # Cleanup
        os.unlink(buffer.name)
        
        return pdf_bytes
```

### 9.2 Database Schema for Certificates

**File**: `supabase/migrations/020_bsa_certificates.sql` (NEW)

```sql
-- BSA Section 63 certificates storage
CREATE TABLE bsa_certificates (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  sha256_hash TEXT NOT NULL,
  file_metadata JSONB,
  acquisition_timestamp TIMESTAMPTZ DEFAULT NOW(),
  device_metadata JSONB,
  part_a_json JSONB,  -- Evidence details (auto-generated)
  part_b_signed BOOLEAN DEFAULT FALSE,
  part_b_signed_at TIMESTAMPTZ,
  part_b_signed_by UUID REFERENCES auth.users(id),
  certificate_data BYTEA,  -- PDF certificate binary
  status VARCHAR(20) DEFAULT 'DRAFT',  -- DRAFT | SIGNED | FINAL
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_bsa_certificates_document ON bsa_certificates(document_id);
CREATE INDEX idx_bsa_certificates_user ON bsa_certificates(user_id);
CREATE INDEX idx_bsa_certificates_case ON bsa_certificates(case_id);
CREATE INDEX idx_bsa_certificates_status ON bsa_certificates(status);

-- Certificate audit log
CREATE TABLE bsa_certificate_audit (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  certificate_id UUID NOT NULL REFERENCES bsa_certificates(id) ON DELETE CASCADE,
  action VARCHAR(50) NOT NULL,  -- CREATED | UPDATED | SIGNED | VERIFIED
  user_id UUID REFERENCES auth.users(id),
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_bsa_audit_certificate ON bsa_certificate_audit(certificate_id);
CREATE INDEX idx_bsa_audit_user ON bsa_certificate_audit(user_id);
```

### 9.3 Certificate API Endpoint

**File**: `backend/app/api/bsa_certificates.py` (NEW)

```python
"""
BSA Section 63 Certificate API

Endpoints for generating, storing, and retrieving electronic evidence certificates.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from supabase import create_client
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from app.config import get_settings
from app.security.auth import get_case_access, get_current_user
from app.ai.bsa_certificates import EvidenceHasher, CertificateGenerator

router = APIRouter(prefix="/api/v1/cases/{case_id}/documents", tags=["bsa_certificates"])

settings = get_settings()

def _db():
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    try:
        return create_client(url, key)
    except Exception:
        raise HTTPException(status_code=500, detail="Database connection failed")


class CertificateGenerateRequest(BaseModel):
    format: str = "pdf"  # pdf | json
    include_hash: bool = True
    device_metadata: Optional[dict] = None


class CertificateResponse(BaseModel):
    certificate_id: UUID
    document_id: UUID
    status: str
    sha256_hash: str


@router.post("/{document_id}/bsa-certificate")
async def generate_certificate(
    request: Request,
    case_id: str,
    document_id: str,
    body: CertificateGenerateRequest,
    user = Depends(get_case_access)
):
    """Generate Section 63 electronic evidence certificate."""
    db = _db()
    
    # Verify document exists
    doc = db.table("documents").select(
        "id, case_id, filename, file_type, storage_path"
    ).eq("id", document_id).single().execute()
    
    if not doc.data:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check case access
    if str(doc.data["case_id"]) != str(case_id):
        raise HTTPException(status_code=400, detail="Document doesn't belong to case")
    
    # Download document for hashing
    file_bytes = db.storage.from_("case-documents").download(doc.data["storage_path"])
    if not file_bytes:
        raise HTTPException(status_code=404, detail="Document file not found")
    
    # Generate hash
    hasher = EvidenceHasher()
    hash_value = hasher.generate_file_hash(
        file_bytes,
        doc.data["filename"],
        datetime.now(timezone.utc)
    )
    
    # Build evidence object
    evidence = {
        "document_id": document_id,
        "filename": doc.data["filename"],
        "file_size": len(file_bytes),
        "mime_type": doc.data["file_type"],
        "hash_value": hash_value,
        "file_bytes": file_bytes  # For PDF generation
    }
    
    # Build custodian info
    custodian = {
        "name": f"{user.user_metadata.get('first_name', '')} {user.user_metadata.get('last_name', '')}".strip(),
        "position": "Legal Practitioner",
        "organization": user.user_metadata.get("organization", "Unknown")
    }
    
    # Generate certificate
    try:
        pdf_bytes = CertificateGenerator.generate_section63_certificate(
            evidence,
            custodian,
            include_hash=body.include_hash,
            include_qr_code=False  # QR code requires additional implementation
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate certificate: {str(e)}")
    
    # Store certificate
    certificate = db.table("bsa_certificates").insert({
        "document_id": document_id,
        "user_id": str(user.id),
        "case_id": case_id,
        "sha256_hash": hash_value,
        "file_metadata": {
            "filename": doc.data["filename"],
            "size": len(file_bytes),
            "mime_type": doc.data["file_type"]
        },
        "acquisition_timestamp": datetime.now(timezone.utc).isoformat(),
        "device_metadata": body.device_metadata,
        "part_a_json": {
            "evidence_identification": {
                "filename": doc.data["filename"],
                "file_size": len(file_bytes),
                "mime_type": doc.data["file_type"],
                "sha256_hash": hash_value
            },
            "system_parameters": {
                "computer_system": "Automated Document Processing System",
                "regularly_used": True,
                "integrity_verified": True,
                "access_controls": "Role-based access with audit logging"
            }
        },
        "part_b_signed": False,
        "certificate_data": pdf_bytes,
        "status": "DRAFT"
    }).execute()
    
    # Log audit event
    db.table("bsa_certificate_audit").insert({
        "certificate_id": certificate.data[0]["id"],
        "action": "CREATED",
        "user_id": str(user.id),
        "metadata": {
            "format": body.format,
            "include_hash": body.include_hash
        }
    }).execute()
    
    return {
        "certificate_id": certificate.data[0]["id"],
        "document_id": document_id,
        "status": "DRAFT",
        "sha256_hash": hash_value
    }


@router.get("/{document_id}/bsa-certificate")
async def get_certificate(
    case_id: str,
    document_id: str,
    format: str = Query("pdf", regex="^(pdf|json)$"),
    user = Depends(get_case_access)
):
    """Download Section 63 certificate."""
    db = _db()
    
    # Find certificate
    cert = db.table("bsa_certificates").select("*").eq("document_id", document_id).eq("case_id", case_id).single().execute()
    
    if not cert.data:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    if format == "json":
        return {
            "certificate_id": cert.data["id"],
            "document_id": cert.data["document_id"],
            "sha256_hash": cert.data["sha256_hash"],
            "part_a_json": cert.data["part_a_json"],
            "part_b_signed": cert.data["part_b_signed"],
            "status": cert.data["status"],
            "created_at": cert.data["created_at"]
        }
    else:
        # Return PDF
        return StreamingResponse(
            iter([cert.data["certificate_data"]]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=bsa-certificate-{document_id}.pdf",
                "Cache-Control": "private, max-age=3600"
            }
        )


@router.post("/{document_id}/bsa-certificate/sign")
async def sign_certificate(
    case_id: str,
    document_id: str,
    user = Depends(get_case_access)
):
    """Sign certificate (Part B - custodian signature)."""
    db = _db()
    
    # Find certificate
    cert = db.table("bsa_certificates").select("id, part_b_signed").eq("document_id", document_id).eq("case_id", case_id).single().execute()
    
    if not cert.data:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    if cert.data["part_b_signed"]:
        raise HTTPException(status_code=400, detail="Certificate already signed")
    
    # Update certificate
    updated = db.table("bsa_certificates").update({
        "part_b_signed": True,
        "part_b_signed_at": datetime.now(timezone.utc).isoformat(),
        "part_b_signed_by": str(user.id),
        "status": "FINAL"
    }).eq("id", cert.data["id"]).execute()
    
    # Log audit event
    db.table("bsa_certificate_audit").insert({
        "certificate_id": cert.data["id"],
        "action": "SIGNED",
        "user_id": str(user.id),
        "metadata": {
            "signed_by": str(user.id),
            "signed_at": datetime.now(timezone.utc).isoformat()
        }
    }).execute()
    
    return {
        "certificate_id": cert.data["id"],
        "status": "FINAL",
        "part_b_signed": True,
        "part_b_signed_at": datetime.now(timezone.utc).isoformat()
    }
```

---

## 10. OCR Bilingual Enhancement (FR-4)

### 10.1 Language Confidence Calibration

**File**: `backend/app/ai/indic_ocr.py` (MODIFIED)

```python
@dataclass
class OCRPageResult:
    page_number: int
    text: str
    language: str
    confidence: float
    language_confidence: Dict[str, float] = field(default_factory=dict)
    bilingual_content: bool = False
    bilingual_confidence_modifier: float = 1.0
    bounding_boxes: List[Dict] = field(default_factory=list)
    words: List[Dict] = field(default_factory=list)
    script: str = "Latin"
```

<tool_call>
<function=todo_list>
    @staticmethod
    def calibrate_confidence_for_bilingual(
        page_text: str,
        primary_language: str,
        secondary_language: str
    ) -> Tuple[float, bool, float]:
        """
        Calibrate OCR confidence for bilingual documents.
        
        Returns: (calibrated_confidence, is_bilingual, modifier)
        """
        # Detect bilingual content
        language_chars = {
            "mr": "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz",
            "hi": "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz"
        }
        
        # Count script transitions (Marathi/English mix)
        script_transitions = 0
        prev_script = None
        
        for char in page_text:
            if char.isascii():
                current_script = "Latin"
            else:
                current_script = "Indic"
            
            if prev_script and current_script != prev_script:
                script_transitions += 1
            
            prev_script = current_script
        
        total_chars = len(page_text)
        transition_ratio = script_transitions / total_chars if total_chars > 0 else 0
        
        is_bilingual = transition_ratio > 0.1  # >10% script transitions indicates bilingual
        
        if is_bilingual:
            # Reduce confidence for bilingual documents
            # Monolingual: ×1.0, Bilingual: ×0.95
            modifier = 0.95
        else:
            modifier = 1.0
        
        return modifier, is_bilingual


class TesseractProvider(BaseOCRProvider):
    """Enhanced Tesseract with bilingual document support."""
    name = "tesseract"
    
    # ... existing code ...
    
    async def process(self, file_bytes: bytes, file_type: str, document_type: str = "general") -> OCRDocumentResult:
        # ... existing code ...
        
        for i, img in enumerate(images):
            # ... existing OCR processing ...
            
            # Calibrate confidence for bilingual content
            calibrated_conf, is_bilingual, modifier = OCRPageResult.calibrate_confidence_for_bilingual(
                calibrated_text, lang, "en" if lang != "en" else "hi"
            )
            
            result.pages.append(OCRPageResult(
                page_number=i + 1,
                text=re.sub(r"\s+", " ", calibrated_text).strip(),
                language=lang,
                confidence=calibrated_conf / 100.0 * modifier,  # Apply bilingual modifier
                language_confidence={
                    "primary": lang,
                    "secondary": "en" if lang != "en" else "hi",
                    "primary_confidence": calibrated_conf / 100.0,
                    "bilingual_modifier": modifier
                },
                bilingual_content=is_bilingual,
                bilingual_confidence_modifier=modifier,
                # ... existing fields ...
            ))
        
        return result
```

### 10.2 Enhanced Document Type Detection

**File**: `backend/app/ai/indic_ocr.py` (MODIFIED)

```python
# Document type specific language priorities
DOCUMENT_LANGUAGE_PRIORITIES = {
    "7_12_extract": ["mr", "hi", "en"],  # Maharashtra - Marathi/Hindi
    "rtc_pahani": ["kn", "en"],           # Karnataka - Kannada
    "patta_chitta": ["ta", "en"],         # Tamil Nadu - Tamil
    "rf_1b": ["te", "ur", "en"],          # Telangana - Telugu/Urdu
    "vf_712": ["gu", "hi", "en"],         # Gujarat - Gujarati
    "khasra_khatauni": ["hi", "en"],      # North India - Hindi
    "sale_deed": ["hi", "en", "kn", "ta", "te", "ml", "mr", "bn", "gu", "pa", "ur", "or", "as"],
    "gift_deed": ["hi", "en"],
    "partition_deed": ["hi", "en"],
    "mortgage_deed": ["hi", "en"],
    "will": ["hi", "en"],
    "general": ["en", "hi"],               # Default: English + Hindi
}


class DocumentTypeDetector:
    """Detect document type for Indian land records."""
    
    # Maharashtra document headers
    MAHARASHTRA_KEYWORDS = {
        "7_12_extract": [
            "GOVERNMENT OF MAHARASHTRA",
            "ZILLA PARISHAD",
            "TALUKA PARISHAD",
            "SUB-REGISTRAR OFFICE",
            "7/12 EXTRACT",
            "MUTABLE ENTRY",
            "VILLAGE LANDING ACCOUNT"
        ],
        "rtc_pahani": [
            "KARNATAKA",
            "RTC",
            "PAHANI",
            "LAND RECORDS"
        ],
        "patta_chitta": [
            "TAMIL NADU",
            "PATTA",
            "CHITTA",
            "LAND RECORDS"
        ]
    }
    
    @classmethod
    def detect_document_type(cls, ocr_text: str, default: str = "general") -> str:
        """Detect document type from OCR text."""
        text_upper = ocr_text.upper()
        
        # Check for Maharashtra keywords
        for doc_type, keywords in cls.MAHARASHTRA_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_upper:
                    return doc_type
        
        return default
    
    @classmethod
    def detect_state(cls, ocr_text: str) -> str:
        """Detect Indian state from document."""
        text_upper = ocr_text.upper()
        
        state_keywords = {
            "Maharashtra": ["MAHARASHTRA", "MUMBAI", "PUNE", "NAGPUR"],
            "Karnataka": ["KARNATAKA", "BANGALORE", "BENGALURU"],
            "Tamil Nadu": ["TAMIL NADU", "CHENNAI", "COIMBATORE"],
            "Telangana": ["TELANGANA", "HYDERABAD"],
            "Gujarat": ["GUJARAT", "AHMEDABAD", "SURAT"],
            "Andhra Pradesh": ["ANDHRA PRADESH", "HYDERABAD", "VIZAG"],
            "West Bengal": ["WEST BENGAL", "KOLKATA", "SERAMPORE"],
        }
        
        for state, keywords in state_keywords.items():
            for keyword in keywords:
                if keyword in text_upper:
                    return state
        
        return "Unknown"
```

---

## 11. Indian Date Format Parsing (FR-5)

### 11.1 Multi-Format Date Parser

**File**: `backend/app/utils/indian_date_parser.py` (NEW)

```python
"""
Indian Date Format Parser

Supports multiple Indian date formats:
- DD/MM/YYYY, DD-MM-YYYY, DD MM YYYY
- Devanagari numerals (०-९)
- Vikram Samvat (V.S. 2060 → 2003 CE)
- Shalivahana Shaka (S.S. 1925 → 2003 CE)
- Marathi months (चैत्र, वैशाख...)
"""

import re
from datetime import datetime
from typing import Optional, Tuple, List, Dict
from dateutil.relativedelta import relativedelta


class IndianDateParser:
    """Parse Indian date formats including Devanagari numerals and Vikram Samvat."""
    
    # Devanagari to Arabic numerals mapping
    DEVANAGARI_TO_ARABIC = {
        "०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
        "५": "5", "६": "6", "७": "7", "८": "8", "९": "9"
    }
    
    # Marathi months mapping
    MARATHI_MONTHS = {
        "चैत्र": 1, "वैशाख": 2, "ज्येष्ठ": 3, "आषाढ": 4,
        "श्रावण": 5, "भाद्रपद": 6, "आश्विन": 7, "कार्तिक": 8,
        "मार्गशीर्ष": 9, "पौष": 10, "माघ": 11, "फाल्गुन": 12
    }
    
    # English month mapping for reference
    ENGLISH_MONTHS = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    }
    
    # Vikram Samvat offset (V.S. 2060 = 2003 CE)
    VIKRAM_SAMVAT_OFFSET = 57
    
    # Shalivahana Shaka offset (S.S. 1925 = 2003 CE)
    SHALIVAHANA_SHAKA_OFFSET = 1925 - 2003
    
    @classmethod
    def convert_devanagari_to_arabic(cls, text: str) -> str:
        """Convert Devanagari numerals to Arabic numerals."""
        for devanagari, arabic in cls.DEVANAGARI_TO_ARABIC.items():
            text = text.replace(devanagari, arabic)
        return text
    
    @classmethod
    def parse_date(cls, text: str) -> Optional[datetime]:
        """
        Parse Indian date formats.
        
        Supported formats:
        - DD/MM/YYYY
        - DD-MM-YYYY
        - DD MM YYYY
        - DD Month YYYY (with English/Marathi months)
        - Vikram Samvat (V.S. YYYY)
        - Shalivahana Shaka (S.S. YYYY)
        
        Returns: datetime object or None if not found
        """
        # Clean text
        text = text.strip()
        
        # Try Devanagari conversion
        if any(c in text for c in cls.DEVANAGARI_TO_ARABIC.keys()):
            text = cls.convert_devanagari_to_arabic(text)
        
        # Try various date patterns
        patterns = [
            # DD/MM/YYYY or DD-MM-YYYY
            (r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', cls._parse_dmy),
            # DD MM YYYY
            (r'(\d{1,2})\s+(\d{1,2})\s+(\d{4})', cls._parse_dmy),
            # DD Month YYYY
            (r'(\d{1,2})\s+([a-zA-Z]+\s+month\s+[a-zA-Z]+)\s+(\d{4})', cls._parse_d_month_y),
            # V.S. YYYY or S.S. YYYY
            (r'(?:V\.S\.|Vikram\s+Samvat|S\.S\.|Shalivahana\s+Shaka)\s+(\d{4})', cls._parse_era_year),
        ]
        
        for pattern, parser in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    result = parser(*match.groups())
                    if result:
                        return result
                except Exception:
                    continue
        
        return None
    
    @classmethod
    def _parse_dmy(cls, day: str, month: str, year: str) -> Optional[datetime]:
        """Parse DD/MM/YYYY format."""
        try:
            day = int(day)
            month = int(month)
            year = int(year)
            
            if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100:
                return datetime(year, month, day)
        except ValueError:
            pass
        
        return None
    
    @classmethod
    def _parse_d_month_y(cls, day: str, month_str: str, year: str) -> Optional[datetime]:
        """Parse DD Month YYYY format."""
        try:
            day = int(day)
            year = int(year)
            
            # Try Marathi months
            month = cls.MARATHI_MONTHS.get(month_str.lower())
            
            if month:
                if 1 <= day <= 31 and 1900 <= year <= 2100:
                    return datetime(year, month, day)
        except ValueError:
            pass
        
        return None
    
    @classmethod
    def _parse_era_year(cls, year: str) -> Optional[datetime]:
        """Parse Vikram Samvat or Shalivahana Shaka year."""
        try:
            year = int(year)
            # Assume Vikram Samvat if not specified
            ce_year = year - cls.VIKRAM_SAMVAT_OFFSET
            if 1900 <= ce_year <= 2100:
                # Return January 1 of that year
                return datetime(ce_year, 1, 1)
        except ValueError:
            pass
        
        return None
    
    @classmethod
    def extract_dates(cls, text: str) -> List[Tuple[datetime, str, int, int]]:
        """
        Extract all dates from text.
        
        Returns: List of (datetime, matched_text, start_pos, end_pos)
        """
        results = []
        
        # Pattern for DD/MM/YYYY and DD-MM-YYYY
        date_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{4}'
        
        for match in re.finditer(date_pattern, text):
            date_str = match.group()
            date = cls.parse_date(date_str)
            if date:
                results.append((date, date_str, match.start(), match.end()))
        
        return results
    
    @classmethod
    def is_indian_date(cls, text: str) -> bool:
        """Check if text contains Indian date format."""
        patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{4}',
            r'\d{1,2}\s+\d{1,2}\s+\d{4}',
        ]
        
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        
        return False


def parse_indian_date(text: str) -> Optional[datetime]:
    """
    Parse Indian date formats from text.
    
    Args:
        text: Text containing potential date
        
    Returns:
        datetime object if date found, None otherwise
    """
    return IndianDateParser.parse_date(text)


def extract_indian_dates(text: str) -> List[Tuple[datetime, str, int, int]]:
    """
    Extract all Indian dates from text.
    
    Args:
        text: Text containing potential dates
        
    Returns:
        List of (datetime, matched_text, start_pos, end_pos)
    """
    return IndianDateParser.extract_dates(text)
```

### 11.2 Entity Extraction Integration

**File**: `backend/app/ai/indic_ocr.py` (MODIFIED)

```python
# ... existing imports ...

def extract_entities(text: str, document_type: str = "general") -> Dict[str, Any]:
    """
    Extract entities from OCR text.
    
    Supports:
    - Dates (Indian formats)
    - Names
    - Property IDs
    - Monetary values
    """
    from app.utils.indian_date_parser import parse_indian_date, extract_indian_dates
    
    entities = {
        "dates": [],
        "names": [],
        "property_ids": [],
        "monetary_values": [],
        "normalized": {}
    }
    
    # Extract dates
    date_results = extract_indian_dates(text)
    for date_obj, matched_text, start, end in date_results:
        entities["dates"].append({
            "text": matched_text,
            "start": start,
            "end": end,
            "date": date_obj.isoformat(),
            "format": "indian"
        })
    
    # Normalize dates for downstream processing
    if date_results:
        entities["normalized"]["earliest_date"] = min(d[0] for d in date_results).isoformat()
        entities["normalized"]["latest_date"] = max(d[0] for d in date_results).isoformat()
    
    # Extract names (simplified regex)
    name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
    for match in re.finditer(name_pattern, text):
        entities["names"].append({
            "text": match.group(1),
            "start": match.start(),
            "end": match.end(),
            "confidence": 0.8
        })
    
    # Extract property IDs (simplified)
    property_pattern = r'\b(PATTA|RTC|7/12|GRNO)\s*[:\-]?\s*[\w\-/]+\b'
    for match in re.finditer(property_pattern, text, re.IGNORECASE):
        entities["property_ids"].append({
            "text": match.group(0),
            "start": match.start(),
            "end": match.end(),
            "type": match.group(1).upper()
        })
    
    # Extract monetary values
    monetary_pattern = r'₹?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\b'
    for match in re.finditer(monetary_pattern, text):
        try:
            amount = float(match.group(1).replace(",", ""))
            entities["monetary_values"].append({
                "text": match.group(0),
                "amount": amount,
                "start": match.start(),
                "end": match.end()
            })
        except ValueError:
            continue
    
    return entities
```

---

## 12. Celery Worker Caching (FR-6)

### 12.1 Redis Integration

**File**: `backend/app/workers/celery_app.py` (MODIFIED)

```python
"""
Celery app configuration with Redis caching support.
"""

import os
from celery import Celery
from redis import Redis
from functools import wraps
from typing import Any, Optional
import hashlib
import json
import pickle

# Redis connection
redis_client = None

def get_redis_client():
    """Get Redis client connection."""
    global redis_client
    
    if redis_client is None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        redis_client = Redis.from_url(redis_url, decode_responses=True)
    
    return redis_client


def cache_result(ttl: int = 86400):
    """
    Decorator for caching Celery task results.
    
    Args:
        ttl: Time-to-live in seconds (default: 86400 = 24 hours)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            redis = get_redis_client()
            
            # Create cache key
            cache_key = _generate_cache_key(func.__name__, args, kwargs)
            
            # Check cache
            cached = redis.get(cache_key)
            if cached:
                return pickle.loads(cached)
            
            # Execute task
            result = func(*args, **kwargs)
            
            # Cache result
            redis.setex(cache_key, ttl, pickle.dumps(result))
            
            return result
        
        return wrapper
    return decorator


def _generate_cache_key(function_name: str, args: tuple, kwargs: dict) -> str:
    """Generate unique cache key based on function name and parameters."""
    # Convert args and kwargs to JSON-serializable format
    cache_data = {
        "function": function_name,
        "args": _serialize_args(args),
        "kwargs": _serialize_kwargs(kwargs)
    }
    
    # Create hash of cache data
    cache_hash = hashlib.md5(
        json.dumps(cache_data, sort_keys=True).encode()
    ).hexdigest()
    
    # Return cache key
    return f"legaiq:celery:{function_name}:{cache_hash}"


def _serialize_args(args: tuple) -> list:
    """Serialize positional arguments."""
    serialized = []
    for arg in args:
        if isinstance(arg, (str, int, float, bool, type(None))):
            serialized.append(arg)
        elif isinstance(arg, (dict, list)):
            serialized.append(json.dumps(arg, sort_keys=True))
        else:
            serialized.append(str(arg))
    return serialized


def _serialize_kwargs(kwargs: dict) -> dict:
    """Serialize keyword arguments."""
    serialized = {}
    for key, value in kwargs.items():
        if isinstance(value, (str, int, float, bool, type(None))):
            serialized[key] = value
        elif isinstance(value, (dict, list)):
            serialized[key] = json.dumps(value, sort_keys=True)
        else:
            serialized[key] = str(value)
    return serialized


# Celery app configuration
celery_app = Celery(
    "legaiq_workers",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.environ.get("CELERY_BACKEND_URL", "redis://localhost:6379/0"),
    include=["app.workers.tasks"]
)

# Redis connection for cache
celery_app.conf.update(
    task_serializer="pickle",
    accept_content=["pickle"],
    result_serializer="pickle",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes max per task
    worker_prefetch_multiplier=1
)

# Task routing
celery_app.conf.task_routes = {
    "tasks.run_ocr": {"queue": "ocr"},
    "tasks.run_extraction": {"queue": "extraction"},
    "tasks.generate_embeddings": {"queue": "embeddings"},
    "tasks.reconstruct_title_chain": {"queue": "title"},
    "tasks.analyze_risks": {"queue": "analysis"},
}
```

### 12.2 Caching Strategy

**File**: `backend/app/workers/caching.py` (NEW)

```python
"""
Celery Worker Caching Module

Provides caching functions for OCR, extraction, and title chain results.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID
import hashlib
import json
import pickle

from app.workers.celery_app import get_redis_client


class WorkerCache:
    """Caching operations for Celery workers."""
    
    # Cache TTLs
    OCR_TTL = 86400  # 24 hours
    EXTRACTION_TTL = 604800  # 7 days
    TITLE_CHAIN_TTL = 604800  # 7 days
    
    @classmethod
    def generate_cache_key(cls, case_id: UUID, document_id: UUID, 
                          job_type: str, params: Dict[str, Any]) -> str:
        """Generate unique cache key for worker operation."""
        # Create parameter hash
        param_hash = hashlib.md5(
            json.dumps(params, sort_keys=True).encode()
        ).hexdigest()
        
        return f"legaiq:worker:{case_id}:{document_id}:{job_type}:{param_hash}"
    
    @classmethod
    def cache_ocr_result(cls, case_id: UUID, document_id: UUID, 
                        ocr_result: Dict[str, Any]) -> str:
        """Cache OCR result."""
        redis = get_redis_client()
        
        params = {
            "provider": ocr_result.get("provider", "unknown"),
            "document_type": ocr_result.get("document_type", "general"),
            "languages": ocr_result.get("detected_languages", [])
        }
        
        cache_key = cls.generate_cache_key(case_id, document_id, "ocr", params)
        
        redis.setex(
            cache_key,
            cls.OCR_TTL,
            pickle.dumps(ocr_result)
        )
        
        return cache_key
    
    @classmethod
    def get_ocr_result(cls, case_id: UUID, document_id: UUID,
                      provider: str, document_type: str, 
                      languages: list) -> Optional[Dict[str, Any]]:
        """Get cached OCR result."""
        redis = get_redis_client()
        
        params = {
            "provider": provider,
            "document_type": document_type,
            "languages": languages
        }
        
        cache_key = cls.generate_cache_key(case_id, document_id, "ocr", params)
        
        cached = redis.get(cache_key)
        if cached:
            return pickle.loads(cached)
        
        return None
    
    @classmethod
    def cache_extraction_result(cls, case_id: UUID, document_id: UUID,
                               extraction_result: Dict[str, Any]) -> str:
        """Cache entity extraction result."""
        redis = get_redis_client()
        
        params = {
            "document_type": extraction_result.get("document_type", "general"),
            "languages": extraction_result.get("detected_languages", [])
        }
        
        cache_key = cls.generate_cache_key(case_id, document_id, "extraction", params)
        
        redis.setex(
            cache_key,
            cls.EXTRACTION_TTL,
            pickle.dumps(extraction_result)
        )
        
        return cache_key
    
    @classmethod
    def get_extraction_result(cls, case_id: UUID, document_id: UUID,
                             document_type: str, languages: list) -> Optional[Dict[str, Any]]:
        """Get cached extraction result."""
        redis = get_redis_client()
        
        params = {
            "document_type": document_type,
            "languages": languages
        }
        
        cache_key = cls.generate_cache_key(case_id, document_id, "extraction", params)
        
        cached = redis.get(cache_key)
        if cached:
            return pickle.loads(cached)
        
        return None
    
    @classmethod
    def cache_title_chain(cls, case_id: UUID, 
                         title_chain: Dict[str, Any]) -> str:
        """Cache title chain reconstruction result."""
        redis = get_redis_client()
        
        params = {
            "method": "graph_based",
            "version": "1.0"
        }
        
        cache_key = cls.generate_cache_key(case_id, "title_chain", "title_chain", params)
        
        redis.setex(
            cache_key,
            cls.TITLE_CHAIN_TTL,
            pickle.dumps(title_chain)
        )
        
        return cache_key
    
    @classmethod
    def get_title_chain(cls, case_id: UUID) -> Optional[Dict[str, Any]]:
        """Get cached title chain result."""
        redis = get_redis_client()
        
        params = {
            "method": "graph_based",
            "version": "1.0"
        }
        
        cache_key = cls.generate_cache_key(case_id, "title_chain", "title_chain", params)
        
        cached = redis.get(cache_key)
        if cached:
            return pickle.loads(cached)
        
        return None
    
    @classmethod
    def invalidate_cache(cls, case_id: UUID, document_id: UUID = None,
                        job_type: str = None) -> int:
        """Invalidate cached results for case/document."""
        redis = get_redis_client()
        
        # Build pattern for cache key deletion
        if document_id and job_type:
            pattern = f"legaiq:worker:{case_id}:{document_id}:{job_type}:*"
        elif document_id:
            pattern = f"legaiq:worker:{case_id}:{document_id}:*"
        else:
            pattern = f"legaiq:worker:{case_id}:*"
        
        # Delete matching keys
        keys = redis.keys(pattern)
        if keys:
            return redis.delete(*keys)
        
        return 0


# Cache instance
cache = WorkerCache()
```

---

## 13. Multi-Agent Orchestration (FR-7)

### 13.1 Agent Context Serialization

**File**: `backend/app/ai/agents/base.py` (MODIFIED)

```python
"""
Base agent classes with context serialization support.
"""

from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class AgentContext(BaseModel):
    """
    Agent context for state passing between agents.
    
    Serializes to JSON for Celery task payloads.
    """
    version: str = "1.0"
    
    # Workflow context
    case_id: UUID
    workflow_id: Optional[UUID] = None
    workflow_type: str = "custom"
    
    # Agent context
    agent_id: UUID = Field(default_factory=uuid4)
    agent_name: str = "unknown"
    agent_role: str = "general"
    
    # Input/Output context
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    context_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Execution context
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    status: str = "INIT"
    error_message: Optional[str] = None
    
    # Metadata
    user_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            UUID: lambda v: str(v),
            datetime: lambda v: v.isoformat()
        }


class Agent(BaseModel):
    """Base agent class with context serialization support."""
    
    name: str
    role: str
    description: str
    max_retries: int = 3
    
    async def run(self, context: AgentContext) -> AgentContext:
        """
        Run agent with context.
        
        Args:
            context: AgentContext with input data
            
        Returns:
            Updated context with output data
        """
        raise NotImplementedError
    
    def serialize_context(self, context: AgentContext) -> str:
        """Serialize context to JSON string."""
        return context.json()
    
    def deserialize_context(self, context_json: str) -> AgentContext:
        """Deserialize context from JSON string."""
        return AgentContext.parse_raw(context_json)


class BudgetExceededError(Exception):
    """Raised when agent exceeds its budget."""
    pass


class LoopLimitError(Exception):
    """Raised when agent exceeds iteration limit."""
    pass


class Permission(Enum):
    """Agent permissions."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


class AgentBudget(BaseModel):
    """Agent budget configuration."""
    max_iterations: int = 100
    max_tokens: int = 100000
    max_cost: float = 10.0
    time_limit_seconds: int = 3600
```

### 13.2 State Transition System

**File**: `backend/app/ai/agents/orchestration.py` (MODIFIED)

```python
"""
Agent orchestration state machine.
"""

from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class WorkflowStatus(Enum):
    """Workflow status."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class NodeStatus(Enum):
    """Node status within workflow."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    RETRYING = "RETRYING"


class WorkflowNode(BaseModel):
    """Node in workflow graph."""
    node_id: UUID = Field(default_factory=uuid4)
    agent_name: str
    agent_role: str
    status: NodeStatus = NodeStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    dependencies: List[UUID] = Field(default_factory=list)


class WorkflowState(BaseModel):
    """State of workflow execution."""
    workflow_id: UUID = Field(default_factory=uuid4)
    case_id: UUID
    workflow_type: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    nodes: Dict[UUID, WorkflowNode] = Field(default_factory=dict)
    current_node: Optional[UUID] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_node(self, node: WorkflowNode) -> None:
        """Add node to workflow."""
        self.nodes[node.node_id] = node
    
    def get_node(self, node_id: UUID) -> Optional[WorkflowNode]:
        """Get node by ID."""
        return self.nodes.get(node_id)
    
    def update_node(self, node_id: UUID, **updates) -> bool:
        """Update node status."""
        if node_id not in self.nodes:
            return False
        
        node = self.nodes[node_id]
        for key, value in updates.items():
            if hasattr(node, key):
                setattr(node, key, value)
        
        return True
    
    def is_completed(self) -> bool:
        """Check if workflow is completed."""
        if self.status == WorkflowStatus.FAILED:
            return True
        
        if self.status == WorkflowStatus.PENDING:
            return False
        
        # Check all nodes are completed
        for node in self.nodes.values():
            if node.status not in [NodeStatus.COMPLETED, NodeStatus.SKIPPED]:
                return False
        
        return True
    
    def get_next_nodes(self, current_node_id: UUID) -> List[WorkflowNode]:
        """Get nodes that can run after current node."""
        current_node = self.nodes.get(current_node_id)
        if not current_node:
            return []
        
        next_nodes = []
        for node in self.nodes.values():
            if node.status == NodeStatus.PENDING:
                if current_node.node_id in node.dependencies:
                    next_nodes.append(node)
        
        return next_nodes
```

### 13.3 Agent Chaining API

**File**: `backend/app/api/agents.py` (NEW)

```python
"""
Agent orchestration API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.config import get_settings
from app.security.auth import get_case_access
from app.workers.celery_app import celery_app
from app.ai.agents.orchestration import WorkflowState, WorkflowNode, WorkflowStatus

router = APIRouter(prefix="/api/v1/cases/{case_id}/agents", tags=["agents"])

settings = get_settings()


class OrchestratorRequest(BaseModel):
    """Request for agent orchestration."""
    workflow_type: str = "custom"
    agent_order: List[str] = []
    context: Dict[str, Any] = {}
    parallel: bool = False


class OrchestratorResponse(BaseModel):
    """Response for agent orchestration."""
    job_id: UUID
    status: str = "PENDING"


@router.post("/orchestrate")
async def orchestrate_agents(
    case_id: str,
    body: OrchestratorRequest,
    user = Depends(get_case_access)
):
    """
    Orchestrate agent workflow.
    
    Supports:
    - Sequential execution (default)
    - Parallel execution (optional)
    - Custom agent ordering
    - Context passing between agents
    """
    # Create workflow state
    workflow = WorkflowState(
        case_id=UUID(case_id),
        workflow_type=body.workflow_type
    )
    
    # Create nodes for each agent
    for agent_name in body.agent_order or ["due_diligence", "title", "contract", "litigation", "bsa", "research"]:
        node = WorkflowNode(
            agent_name=agent_name,
            agent_role=agent_name.replace("_", " ").title()
        )
        workflow.add_node(node)
    
    # Initialize first node
    if workflow.nodes:
        first_node = list(workflow.nodes.values())[0]
        workflow.current_node = first_node.node_id
        workflow.update_node(first_node.node_id, status="PENDING")
    
    # Start workflow
    job_id = workflow.workflow_id
    
    # Queue workflow execution
    from app.workers.tasks import orchestrate_workflow_task
    orchestrate_workflow_task.delay(
        case_id=str(case_id),
        workflow_id=str(job_id),
        agent_order=body.agent_order,
        context=body.context,
        parallel=body.parallel
    )
    
    return OrchestratorResponse(
        job_id=job_id,
        status="PENDING"
    )


@router.get("/{job_id}/status")
async def get_orchestration_status(
    case_id: str,
    job_id: UUID,
    user = Depends(get_case_access)
):
    """Get orchestration job status."""
    # This would query the database for workflow state
    # For now, return placeholder
    return {
        "job_id": job_id,
        "case_id": case_id,
        "status": "RUNNING",
        "nodes": []
    }
```

---

## 14. JSON Schema Compliance (FR-8)

### 14.1 Schema Definitions

**File**: `backend/app/schemas/definitions/document.json` (NEW)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://legaiq.com/schemas/document/v1",
  "title": "Document Record",
  "description": "Document record structure for LegAIQ platform",
  "type": "object",
  "version": "v1",
  
  "properties": {
    "document_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique document identifier"
    },
    "case_id": {
      "type": "string",
      "format": "uuid",
      "description": "Parent case identifier"
    },
    "filename": {
      "type": "string",
      "description": "Original filename"
    },
    "file_type": {
      "type": "string",
      "description": "MIME type of document"
    },
    "storage_path": {
      "type": "string",
      "description": "Storage path in Supabase"
    },
    "page_count": {
      "type": "integer",
      "minimum": 0
    },
    "language": {
      "type": "string",
      "description": "Primary language code (ISO 639-1)"
    },
    "ocr_confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    },
    "document_type": {
      "type": "string",
      "enum": ["general", "7_12_extract", "rtc_pahani", "patta_chitta", "sale_deed", "gift_deed", "partition_deed", "mortgage_deed", "will"]
    },
    "status": {
      "type": "string",
      "enum": ["UPLOADED", "OCR_QUEUED", "OCR_RUNNING", "OCR_COMPLETED", "EXTRACTING", "EXTRACTED", "FAILED"]
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time"
    }
  },
  
  "required": ["document_id", "case_id", "filename", "file_type", "storage_path", "status", "created_at"]
}
```

**File**: `backend/app/schemas/definitions/ocr_result.json` (NEW)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://legaiq.com/schemas/ocr_result/v1",
  "title": "OCR Processing Result",
  "description": "OCR result structure for LegAIQ platform",
  "type": "object",
  "version": "v1",
  
  "properties": {
    "document_id": {
      "type": "string",
      "format": "uuid"
    },
    "pages": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "page_number": {
            "type": "integer",
            "minimum": 1
          },
          "text": {
            "type": "string"
          },
          "language": {
            "type": "string"
          },
          "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
          },
          "language_confidence": {
            "type": "object",
            "properties": {
              "primary": {"type": "string"},
              "secondary": {"type": "string"},
              "primary_confidence": {"type": "number"},
              "bilingual_modifier": {"type": "number"}
            }
          },
          "bilingual_content": {
            "type": "boolean"
          },
          "script": {
            "type": "string"
          }
        },
        "required": ["page_number", "text", "language", "confidence"]
      }
    },
    "provider": {
      "type": "string",
      "enum": ["tesseract", "paddleocr", "google_vision"]
    },
    "document_type": {
      "type": "string"
    },
    "detected_languages": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "mean_confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    }
  },
  
  "required": ["document_id", "pages", "provider", "document_type", "detected_languages"]
}
```

### 14.2 Schema Validation Middleware

**File**: `backend/app/middleware/schema_validation.py` (NEW)

```python
"""
JSON Schema Validation Middleware for FastAPI.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from jsonschema import validate, ValidationError

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse


class SchemaValidator:
    """JSON Schema validator for LegAIQ API."""
    
    def __init__(self, schemas_dir: str = "app/schemas/definitions"):
        self.schemas_dir = Path(schemas_dir)
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self._load_schemas()
    
    def _load_schemas(self) -> None:
        """Load all schemas from directory."""
        if not self.schemas_dir.exists():
            return
        
        for schema_file in self.schemas_dir.glob("*.json"):
            with open(schema_file) as f:
                schema_data = json.load(f)
                schema_id = schema_data.get("$id", schema_file.stem)
                version = schema_data.get("version", "v1")
                self.schemas[f"{schema_id}:{version}"] = schema_data
    
    def validate_request(self, data: Dict[str, Any], schema_name: str, 
                        version: str = "v1") -> bool:
        """Validate request data against schema."""
        schema_key = f"{schema_name}:{version}"
        
        if schema_key not in self.schemas:
            raise ValueError(f"Schema not found: {schema_key}")
        
        try:
            validate(instance=data, schema=self.schemas[schema_key])
            return True
        except ValidationError as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Validation failed",
                    "message": e.message,
                    "path": list(e.path),
                    "schema": e.schema
                }
            )
    
    def validate_response(self, data: Dict[str, Any], schema_name: str,
                         version: str = "v1") -> bool:
        """Validate response data against schema."""
        return self.validate_request(data, schema_name, version)


# Global validator instance
validator = SchemaValidator()


async def validate_request_body(schema_name: str, version: str = "v1"):
    """FastAPI dependency for request body validation."""
    async def validator_dep(request: Request):
        try:
            body = await request.json()
            validator.validate_request(body, schema_name, version)
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid request body")
    
    return validator_dep
```

### 14.3 Migration Script

**File**: `scripts/migrate_to_schemas.py` (NEW)

```python
"""
Migration script to update existing data to conform to new schemas.
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List

from supabase import create_client, Client
from app.config import get_settings


def load_schema(schema_name: str, version: str = "v1") -> Dict[str, Any]:
    """Load schema from file."""
    schema_path = Path(f"app/schemas/definitions/{schema_name}.json")
    with open(schema_path) as f:
        schema = json.load(f)
    return schema


def migrate_document(data: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate document record to new schema."""
    migrated = {
        "document_id": str(data.get("id")),
        "case_id": str(data.get("case_id")),
        "filename": data.get("filename", "unknown"),
        "file_type": data.get("file_type", "application/pdf"),
        "storage_path": data.get("storage_path", ""),
        "page_count": data.get("page_count", 0),
        "language": data.get("language"),
        "ocr_confidence": data.get("ocr_confidence", 0),
        "document_type": data.get("document_type", "general"),
        "status": data.get("status", "UPLOADED"),
        "metadata": data.get("metadata", {}),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at")
    }
    
    return migrated


def migrate_ocr_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate OCR result to new schema."""
    pages = []
    
    for page in data.get("pages", []):
        pages.append({
            "page_number": page.get("page_number"),
            "text": page.get("text", ""),
            "language": page.get("language", "en"),
            "confidence": page.get("confidence", 0),
            "language_confidence": page.get("language_confidence", {}),
            "bilingual_content": page.get("bilingual_content", False),
            "script": page.get("script", "Latin")
        })
    
    migrated = {
        "document_id": str(data.get("document_id")),
        "pages": pages,
        "provider": data.get("provider", "tesseract"),
        "document_type": data.get("document_type", "general"),
        "detected_languages": data.get("detected_languages", ["en"]),
        "mean_confidence": data.get("mean_confidence", 0)
    }
    
    return migrated


async def migrate_data():
    """Run migration for all data."""
    settings = get_settings()
    
    # Initialize Supabase client
    supabase: Client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY
    )
    
    # Migrate documents
    documents = supabase.table("documents").select("*").execute()
    
    for doc in documents.data:
        migrated = migrate_document(doc)
        
        # Update in database
        supabase.table("documents").update(migrated).eq("id", doc["id"]).execute()
        
        print(f"Migrated document: {doc['id']}")
    
    # Migrate OCR results
    ocr_results = supabase.table("document_pages").select("*").execute()
    
    # Group by document_id
    pages_by_doc = {}
    for page in ocr_results.data:
        doc_id = str(page["document_id"])
        if doc_id not in pages_by_doc:
            pages_by_doc[doc_id] = []
        pages_by_doc[doc_id].append(page)
    
    for doc_id, pages in pages_by_doc.items():
        # Build OCR result
        ocr_result = {
            "document_id": doc_id,
            "pages": pages,
            "provider": "tesseract",
            "document_type": "general",
            "detected_languages": ["en"],
            "mean_confidence": 0.9
        }
        
        migrated = migrate_ocr_result(ocr_result)
        
        # Store migrated result
        supabase.table("ocr_results").insert(migrated).execute()
        
        print(f"Migrated OCR result: {doc_id}")
    
    print("Migration completed!")


if __name__ == "__main__":
    asyncio.run(migrate_data())
```

---

## 15. Implementation Plan

### Phase 1: Priority 1 - Integration Failures (2 weeks)
1. **Week 1**:
   - Deep Research Integration (FR-1)
   - Database Schema (FR-1.2)
   - Frontend Integration (FR-1.4)

2. **Week 2**:
   - Document Viewer Authentication (FR-2)
   - BSA Section 63 Certification (FR-3)

### Phase 2: Priority 2 - Feature Enhancements (2 weeks)
1. **Week 1**:
   - OCR Bilingual Enhancement (FR-4)
   - Indian Date Format Parsing (FR-5)

2. **Week 2**:
   - Celery Worker Caching (FR-6)
   - Testing and documentation

### Phase 3: Priority 3 - Production Hardening (2 weeks)
1. **Week 1**:
   - Multi-Agent Orchestration (FR-7)
   - JSON Schema Compliance (FR-8.1, FR-8.2)

2. **Week 2**:
   - Migration Script (FR-8.3)
   - Testing, performance optimization, documentation

---

## 16. Testing Strategy

### 16.1 Unit Tests
- **Deep Research**: Test OpenAI API integration, event streaming, result storage
- **Authentication**: Test pre-signed URL generation with token forwarding
- **BSA Certificates**: Test SHA-256 hash generation, PDF certificate creation
- **OCR Enhancement**: Test bilingual confidence calibration, document type detection
- **Date Parser**: Test Indian date format parsing, Devanagari conversion
- **Caching**: Test Redis cache operations, key generation, TTL handling
- **Agent Orchestration**: Test context serialization, state transitions, workflow execution
- **Schema Validation**: Test request/response validation, error handling

### 16.2 Integration Tests
- End-to-end deep research workflow
- Document upload → OCR → extraction → caching pipeline
- BSA certificate generation and download
- Multi-agent workflow orchestration
- Schema validation middleware

### 16.3 Performance Tests
- Deep research streaming response time (<5 seconds)
- Document download URL generation (<100ms)
- OCR caching performance (>80% improvement)
- Agent orchestration parallel execution overhead (<200ms)
- Schema validation latency (<50ms)

### 16.4 Security Tests
- RLS policy enforcement
- Authentication token forwarding
- SQL injection prevention
- XSS prevention
- Rate limiting

---

## 17. Security Considerations

### NFR-1: Security Requirements

1. **Deep Research API**:
   - API keys must not be logged or exposed in responses
   - Use environment variables for OpenAI API key
   - Implement request rate limiting

2. **Document Download URLs**:
   - URLs must expire after configurable timeout (default: 1 hour)
   - Implement IP-based binding for URLs
   - Log all document access for audit trail

3. **BSA Certificates**:
   - Include audit trail with timestamp and user ID
   - Store certificates in immutable storage
   - Implement certificate signing verification

4. **Redis Cache**:
   - Enable Redis authentication
   - Use TLS for Redis connections in production
   - Implement cache invalidation for sensitive data

5. **Authentication**:
   - All endpoints must enforce existing Supabase RLS policies
   - Implement request signing for internal API calls
   - Use secure session handling

---

## 18. Performance Targets

### NFR-2: Performance Requirements

1. **Deep Research**:
   - Streaming response begins within 5 seconds of request
   - Final report delivered within 30 seconds for o4-mini-deep-research
   - Support concurrent requests up to 100

2. **Document Viewer**:
   - Pre-signed URL generation <100ms
   - Document download URL expires after 1 hour (configurable)
   - Support 1000 concurrent document views

3. **OCR Caching**:
   - Reduce repeated OCR processing time from 30s to <5s
   - Cache hit rate >90% for repeated documents
   - Cache TTL: 24 hours for OCR, 7 days for extraction

4. **Agent Orchestration**:
   - Support parallel execution with <200ms overhead
   - State transition time <100ms
   - Workflow recovery time <60 seconds

5. **Schema Validation**:
   - Add <50ms latency to API responses
   - Support schema version negotiation via Accept header
   - Handle validation errors gracefully

---

## 19. Migration Path

### Database Migrations
1. `016_deep_research.sql` - Deep research results table
2. `017_deep_research_rls.sql` - RLS policies for deep research
3. `018_deep_research_events.sql` - Deep research events for streaming
4. `019_storage_policies.sql` - Storage bucket policies
5. `020_bsa_certificates.sql` - BSA certificate storage table

### Configuration Changes
- Add `DEEP_RESEARCH_ASSISTANT_ID` to environment variables
- Add `OPENAI_API_KEY` for Deep Research (if not already present)
- Configure Redis connection in `docker-compose.yml`

### Frontend Changes
- Add `DeepResearchPanel` component to case workspace
- Update `DocumentViewer` with token forwarding
- Add certificate download integration

---

## 20. Deployment Checklist

- [ ] Apply database migrations
- [ ] Configure Redis in production
- [ ] Set environment variables for Deep Research
- [ ] Update RLS policies
- [ ] Deploy backend changes
- [ ] Deploy frontend changes
- [ ] Run migration script for existing data
- [ ] Test all features
- [ ] Verify security policies
- [ ] Monitor performance metrics
- [ ] Update documentation

---

**Document Status**: DESIGN COMPLETE  
**Next Steps**: IMPLEMENTATION  
**Version**: 1.0  
**Date**: 2025-04-05