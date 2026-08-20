"""State Land Portal API Router for 5 Major Indian States.

Endpoints for live land verification across Mahabhulekh (Maharashtra), Bhoomi (Karnataka),
Dharani (Telangana), AnyRoR (Gujarat), and TNREGINET (Tamil Nadu).
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.ai.state_portals import (
    PortalState,
    get_comprehensive_land_report,
    get_portal_connector,
    search_all_portals,
)
from app.config import get_settings
from app.security.auth import AuthContext, get_auth_context, require_role

settings = get_settings()
router = APIRouter(prefix="/property/portals", tags=["state-land-portals"])


class StatePortalQueryRequest(BaseModel):
    state: str = Field(description="maharashtra | karnataka | tamil_nadu | telangana | gujarat")
    survey_number: str = Field(description="Survey / Gat / Khasra / Survey Sub-division number")
    district: str
    taluk: str
    village: str
    years_search: int = Field(default=30, description="Encumbrance search period in years")


class SupportedPortal(BaseModel):
    state_code: str
    state_name: str
    portal_name: str
    portal_url: str
    document_types: List[str]
    sample_survey: str


SUPPORTED_PORTALS_INFO = [
    {
        "state_code": "maharashtra",
        "state_name": "Maharashtra",
        "portal_name": "Mahabhulekh / Satbara",
        "portal_url": "https://mahabhulekh.maharashtra.gov.in",
        "document_types": ["7/12 Extract (Satbara Utara)", "8A Khata", "Ferfar (Mutation)"],
        "sample_survey": "124/2",
    },
    {
        "state_code": "karnataka",
        "state_name": "Karnataka",
        "portal_name": "Bhoomi (RTC / Pahani)",
        "portal_url": "https://bhoomi.karnataka.gov.in",
        "document_types": ["RTC (Pahani)", "Mutation Register (MR)", "Pattadar Passbook"],
        "sample_survey": "45/1A",
    },
    {
        "state_code": "tamil_nadu",
        "state_name": "Tamil Nadu",
        "portal_name": "TNREGINET / Patta Chitta",
        "portal_url": "https://tnreginet.gov.in",
        "document_types": ["Patta Copy", "Chitta Extract", "Adangal Register", "EC"],
        "sample_survey": "203/2B",
    },
    {
        "state_code": "telangana",
        "state_name": "Telangana",
        "portal_name": "Dharani / Maa Bhoomi",
        "portal_url": "https://dharani.telangana.gov.in",
        "document_types": ["ROR-1B", "Pattadar Passbook", "Encumbrance Certificate"],
        "sample_survey": "150/3",
    },
    {
        "state_code": "gujarat",
        "state_name": "Gujarat",
        "portal_name": "AnyRoR / Bhulekh Gujarat",
        "portal_url": "https://anyror.gujarat.gov.in",
        "document_types": ["VF 7/12 (Satbara)", "Village Form 6", "VF 8A"],
        "sample_survey": "456/1",
    },
]


@router.get("/supported")
async def get_supported_portals(ctx: AuthContext = Depends(get_auth_context)):
    """Return all supported state revenue portal connectors and metadata."""
    return {
        "count": len(SUPPORTED_PORTALS_INFO),
        "portals": SUPPORTED_PORTALS_INFO,
    }


@router.post("/search")
async def search_state_portal(
    body: StatePortalQueryRequest,
    ctx: AuthContext = Depends(get_auth_context),
):
    """Execute live land record search against the designated state revenue portal."""
    try:
        portal_state = PortalState(body.state.lower())
    except ValueError:
        valid_states = [s.value for s in PortalState]
        raise HTTPException(400, f"Unsupported state: {body.state}. Supported states: {valid_states}")

    report = await get_comprehensive_land_report(
        survey_number=body.survey_number,
        district=body.district,
        taluk=body.taluk,
        village=body.village,
        state=portal_state,
        mock_mode=True,
    )

    return report


@router.post("/search-all")
async def search_all_state_portals(
    survey_number: str = Query(...),
    district: str = Query(...),
    taluk: str = Query(...),
    village: str = Query(...),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Parallel multi-state search across all 5 state portal connectors."""
    results = await search_all_portals(
        survey_number=survey_number,
        district=district,
        taluk=taluk,
        village=village,
        mock_mode=True,
    )

    serialized = {}
    for state, res in results.items():
        serialized[state.value] = {
            "success": res.success,
            "records_count": len(res.records),
            "records": [
                {
                    "survey_number": r.survey_number,
                    "district": r.district,
                    "owners": r.owner_names,
                    "area_formatted": r.area_formatted,
                    "document_type": r.document_type,
                    "mutations": len(r.mutation_entries),
                    "encumbrances": len(r.encumbrances),
                    "confidence": r.confidence,
                }
                for r in res.records
            ] if res.records else [],
        }

    return {
        "survey_number": survey_number,
        "location": {"district": district, "taluk": taluk, "village": village},
        "states_searched": len(serialized),
        "results": serialized,
    }
