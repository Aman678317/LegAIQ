-- BSA Section 63 certificates storage
CREATE TABLE IF NOT EXISTS bsa_certificates (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  sha256_hash TEXT NOT NULL,
  file_metadata JSONB DEFAULT '{}'::jsonb,
  acquisition_timestamp TIMESTAMPTZ DEFAULT NOW(),
  device_metadata JSONB DEFAULT '{}'::jsonb,
  part_a_json JSONB DEFAULT '{}'::jsonb,  -- Evidence details (auto-generated)
  part_b_signed BOOLEAN DEFAULT FALSE,
  part_b_signed_at TIMESTAMPTZ,
  part_b_signed_by UUID REFERENCES auth.users(id),
  certificate_data BYTEA,  -- PDF certificate binary
  status VARCHAR(20) DEFAULT 'DRAFT',  -- DRAFT | SIGNED | FINAL
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bsa_certificates_document ON bsa_certificates(document_id);
CREATE INDEX IF NOT EXISTS idx_bsa_certificates_user ON bsa_certificates(user_id);
CREATE INDEX IF NOT EXISTS idx_bsa_certificates_case ON bsa_certificates(case_id);
CREATE INDEX IF NOT EXISTS idx_bsa_certificates_status ON bsa_certificates(status);

-- Certificate audit log
CREATE TABLE IF NOT EXISTS bsa_certificate_audit (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  certificate_id UUID NOT NULL REFERENCES bsa_certificates(id) ON DELETE CASCADE,
  action VARCHAR(50) NOT NULL,  -- CREATED | UPDATED | SIGNED | VERIFIED
  user_id UUID REFERENCES auth.users(id),
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bsa_audit_certificate ON bsa_certificate_audit(certificate_id);
CREATE INDEX IF NOT EXISTS idx_bsa_audit_user ON bsa_certificate_audit(user_id);

ALTER TABLE bsa_certificates ENABLE ROW LEVEL SECURITY;
ALTER TABLE bsa_certificate_audit ENABLE ROW LEVEL SECURITY;

CREATE POLICY bsa_certificates_user_read
  ON bsa_certificates FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY bsa_certificates_user_insert
  ON bsa_certificates FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY bsa_certificates_user_update
  ON bsa_certificates FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY bsa_certificate_audit_user_read
  ON bsa_certificate_audit FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY bsa_certificate_audit_user_insert
  ON bsa_certificate_audit FOR INSERT
  WITH CHECK (auth.uid() = user_id);
