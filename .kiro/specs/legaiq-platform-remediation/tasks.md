# Tasks: LegAIQ Legal Intelligence Platform Remediation

**Feature**: legaiq-platform-remediation  
**Version**: 1.0  
**Date**: 2025-04-05  
**Status**: TASKS

---

## Milestone 1: Critical Integration Fixes (Week 1)

### T1.1.1: Deep Research FastAPI Integration - Create New Endpoint
**Estimated Effort**: 16 hours  
**Dependencies**: None  
**Files to Modify/Create**: `backend/app/api/deep_research.py` (NEW)

#### Description
Create a new FastAPI endpoint at `/api/v1/cases/{case_id}/deep-research` to replace the Streamlit deep research app and integrate with the main application.

#### Acceptance Criteria
- [-] Endpoint accepts POST with `question`, `model`, and `max_tool_calls` fields
- [~] Returns 202 Accepted with task_id and status "PENDING"
- [~] Returns 404 if case doesn't exist or user lacks access
- [~] Supports o4-mini-deep-research and o3-deep-research models
- [~] Implements proper authentication via existing `get_case_access` dependency
- [~] Creates deep research session for streaming state

#### Testing Requirements
- Unit tests for request validation
- Integration tests for case access control
- Test 404 responses for non-existent cases
- Test authentication rejection

---

### T1.1.2: Deep Research Streaming Support - SSE Implementation
**Estimated Effort**: 12 hours  
**Dependencies**: T1.1.1  
**Files to Modify/Create**: `backend/app/api/deep_research.py` (MODIFIED)

#### Description
Implement Server-Sent Events (SSE) streaming for deep research progress updates to the frontend.

#### Acceptance Criteria
- [~] SSE endpoint at `/api/v1/cases/{case_id}/deep-research/stream/{task_id}`
- [~] Streams events: `reasoning`, `web_search`, `citation_found`, `step_completed`
- [~] Final message with "complete" type containing final report
- [~] Error events with clear error messages
- [~] Connection stays alive during research (max 5 minutes)
- [~] Client-side reconnection support

#### Testing Requirements
- Test SSE connection establishment
- Test event streaming during research
- Test connection timeout handling
- Test error event transmission
- Test client-side event handling

---

### T1.1.3: Deep Research Celery Task Integration
**Estimated Effort**: 16 hours  
**Dependencies**: T1.1.2, T1.2.1 (DB migration)  
**Files to Modify/Create**: `backend/app/workers/tasks.py` (MODIFIED), `backend/app/workers/deep_research.py` (NEW)

#### Description
Implement Celery task for async deep research processing with OpenAI API integration.

#### Acceptance Criteria
- [~] Task: `tasks.deep_research_task(case_id, user_id, question, model, max_tool_calls)`
- [~] Returns `{"task_id": str, "status": "PENDING" | "SUCCESS" | "FAILURE"}`
- [~] Creates deep research session in Supabase
- [~] Streams events to Supabase for real-time updates
- [~] Stores final report in `deep_research_results` table
- [~] Handles OpenAI API errors with retry logic (max 3 retries)
- [~] Updates session status on completion (SUCCESS/FAILURE)

#### Testing Requirements
- Unit tests for task initialization
- Test OpenAI API integration (with mock or actual)
- Test retry logic with simulated failures
- Test session state management
- Test report storage

---

### T1.1.4: Deep Research Database Migration
**Estimated Effort**: 4 hours  
**Dependencies**: None  
**Files to Modify/Create**: `supabase/migrations/016_deep_research.sql` (NEW), `supabase/migrations/017_deep_research_rls.sql` (NEW), `supabase/migrations/018_deep_research_events.sql` (NEW)

#### Description
Create database tables and RLS policies for deep research results and sessions.

#### Acceptance Criteria
- [~] `deep_research_results` table with proper schema
- [~] `deep_research_sessions` table for streaming state
- [~] `deep_research_events` table for event storage
- [~] RLS policies for user isolation
- [~] Admin access policy
- [~] Proper indexes on foreign keys
- [~] Migration runs without errors

#### Testing Requirements
- Test migration execution
- Verify table creation
- Test RLS policy enforcement
- Test cascade deletes

---

### T1.1.5: Deep Research Frontend Component
**Estimated Effort**: 24 hours  
**Dependencies**: T1.1.1, T1.1.2  
**Files to Modify/Create**: `frontend/components/deep-research/DeepResearchPanel.tsx` (NEW), `frontend/lib/api.ts` (MODIFIED)

#### Description
Create frontend component for accessing deep research from case workspace with live streaming.

#### Acceptance Criteria
- [~] Panel accessible from case detail page "Research" tab
- [~] Question input with example suggestions
- [~] Model selector (o4-mini, o3)
- [~] Max tool calls slider with guidance
- [~] Live streaming progress feed
- [~] Final report display with markdown rendering
- [~] Citation list with link preview
- [~] Download report as Markdown
- [~] Accessible from case workspace

#### Testing Requirements
- Unit tests for component state
- Integration tests for API calls
- Test SSE connection from frontend
- Test markdown rendering
- Test download functionality

---

### T1.2.1: Document Viewer Signed URLs - Backend Endpoint
**Estimated Effort**: 12 hours  
**Dependencies**: None  
**Files to Modify/Create**: `backend/app/api/documents.py` (MODIFIED)

#### Description
Implement pre-signed URL generation endpoint with token forwarding for Supabase Storage.

#### Acceptance Criteria
- [~] Endpoint at `/api/v1/cases/{case_id}/documents/{document_id}/download-url`
- [~] Generates signed URL with token forwarding
- [~] Returns URL with proper cache-control headers
- [~] Supports configurable expiration (default 1 hour)
- [~] Returns 404 for non-existent documents
- [~] Returns 403 for unauthorized access
- [~] Validates document belongs to case

#### Testing Requirements
- Test signed URL generation
- Test token forwarding in headers
- Test 404 responses
- Test 403 responses
- Test URL expiration

---

### T1.2.2: Document Viewer RLS Policy Configuration
**Estimated Effort**: 8 hours  
**Dependencies**: None  
**Files to Modify/Create**: `supabase/migrations/019_storage_policies.sql` (NEW)

#### Description
Update Supabase RLS policies to allow authenticated storage access with case membership checks.

#### Acceptance Criteria
- [~] Policy `authenticated_users_can_read_case_documents` with case membership check
- [~] Function `case_member(user_id, case_id)` for membership verification
- [~] Admin access policy for service role operations
- [~] Policies allow both document owner and case members
- [ ] Migration runs without errors

#### Testing Requirements
- Test migration execution
- Verify RLS policy enforcement
- Test with case owner
- Test with case member
- Test with non-member (should fail)

---

### T1.2.3: Document Viewer Frontend Token Forwarding
**Estimated Effort**: 16 hours  
**Dependencies**: T1.2.1, T1.2.2  
**Files to Modify/Create**: `frontend/components/document-viewer/DocumentViewer.tsx` (MODIFIED), `frontend/components/document-viewer/types.ts` (MODIFIED)

#### Description
Update DocumentViewer component to forward authentication tokens in requests.

#### Acceptance Criteria
- [~] Component loads Supabase auth token
- [~] Token forwarded in Authorization header
- [~] HEAD requests with token forwarding
- [~] GET fallback on HEAD 405/501
- [~] Clear error messages for 403/404
- [~] Retry logic for transient failures (max 3 retries)
- [~] Component tested with authenticated requests

#### Testing Requirements
- Unit tests for token handling
- Integration tests for document retrieval
- Test with valid token
- Test with expired token
- Test retry logic

---

### T1.3.1: BSA Section 63 SHA-256 Hash Generation
**Estimated Effort**: 12 hours  
**Dependencies**: None  
**Files to Modify/Create**: `backend/app/ai/bsa_certificates.py` (NEW - partial), `backend/app/api/documents.py` (MODIFIED)

#### Description
Implement cryptographically secure SHA-256 hashing for electronic records with metadata inclusion.

#### Acceptance Criteria
- [~] Function `generate_file_hash(file_bytes, filename, timestamp)` returns SHA-256 hex digest
- [~] Hash format: `{filename}|{size}|{timestamp}|{content_hash}`
- [~] Function `generate_incremental_hash(file_path)` for large files
- [~] Function `verify_hash(file_bytes, expected_hash, filename)` for integrity verification
- [~] Hash stored in `documents.hash_value` column
- [~] Hash regenerated on document update

#### Testing Requirements
- Unit tests for hash generation
- Test incremental hashing for large files
- Test hash verification
- Test metadata inclusion in hash
- Test hash collisions (should not happen)

---

### T1.3.2: BSA Section 63 Certificate PDF Generation
**Estimated Effort**: 20 hours  
**Dependencies**: T1.3.1  
**Files to Modify/Create**: `backend/app/ai/bsa_certificates.py` (MODIFIED)

#### Description
Generate court-admissible Section 63 electronic evidence certificates as PDF.

#### Acceptance Criteria
- [~] Function `generate_section63_certificate(evidence, custodian)` returns PDF bytes
- [~] Certificate includes header with statutory declaration
- [~] Certificate includes evidence identification (file name, hash, algorithm)
- [~] Certificate includes system parameters
- [~] Certificate includes custodian declaration
- [~] Certificate includes custodian information
- [~] Certificate includes timestamp and verification info
- [~] PDF generated using reportlab

#### Testing Requirements
- Test PDF generation
- Verify PDF structure
- Test hash inclusion in certificate
- Test custodian information formatting

---

### T1.3.3: BSA Section 63 Certificate API Endpoint
**Estimated Effort**: 12 hours  
**Dependencies**: T1.3.2, T1.3.4 (DB migration)  
**Files to Modify/Create**: `backend/app/api/bsa_certificates.py` (NEW)

#### Description
Create API endpoint for downloading Section 63 certificates.

#### Acceptance Criteria
- [~] POST endpoint at `/api/v1/cases/{case_id}/documents/{document_id}/bsa-certificate`
- [~] GET endpoint for certificate download
- [~] Supports `?format=pdf|json` parameter
- [~] Verifies user has access to case
- [~] Returns PDF with proper Content-Disposition header
- [~] Returns JSON with certificate metadata
- [~] Logs certificate generation for audit trail

#### Testing Requirements
- Test certificate generation
- Test PDF download
- Test JSON download
- Test access control
- Test audit logging

---

### T1.3.4: BSA Section 63 Certificate Database Schema
**Estimated Effort**: 4 hours  
**Dependencies**: None  
**Files to Modify/Create**: `supabase/migrations/020_bsa_certificates.sql` (NEW)

#### Description
Create database tables for storing BSA certificates and audit trail.

#### Acceptance Criteria
- [~] `bsa_certificates` table with proper schema
- [~] `bsa_certificate_audit` table for audit trail
- [ ] RLS policies for user isolation
- [ ] Proper indexes on foreign keys
- [ ] Migration runs without errors

#### Testing Requirements
- Test migration execution
- Verify table creation
- Test RLS policy enforcement

---

## Milestone 2: Feature Enhancements (Week 2)

### T2.1.1: OCR Bilingual Language Detection
**Estimated Effort**: 12 hours  
**Dependencies**: None  
**Files to Modify/Create**: `backend/app/ai/indic_ocr.py` (MODIFIED)

#### Description
Implement language detection and confidence calibration for bilingual documents.

#### Acceptance Criteria
- [~] Function `calibrate_confidence_for_bilingual(page_text, primary_language, secondary_language)` returns confidence modifier
- [~] Detects script transitions for bilingual content
- [~] Applies ×0.95 modifier for bilingual documents
- [~] Applies ×1.0 modifier for monolingual documents
- [~] Tracks bilingual content flag in OCRPageResult
- [~] Stores language_confidence dictionary with primary/secondary

#### Testing Requirements
- Test bilingual document confidence calibration
- Test monolingual document confidence
- Test script transition detection
- Test confidence modifier application

---

### T2.1.2: OCR Document Type Detection Enhancement
**Estimated Effort**: 12 hours  
**Dependencies**: T2.1.1  
**Files to Modify/Create**: `backend/app/ai/indic_ocr.py` (MODIFIED)

#### Description>
Implement enhanced document type detection for Maharashtra land records.

#### Acceptance Criteria
- [~] Detects Maharashtra keywords in OCR text
- [~] Identifies "7_12_extract" document type
- [~] Identifies "RTC_PAHANI" for Karnataka
- [~] Identifies "PATTA_CHITTA" for Tamil Nadu
- [~] Returns "general" as default
- [~] Stores document_type in OCRDocumentResult

#### Testing Requirements
- Test Maharashtra document detection
- Test Karnataka document detection
- Test Tamil Nadu document detection
- Test default fallback

---

### T2.2.1: Indian Date Parser Multi-Format Support
**Estimated Effort**: 24 hours  
**Dependencies**: None  
**Files to Modify/Create**: `backend/app/utils/indian_date_parser.py` (NEW)

#### Description
Create robust date parser supporting Indian formats including Devanagari numerals and Vikram Samvat.

#### Acceptance Criteria
- [~] Supports DD/MM/YYYY format
- [~] Supports DD-MM-YYYY format
- [~] Supports DD MM YYYY format
- [~] Supports Devanagari numerals (१५/६/२००३)
- [~] Supports Vikram Samvat (V.S. 2060 → 2003 CE)
- [~] Supports Shalivahana Shaka (S.S. 1925 → 2003 CE)
- [~] Supports Marathi months (चैत्र, वैशाख)
- [~] Function `parse_indian_date(text)` returns datetime or None
- [~] Function `extract_dates(text)` returns all dates in text

#### Testing Requirements
- Test all supported formats
- Test Devanagari numeral conversion
- Test Vikram Samvat conversion
- Test Shalivahana Shaka conversion
- Test Marathi month parsing
- Test edge cases (invalid dates)

---

### T2.2.2: Entity Extraction Integration with Indian Date Parser
**Estimated Effort**: 8 hours  
**Dependencies**: T2.2.1  
**Files to Modify/Create**: `backend/app/ai/tasks.py` (MODIFIED), `backend/app/ai/indic_ocr.py` (MODIFIED)

#### Description
Update entity extraction to use new date parser instead of basic regex.

#### Acceptance Criteria
- [~] Replaces basic regex patterns with `parse_indian_date()`
- [~] Parses dates in party details section
- [~] Parses dates in property schedules
- [~] Parses dates in execution clauses
- [~] Parses dates in registration details
- [~] Stores parsed dates in normalized ISO format
- [~] Flags dates with low confidence for review

#### Testing Requirements
- Test entity extraction with Indian dates
- Test ISO format storage
- Test confidence flagging

---

### T2.3.1: Redis Integration for Celery Workers
**Estimated Effort**: 12 hours  
**Dependencies**: None  
**Files to Modify/Create**: `backend/app/config.py` (MODIFIED), `backend/app/workers/celery_app.py` (MODIFIED)

#### Description>
Add Redis caching layer configuration for Celery worker intermediate results.

#### Acceptance Criteria
- [~] Redis connection added to Celery config
- [~] Cache keys follow naming convention: `legaiq:{service}:{resource}:{id}:{hash}`
- [~] TTL: 24 hours for OCR results, 7 days for extraction results
- [~] Redis connection tested and working
- [~] Cache metrics implemented

#### Testing Requirements
- Test Redis connection
- Test cache key generation
- Test TTL enforcement

---

### T2.3.2: OCR Result Caching
**Estimated Effort**: 16 hours  
**Dependencies**: T2.3.1  
**Files to Modify/Create**: `backend/app/workers/cache.py` (NEW), `backend/app/workers/tasks.py` (MODIFIED)

#### Description
Implement caching strategy for OCR results with cache key generation.

#### Acceptance Criteria
- [~] Function `cache_ocr_result(case_id, document_id, ocr_result)`
- [~] Function `get_ocr_result(case_id, document_id)` returns cached result or None
- [~] Cache key based on hash of parameters
- [~] Returns `cached: true` flag for cached results
- [~] Cache invalidation on document update
- [~] Cache metrics logged

#### Testing Requirements
- Test cache storage
- Test cache retrieval
- Test cache invalidation
- Test cache hit/miss metrics

---

### T2.3.3: Extraction Result Caching
**Estimated Effort**: 12 hours  
**Dependencies**: T2.3.2  
**Files to Modify/Create**: `backend/app/workers/cache.py` (MODIFIED)

#### Description
Implement caching for entity extraction results.

#### Acceptance Criteria
- [~] Function `cache_extraction_result(case_id, document_id, extraction_result)`
- [~] Function `get_extraction_result(case_id, document_id)` returns cached result or None
- [ ] Cache invalidation on document update
- [ ] Cache metrics logged

#### Testing Requirements
- Test cache storage and retrieval
- Test cache invalidation

---

## Milestone 3: Production Hardening (Week 3)

### T3.1.1: Multi-Agent Context Serialization
**Estimated Effort**: 20 hours  
**Dependencies**: None  
**Files to Modify/Create**: `backend/app/agents/context.py` (NEW)

#### Description
Implement proper context serialization for agent state passing using Pydantic models.

#### Acceptance Criteria
- [~] `AgentContext` Pydantic model with all required fields
- [~] Function `serialize_context(context)` returns JSON string
- [~] Function `deserialize_context(json_str)` returns AgentContext
- [~] Context versioning supported
- [~] Context size limit (max 100KB) enforced
- [~] Context transitions logged for debugging

#### Testing Requirements
- Test context serialization
- Test context deserialization
- Test version compatibility
- Test size limit enforcement

---

### T3.1.2: Agent State Machine
**Estimated Effort**: 16 hours  
**Dependencies**: T3.1.1  
**Files to Modify/Create**: `backend/app/agents/state_machine.py` (NEW), `backend/app/workers/tasks.py` (MODIFIED)

#### Description
Create state machine for agent orchestration with proper state transitions.

#### Acceptance Criteria
- [~] States: INIT, RESEARCHING, ANALYZING, GENERATING, REVIEWING, COMPLETED, FAILED
- [~] State transitions logged in Supabase `agent_jobs.state`
- [~] Timeout handling for stuck states
- [~] Manual state override for recovery
- [~] State transitions trigger next agent in workflow

#### Testing Requirements
- Test state transitions
- Test timeout handling
- Test manual override

---

### T3.1.3: Multi-Agent Orchestration API
**Estimated Effort**: 20 hours  
**Dependencies**: T3.1.2  
**Files to Modify/Create**: `backend/app/api/agents.py` (NEW)

#### Description
Create API for orchestrating agent workflows with parallel execution support.

#### Acceptance Criteria
- [~] POST endpoint at `/api/v1/cases/{case_id}/agents/orchestrate`
- [~] Supports workflows: due_diligence, title, contract, litigation, bsa, research
- [~] Returns job_id and status
- [~] Supports parallel agent execution where safe
- [~] SSE streaming for progress updates
- [~] Returns aggregated results from all agents

#### Testing Requirements
- Test orchestration API
- Test parallel execution
- Test result aggregation
- Test SSE streaming

---

### T3.2.1: JSON Schema Repository
**Estimated Effort**: 16 hours  
**Dependencies**: None  
**Files to Modify/Create**: `backend/app/schemas/definitions/` (NEW directory with JSON files)

#### Description
Create centralized JSON schema repository with versioned schemas.

#### Acceptance Criteria
- [~] `document.json` schema
- [~] `ocr_result.json` schema
- [~] `extraction_result.json` schema
- [~] `title_chain.json` schema
- [~] `bsa_certificate.json` schema
- [~] `agent_result.json` schema
- [~] All schemas in JSON Schema Draft 2020-12 format
- [~] Versioned schemas (v1, v2, etc.)
- [~] Function `validate_schema(data, schema_name, version)` implemented

#### Testing Requirements
- Test schema validation
- Test versioned schemas
- Test validation failure handling

---

### T3.2.2: Schema Validation Middleware
**Estimated Effort**: 16 hours  
**Dependencies**: T3.2.1  
**Files to Modify/Create**: `backend/app/middleware/schema_validation.py` (NEW)

#### Description
Add JSON schema validation middleware to API endpoints.

#### Acceptance Criteria
- [~] Request body validation against schema
- [~] Response body validation against schema
- [~] Returns 400 with detailed error on validation failure
- [~] Logs validation errors for debugging
- [~] Supports schema version negotiation via Accept header
- [~] Adds <50ms latency to API responses

#### Testing Requirements
- Test request validation
- Test response validation
- Test 400 error responses
- Test latency measurement

---

## Task Summary

| Milestone | Tasks | Total Hours |
|-----------|-------|-------------|
| Milestone 1: Critical Integration Fixes | 12 | 124 |
| Milestone 2: Feature Enhancements | 7 | 84 |
| Milestone 3: Production Hardening | 6 | 52 |
| **Total** | **25** | **260** |

---

## Testing Summary

| Category | Tests | Coverage |
|----------|-------|----------|
| Unit Tests | 50+ | All new functions |
| Integration Tests | 20+ | All endpoints, DB operations |
| E2E Tests | 10+ | Critical user workflows |
| Performance Tests | 5+ | Latency, throughput |

---

## Deployment Checklist

- [~] Apply database migrations (016-020)
- [~] Verify Redis is running
- [~] Verify case-documents bucket exists
- [~] Run backend tests: `pytest backend/app`
- [~] Run frontend tests: `npm run test`
- [~] Run E2E tests: `npm run test:e2e`
- [~] Deploy to staging environment
- [~] Verify deep research integration
- [~] Verify document viewer with authentication
- [~] Verify BSA certificate generation
- [~] Deploy to production
