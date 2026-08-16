"""In-memory fake of the Supabase REST client.

Implements only the query surface Jurisiva uses:
  table().select/insert/update/upsert/delete with eq/neq/in_/ilike/order/
  range/limit/single and count="exact"; rpc(); storage.from_().download/
  upload/create_signed_url/remove.

Purpose: run the ENTIRE worker + API pipeline in tests with no network,
no database, and no external services. Not a general Supabase emulator.
"""
import fnmatch
import re
import uuid
from datetime import datetime, timezone


class FakeResult:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class FakeQuery:
    def __init__(self, store: "TableStore", table: str):
        self._store = store
        self._table = table
        self._filters: list[tuple[str, str, object]] = []
        self._select_cols = "*"
        self._count_mode = False
        self._order: list[tuple[str, bool]] = []  # (key, desc)
        self._range: tuple[int, int] | None = None
        self._limit: int | None = None
        self._single = False
        self._op = "select"
        self._payload = None
        self._upsert_conflict: list[str] | None = None

    # ---- fluent API ----
    def select(self, cols="*", count=None):
        self._select_cols = cols
        if count == "exact":
            self._count_mode = True
        return self

    def insert(self, rows):
        self._op = "insert"
        self._payload = rows
        return self

    def update(self, values: dict):
        self._op = "update"
        self._payload = values
        return self

    def upsert(self, rows, on_conflict: str | None = None):
        self._op = "upsert"
        self._payload = rows
        self._upsert_conflict = on_conflict.split(",") if on_conflict else None
        return self

    def delete(self):
        self._op = "delete"
        return self

    def eq(self, col, val):
        self._filters.append(("eq", col, val))
        return self

    def neq(self, col, val):
        self._filters.append(("neq", col, val))
        return self

    def in_(self, col, vals):
        self._filters.append(("in", col, list(vals)))
        return self

    def ilike(self, col, pattern):
        self._filters.append(("ilike", col, pattern))
        return self

    def gte(self, col, val):
        self._filters.append(("gte", col, val))
        return self

    def lte(self, col, val):
        self._filters.append(("lte", col, val))
        return self

    def order(self, col, desc=False, nullsfirst=True):
        self._order.append((col, desc))
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def single(self):
        self._single = True
        return self

    # ---- matching ----
    def _matches(self, row: dict) -> bool:
        for kind, col, val in self._filters:
            actual = row.get(col)
            if kind == "eq" and actual != val:
                return False
            if kind == "neq" and actual == val:
                return False
            if kind == "in" and actual not in val:
                return False
            if kind == "ilike":
                pattern = str(val).replace("%", "*").replace("_", "?")
                if not fnmatch.fnmatch(str(actual or "").lower(), pattern.lower()):
                    return False
            if kind in ("gte", "lte"):
                try:
                    a, b = str(actual), str(val)
                except Exception:
                    return False
                if kind == "gte" and not a >= b:
                    return False
                if kind == "lte" and not a > b:
                    return False
        return True

    # ---- execution ----
    def execute(self) -> FakeResult:
        store = self._store
        table = self._table
        rows = store.rows(table)

        if self._op == "insert":
            items = self._payload if isinstance(self._payload, list) else [self._payload]
            out = []
            for item in items:
                row = _apply_defaults(table, dict(item))
                row.setdefault("id", str(uuid.uuid4()))
                rows.append(row)
                out.append(row)
            return FakeResult(out, len(out))

        if self._op == "update":
            matched = [r for r in rows if self._matches(r)]
            for r in matched:
                r.update(self._payload)
            return FakeResult(matched, len(matched))

        if self._op == "delete":
            matched = [r for r in rows if self._matches(r)]
            store.data[table] = [r for r in rows if not self._matches(r)]
            return FakeResult(matched, len(matched))

        if self._op == "upsert":
            items = self._payload if isinstance(self._payload, list) else [self._payload]
            out = []
            for item in items:
                row = dict(item)
                existing = None
                if self._upsert_conflict:
                    for r in rows:
                        if all(r.get(c) == row.get(c) for c in self._upsert_conflict):
                            existing = r
                            break
                if existing:
                    existing.update(row)
                    out.append(existing)
                else:
                    row.setdefault("id", str(uuid.uuid4()))
                    rows.append(row)
                    out.append(row)
            return FakeResult(out, len(out))

        # select
        selected = [r for r in rows if self._matches(r)]

        for col, desc in reversed(self._order):
            selected = sorted(
                selected,
                key=lambda r: (_sort_key(r.get(col)), r.get(col) is None),
                reverse=desc,
            )

        if self._range is not None:
            start, end = self._range
            selected = selected[start : end + 1]
        if self._limit is not None:
            selected = selected[: self._limit]

        # emulate nested select joins we rely on: documents(file_name), profiles(...), organizations(name)
        selected = [_apply_joins(self._select_cols, row, store) for row in selected]

        count = len([r for r in rows if self._matches(r)]) if self._count_mode else None
        if self._single:
            return FakeResult(selected[0] if selected else None, count)
        return FakeResult(selected, count)


def _sort_key(v):
    if v is None:
        return (0, "")
    if isinstance(v, bool):
        return (1, v)
    if isinstance(v, (int, float)):
        return (2, v)
    return (3, str(v))


def _apply_joins(cols: str, row: dict, store: "TableStore") -> dict:
    out = dict(row)
    if "documents(file_name)" in cols and row.get("document_id"):
        docs = [d for d in store.rows("documents") if d["id"] == row["document_id"]]
        out["documents"] = {"file_name": docs[0]["file_name"]} if docs else None
    if "profiles(" in cols and row.get("user_id"):
        profiles = [p for p in store.rows("profiles") if p["id"] == row["user_id"]]
        if profiles:
            p = profiles[0]
            keys = re.search(r"profiles\(([^)]*)\)", cols)
            fields = [k.strip() for k in keys.group(1).split(",")] if keys else ["email"]
            out["profiles"] = {f: p.get(f) for f in fields}
    if "organizations(name)" in cols and row.get("organization_id"):
        orgs = [o for o in store.rows("organizations") if o["id"] == row["organization_id"]]
        out["organizations"] = {"name": orgs[0]["name"]} if orgs else None
    if "plans(" in cols and row.get("plan_code"):
        plans = [p for p in store.rows("plans") if p["code"] == row["plan_code"]]
        if plans:
            keys = re.search(r"plans\(([^)]*)\)", cols)
            fields = [k.strip() for k in keys.group(1).split(",")] if keys else ["code", "name"]
            out["plans"] = {f: plans[0].get(f) for f in fields}
    return out


class TableStore:
    def __init__(self):
        self.data: dict[str, list[dict]] = {}

    def rows(self, table: str) -> list[dict]:
        return self.data.setdefault(table, [])


class FakeBucket:
    def __init__(self, store: dict):
        self.store = store

    def upload(self, path: str, data: bytes, options=None):
        self.store[path] = data
        return {"path": path}

    def download(self, path: str) -> bytes:
        if path not in self.store:
            raise FileNotFoundError(path)
        return self.store[path]

    def remove(self, paths: list[str]):
        for p in paths:
            self.store.pop(p, None)
        return [{"path": p} for p in paths]

    def create_signed_url(self, path: str, seconds: int):
        if path not in self.store:
            raise FileNotFoundError(path)
        return f"http://fake-storage/{path}?sig=test&expires={seconds}"


class FakeStorage:
    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.buckets: dict[str, FakeBucket] = {}

    def from_(self, bucket: str) -> FakeBucket:
        if bucket not in self.buckets:
            self.buckets[bucket] = FakeBucket(self.objects)
        return self.buckets[bucket]


class Executable:
    """Wraps an already-computed result so callers can .execute() it."""
    def __init__(self, result: FakeResult):
        self._result = result

    def execute(self) -> FakeResult:
        return self._result


class FakeSupabase:
    """Drop-in replacement for supabase.create_client() in tests."""

    def __init__(self):
        self.tables = TableStore()
        self.storage = FakeStorage()

    # ---- client API ----
    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self.tables, name)

    def rpc(self, fn: str, params: dict | None = None) -> Executable:
        params = params or {}
        rows = self.tables.rows

        if fn == "log_activity":
            rows("activity_events").append({
                "id": str(uuid.uuid4()),
                "case_id": params.get("p_case_id"),
                "actor_id": str(uuid.uuid4()),
                "event_type": params.get("p_event_type"),
                "description": params.get("p_description"),
                "metadata": params.get("p_metadata"),
                "created_at": _now(),
            })
            return Executable(FakeResult(None))

        if fn == "keyword_search_chunks":
            query = (params.get("p_query") or "").lower()
            words = [w for w in re.split(r"\W+", query) if len(w) > 2][:8]
            out = []
            for c in rows("document_chunks"):
                if c.get("case_id") != params.get("p_case_id"):
                    continue
                content = (c.get("content") or "").lower()
                score = sum(1 for w in words if w in content)
                if score == 0:
                    continue
                docs = [d for d in rows("documents") if d["id"] == c["document_id"]]
                out.append({
                    "id": c["id"], "case_id": c["case_id"],
                    "document_id": c["document_id"],
                    "document_name": docs[0]["file_name"] if docs else "unknown",
                    "page_number": c["page_number"],
                    "chunk_index": c.get("chunk_index", 0),
                    "content": c["content"],
                    "rank": score,
                })
            out.sort(key=lambda r: r["rank"], reverse=True)
            return Executable(FakeResult(out[: params.get("p_top_k", 12)]))

        if fn == "match_document_chunks":
            # vector search unavailable in fake; keyword path covers retrieval tests
            return Executable(FakeResult([]))

        if fn == "get_risk_counts":
            counts: dict[str, int] = {}
            for r in rows("risks"):
                if r.get("case_id") == params.get("p_case_id") and not r.get("resolved"):
                    counts[r["level"]] = counts.get(r["level"], 0) + 1
            return Executable(FakeResult([{"level": k, "count": v} for k, v in counts.items()]))

        if fn in ("is_org_member", "can_manage_org", "is_case_member", "can_manage_case", "is_platform_admin", "user_role_in_org"):
            # Policies don't run in the fake; the API code performs its own
            # service-role membership checks anyway.
            return Executable(FakeResult(True))

        raise ValueError(f"FakeSupabase.rpc: unimplemented function '{fn}'")


def _now():
    return datetime.now(timezone.utc).isoformat()


# Column defaults the real database applies on INSERT.
TABLE_DEFAULTS: dict[str, dict] = {
    "cases": {"status": "ACTIVE"},
    "documents": {"status": "UPLOADED"},
    "jobs": {"state": "QUEUED", "progress": 0, "attempts": 0, "max_attempts": 3},
    "organizations": {"plan": "FREE"},
    "drafts": {"status": "REVIEW", "version": 1},
    "reports": {"status": "QUEUED"},
    "risks": {"resolved": False},
    "agent_runs": {"status": "RUNNING", "llm_calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "iterations": 0},
    "voice_sessions": {"status": "ACTIVE", "language": "en"},
}
TIMESTAMP_COLUMNS = ("created_at", "updated_at", "started_at")


def _apply_defaults(table: str, row: dict) -> dict:
    for key, value in TABLE_DEFAULTS.get(table, {}).items():
        if row.get(key) is None:
            row[key] = value
    for col in TIMESTAMP_COLUMNS:
        if row.get(col) is None:
            row[col] = _now()
    return row


def make_fake():
    return FakeSupabase()
