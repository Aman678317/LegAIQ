# Rajora AI Private LLM — Sovereign Deployment & Infrastructure Guide
**Standard Operating Procedure:** `RAJORA-SOP-AI-2026-04`  
**Target Platform:** LegAIQ / Jurisiva AI Enterprise Legal Intelligence  
**Classification:** Enterprise Confidential / Sovereign Deployment  
**Revision:** 1.0.0 (August 2026)

---

## 1. Executive Summary & Architecture Overview

The **Rajora AI Private LLM** integration provides enterprise legal organizations with a self-hosted, air-gapped, zero third-party data egress inference engine. Designed for strict compliance with the **Digital Personal Data Protection (DPDP) Act 2023** and **Bharatiya Sakshya Adhiniyam (BSA) 2023**, the architecture guarantees that privileged client communications, sensitive land titles, corporate contracts, and court litigation materials never leave the customer's sovereign cloud or on-premise perimeter.

### 1.1 Core Tenets
1. **Zero Third-Party Egress:** All inference requests execute on dedicated hardware owned or isolated by the enterprise. No external API calls to public LLM vendors (OpenAI, Anthropic, Google) are made when routing to `rajora-private`.
2. **Timing-Safe Internal Verification:** API access is governed via cryptographic SHA-256 hashes and constant-time HMAC secret checks (`hmac.compare_digest`).
3. **Multi-Tenant Row Level Security:** Tenant boundaries are strictly enforced via PostgreSQL Row Level Security (RLS) policies tied to `public.can_manage_org(org_id)` and Supabase `auth.uid()`.
4. **Single-Reveal Provisioning:** Plaintext API keys (`rj_live_...`) are revealed exactly once during generation. Only SHA-256 hashes and 12-character prefixes are stored.
5. **Zero-Cost Telemetry:** Native token usage tracking registers `estimated_cost_usd = 0.0` for all self-hosted compute workloads.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 Enterprise Sovereign Perimeter                                   │
│                                                                                                  │
│  ┌───────────────────────┐             ┌─────────────────────────┐                               │
│  │  Next.js Frontend     │             │  FastAPI Backend        │                               │
│  │  (App Router)         │────────────▶│  - Provider Router      │                               │
│  │  - Health Proxy       │   Internal  │  - Admin Key Management │                               │
│  │  - Model Selector     │   mTLS/VPC  │  - Internal Verifier    │                               │
│  └───────────────────────┘             └────────────┬────────────┘                               │
│                                                     │                                            │
│                         ┌───────────────────────────┴───────────────────────────┐                │
│                         │                                                       │                │
│                         ▼                                                       ▼                │
│           ┌──────────────────────────┐                            ┌───────────────────────────┐  │
│           │  Supabase / PostgreSQL   │                            │  Rajora LLM Inference     │  │
│           │  - rajora_llm_keys (RLS) │                            │  - vLLM / TGI Engine      │  │
│           │  - SHA-256 key_hash      │                            │  - NVIDIA H100 / A100 /   │  │
│           │  - audit_events          │                            │    L40S Sovereign Cluster │  │
│           └──────────────────────────┘                            └───────────────────────────┘  │
│                                                                                                  │
│  [ Air-Gapped Private VPC Subnet — No Outbound Internet Gateway — Zero External Telemetry ]      │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Hardware & Infrastructure Prerequisites

The Rajora AI inference engine is optimized for high-throughput, low-latency legal reasoning, contract analysis, and multi-lingual Indian statutory extraction.

### 2.1 GPU Hardware Matrix
Depending on the model parameter size and quantization strategy, provision nodes matching the following profiles:

| Profile | Model Target | Quantization | Min GPU Configuration | Min VRAM | Host System Spec |
|---------|--------------|--------------|-----------------------|----------|-------------------|
| **Tier 1 (Flagship)** | 70B Parameters (e.g. Llama-3.3-70B / Rajora Legal 70B) | FP16 / BF16 | 4x NVIDIA A100 (80GB) or 2x NVIDIA H100 (80GB SXM5) | 160 GB | 32 CPU Cores, 256 GB RAM, 1 TB NVMe |
| **Tier 2 (High Performance)** | 70B Parameters | AWQ / GPTQ (INT4/INT8) | 2x NVIDIA A100 (80GB) or 2x NVIDIA L40S (48GB) | 96 GB | 16 CPU Cores, 128 GB RAM, 500 GB NVMe |
| **Tier 3 (Standard Private)** | 8B–14B Parameters (e.g. Rajora Legal 8B) | BF16 / FP16 | 1x NVIDIA A100 (40GB/80GB) or 1x NVIDIA L40S (48GB) | 40 GB | 8 CPU Cores, 64 GB RAM, 250 GB NVMe |
| **Tier 4 (Edge / Local)** | 8B Parameters | Q4_K_M / INT4 | 1x NVIDIA RTX 4090 (24GB) or 1x RTX 6000 Ada | 24 GB | 8 CPU Cores, 32 GB RAM, 100 GB NVMe |

### 2.2 System & Driver Requirements
- **Operating System:** Ubuntu 22.04 LTS / Ubuntu 24.04 LTS (x86_64 or ARM64).
- **NVIDIA CUDA Driver:** Version 535.129.03+ or 550.54.14+ (CUDA 12.2 / 12.4).
- **Container Runtime:** Docker Engine 24.0+ with NVIDIA Container Toolkit (`nvidia-container-toolkit`).
- **Inference Runtime Engine:**
  - **vLLM** (Recommended): `vllm/vllm-openai:latest`
  - **HuggingFace TGI:** `ghcr.io/huggingface/text-generation-inference:latest`
  - **NVIDIA Triton:** `nvcr.io/nvidia/tritonserver:24.04-trtllm-py3`

---

## 3. Network Topology & VPC Isolation

To guarantee compliance with RAJORA-SOP-AI-2026-04, the Rajora inference cluster must be provisioned inside an isolated Virtual Private Cloud (VPC) subnet.

### 3.1 Subnet Architecture
1. **Application Subnet (Private with NAT Gateway):** Hosts Next.js Frontend and FastAPI Backend workers. Communicates with Supabase and internal inference endpoints.
2. **Inference Subnet (Isolated / Air-Gapped):** Hosts GPU nodes. **No Internet Gateway (IGW) or NAT Gateway route allowed.**
3. **Internal Load Balancer:** An AWS Application Load Balancer (ALB) or Google Cloud Internal TCP/UDP Load Balancer exposes port `8080` (or `8000`) exclusively inside the VPC CIDR (e.g., `10.0.0.0/16`).

### 3.2 Security Group / Firewall Rules
```
Inbound to Inference Nodes:
  - Protocol: TCP
  - Port: 8080
  - Source: Security Group of FastAPI Backend (App Tier only)
  - Action: ALLOW

Outbound from Inference Nodes:
  - Destination: 0.0.0.0/0
  - Action: DENY (Strict zero egress)
```

---

## 4. Inference Node Setup & vLLM Container Deployment

### 4.1 Running the vLLM Inference Container
Run the following container command on your GPU host. Ensure model weights are mounted from a high-speed local NVMe partition.

```bash
docker run -d \
  --name rajora-inference \
  --gpus all \
  --restart unless-stopped \
  --network host \
  --ipc host \
  -v /opt/models/rajora-private-v1:/model \
  -e HF_DATASETS_OFFLINE=1 \
  -e TRANSFORMERS_OFFLINE=1 \
  -e VLLM_NO_USAGE_STATS=1 \
  -e DO_NOT_TRACK=1 \
  vllm/vllm-openai:latest \
  --model /model \
  --served-model-name rajora-private-v1 \
  --host 0.0.0.0 \
  --port 8080 \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.92 \
  --trust-remote-code
```

### 4.2 Verifying Direct Health of Inference Server
```bash
curl -i -X GET http://localhost:8080/health \
  -H "X-API-Key: rj_live_bootstrap_test_key"
```
**Expected Response:** `HTTP/1.1 200 OK`

---

## 5. Environment Variable Configuration

Configure the application tier environment variables in `.env` (or via Kubernetes Secrets / HashiCorp Vault).

### 5.1 Backend Environment Variables (`backend/app/config.py`)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `RAJORA_BASE_URL` | `string` | `""` | Base HTTP URL to the Rajora inference server (e.g. `http://rajora-inference.internal:8080`). |
| `RAJORA_SERVICE_API_KEY` | `string` | `""` | Active sovereign API key (`rj_live_...`) used by backend workers for completion requests. |
| `RAJORA_DEFAULT_MODEL` | `string` | `rajora-private-v1` | Default sovereign model identifier sent in inference payloads. |
| `RAJORA_TIMEOUT_SECONDS` | `integer` | `120` | HTTP timeout (in seconds) for inference completion requests. |
| `RAJORA_INTERNAL_SECRET` | `string` | `""` | High-entropy secret token (min 64 chars) for securing `/internal/rajora/verify-key`. |

#### Example `.env` Configuration
```ini
# ================================================================
# Rajora AI Private LLM (Self-Hosted Sovereign Inference)
# ================================================================
RAJORA_BASE_URL=http://rajora-inference.internal:8080
RAJORA_SERVICE_API_KEY=rj_live_9b4e7a2d8f1c0e3a5b6d7e8f90123456789abcdef0123456
RAJORA_DEFAULT_MODEL=rajora-private-v1
RAJORA_TIMEOUT_SECONDS=120
RAJORA_INTERNAL_SECRET=sec_int_8f3a9e2b1c7d4e5f6a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f
```

### 5.2 Frontend Environment Variables (`frontend/.env.local`)
| Variable | Type | Example | Description |
|----------|------|---------|-------------|
| `BACKEND_URL` | `string` | `http://127.0.0.1:8000` | Backend API server URL used by Next.js Server Components and Route Handlers (`/api/rajora/health`). |
| `NEXT_PUBLIC_API_URL` | `string` | `http://localhost:8000/api/v1` | Public client API base URL. |

---

## 6. Database Schema & Multi-Tenant Row Level Security (RLS)

Database migration `supabase/migrations/014_rajora_llm_keys.sql` provisions key management with cryptographic indexing and RLS.

### 6.1 Schema Definition
```sql
create table if not exists public.rajora_llm_keys (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references public.organizations(id) on delete cascade,
  user_id uuid references auth.users(id) on delete set null,
  key_hash text unique not null,
  key_prefix text not null,
  label text,
  active boolean default true not null,
  created_at timestamptz default now() not null,
  last_used_at timestamptz,
  revoked_at timestamptz
);

create index if not exists idx_rajora_llm_keys_org on public.rajora_llm_keys(org_id);
create index if not exists idx_rajora_llm_keys_user on public.rajora_llm_keys(user_id);
create unique index if not exists idx_rajora_llm_keys_active_hash on public.rajora_llm_keys(key_hash) where active = true;

alter table public.rajora_llm_keys enable row level security;
```

### 6.2 Security Policies
- **User Scoping:** Regular users can view only their own provisioned keys:
  ```sql
  create policy "users read own rajora keys" on public.rajora_llm_keys
    for select using (user_id = auth.uid());
  ```
- **Organization Admin Scoping:** Organization Owners and Admins manage keys within their organization:
  ```sql
  create policy "org admins manage rajora keys" on public.rajora_llm_keys
    for all using (public.can_manage_org(org_id))
    with check (public.can_manage_org(org_id));
  ```

---

## 7. API Key Provisioning Lifecycle (Admin Flow)

Key generation follows a strict single-reveal operational model.

### 7.1 Key Generation Flow (`POST /api/v1/admin/rajora-keys`)
1. Caller must authenticate with a valid JWT and possess `is_platform_admin = true`.
2. The server verifies target `org_id` exists in `organizations`.
3. The server generates a cryptographic token `raw_key = f"rj_live_{secrets.token_hex(24)}"`.
4. The server extracts the first 12 characters as `key_prefix` (e.g., `rj_live_9b4e`).
5. The server computes `key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()`.
6. The record is inserted into `rajora_llm_keys` with `active = True`.
7. An audit event `admin.rajora_key_created` is written to `audit_events`.
8. The raw key is returned **once** in the HTTP response:

```bash
curl -X POST http://localhost:8000/api/v1/admin/rajora-keys \
  -H "Authorization: Bearer <PLATFORM_ADMIN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "8e3c12d4-5f6a-4b7e-9c1d-2e3f4a5b6c7d",
    "label": "Production Primary Sovereign Key"
  }'
```

**Response (HTTP 200):**
```json
{
  "id": "7b1c3d4e-9f0a-4b1c-8d2e-3f4a5b6c7d8e",
  "org_id": "8e3c12d4-5f6a-4b7e-9c1d-2e3f4a5b6c7d",
  "user_id": null,
  "key_prefix": "rj_live_9b4e",
  "label": "Production Primary Sovereign Key",
  "active": true,
  "api_key": "rj_live_9b4e7a2d8f1c0e3a5b6d7e8f90123456789abcdef0123456",
  "created_at": "2026-08-20T16:00:00.000000+00:00"
}
```

> ⚠️ **CRITICAL:** Store `api_key` immediately in your secure secret manager. The database stores only the SHA-256 hash; the raw key cannot be retrieved again.

### 7.2 Key Listing Flow (`GET /api/v1/admin/rajora-keys`)
Lists all keys with safe metadata. Note that `key_hash` is explicitly excluded from the returned payload.

```bash
curl -X GET "http://localhost:8000/api/v1/admin/rajora-keys?org_id=8e3c12d4-5f6a-4b7e-9c1d-2e3f4a5b6c7d" \
  -H "Authorization: Bearer <PLATFORM_ADMIN_JWT>"
```

### 7.3 Key Revocation Flow (`POST /api/v1/admin/rajora-keys/{key_id}/revoke`)
Revokes a compromised or decommissioned key instantly:

```bash
curl -X POST http://localhost:8000/api/v1/admin/rajora-keys/7b1c3d4e-9f0a-4b1c-8d2e-3f4a5b6c7d8e/revoke \
  -H "Authorization: Bearer <PLATFORM_ADMIN_JWT>"
```

**Result:** `active` is set to `False`, `revoked_at` is stamped with the current UTC timestamp, and audit event `admin.rajora_key_revoked` is emitted. Subsequent inference verification attempts will immediately return `401 Unauthorized`.

---

## 8. Internal Key Verification Protocol

The internal verification endpoint (`POST /internal/rajora/verify-key`) allows the self-hosted inference proxy or gateway to authenticate inbound API calls against the central Supabase registry.

```
┌─────────────────────────┐                            ┌─────────────────────────┐
│  Inference Gateway /    │                            │  FastAPI Backend        │
│  Proxy Filter           │                            │  /internal/rajora/      │
│                         │                            │  verify-key             │
└───────────┬─────────────┘                            └────────────┬────────────┘
            │                                                       │
            │  POST /internal/rajora/verify-key                     │
            │  Headers:                                             │
            │    X-Internal-Secret: <RAJORA_INTERNAL_SECRET>        │
            │    X-API-Key: rj_live_...                             │
            ├──────────────────────────────────────────────────────▶│
            │                                                       │ 1. hmac.compare_digest()
            │                                                       │ 2. sha256(x_api_key)
            │                                                       │ 3. Lookup rajora_llm_keys
            │                                                       │ 4. Update last_used_at
            │  HTTP 200 OK                                          │
            │  { "valid": true, "org_id": "...", ... }              │
            │◀──────────────────────────────────────────────────────┤
```

### 8.1 Verification Request Contract
```bash
curl -X POST http://localhost:8000/internal/rajora/verify-key \
  -H "X-Internal-Secret: sec_int_8f3a9e2b1c7d4e5f6a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f" \
  -H "X-API-Key: rj_live_9b4e7a2d8f1c0e3a5b6d7e8f90123456789abcdef0123456"
```

### 8.2 Security Guarantees
- **Constant-Time Comparison:** `hmac.compare_digest(x_internal_secret.encode('utf-8'), expected_secret.encode('utf-8'))` prevents side-channel timing analysis attacks.
- **SHA-256 Hash Matching:** The raw API key is never compared directly in SQL string literals; lookup is executed strictly on `key_hash`.
- **Usage Tracking:** Every successful verification touches `last_used_at` with the current UTC timestamp for accurate fleet auditing.

---

## 9. Frontend Integration & Health Telemetry

The frontend provides end-to-end telemetry and dynamic model selection.

### 9.1 Next.js Health Proxy (`/api/rajora/health`)
Located in `frontend/app/api/rajora/health/route.ts`, this route proxies health checks to FastAPI `/api/rajora/health` (or `/rajora/health`) with an internal 3,000 ms timeout.

### 9.2 Client Library (`frontend/lib/rajora.ts`)
- `checkRajoraStatus()`: Evaluates server latency and connectivity. Returns `{ online: boolean, status: string, latency_ms: number, model: string }`.
- `isRajoraModel(modelId)`: Detects Rajora sovereign model IDs (`rajora-private`, `rajora`).
- `createRajoraRequestPayload()`: Builds the standard payload `{ prompt, max_tokens, temperature, model, provider: "rajora" }`.

### 9.3 Model Selector & Settings UI
- **Model Selector:** Appears as **"Rajora Private LLM"** with the badge **`Private · Zero Third-Party`** in:
  - Case Q&A / Chat Workspace (`frontend/app/(app)/cases/[caseId]/questions/page.tsx`)
  - Drafting Studio & Multi-Agent Workflow Canvas
- **Settings Card (`/settings`):** Displays real-time connection state (`Online & Active` vs `Offline / Standby`), live inference latency in ms, active model version, and direct link to the Admin Console.

---

## 10. Verification & Test Suite Execution

Validate your sovereign deployment using the comprehensive hermetic test suites.

### 10.1 Backend Test Execution
```bash
# Run all Rajora provider and API tests
pytest backend/tests/test_rajora_provider.py backend/tests/test_rajora_api.py backend/tests/test_rajora_adversarial.py -v
```

### 10.2 Frontend Test Execution
```bash
# Run Rajora frontend unit and integration tests
npx vitest run frontend/lib/rajora.test.ts
```

### 10.3 Security & Secret Audit
Ensure no secrets or live tokens are inadvertently committed:
```bash
git grep -i -E "(rj_live_[a-f0-9]{20,}|sec_int_[a-f0-9]{20,})"
```
*Expected Result:* Clean (no real credentials in source control).

---

## 11. Operational Runbook & Troubleshooting

### Scenario A: Inference Status shows `Offline / Standby` (HTTP 503)
1. **Check Base URL:** Verify `RAJORA_BASE_URL` in `.env` matches the internal IP or hostname of the GPU host.
2. **Check Port Accessibility:** Test connectivity from the backend container:
   ```bash
   curl -i http://rajora-inference.internal:8080/health
   ```
3. **Inspect GPU Container Logs:**
   ```bash
   docker logs --tail 100 rajora-inference
   ```

### Scenario B: HTTP 401 Unauthorized during Internal Key Verification
1. **Verify `X-Internal-Secret`:** Ensure the secret sent by the inference proxy matches `RAJORA_INTERNAL_SECRET` in backend `.env`.
2. **Check Key Active Status:** Verify in database that `active = true` and `revoked_at is null` for the corresponding `key_hash`.

### Scenario C: CUDA Out of Memory (OOM) on vLLM Node
1. **Reduce Context Window:** Lower `--max-model-len` from `32768` to `16384` or `8192`.
2. **Tune Memory Utilization:** Set `--gpu-memory-utilization 0.90` (or `0.85`).
3. **Enable Quantization:** Switch to `--quantization awq` or `--quantization gptq` if running on smaller VRAM cards (e.g. 24GB/48GB).

### Scenario D: Emergency Key Revocation SOP
If an API key is suspected to be compromised:
1. Navigate to **Admin Console &rarr; Rajora Sovereign Keys**.
2. Locate the key by its 12-character prefix (e.g. `rj_live_9b4e`).
3. Click **Revoke Key** (or execute `POST /api/v1/admin/rajora-keys/{key_id}/revoke`).
4. Generate a replacement key and update `RAJORA_SERVICE_API_KEY` on the application backend.
5. Reload the FastAPI service:
   ```bash
   systemctl reload jurisiva-backend # or docker restart jurisiva-backend
   ```

---

## 12. Regulatory Compliance & Attestation Sign-off

| Standard / Act | Requirement | Technical Implementation | Attestation |
|----------------|-------------|--------------------------|-------------|
| **DPDP Act 2023** | Zero third-party data transmission | Isolated VPC inference on customer hardware; no external API routing | COMPLIANT |
| **BSA 2023 Sec 63** | Tamper-evident electronic processing | SHA-256 key hashing, immutable audit events for key creation and revocation | COMPLIANT |
| **ISO/IEC 27001** | Least-privilege access control | Row Level Security (`public.can_manage_org`), platform-admin gated endpoints | COMPLIANT |

*Deployment Guide Maintained per Standard Operating Procedure RAJORA-SOP-AI-2026-04.*
