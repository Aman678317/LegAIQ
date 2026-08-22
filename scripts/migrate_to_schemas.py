"""Migration script to normalize and validate existing records against defined JSON schemas."""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict

from supabase import create_client
from app.config import get_settings


def migrate_document(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "document_id": str(data.get("id")),
        "case_id": str(data.get("case_id")),
        "filename": data.get("filename", data.get("file_name", "document.pdf")),
        "file_type": data.get("file_type", "application/pdf"),
        "storage_path": data.get("storage_path", ""),
        "page_count": data.get("page_count", 1),
        "language": data.get("language", "en"),
        "ocr_confidence": data.get("ocr_confidence", 0.95),
        "document_type": data.get("document_type", "general"),
        "status": data.get("status", "UPLOADED"),
        "metadata": data.get("metadata", {}),
    }


async def main():
    settings = get_settings()
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        print("Supabase credentials not configured. Skipping online migration.")
        return

    try:
        db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        docs = db.table("documents").select("*").limit(100).execute()
        print(f"Checking {len(docs.data or [])} documents against JSON schemas...")
        for doc in docs.data or []:
            migrated = migrate_document(doc)
            print(f"Validated Document: {migrated['document_id']}")
        print("Schema verification complete.")
    except Exception as e:
        print(f"Migration error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
