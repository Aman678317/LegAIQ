"""Celery Worker Redis Caching Layer.

Provides persistent and intermediate caching for OCR results, entity extractions,
and ownership title chains to eliminate redundant compute costs.
"""

import hashlib
import json
import os
import pickle
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

# Optional Redis connection with in-memory fallback
_in_memory_cache: Dict[str, bytes] = {}


def get_redis_client():
    """Get Redis client connection or None if unavailable."""
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    try:
        from redis import Redis
        client = Redis.from_url(redis_url, decode_responses=False)
        client.ping()
        return client
    except Exception:
        return None


class WorkerCache:
    """Caching operations for Celery workers with Redis & in-memory fallbacks."""

    OCR_TTL = 86400        # 24 hours
    EXTRACTION_TTL = 604800 # 7 days
    TITLE_CHAIN_TTL = 604800 # 7 days

    @classmethod
    def generate_cache_key(
        cls,
        case_id: Any,
        document_id: Any,
        job_type: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate unique cache key based on resource IDs and parameters."""
        param_hash = hashlib.md5(
            json.dumps(params or {}, sort_keys=True).encode()
        ).hexdigest()[:12]
        return f"legaiq:worker:{case_id}:{document_id}:{job_type}:{param_hash}"

    @classmethod
    def cache_ocr_result(cls, case_id: Any, document_id: Any, ocr_result: Dict[str, Any]) -> str:
        """Cache OCR result."""
        cache_key = cls.generate_cache_key(case_id, document_id, "ocr", {
            "provider": ocr_result.get("provider", "tesseract"),
            "doc_type": ocr_result.get("document_type", "general"),
        })
        payload = pickle.dumps(ocr_result)
        redis = get_redis_client()
        if redis:
            try:
                redis.setex(cache_key, cls.OCR_TTL, payload)
                return cache_key
            except Exception:
                pass
        _in_memory_cache[cache_key] = payload
        return cache_key

    @classmethod
    def get_ocr_result(
        cls,
        case_id: Any,
        document_id: Any,
        provider: str = "tesseract",
        document_type: str = "general",
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached OCR result if present."""
        cache_key = cls.generate_cache_key(case_id, document_id, "ocr", {
            "provider": provider,
            "doc_type": document_type,
        })
        redis = get_redis_client()
        if redis:
            try:
                raw = redis.get(cache_key)
                if raw:
                    return pickle.loads(raw)
            except Exception:
                pass
        if cache_key in _in_memory_cache:
            return pickle.loads(_in_memory_cache[cache_key])
        return None

    @classmethod
    def cache_extraction_result(cls, case_id: Any, document_id: Any, extraction_result: Dict[str, Any]) -> str:
        """Cache entity extraction result."""
        cache_key = cls.generate_cache_key(case_id, document_id, "extraction")
        payload = pickle.dumps(extraction_result)
        redis = get_redis_client()
        if redis:
            try:
                redis.setex(cache_key, cls.EXTRACTION_TTL, payload)
                return cache_key
            except Exception:
                pass
        _in_memory_cache[cache_key] = payload
        return cache_key

    @classmethod
    def get_extraction_result(cls, case_id: Any, document_id: Any) -> Optional[Dict[str, Any]]:
        """Retrieve cached entity extraction result."""
        cache_key = cls.generate_cache_key(case_id, document_id, "extraction")
        redis = get_redis_client()
        if redis:
            try:
                raw = redis.get(cache_key)
                if raw:
                    return pickle.loads(raw)
            except Exception:
                pass
        if cache_key in _in_memory_cache:
            return pickle.loads(_in_memory_cache[cache_key])
        return None

    @classmethod
    def cache_title_chain(cls, case_id: Any, title_chain: Dict[str, Any]) -> str:
        """Cache reconstructed ownership DAG result."""
        cache_key = cls.generate_cache_key(case_id, "title_chain", "ownership_dag")
        payload = pickle.dumps(title_chain)
        redis = get_redis_client()
        if redis:
            try:
                redis.setex(cache_key, cls.TITLE_CHAIN_TTL, payload)
                return cache_key
            except Exception:
                pass
        _in_memory_cache[cache_key] = payload
        return cache_key

    @classmethod
    def get_title_chain(cls, case_id: Any) -> Optional[Dict[str, Any]]:
        """Retrieve cached ownership title chain."""
        cache_key = cls.generate_cache_key(case_id, "title_chain", "ownership_dag")
        redis = get_redis_client()
        if redis:
            try:
                raw = redis.get(cache_key)
                if raw:
                    return pickle.loads(raw)
            except Exception:
                pass
        if cache_key in _in_memory_cache:
            return pickle.loads(_in_memory_cache[cache_key])
        return None

    @classmethod
    def invalidate_cache(cls, case_id: Any, document_id: Optional[Any] = None) -> int:
        """Invalidate cache entries for a case/document."""
        redis = get_redis_client()
        deleted = 0
        pattern = f"legaiq:worker:{case_id}:*"
        if redis:
            try:
                keys = redis.keys(pattern)
                if keys:
                    deleted += redis.delete(*keys)
            except Exception:
                pass
        keys_to_del = [k for k in _in_memory_cache if str(case_id) in k]
        for k in keys_to_del:
            del _in_memory_cache[k]
            deleted += 1
        return deleted


cache = WorkerCache()
