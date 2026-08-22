from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import get_settings

settings = get_settings()

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute", "1000/hour"])

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
# Automatically allows all Vercel preview & production deployments (*.vercel.app), localhost, and custom origins
configured_origins = settings.CORS_ORIGINS
allowed_origins = [o for o in configured_origins if o != "*"]
if "http://localhost:3000" not in allowed_origins:
    allowed_origins.extend(["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["http://localhost:3000"],
    allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)


@app.get("/")
async def root():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# Import and mount routers
from app.api.cases import router as cases_router
from app.api.documents import router as documents_router
from app.api.analysis import router as analysis_router
from app.api.ownership import router as ownership_router
from app.api.comparison import router as comparison_router
from app.api.risks import router as risks_router
from app.api.research import router as research_router
from app.api.drafts import router as drafts_router
from app.api.reports import router as reports_router
from app.api.properties import router as properties_router
from app.api.jobs import router as jobs_router
from app.api.events import router as events_router
from app.api.voice import router as voice_router
from app.api.admin import router as admin_router
from app.api.org import router as org_router
from app.api.billing import router as billing_router
from app.api.ai import router as ai_router
from app.api.sso import router as sso_router
from app.api.pii import router as pii_router
from app.api.analytics import router as analytics_router
from app.api.contract_intelligence import router as contract_intelligence_router
from app.api.review_tables import router as review_tables_router
from app.api.workflows import router as workflows_router
from app.api.shared_spaces import router as shared_spaces_router
from app.api.state_portals import router as state_portals_router
from app.api.bsa import router as bsa_router
from app.api.deep_research import router as deep_research_router
from app.api.bsa_certificates import router as bsa_certificates_router
from app.api.agents import router as agents_router

app.include_router(cases_router, prefix=settings.API_V1_PREFIX)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)
app.include_router(analysis_router, prefix=settings.API_V1_PREFIX)
app.include_router(ownership_router, prefix=settings.API_V1_PREFIX)
app.include_router(comparison_router, prefix=settings.API_V1_PREFIX)
app.include_router(risks_router, prefix=settings.API_V1_PREFIX)
app.include_router(research_router, prefix=settings.API_V1_PREFIX)
app.include_router(drafts_router, prefix=settings.API_V1_PREFIX)
app.include_router(reports_router, prefix=settings.API_V1_PREFIX)
app.include_router(properties_router, prefix=settings.API_V1_PREFIX)
app.include_router(jobs_router, prefix=settings.API_V1_PREFIX)
app.include_router(events_router, prefix=settings.API_V1_PREFIX)
app.include_router(voice_router, prefix=settings.API_V1_PREFIX)
app.include_router(admin_router, prefix=settings.API_V1_PREFIX)
app.include_router(org_router, prefix=settings.API_V1_PREFIX)
app.include_router(billing_router, prefix=settings.API_V1_PREFIX)
app.include_router(ai_router, prefix=settings.API_V1_PREFIX)
app.include_router(sso_router, prefix=settings.API_V1_PREFIX)
app.include_router(pii_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)
app.include_router(contract_intelligence_router, prefix=settings.API_V1_PREFIX)
app.include_router(review_tables_router, prefix=settings.API_V1_PREFIX)
app.include_router(workflows_router, prefix=settings.API_V1_PREFIX)
app.include_router(shared_spaces_router, prefix=settings.API_V1_PREFIX)
app.include_router(state_portals_router, prefix=settings.API_V1_PREFIX)
app.include_router(bsa_router, prefix=settings.API_V1_PREFIX)
app.include_router(deep_research_router, prefix=settings.API_V1_PREFIX)
app.include_router(bsa_certificates_router, prefix=settings.API_V1_PREFIX)
app.include_router(agents_router, prefix=settings.API_V1_PREFIX)



