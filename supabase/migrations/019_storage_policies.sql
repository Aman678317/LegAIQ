-- Storage bucket policies for case-documents
-- Function to check case membership safely
CREATE OR REPLACE FUNCTION case_member(u_id UUID, c_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM case_members
    WHERE case_id = c_id AND user_id = u_id
  ) OR EXISTS (
    SELECT 1 FROM cases
    WHERE id = c_id AND user_id = u_id
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Storage object policies for authenticated users
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE schemaname = 'storage' AND tablename = 'objects' AND policyname = 'authenticated_users_can_read_case_documents'
  ) THEN
    CREATE POLICY authenticated_users_can_read_case_documents
      ON storage.objects FOR SELECT
      USING (
        bucket_id = 'case-documents'
        AND (
          auth.uid() IS NOT NULL
        )
      );
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE schemaname = 'storage' AND tablename = 'objects' AND policyname = 'authenticated_users_can_insert_case_documents'
  ) THEN
    CREATE POLICY authenticated_users_can_insert_case_documents
      ON storage.objects FOR INSERT
      WITH CHECK (
        bucket_id = 'case-documents'
        AND auth.uid() IS NOT NULL
      );
  END IF;
END $$;
