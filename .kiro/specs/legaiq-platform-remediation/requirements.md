# Requirements: LegAIQ Legal Intelligence Platform Remediation

## 1. Problem Statement

The LegAIQ Legal Intelligence Platform is a Harvey-class legal intelligence system designed for Indian legal practitioners, law firms, and property professionals. The platform processes legacy property documents in 13+ Indian languages, reconstructs ownership chains, identifies title risks, and generates court-ready documentation.

**Current State**: The platform is well-architected with:
- Backend: FastAPI with 26+ API routers, multi-provider LLM support (Groq, NVIDIA, OpenAI, Anthropic, Ollama), Celery workers, Supabase PostgreSQL
- Frontend: Next.js 15 App Router with cases, chat, contracts, workflows modules
- Database: 15 Supabase migrations with RLS policies
- AI: Indic OCR (13 languages), BSA 2023 evidence engine, land intelligence, contract intelligence

**Critical Issues**: Three categories of problems require remediation:

### Priority 1: Integration Failures (BLOCKING)
1. **Deep Research Streamlit Isolation** - The `deep_research_streamlit/app.py` is completely standalone with no connection to the FastAPI backend, Supabase authentication, or case storage. Users cannot access case-specific research results from the main application.

2. **Document Viewer Authentication** - The frontend `DocumentViewer.tsx` and backend `documents.py` don't properly forward authentication tokens to Supabase Storage, causing RLS policies to reject legitimate requests for document retrieval.

3. **BSA Section 63 Cryptographic Hashing Missing** - While `bharatiya_sakshya.py` contains evidence logic, it lacks actual SHA-256 hash generation and PDF certificate export functionality required for electronic evidence admissibility.

### Priority 2: Feature Enhancements
4. **OCR Bilingual Document Handling** - The `indic_ocr.py` module needs enhanced confidence calibration for mixed Marathi/English documents, which are common in Maharashtra land records.

5. **Entity Resolution Indian Date Formats** - The current tasks.py uses basic regex patterns that don't handle Indian date formats (DD/MM/YYYY, DD-MM-YYYY, Devanagari numerals, Vikram Samvat calendar).

6. **Celery Workers Lack Persistent Shared State** - Intermediate processing results are not cached, causing redundant OCR and extraction work on repeated requests.

### Priority 3: Production Hardening
7. **Multi-Agent Orchestration** - State passing between specialized agents (Due Diligence, Title Examiner, Contract Reviewer, Litigation Strategist, BSA, Research) has context serialization issues.

8. **BigLaw Bench Schema Mismatch** - Output JSON structures don't consistently conform to predefined JSON schemas, causing validation failures in downstream systems.

## 2. Goals and Non-Goals

### Goals
- [ ] Integrate Deep Research functionality into the main application workflow
- [ ] Fix document viewer authentication and authorization flow
- [ ] Implement complete BSA 2023 Section 63 electronic evidence certification
- [ ] Improve OCR accuracy for bilingual Indian documents
- [ ] Add comprehensive Indian date format parsing
- [ ] Implement Redis-backed caching for Celery workers
- [ ] Fix multi-agent state passing and serialization
- [ ] Ensure all outputs conform to JSON schemas

### Non-Goals
- [ ] Complete platform rewrite or architecture change
- [ ] Adding new AI models or providers
- [ ] Changing core business logic or legal interpretations
- [ ] Major UI/UX redesign
- [ ] Database schema changes beyond migration patches

## 3. User Stories

### Priority 1 (Critical - Must Have)
- **US-1.1**: As a legal practitioner, I want to run deep research on case-specific queries and see results within the main application, so I can quickly gather case law and statutory references without switching tools.

- **US-1.2**: As a legal practitioner, I want to view uploaded documents in the document viewer without authentication errors, so I can review evidence and prepare for court.

- **US-1.3**: As a legal practitioner, I want electronic evidence documents to have SHA-256 hash certificates that courts will accept, so my digital submissions are legally valid.

### Priority 2 (Important - Should Have)
- **US-2.1**: As a legal practitioner, I want the OCR engine to correctly handle Marathi-English bilingual documents, so I can process Maharashtra land records accurately.

- **US-2.2**: As a legal practitioner, I want the system to recognize Indian date formats including Devanagari numerals, so I don't miss critical dates in historical documents.

- **US-2.3**: As a system administrator, I want Celery workers to cache intermediate results, so repeated document processing is faster and costs less.

### Priority 3 (Production - Should Have)
- **US-3.1**: As a platform user, I want specialized agents to work together seamlessly, so I can get comprehensive case analysis without context loss between agents.

- **US-3.2**: As a platform developer, I want all API responses to conform to JSON schemas, so downstream systems can reliably consume our data.

## 4. Functional Requirements

### FR-1: Deep Research Integration (Priority 1)

#### FR-1.1: Backend API Endpoint
- **ID**: FR-1.1
- **Type**: New Endpoint
- **Description**: Create `/api/v1/cases/{case_id}/deep-research` endpoint in FastAPI backend
- **Details**:
  - Accepts: `POST` with `{ "question": string, "model": "o4-mini-deep-research" | "o3-deep-research", "max_tool_calls": int }`
  - Returns: Streaming SSE response with research progress and final report
  - Integrates with OpenAI Deep Research API
  - Stores results in Supabase `deep_research_results` table with case association
  - Implements proper authentication via existing auth context
  - Returns 404 if case doesn't exist or user lacks access
- **Dependencies**: FR-1.2, FR-1.3

#### FR-1.2: Database Schema
- **ID**: FR-1.2
- **Type**: New Migration
- **Description**: Create Supabase migration for deep research results storage
- **Details**:
  ```sql
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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT fk_case FOREIGN KEY (case_id) REFERENCES cases(id)
  );
  CREATE INDEX idx_deep_research_case ON deep_research_results(case_id);
  CREATE INDEX idx_deep_research_user ON deep_research_results(user_id);
  ```
- **Dependencies**: None

#### FR-1.3: Celery Task Integration
- **ID**: FR-1.3
- **Type**: New Task
- **Description**: Implement Celery task for async deep research processing
- **Details**:
  - Task: `tasks.deep_research_task(case_id: UUID, user_id: UUID, question: str, model: str, max_tool_calls: int = 0)`
  - Returns: `{"task_id": str, "status": "PENDING" | "RUNNING" | "SUCCESS" | "FAILURE"}`
  - Stores streaming events in Supabase for real-time progress updates
  - On completion, stores final report in `deep_research_results` table
  - Handles OpenAI API errors gracefully with retry logic
- **Dependencies**: FR-1.2

#### FR-1.4: Frontend Integration
- **ID**: FR-1.4
- **Type**: UI Component
- **Description**: Create frontend component to access deep research from case workspace
- **Details**:
  - Component: `<DeepResearchPanel caseId={caseId} />`
  - Features:
    - Question input field with example suggestions
    - Model selector (o4-mini, o3)
    - Max tool calls slider with cost/latency guidance
    - Live streaming progress feed (reasoning, web searches, citations)
    - Final report display with markdown rendering
    - Citation list with link preview
    - Download report as Markdown
    - View raw API events for debugging
  - Integration: Accessible from case detail page "Research" tab
- **Dependencies**: FR-1.1

### FR-2: Document Viewer Authentication (Priority 1)

#### FR-2.1: Pre-Signed URL Generation
- **ID**: FR-2.1
- **Type**: Backend Enhancement
- **Description**: Implement pre-signed URL generation with token forwarding for Supabase Storage
- **Details**:
  - Endpoint: `/api/v1/cases/{case_id}/documents/{document_id}/download-url`
  - Current: Uses `create_signed_url` with default expiration
  - Enhancement: Forward user's Supabase JWT token in storage request headers
  - Support both `GET` (file download) and `HEAD` (inspection) requests
  - Support `requestInit` customization for auth headers
  - Return URL with proper cache-control headers
- **Dependencies**: FR-2.2

#### FR-2.2: RLS Policy Configuration
- **ID**: FR-2.2
- **Type**: Migration Enhancement
- **Description**: Update Supabase RLS policies to allow authenticated storage access
- **Details**:
  - Storage bucket: `case-documents`
  - Policy: `authenticated_users_can_read_case_documents`
  - Condition: `auth.uid() = case_owner_id OR case_member(auth.uid(), case_id)`
  - Add policy for service role key fallback for internal operations
  - Test policy with authenticated user tokens
- **Dependencies**: None

#### FR-2.3: Frontend Token Forwarding
- **ID**: FR-2.3
- **Type**: UI Enhancement
- **Description**: Update `DocumentViewer.tsx` to forward authentication tokens
- **Details**:
  - Add `requestOptions.requestInit` with authorization header
  - Pass Supabase auth token in `headers: { Authorization: 'Bearer <token>' }`
  - Implement HEAD fallback to GET on 405/501 responses
  - Show clear error messages for 403/404 responses
  - Add retry logic for transient auth failures
- **Dependencies**: FR-2.1

### FR-3: BSA Section 63 Certification (Priority 1)

#### FR-3.1: SHA-256 Hash Generation
- **ID**: FR-3.1
- **Type**: Backend Enhancement
- **Description**: Implement cryptographically secure SHA-256 hashing for electronic records
- **Details**:
  - Function: `generate_file_hash(file_bytes: bytes) -> str` (SHA-256 hex digest)
  - Include file metadata in hash: `{filename}|{size}|{timestamp}|{content_hash}`
  - Support incremental hashing for large files
  - Store hash in Supabase `documents.hash_value` column
  - Regenerate hash on document update
- **Dependencies**: None

#### FR-3.2: Section 63 Certificate PDF Export
- **ID**: FR-3.2
- **Type**: New Module
- **Description**: Generate court-admissible Section 63 electronic evidence certificates
- **Details**:
  - Module: `app/ai/bsa_certificates.py`
  - Function: `generate_section63_certificate(evidence: EvidenceItem, custodian: Dict) -> bytes`
  - Certificate Structure:
    - Header: "Section 63 Electronic Evidence Certificate"
    - Evidence identification (file name, hash, algorithm)
    - System parameters (computer generated, regular use, integrity verified)
    - Statutory declaration by custodian
    - Timestamp and digital signature placeholder
  - PDF generation using `reportlab` or `pdfkit`
  - Include QR code for hash verification (optional)
  - Sign with X.509 certificate (optional for now)
- **Dependencies**: FR-3.1

#### FR-3.3: Certificate API Endpoint
- **ID**: FR-3.3
- **Type**: New Endpoint
- **Description**: Create API endpoint to download Section 63 certificates
- **Details**:
  - Endpoint: `GET /api/v1/cases/{case_id}/documents/{document_id}/bsa-certificate`
  - Returns: PDF document with Section 63 certificate
  - Parameters: `?format=pdf|json&include_hash=true`
  - Verify user has access to case before generating
  - Cache certificate for 24 hours for efficiency
  - Log certificate generation for audit trail
- **Dependencies**: FR-3.2

### FR-4: OCR Bilingual Handling (Priority 2)

#### FR-4.1: Language Confidence Calibration
- **ID**: FR-4.1
- **Type**: Backend Enhancement
- **Description**: Enhance `indic_ocr.py` to better calibrate confidence for bilingual documents
- **Details**:
  - Detect language mix per document segment
  - Apply language-specific confidence adjustments:
    - Monolingual Marathi: confidence × 1.0
    - Monolingual English: confidence × 1.0
    - Marathi/English mix: confidence × 0.95 (reduce slightly)
    - English/Marathi mix: confidence × 0.95
  - Track per-language word counts
  - Flag documents with >30% bilingual content for manual review
  - Store language detection confidence in `OCRPageResult`
- **Dependencies**: FR-4.2

#### FR-4.2: Enhanced Document Type Detection
- **ID**: FR-4.2
- **Type**: Backend Enhancement
- **Description**: Improve document type detection for Maharashtra land records
- **Details**:
  - Add `7_12_extract` document type detection for Marathi/English mix
  - Detect common Maharashtra document headers:
    - "GOVERNMENT OF MAHARASHTRA"
    - "ZILLA PARISHAD"
    - "TALUKA PARISHAD"
    - "SUB-REGISTRAR OFFICE"
  - Apply Marathi priority for Maharashtra documents
  - Fall back to English for non-Maharashtra documents
  - Store detected state/document type in document metadata
- **Dependencies**: FR-4.1

### FR-5: Indian Date Format Recognition (Priority 2)

#### FR-5.1: Multi-Format Date Parser
- **ID**: FR-5.1
- **Type**: New Module
- **Description**: Create robust date parser supporting Indian formats
- **Details**:
  - Module: `app/ai/date_parser.py`
  - Supported formats:
    - DD/MM/YYYY (e.g., "15/06/2003")
    - DD-MM-YYYY (e.g., "15-06-2003")
    - DD MM YYYY (e.g., "15 June 2003")
    - Devanagari numerals (e.g., "१५/६/२००३")
    - Vikram Samvat (e.g., "V.S. 2060" → 2003 CE)
    - Shalivahana Shaka (e.g., "S.S. 1925" → 2003 CE)
  - Function: `parse_indian_date(text: str) -> Optional[datetime]`
  - Return: Parsed datetime or None if not found
  - Context-aware: Extract date from legal document sections
- **Dependencies**: None

#### FR-5.2: Entity Extraction Integration
- **ID**: FR-5.2
- **Type**: Backend Enhancement
- **Description**: Update entity extraction to use new date parser
- **Details**:
  - Replace basic regex in `tasks.py` with `parse_indian_date()`
  - Update `extract_entities()` in `indic_ocr.py`
  - Parse dates in: party details, property schedules, execution clauses, registration details
  - Store parsed dates in normalized ISO format
  - Flag dates with low confidence for review
- **Dependencies**: FR-5.1

### FR-6: Celery Worker Caching (Priority 2)

#### FR-6.1: Redis Integration
- **ID**: FR-6.1
- **Type**: Infrastructure Enhancement
- **Description**: Add Redis caching layer for Celery worker intermediate results
- **Details**:
  - Add Redis connection to Celery config
  - Cache keys: `{case_id}:{document_id}:{job_type}:{hash(parameters)}`
  - TTL: 24 hours for OCR results, 7 days for extraction results
  - Return cached results with `cached: true` flag
  - Cache invalidation on document update
  - Implement cache metrics and monitoring
- **Dependencies**: FR-6.2

#### FR-6.2: Caching Strategy
- **ID**: FR-6.2
- **Type**: Backend Enhancement
- **Description**: Implement caching strategy for common operations
- **Details**:
  - Cache OCR results: `cache_ocr_result(case_id, document_id, ocr_result)`
  - Cache extraction results: `cache_extraction_result(case_id, document_id, extraction_result)`
  - Cache title chain reconstruction: `cache_title_chain(case_id, title_chain)`
  - Check cache before expensive operations
  - Store cache key in job result for tracking
- **Dependencies**: FR-6.1

### FR-7: Multi-Agent Orchestration (Priority 3)

#### FR-7.1: Agent Context Serialization
- **ID**: FR-7.1
- **Type**: Backend Enhancement
- **Description**: Implement proper context serialization for agent state passing
- **Details**:
  - Define `AgentContext` Pydantic model with all required fields
  - Serialize context to JSON for Celery task payloads
  - Deserialize context at agent start
  - Support context versioning for backward compatibility
  - Log context transitions for debugging
  - Implement context size limits (max 100KB)
- **Dependencies**: None

#### FR-7.2: State Transition System
- **ID**: FR-7.2
- **Type**: Backend Enhancement
- **Description**: Create state machine for agent orchestration
- **Details**:
  - States: `INIT`, `RESEARCHING`, `ANALYZING`, `GENERATING`, `REVIEWING`, `COMPLETED`, `FAILED`
  - Transitions triggered by job completion events
  - Store current state in Supabase `agent_jobs.state`
  - Implement timeout handling for stuck states
  - Allow manual state override for recovery
- **Dependencies**: FR-7.1

#### FR-7.3: Agent Chaining API
- **ID**: FR-7.3
- **Type**: New Endpoint
- **Description**: Create API for orchestrating agent workflows
- **Details**:
  - Endpoint: `POST /api/v1/cases/{case_id}/agents/orchestrate`
  - Payload: `{ "workflow": "due_diligence|title|contract|litigation|bsa|research", "agent_order": ["agent1", "agent2", ...], "context": {...} }`
  - Returns: `{ "job_id": UUID, "status": "PENDING" }`
  - Monitor job progress via SSE stream
  - Return aggregated results from all agents
  - Support parallel agent execution where safe
- **Dependencies**: FR-7.2

### FR-8: JSON Schema Compliance (Priority 3)

#### FR-8.1: Schema Definition Repository
- **ID**: FR-8.1
- **Type**: New Module
- **Description**: Create centralized JSON schema repository
- **Details**:
  - Module: `backend/app/schemas/definitions/`
  - Schemas:
    - `document.json` - Document record structure
    - `ocr_result.json` - OCR processing result
    - `extraction_result.json` - Entity extraction result
    - `title_chain.json` - Ownership chain structure
    - `bsa_certificate.json` - Section 63 certificate
    - `agent_result.json` - Agent workflow output
  - JSON Schema Draft 2020-12 format
  - Versioned schemas (v1, v2, etc.)
  - Schema validation function: `validate_schema(data: dict, schema_name: str, version: str = "v1")`
- **Dependencies**: None

#### FR-8.2: Schema Validation Middleware
- **ID**: FR-8.2
- **Type**: Backend Enhancement
- **Description**: Add JSON schema validation to API endpoints
- **Details**:
  - Middleware for FastAPI routes
  - Validate request body against schema
  - Validate response body against schema
  - Return 400 with detailed error on validation failure
  - Log validation errors for debugging
  - Support schema version negotiation via Accept header
- **Dependencies**: FR-8.1

#### FR-8.3: Migration Path for Existing Data
- **ID**: FR-8.3
- **Type**: Migration Script
- **Description**: Create script to migrate existing data to conform to new schemas
- **Details**:
  - Script: `scripts/migrate_to_schemas.py`
  - Reads existing data from Supabase
  - Maps old fields to new schema structure
  - Transforms data to符合 schema requirements
  - Writes back to Supabase with schema version
  - Handles data loss gracefully with warnings
  - Supports dry-run mode for testing
- **Dependencies**: FR-8.1

## 5. Non-Functional Requirements

### NFR-1: Security
- **NFR-1.1**: All API endpoints must enforce existing Supabase RLS policies
- **NFR-1.2**: Deep Research API calls must not expose API keys in logs or responses
- **NFR-1.3**: Document download URLs must expire after configurable timeout (default: 1 hour)
- **NFR-1.4**: BSA certificates must include audit trail with timestamp and user ID
- **NFR-1.5**: Redis cache must be secured with authentication and TLS where possible

### NFR-2: Performance
- **NFR-2.1**: Deep research streaming response must begin within 5 seconds of request
- **NFR-2.2**: Document download URL generation must complete in <100ms
- **NFR-2.3**: OCR caching must reduce repeated processing time by >80%
- **NFR-2.4**: Agent orchestration must support parallel execution with <200ms overhead
- **NFR-2.5**: Schema validation must add <50ms latency to API responses

### NFR-3: Reliability
- **NFR-3.1**: Deep research must handle OpenAI API outages with graceful degradation
- **NFR-3.2**: Document viewer must retry failed requests up to 3 times with exponential backoff
- **NFR-3.3**: Celery worker cache must survive Redis restarts with persistent storage
- **NFR-3.4**: Agent state machine must recover from crashes within 60 seconds
- **NFR-3.5**: Schema validation must not fail due to minor version mismatches

### NFR-4: Maintainability
- **NFR-4.1**: All new code must include unit tests with >90% coverage
- **NFR-4.2**: JSON schemas must be versioned and documented
- **NFR-4.3**: Agent context must be serializable to JSON for debugging
- **NFR-4.4**: All new endpoints must include OpenAPI documentation
- **NFR-4.5**: Redis cache keys must follow naming convention: `legaiq:{service}:{resource}:{id}`

### NFR-5: Compliance
- **NFR-5.1**: BSA Section 63 certificates must comply with Indian Evidence Act requirements
- **NFR-5.2**: All electronic evidence must maintain chain of custody in Supabase
- **NFR-5.3**: Personal data processing must comply with DPDP Act 2023
- **NFR-5.4**: Audit logs must be immutable and tamper-evident
- **NFR-5.5**: Document hashes must use FIPS 140-2 compliant SHA-256 implementation

## 6. Success Criteria

### SC-1: Integration Success (Priority 1)
- [ ] Deep research can be initiated from case workspace and results are visible in-app
- [ ] Document viewer displays at least 95% of documents without authentication errors
- [ ] BSA certificates are generated with valid SHA-256 hashes and court-ready PDF format

### SC-2: Feature Success (Priority 2)
- [ ] OCR confidence for bilingual Maharashtra documents improves by >15%
- [ ] Indian date parser correctly identifies 90% of dates in legal documents
- [ ] Celery worker cache reduces repeated OCR processing time from 30s to <5s

### SC-3: Production Success (Priority 3)
- [ ] Multi-agent workflows complete without context loss or serialization errors
- [ ] 95% of API responses pass schema validation on first attempt
- [ ] Agent state recovery time is <60 seconds after crash

### SC-4: Quality Success
- [ ] All new features have unit tests with >90% coverage
- [ ] All new features have integration tests
- [ ] No new security vulnerabilities introduced
- [ ] Performance regression <10% for existing functionality

## 7. Technical Constraints

### TC-1: Backend
- Must use existing FastAPI framework (no framework migration)
- Must use existing Supabase connection pool
- Must use existing Celery worker infrastructure
- Must maintain current authentication flow (Supabase Auth)
- Must be compatible with Python 3.12

### TC-2: Frontend
- Must use existing Next.js 15 App Router structure
- Must use existing DocumentViewer component architecture
- Must maintain current TypeScript strict mode (no TS errors)
- Must be compatible with modern browsers (Chrome, Firefox, Safari, Edge)

### TC-3: Database
- Must use existing Supabase PostgreSQL instance
- Must maintain existing RLS policies (no schema changes unless migration patch)
- Must use existing pgvector extension
- Must support existing migrations 001-015

### TC-4: AI/ML
- Must maintain existing provider routing (Groq, OpenAI, Anthropic, Ollama)
- Must support existing OCR providers (PaddleOCR, Tesseract, Google Vision)
- Must maintain existing BSA 2023 legal logic
- Must preserve existing land record parsing rules

### TC-5: Deployment
- Must deploy to existing Render infrastructure
- Must use existing Docker Compose for local development
- Must maintain existing CI/CD pipeline (GitHub Actions)
- Must support zero-downtime deployments

## 8. Dependencies

### D-1: External Dependencies
- **OpenAI API**: For Deep Research functionality
- **Redis**: For Celery worker caching (already in docker-compose)
- **Supabase Storage**: For document storage (already in use)

### D-2: Internal Dependencies
- **Backend**:
  - `app/api/cases.py` - Case access control
  - `app/security/auth.py` - Authentication context
  - `app/config.py` - Configuration management
  - `app/workers.py` - Celery task infrastructure
  - `app/ai/bsa_certificates.py` - New module (FR-3.2)
  
- **Frontend**:
  - `app/cases/[id]/page.tsx` - Case detail page
  - `lib/api.ts` - API client
  - `components/document-viewer/` - Document viewer component

### D-3: Infrastructure Dependencies
- **Supabase**: Must apply migration for deep research results table
- **Redis**: Must verify Redis is running (already in docker-compose.yml)
- **Storage**: Must verify case-documents bucket exists with proper policies

### D-4: Testing Dependencies
- **Pytest**: For backend unit tests
- **Vitest**: For frontend unit tests
- **Playwright**: For E2E tests
- **OpenAI API key**: For testing Deep Research (optional, can use mock)

## 9. Out of Scope

### OOS-1: Feature Creep
- No new AI models or providers
- No changes to existing legal logic or interpretations
- No major UI redesign
- No database schema changes beyond necessary migrations

### OOS-2: Performance Expectations
- Deep research will not be faster than OpenAI's native implementation
- Document viewer will not support formats beyond existing capabilities
- Agent orchestration will not support real-time collaboration

### OOS-3: Support Scope
- This remediation does not include training new ML models
- This remediation does not include major infrastructure changes
- This remediation does not include changes to legal database content

## 10. Acceptance Test Scenarios

### ATS-1: Deep Research Integration
1. User navigates to case workspace
2. User clicks "Deep Research" tab
3. User enters research question and clicks "Run"
4. User sees streaming progress (reasoning, web searches)
5. User sees final report with citations
6. User can download report as Markdown
7. Report is stored in Supabase with case association

### ATS-2: Document Viewer
1. User uploads document to case
2. User clicks document in viewer
3. Document displays without authentication errors
4. User can download document
5. User can open document in new tab
6. HEAD requests return proper Content-Type/Length

### ATS-3: BSA Certificate
1. User uploads electronic document
2. System generates SHA-256 hash of document
3. User clicks "Generate Section 63 Certificate"
4. PDF certificate downloads with proper structure
5. Certificate includes hash verification
6. Certificate includes statutory declaration

### ATS-4: OCR Enhancement
1. User uploads Maharashtra 7/12 extract (Marathi+English)
2. OCR processes document with enhanced confidence
3. Document type correctly identified as "7_12_extract"
4. Language detected as "Marathi/English mix"
5. Entity extraction recognizes Marathi date formats

### ATS-5: Date Parser
1. User uploads document with "15/06/2003"
2. Date correctly parsed as June 15, 2003
3. User uploads document with "१५/६/२००३"
4. Date correctly parsed (Devanagari numerals)
5. User uploads document with "V.S. 2060"
6. Date correctly converted to 2003 CE

### ATS-6: Worker Caching
1. User processes document with OCR
2. First run takes 30 seconds
3. User requests same document again
4. Second run completes in <5 seconds
5. Cache key logged with hash of parameters

### ATS-7: Agent Orchestration
1. User initiates "Due Diligence" workflow
2. System creates agent job with context
3. Agent states progress (INIT → RESEARCHING → ANALYZING → COMPLETED)
4. User can view aggregated results from all agents
5. System logs context transitions

### ATS-8: Schema Compliance
1. API endpoint receives request
2. Request body validates against schema
3. API endpoint returns response
4. Response body validates against schema
5. Invalid data returns 400 with error details
6. Schema version is in response header
