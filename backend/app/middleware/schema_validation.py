"""JSON Schema Validation Middleware for FastAPI."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse


class SchemaValidator:
    """JSON Schema validator for LegAIQ API requests and responses."""

    def __init__(self, schemas_dir: Optional[str] = None):
        base_path = Path(__file__).parent.parent / "schemas" / "definitions"
        self.schemas_dir = Path(schemas_dir) if schemas_dir else base_path
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self._load_schemas()

    def _load_schemas(self) -> None:
        if not self.schemas_dir.exists():
            return
        for schema_file in self.schemas_dir.glob("*.json"):
            try:
                with open(schema_file, encoding="utf-8") as f:
                    data = json.load(f)
                    schema_id = data.get("$id", schema_file.stem)
                    version = data.get("version", "v1")
                    self.schemas[f"{schema_file.stem}:{version}"] = data
                    self.schemas[f"{schema_id}:{version}"] = data
            except Exception:
                pass

    def validate_request(self, data: Dict[str, Any], schema_name: str, version: str = "v1") -> bool:
        schema_key = f"{schema_name}:{version}"
        schema = self.schemas.get(schema_key)
        if not schema:
            return True  # Permissive if schema definition not found

        try:
            from jsonschema import validate, ValidationError
            validate(instance=data, schema=schema)
            return True
        except ImportError:
            # Fallback basic required key check
            required = schema.get("required", [])
            missing = [k for k in required if k not in data]
            if missing:
                raise HTTPException(status_code=400, detail=f"Missing required fields: {missing}")
            return True
        except Exception as e:
            raise HTTPException(status_code=400, detail={"error": "Schema validation failed", "details": str(e)})

    def validate_response(self, data: Dict[str, Any], schema_name: str, version: str = "v1") -> bool:
        return self.validate_request(data, schema_name, version)


validator = SchemaValidator()


def validate_request_body(schema_name: str, version: str = "v1"):
    """FastAPI dependency for request body schema validation."""
    async def validator_dep(request: Request):
        try:
            body = await request.json()
            validator.validate_request(body, schema_name, version)
        except HTTPException:
            raise
        except Exception:
            pass
    return validator_dep
