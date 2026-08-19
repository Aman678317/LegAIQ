"""Command Center Analytics API — Team productivity, case velocity, AI ROI."""
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from supabase import create_client

from app.config import get_settings
from app.security.auth import AuthContext, get_auth_context, require_role

settings = get_settings()
router = APIRouter(prefix="/analytics", tags=["analytics"])


def svc():
    url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or "placeholder-key"
    try:
        return create_client(url, key)
    except Exception:
        return None


# ==================== Enums & Models ====================

class TimeRange(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    ALL = "all"


class CaseType(str, Enum):
    PROPERTY = "PROPERTY"
    CIVIL = "CIVIL"
    CRIMINAL = "CRIMINAL"
    CORPORATE = "CORPORATE"
    FAMILY = "FAMILY"
    TAX = "TAX"
    IP = "IP"
    OTHER = "OTHER"


class TeamProductivityMetrics(BaseModel):
    """Team productivity metrics for an organization."""
    organization_id: str
    period: TimeRange
    period_start: datetime
    period_end: datetime
    
    # Case metrics
    total_cases: int = 0
    active_cases: int = 0
    completed_cases: int = 0
    new_cases: int = 0
    cases_by_type: Dict[str, int] = Field(default_factory=dict)
    cases_by_status: Dict[str, int] = Field(default_factory=dict)
    
    # User metrics
    total_users: int = 0
    active_users: int = 0
    cases_per_user: float = 0.0
    documents_per_user: float = 0.0
    
    # Document metrics
    total_documents: int = 0
    processed_documents: int = 0
    pending_documents: int = 0
    avg_document_size_mb: float = 0.0
    
    # Time metrics
    avg_case_duration_days: Optional[float] = None
    avg_time_to_first_action_days: Optional[float] = None
    
    # AI metrics
    ai_jobs_run: int = 0
    ai_jobs_succeeded: int = 0
    ai_jobs_failed: int = 0
    ai_cost_estimate_usd: float = 0.0
    ai_time_saved_hours: float = 0.0
    
    # Top performers
    top_users_by_cases: List[Dict[str, Any]] = Field(default_factory=list)
    top_users_by_documents: List[Dict[str, Any]] = Field(default_factory=list)


class CaseVelocityMetrics(BaseModel):
    """Case velocity metrics for a specific case or organization."""
    case_id: Optional[str] = None
    organization_id: str
    period: TimeRange
    period_start: datetime
    period_end: datetime
    
    # Velocity metrics
    cases_created: int = 0
    cases_completed: int = 0
    cases_in_progress: int = 0
    
    # Stage progression
    stage_durations: Dict[str, float] = Field(default_factory=dict)  # avg days per stage
    bottlenecks: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Document processing velocity
    docs_uploaded: int = 0
    docs_processed: int = 0
    avg_processing_time_hours: float = 0.0
    
    # AI processing velocity
    ai_tasks_queued: int = 0
    ai_tasks_completed: int = 0
    avg_ai_processing_time_seconds: float = 0.0
    
    # Trends (for charts)
    daily_cases_created: List[Dict[str, Any]] = Field(default_factory=list)
    daily_cases_completed: List[Dict[str, Any]] = Field(default_factory=list)
    daily_docs_processed: List[Dict[str, Any]] = Field(default_factory=list)


class AIROIMetrics(BaseModel):
    """AI Return on Investment metrics."""
    organization_id: str
    period: TimeRange
    period_start: datetime
    period_end: datetime
    
    # Usage metrics
    total_ai_calls: int = 0
    ai_calls_by_type: Dict[str, int] = Field(default_factory=dict)
    ai_calls_by_provider: Dict[str, int] = Field(default_factory=dict)
    
    # Cost metrics
    estimated_ai_cost_usd: float = 0.0
    cost_by_provider: Dict[str, float] = Field(default_factory=dict)
    cost_by_type: Dict[str, float] = Field(default_factory=dict)
    
    # Savings metrics
    estimated_manual_hours_saved: float = 0.0
    estimated_cost_savings_usd: float = 0.0
    roi_percentage: float = 0.0
    
    # Efficiency metrics
    avg_ai_response_time_ms: float = 0.0
    ai_success_rate: float = 0.0
    tasks_automated: int = 0
    tasks_requiring_review: int = 0
    
    # Trends
    daily_ai_usage: List[Dict[str, Any]] = Field(default_factory=list)
    daily_ai_cost: List[Dict[str, Any]] = Field(default_factory=list)
    daily_time_saved: List[Dict[str, Any]] = Field(default_factory=list)


class DashboardSummary(BaseModel):
    """Executive dashboard summary."""
    organization_id: str
    generated_at: datetime
    
    # Key metrics
    total_cases: int = 0
    active_cases: int = 0
    cases_this_month: int = 0
    cases_completed_this_month: int = 0
    
    total_documents: int = 0
    documents_this_month: int = 0
    documents_processed_this_month: int = 0
    
    active_users: int = 0
    team_size: int = 0
    
    ai_jobs_this_month: int = 0
    ai_success_rate: float = 0.0
    estimated_monthly_ai_cost: float = 0.0
    estimated_monthly_savings: float = 0.0
    
    # Alerts
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Recent activity
    recent_activity: List[Dict[str, Any]] = Field(default_factory=list)


# ==================== Helper Functions ====================

def get_period_range(time_range: TimeRange) -> tuple[datetime, datetime]:
    """Get start and end datetime for a time range."""
    now = datetime.now(timezone.utc)
    if time_range == TimeRange.DAY:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == TimeRange.WEEK:
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == TimeRange.MONTH:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif time_range == TimeRange.QUARTER:
        quarter_start_month = ((now.month - 1) // 3) * 3 + 1
        start = now.replace(month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif time_range == TimeRange.YEAR:
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:  # ALL
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    return start, now


async def get_org_members(db, org_id: str) -> List[Dict]:
    """Get all members of an organization."""
    try:
        result = db.table("memberships").select("user_id, role, created_at, profiles(email, full_name)").eq("organization_id", org_id).execute()
        return result.data or []
    except Exception:
        return []


async def get_user_activity(db, org_id: str, user_id: str, start: datetime, end: datetime) -> Dict:
    """Get user activity metrics."""
    try:
        # Cases created
        cases_created = db.table("cases").select("id", count="exact").eq("organization_id", org_id).eq("created_by", user_id).gte("created_at", start.isoformat()).lte("created_at", end.isoformat()).execute()
        
        # Documents uploaded
        docs_uploaded = db.table("documents").select("id", count="exact").eq("case_id", "temp").execute()  # Will filter by case
        # Get user's cases first
        user_cases = db.table("cases").select("id").eq("organization_id", org_id).eq("created_by", user_id).execute()
        case_ids = [c["id"] for c in (user_cases.data or [])]
        
        if case_ids:
            docs_uploaded = db.table("documents").select("id", count="exact").in_("case_id", case_ids).gte("created_at", start.isoformat()).lte("created_at", end.isoformat()).execute()
        
        return {
            "user_id": user_id,
            "cases_created": cases_created.count or 0,
            "documents_uploaded": docs_uploaded.count or 0 if case_ids else 0,
        }
    except Exception:
        return {"user_id": user_id, "cases_created": 0, "documents_uploaded": 0}


# ==================== API Endpoints ====================

@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard_summary(
    org_id: str = Query(..., description="Organization ID"),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Get executive dashboard summary for an organization."""
    db = svc()
    if not db:
        raise HTTPException(500, "Database not available")
    
    # Verify user has access to org
    membership = db.table("memberships").select("role").eq("organization_id", org_id).eq("user_id", ctx.user_id).single().execute()
    if not membership.data:
        raise HTTPException(403, "Not a member of this organization")
    
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get all cases
    cases = db.table("cases").select("*").eq("organization_id", org_id).execute().data or []
    total_cases = len(cases)
    active_cases = len([c for c in cases if c.get("status") in ("OPEN", "IN_PROGRESS", "ACTIVE")])
    cases_this_month = len([c for c in cases if c.get("created_at") and c["created_at"] >= month_start.isoformat()])
    completed_this_month = len([c for c in cases if c.get("status") in ("CLOSED", "RESOLVED", "COMPLETED") and c.get("updated_at") and c["updated_at"] >= month_start.isoformat()])
    
    # Get all documents
    case_ids = [c["id"] for c in cases]
    docs = []
    if case_ids:
        docs = db.table("documents").select("*").in_("case_id", case_ids).execute().data or []
    total_documents = len(docs)
    docs_this_month = len([d for d in docs if d.get("created_at") and d["created_at"] >= month_start.isoformat()])
    docs_processed_this_month = len([d for d in docs if d.get("status") == "COMPLETED" and d.get("updated_at") and d["updated_at"] >= month_start.isoformat()])
    
    # Get members
    members = await get_org_members(db, org_id)
    team_size = len(members)
    active_users = len([m for m in members if m.get("created_at")])  # Simplified
    
    # Get AI jobs
    ai_jobs = []
    if case_ids:
        ai_jobs = db.table("jobs").select("*").in_("case_id", case_ids).eq("job_type", "ai").gte("created_at", month_start.isoformat()).execute().data or []
    ai_jobs_this_month = len(ai_jobs)
    ai_succeeded = len([j for j in ai_jobs if j.get("state") == "COMPLETED"])
    ai_success_rate = (ai_succeeded / ai_jobs_this_month * 100) if ai_jobs_this_month > 0 else 0.0
    
    # Estimate costs (rough estimates)
    estimated_monthly_ai_cost = ai_jobs_this_month * 0.02  # $0.02 per AI job estimate
    estimated_monthly_savings = ai_jobs_this_month * 0.5  # 30 min saved per job at $50/hr
    
    # Recent activity
    recent_activity = []
    try:
        activities = db.table("activity_log").select("*").eq("case_id", case_ids[0] if case_ids else "none").order("created_at", desc=True).limit(10).execute()
        recent_activity = activities.data or []
    except Exception:
        pass
    
    # Alerts
    alerts = []
    if active_cases > 0 and active_users == 0:
        alerts.append({"type": "warning", "message": "Active cases but no active team members"})
    if ai_success_rate < 80 and ai_jobs_this_month > 10:
        alerts.append({"type": "warning", "message": f"AI success rate is {ai_success_rate:.1f}% (below 80%)"})
    if cases_this_month > completed_this_month * 3:
        alerts.append({"type": "info", "message": "Case backlog growing - consider adding resources"})
    
    return DashboardSummary(
        organization_id=org_id,
        generated_at=now,
        total_cases=total_cases,
        active_cases=active_cases,
        cases_this_month=cases_this_month,
        cases_completed_this_month=completed_this_month,
        total_documents=total_documents,
        documents_this_month=docs_this_month,
        documents_processed_this_month=docs_processed_this_month,
        active_users=active_users,
        team_size=team_size,
        ai_jobs_this_month=ai_jobs_this_month,
        ai_success_rate=ai_success_rate,
        estimated_monthly_ai_cost=estimated_monthly_ai_cost,
        estimated_monthly_savings=estimated_monthly_savings,
        alerts=alerts,
        recent_activity=recent_activity,
    )


@router.get("/team-productivity", response_model=TeamProductivityMetrics)
async def get_team_productivity(
    org_id: str = Query(..., description="Organization ID"),
    period: TimeRange = Query(TimeRange.MONTH, description="Time period"),
    ctx: AuthContext = Depends(require_role("ADMIN", "OWNER")),
):
    """Get team productivity metrics (requires ADMIN/OWNER)."""
    db = svc()
    if not db:
        raise HTTPException(500, "Database not available")
    
    period_start, period_end = get_period_range(period)
    
    # Verify access
    membership = db.table("memberships").select("role").eq("organization_id", org_id).eq("user_id", ctx.user_id).single().execute()
    if not membership.data:
        raise HTTPException(403, "Not a member of this organization")
    
    # Get all cases in period
    cases = db.table("cases").select("*").eq("organization_id", org_id).gte("created_at", period_start.isoformat()).lte("created_at", period_end.isoformat()).execute().data or []
    
    # Get members
    members = await get_org_members(db, org_id)
    total_users = len(members)
    
    # Case metrics
    total_cases = len(cases)
    active_cases = len([c for c in cases if c.get("status") in ("OPEN", "IN_PROGRESS", "ACTIVE")])
    completed_cases = len([c for c in cases if c.get("status") in ("CLOSED", "RESOLVED", "COMPLETED")])
    new_cases = len(cases)
    
    cases_by_type = {}
    cases_by_status = {}
    for c in cases:
        ct = c.get("case_type", "OTHER")
        cases_by_type[ct] = cases_by_type.get(ct, 0) + 1
        cs = c.get("status", "UNKNOWN")
        cases_by_status[cs] = cases_by_status.get(cs, 0) + 1
    
    # Document metrics
    case_ids = [c["id"] for c in cases]
    docs = []
    if case_ids:
        docs = db.table("documents").select("*").in_("case_id", case_ids).execute().data or []
    
    total_documents = len(docs)
    processed_documents = len([d for d in docs if d.get("status") == "COMPLETED"])
    pending_documents = len([d for d in docs if d.get("status") in ("PROCESSING", "PENDING", "UPLOADED")])
    avg_doc_size = sum(d.get("file_size", 0) for d in docs) / len(docs) / (1024 * 1024) if docs else 0
    
    # AI metrics
    ai_jobs = []
    if case_ids:
        ai_jobs = db.table("jobs").select("*").in_("case_id", case_ids).eq("job_type", "ai").execute().data or []
    ai_jobs_run = len(ai_jobs)
    ai_succeeded = len([j for j in ai_jobs if j.get("state") == "COMPLETED"])
    ai_failed = len([j for j in ai_jobs if j.get("state") == "FAILED"])
    
    # Estimate AI cost and time saved
    ai_cost = ai_jobs_run * 0.02
    ai_time_saved = ai_succeeded * 0.5  # 30 min per job
    
    # User performance
    user_performance = []
    for member in members:
        uid = member["user_id"]
        activity = await get_user_activity(db, org_id, uid, period_start, period_end)
        user_performance.append({
            "user_id": uid,
            "email": member.get("profiles", {}).get("email"),
            "name": member.get("profiles", {}).get("full_name"),
            "role": member.get("role"),
            "cases_created": activity["cases_created"],
            "documents_uploaded": activity["documents_uploaded"],
        })
    
    # Sort top performers
    top_by_cases = sorted(user_performance, key=lambda x: x["cases_created"], reverse=True)[:5]
    top_by_docs = sorted(user_performance, key=lambda x: x["documents_uploaded"], reverse=True)[:5]
    
    # Avg case duration
    completed_cases_data = [c for c in cases if c.get("status") in ("CLOSED", "RESOLVED", "COMPLETED") and c.get("created_at") and c.get("updated_at")]
    avg_duration = None
    if completed_cases_data:
        durations = [(datetime.fromisoformat(c["updated_at"].replace("Z", "+00:00")) - datetime.fromisoformat(c["created_at"].replace("Z", "+00:00"))).days for c in completed_cases_data]
        avg_duration = sum(durations) / len(durations) if durations else None
    
    active_user_count = len([u for u in user_performance if u["cases_created"] > 0 or u["documents_uploaded"] > 0])
    
    return TeamProductivityMetrics(
        organization_id=org_id,
        period=period,
        period_start=period_start,
        period_end=period_end,
        total_cases=total_cases,
        active_cases=active_cases,
        completed_cases=completed_cases,
        new_cases=new_cases,
        cases_by_type=cases_by_type,
        cases_by_status=cases_by_status,
        total_users=total_users,
        active_users=active_user_count,
        cases_per_user=total_cases / max(active_user_count, 1),
        documents_per_user=total_documents / max(active_user_count, 1),
        total_documents=total_documents,
        processed_documents=processed_documents,
        pending_documents=pending_documents,
        avg_document_size_mb=round(avg_doc_size, 2),
        avg_case_duration_days=round(avg_duration, 1) if avg_duration else None,
        ai_jobs_run=ai_jobs_run,
        ai_jobs_succeeded=ai_succeeded,
        ai_jobs_failed=ai_failed,
        ai_cost_estimate_usd=round(ai_cost, 2),
        ai_time_saved_hours=round(ai_time_saved, 1),
        top_users_by_cases=top_by_cases,
        top_users_by_documents=top_by_docs,
    )


@router.get("/case-velocity", response_model=CaseVelocityMetrics)
async def get_case_velocity(
    org_id: str = Query(..., description="Organization ID"),
    case_id: Optional[str] = Query(None, description="Specific case ID (optional)"),
    period: TimeRange = Query(TimeRange.MONTH, description="Time period"),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Get case velocity metrics."""
    db = svc()
    if not db:
        raise HTTPException(500, "Database not available")
    
    # Verify access
    membership = db.table("memberships").select("role").eq("organization_id", org_id).eq("user_id", ctx.user_id).single().execute()
    if not membership.data:
        raise HTTPException(403, "Not a member of this organization")
    
    period_start, period_end = get_period_range(period)
    
    # Build query
    query = db.table("cases").select("*").eq("organization_id", org_id)
    if case_id:
        query = query.eq("id", case_id)
    else:
        query = query.gte("created_at", period_start.isoformat()).lte("created_at", period_end.isoformat())
    
    cases = query.execute().data or []
    
    if case_id and not cases:
        raise HTTPException(404, "Case not found")
    
    case_ids = [c["id"] for c in cases]
    
    # Case metrics
    cases_created = len(cases)
    cases_completed = len([c for c in cases if c.get("status") in ("CLOSED", "RESOLVED", "COMPLETED")])
    cases_in_progress = len([c for c in cases if c.get("status") in ("OPEN", "IN_PROGRESS", "ACTIVE")])
    
    # Stage durations (from activity log)
    stage_durations = {}
    bottlenecks = []
    if case_ids:
        try:
            activities = db.table("activity_log").select("*").in_("case_id", case_ids).order("created_at").execute().data or []
            
            # Group by case and stage
            case_stages = {}
            for act in activities:
                cid = act.get("case_id")
                event = act.get("event_type", "")
                if cid not in case_stages:
                    case_stages[cid] = []
                case_stages[cid].append({
                    "event": event,
                    "time": datetime.fromisoformat(act["created_at"].replace("Z", "+00:00")) if act.get("created_at") else None,
                })
            
            # Calculate stage durations
            for cid, stages in case_stages.items():
                for i in range(len(stages) - 1):
                    if stages[i]["time"] and stages[i+1]["time"]:
                        duration = (stages[i+1]["time"] - stages[i]["time"]).total_seconds() / 3600  # hours
                        event = stages[i]["event"]
                        if event not in stage_durations:
                            stage_durations[event] = []
                        stage_durations[event].append(duration)
            
            # Average
            stage_durations = {k: round(sum(v) / len(v), 1) for k, v in stage_durations.items() if v}
            
            # Find bottlenecks (stages > 48 hours)
            for stage, avg_hours in stage_durations.items():
                if avg_hours > 48:
                    bottlenecks.append({
                        "stage": stage,
                        "avg_hours": avg_hours,
                        "severity": "high" if avg_hours > 168 else "medium",
                    })
        except Exception:
            pass
    
    # Document velocity
    docs = []
    if case_ids:
        docs = db.table("documents").select("*").in_("case_id", case_ids).execute().data or []
    docs_uploaded = len(docs)
    docs_processed = len([d for d in docs if d.get("status") == "COMPLETED"])
    
    # Avg processing time
    processed_docs = [d for d in docs if d.get("status") == "COMPLETED" and d.get("created_at") and d.get("updated_at")]
    avg_processing = 0.0
    if processed_docs:
        times = [(datetime.fromisoformat(d["updated_at"].replace("Z", "+00:00")) - datetime.fromisoformat(d["created_at"].replace("Z", "+00:00"))).total_seconds() / 3600 for d in processed_docs]
        avg_processing = round(sum(times) / len(times), 1)
    
    # AI velocity
    ai_tasks = []
    if case_ids:
        ai_tasks = db.table("jobs").select("*").in_("case_id", case_ids).eq("job_type", "ai").execute().data or []
    ai_queued = len(ai_tasks)
    ai_completed = len([j for j in ai_tasks if j.get("state") == "COMPLETED"])
    
    ai_times = [j for j in ai_tasks if j.get("state") == "COMPLETED" and j.get("started_at") and j.get("completed_at")]
    avg_ai_time = 0.0
    if ai_times:
        times = [(datetime.fromisoformat(j["completed_at"].replace("Z", "+00:00")) - datetime.fromisoformat(j["started_at"].replace("Z", "+00:00"))).total_seconds() for j in ai_times]
        avg_ai_time = round(sum(times) / len(times), 1)
    
    # Daily trends (simplified)
    daily_cases_created = []
    daily_cases_completed = []
    daily_docs_processed = []
    
    # Generate daily buckets
    current = period_start
    while current <= period_end:
        day_str = current.date().isoformat()
        day_cases = len([c for c in cases if c.get("created_at") and c["created_at"].startswith(day_str)])
        day_completed = len([c for c in cases if c.get("updated_at") and c["updated_at"].startswith(day_str) and c.get("status") in ("CLOSED", "RESOLVED", "COMPLETED")])
        day_docs = len([d for d in docs if d.get("updated_at") and d["updated_at"].startswith(day_str) and d.get("status") == "COMPLETED"])
        
        daily_cases_created.append({"date": day_str, "count": day_cases})
        daily_cases_completed.append({"date": day_str, "count": day_completed})
        daily_docs_processed.append({"date": day_str, "count": day_docs})
        
        current += timedelta(days=1)
    
    return CaseVelocityMetrics(
        case_id=case_id,
        organization_id=org_id,
        period=period,
        period_start=period_start,
        period_end=period_end,
        cases_created=cases_created,
        cases_completed=cases_completed,
        cases_in_progress=cases_in_progress,
        stage_durations=stage_durations,
        bottlenecks=bottlenecks,
        docs_uploaded=docs_uploaded,
        docs_processed=docs_processed,
        avg_processing_time_hours=avg_processing,
        ai_tasks_queued=ai_queued,
        ai_tasks_completed=ai_completed,
        avg_ai_processing_time_seconds=avg_ai_time,
        daily_cases_created=daily_cases_created,
        daily_cases_completed=daily_cases_completed,
        daily_docs_processed=daily_docs_processed,
    )


@router.get("/ai-roi", response_model=AIROIMetrics)
async def get_ai_roi(
    org_id: str = Query(..., description="Organization ID"),
    period: TimeRange = Query(TimeRange.MONTH, description="Time period"),
    ctx: AuthContext = Depends(require_role("ADMIN", "OWNER")),
):
    """Get AI ROI metrics (requires ADMIN/OWNER)."""
    db = svc()
    if not db:
        raise HTTPException(500, "Database not available")
    
    # Verify access
    membership = db.table("memberships").select("role").eq("organization_id", org_id).eq("user_id", ctx.user_id).single().execute()
    if not membership.data:
        raise HTTPException(403, "Not a member of this organization")
    
    period_start, period_end = get_period_range(period)
    
    # Get cases in period
    cases = db.table("cases").select("id").eq("organization_id", org_id).gte("created_at", period_start.isoformat()).lte("created_at", period_end.isoformat()).execute().data or []
    case_ids = [c["id"] for c in cases]
    
    # Get AI jobs
    ai_jobs = []
    if case_ids:
        ai_jobs = db.table("jobs").select("*").in_("case_id", case_ids).eq("job_type", "ai").execute().data or []
    
    total_ai_calls = len(ai_jobs)
    ai_succeeded = len([j for j in ai_jobs if j.get("state") == "COMPLETED"])
    ai_failed = len([j for j in ai_jobs if j.get("state") == "FAILED"])
    
    # AI calls by type (from payload)
    ai_by_type = {}
    ai_by_provider = {}
    for job in ai_jobs:
        payload = job.get("payload", {})
        job_subtype = payload.get("task_type", "unknown")
        ai_by_type[job_subtype] = ai_by_type.get(job_subtype, 0) + 1
        provider = payload.get("provider", "openai")
        ai_by_provider[provider] = ai_by_provider.get(provider, 0) + 1
    
    # Cost estimates (rough)
    cost_per_call = {
        "openai": 0.03,
        "anthropic": 0.02,
        "google": 0.01,
        "ollama": 0.001,
    }
    
    cost_by_provider = {}
    for provider, count in ai_by_provider.items():
        cost_by_provider[provider] = round(count * cost_per_call.get(provider, 0.02), 2)
    
    cost_by_type = {}
    for jtype, count in ai_by_type.items():
        cost_by_type[jtype] = round(count * 0.02, 2)
    
    total_cost = sum(cost_by_provider.values())
    
    # Savings estimates
    manual_hours_per_task = 0.5  # 30 min
    hourly_rate = 75.0  # $75/hr for legal work
    hours_saved = ai_succeeded * manual_hours_per_task
    cost_savings = hours_saved * hourly_rate
    roi = ((cost_savings - total_cost) / total_cost * 100) if total_cost > 0 else 0
    
    # Avg response time
    completed_jobs = [j for j in ai_jobs if j.get("state") == "COMPLETED" and j.get("started_at") and j.get("completed_at")]
    avg_response_ms = 0.0
    if completed_jobs:
        times = [(datetime.fromisoformat(j["completed_at"].replace("Z", "+00:00")) - datetime.fromisoformat(j["started_at"].replace("Z", "+00:00"))).total_seconds() * 1000 for j in completed_jobs]
        avg_response_ms = round(sum(times) / len(times))
    
    success_rate = (ai_succeeded / total_ai_calls * 100) if total_ai_calls > 0 else 0
    
    # Tasks automated vs requiring review
    tasks_automated = ai_succeeded
    tasks_requiring_review = ai_failed + len([j for j in ai_jobs if j.get("state") == "COMPLETED" and j.get("requires_review")])
    
    # Daily trends
    daily_ai_usage = []
    daily_ai_cost = []
    daily_time_saved = []
    
    current = period_start
    while current <= period_end:
        day_str = current.date().isoformat()
        day_jobs = [j for j in ai_jobs if j.get("created_at") and j["created_at"].startswith(day_str)]
        day_succeeded = len([j for j in day_jobs if j.get("state") == "COMPLETED"])
        day_cost = sum(cost_per_call.get(j.get("payload", {}).get("provider", "openai"), 0.02) for j in day_jobs)
        day_saved = day_succeeded * manual_hours_per_task
        
        daily_ai_usage.append({"date": day_str, "count": len(day_jobs)})
        daily_ai_cost.append({"date": day_str, "cost": round(day_cost, 2)})
        daily_time_saved.append({"date": day_str, "hours": round(day_saved, 1)})
        
        current += timedelta(days=1)
    
    return AIROIMetrics(
        organization_id=org_id,
        period=period,
        period_start=period_start,
        period_end=period_end,
        total_ai_calls=total_ai_calls,
        ai_calls_by_type=ai_by_type,
        ai_calls_by_provider=ai_by_provider,
        estimated_ai_cost_usd=round(total_cost, 2),
        cost_by_provider=cost_by_provider,
        cost_by_type=cost_by_type,
        estimated_manual_hours_saved=round(hours_saved, 1),
        estimated_cost_savings_usd=round(cost_savings, 2),
        roi_percentage=round(roi, 1),
        avg_ai_response_time_ms=avg_response_ms,
        ai_success_rate=round(success_rate, 1),
        tasks_automated=tasks_automated,
        tasks_requiring_review=tasks_requiring_review,
        daily_ai_usage=daily_ai_usage,
        daily_ai_cost=daily_ai_cost,
        daily_time_saved=daily_time_saved,
    )


@router.get("/export")
async def export_analytics(
    org_id: str = Query(..., description="Organization ID"),
    report_type: str = Query("all", description="Report type: all, productivity, velocity, roi"),
    format: str = Query("json", description="Export format: json, csv"),
    period: TimeRange = Query(TimeRange.MONTH, description="Time period"),
    ctx: AuthContext = Depends(require_role("ADMIN", "OWNER")),
):
    """Export analytics data."""
    db = svc()
    if not db:
        raise HTTPException(500, "Database not available")
    
    # Verify access
    membership = db.table("memberships").select("role").eq("organization_id", org_id).eq("user_id", ctx.user_id).single().execute()
    if not membership.data:
        raise HTTPException(403, "Not a member of this organization")
    
    # For now, just return JSON
    # In production, would generate CSV/PDF
    return {
        "message": "Export functionality - would generate file in production",
        "report_type": report_type,
        "format": format,
        "period": period.value,
    }


@router.get("/health")
async def analytics_health():
    """Health check for analytics service."""
    return {
        "status": "healthy",
        "service": "analytics",
        "features": ["team-productivity", "case-velocity", "ai-roi", "dashboard"],
    }