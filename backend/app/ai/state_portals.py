"""State Land Portal Connectors for 5 Major Indian States.

Integrates with official state revenue portals:
- Maharashtra: Mahabhulekh (Satbara/7-12)
- Karnataka: Bhoomi (RTC/Pahani)
- Tamil Nadu: Patta Chitta / TNREGINET
- Telangana: Dharani / Maa Bhoomi
- Gujarat: AnyROR / Bhulekh Gujarat

Each connector provides:
1. Search by survey/gat/khasra number
2. Search by owner name
3. Document retrieval (RTC, 7-12, Patta, etc.)
4. Mutation history
5. Encumbrance certificates

Note: Most state portals don't have official public APIs. This module provides:
- Structured scraping interfaces (with rate limiting)
- Mock implementations for development
- Plugin architecture for future official API integration
"""

import asyncio
import json
import re
import secrets
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx


class PortalState(str, Enum):
    MAHARASHTRA = "maharashtra"
    KARNATAKA = "karnataka"
    TAMIL_NADU = "tamil_nadu"
    TELANGANA = "telangana"
    GUJARAT = "gujarat"


@dataclass
class PortalConfig:
    """Configuration for a state portal."""
    base_url: str
    search_endpoint: str
    document_endpoint: str
    rate_limit_per_minute: int = 30
    timeout_seconds: int = 30
    requires_captcha: bool = False
    requires_session: bool = True


@dataclass
class LandRecord:
    """Standardized land record from any state portal."""
    state: PortalState
    survey_number: str
    district: str
    taluk: str
    village: str
    owner_names: List[str]
    area_sqm: float
    area_formatted: str
    land_type: str
    tenure: str
    document_type: str
    document_reference: str
    mutation_entries: List[Dict[str, Any]] = field(default_factory=list)
    encumbrances: List[Dict[str, Any]] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    confidence: float = 0.0


@dataclass
class PortalSearchResult:
    """Result of a portal search."""
    success: bool
    records: List[LandRecord] = field(default_factory=list)
    error: Optional[str] = None
    query: Optional[Dict[str, Any]] = None
    source_url: Optional[str] = None
    rate_limited: bool = False


class BasePortalConnector(ABC):
    """Abstract base class for state portal connectors."""

    def __init__(self, config: PortalConfig, mock_mode: bool = True):
        self.config = config
        self.mock_mode = mock_mode
        self._last_request_time = 0.0
        self._request_count = 0
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout_seconds,
                headers={"User-Agent": "Mozilla/5.0 (compatible; LegAIQ/1.0; +https://legaiq.in)"}
            )
        return self._client

    async def _rate_limit(self):
        """Enforce rate limiting."""
        if self.mock_mode:
            return
        elapsed = time.time() - self._last_request_time
        min_interval = 60.0 / self.config.rate_limit_per_minute
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request_time = time.time()
        self._request_count += 1

    @abstractmethod
    async def search_by_survey(self, survey_number: str, district: str, taluk: str, village: str, hobli: Optional[str] = None, **kwargs: Any) -> PortalSearchResult:
        """Search land records by survey/gat/khasra number."""
        pass

    async def search_by_survey_number(self, survey_number: str, district: str, taluk: str, village: str, hobli: Optional[str] = None, **kwargs: Any) -> PortalSearchResult:
        """Alias for search_by_survey supporting hobli and extra kwargs."""
        return await self.search_by_survey(survey_number=survey_number, district=district, taluk=taluk, village=village, hobli=hobli, **kwargs)

    @abstractmethod
    async def search_by_owner(self, owner_name: str, district: str, taluk: str, village: Optional[str] = None) -> PortalSearchResult:
        """Search land records by owner name."""
        pass

    @abstractmethod
    async def get_mutation_history(self, survey_number: str, district: str, taluk: str, village: str) -> PortalSearchResult:
        """Get mutation history for a survey number."""
        pass

    @abstractmethod
    async def get_encumbrance_certificate(self, survey_number: str, district: str, taluk: str, village: str, years: int = 30) -> PortalSearchResult:
        """Get encumbrance certificate for a survey number."""
        pass

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    def _create_mock_record(self, survey_number: str, district: str, taluk: str, village: str) -> LandRecord:
        """Create a mock land record for development/testing."""
        # Use secrets for secure random generation - mock data, not cryptographic
        owner_num = secrets.randbelow(100) + 1
        coowner_num = secrets.randbelow(100) + 1
        area_sqm = secrets.randbelow(9000) + 1000
        acres = secrets.randbelow(5) + 1
        gunta = secrets.randbelow(40)
        is_agricultural = secrets.randbelow(10) > 2  # 70% chance
        doc_ref_num = secrets.randbelow(9000) + 1000
        has_encumbrance = secrets.randbelow(2) == 1
        
        return LandRecord(
            state=self.state,
            survey_number=survey_number,
            district=district,
            taluk=taluk,
            village=village,
            owner_names=[f"Mock Owner {owner_num}", f"Co-owner {coowner_num}"],
            area_sqm=area_sqm,
            area_formatted=f"{acres} Acre(s) {gunta} Gunta(s)",
            land_type="Agricultural" if is_agricultural else "Non-Agricultural",
            tenure="Bhumidhari with transferable rights",
            document_type="RTC" if self.state == PortalState.KARNATAKA else "7/12 Extract",
            document_reference=f"DOC/{doc_ref_num}/{datetime.now().year}",
            mutation_entries=[
                {"date": "2020-01-15", "type": "Sale", "from": "Previous Owner", "to": "Current Owner", "doc_ref": "DOC/1234/2020"},
                {"date": "2015-03-22", "type": "Inheritance", "from": "Ancestor", "to": "Previous Owner", "doc_ref": "DOC/5678/2015"},
            ],
            encumbrances=[
                {"type": "Mortgage", "bank": "State Bank of India", "amount": "50,00,000", "date": "2021-06-10"},
            ] if has_encumbrance else [],
            raw_data={"mock": True},
            confidence=0.75,
        )


class MaharashtraPortal(BasePortalConnector):
    """Mahabhulekh (Maharashtra Land Records) Connector.
    
    Portal: https://mahabhulekh.maharashtra.gov.in
    Also known as: Satbara Utara, 7/12 Extract
    """

    state = PortalState.MAHARASHTRA

    def __init__(self, mock_mode: bool = True):
        config = PortalConfig(
            base_url="https://mahabhulekh.maharashtra.gov.in",
            search_endpoint="/api/v1/search",
            document_endpoint="/api/v1/document",
            rate_limit_per_minute=20,
            requires_captcha=True,
        )
        super().__init__(config, mock_mode)

    async def search_by_survey(self, survey_number: str, district: str, taluk: str, village: str, hobli: Optional[str] = None, **kwargs: Any) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)  # Simulate network
            record = self._create_mock_record(survey_number, district, taluk, village)
            record.document_type = "7/12 Extract (Satbara Utara)"
            record.document_reference = f"7-12/{survey_number}/{district}/{taluk}/{village}"
            record.land_type = "Jirayat / Bagayat"
            return PortalSearchResult(success=True, records=[record], query={"survey": survey_number, "district": district, "taluk": taluk, "village": village})

        try:
            client = await self._get_client()
            resp = await client.post(
                urljoin(self.config.base_url, self.config.search_endpoint),
                json={
                    "survey_number": survey_number,
                    "district": district,
                    "taluka": taluk,
                    "village": village,
                    "document_type": "7_12"
                }
            )
            resp.raise_for_status()
            data = resp.json()
            records = self._parse_maharashtra_response(data)
            return PortalSearchResult(success=True, records=records, query={"survey": survey_number})
        except Exception as e:
            return PortalSearchResult(success=False, error=str(e), query={"survey": survey_number})

    async def search_by_owner(self, owner_name: str, district: str, taluk: str, village: Optional[str] = None) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)
            record = self._create_mock_record(f"OWNER-{owner_name[:10]}", district, taluk, village or "")
            record.owner_names = [owner_name]
            return PortalSearchResult(success=True, records=[record], query={"owner": owner_name, "district": district, "taluk": taluk, "village": village})

        # Real implementation would use owner search endpoint
        return PortalSearchResult(success=False, error="Owner search not implemented for Maharashtra API", query={"owner": owner_name})

    async def get_mutation_history(self, survey_number: str, district: str, taluk: str, village: str) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)
            record = self._create_mock_record(survey_number, district, taluk, village)
            record.mutation_entries = [
                {"date": "2022-08-15", "type": "Sale", "from": "Seller Name", "to": "Buyer Name", "doc_ref": f"DOC/{survey_number}/2022", "area": "2 Acres 10 Guntas"},
                {"date": "2018-11-03", "type": "Partition", "from": "Joint Family", "to": "Individual Shares", "doc_ref": f"PART/{survey_number}/2018", "area": "4 Acres 20 Guntas"},
                {"date": "2010-04-20", "type": "Inheritance", "from": "Father", "to": "Sons", "doc_ref": f"INH/{survey_number}/2010", "area": "4 Acres 20 Guntas"},
            ]
            return PortalSearchResult(success=True, records=[record], query={"survey": survey_number, "type": "mutation"})

        return PortalSearchResult(success=False, error="Mutation API not available", query={"survey": survey_number})

    async def get_encumbrance_certificate(self, survey_number: str, district: str, taluk: str, village: str, years: int = 30) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)
            record = self._create_mock_record(survey_number, district, taluk, village)
            record.encumbrances = [
                {"type": "Mortgage", "bank": "Bank of Maharashtra", "amount": "25,00,000", "date": "2023-01-10", "status": "Active", "doc_ref": "MORT/2023/001"},
                {"type": "Charge", "bank": "HDFC Bank", "amount": "15,00,000", "date": "2021-05-20", "status": "Released", "doc_ref": "CHG/2021/045"},
            ]
            return PortalSearchResult(success=True, records=[record], query={"survey": survey_number, "type": "encumbrance", "years": years})

        return PortalSearchResult(success=False, error="EC API not available", query={"survey": survey_number})

    def _parse_maharashtra_response(self, data: Dict) -> List[LandRecord]:
        """Parse Maharashtra portal API response."""
        records = []
        for item in data.get("records", []):
            records.append(LandRecord(
                state=self.state,
                survey_number=item.get("survey_no", ""),
                district=item.get("district", ""),
                taluk=item.get("taluka", ""),
                village=item.get("village", ""),
                owner_names=item.get("owners", []),
                area_sqm=float(item.get("area_sqm", 0)),
                area_formatted=item.get("area_display", ""),
                land_type=item.get("land_type", ""),
                tenure=item.get("tenure", ""),
                document_type="7/12 Extract",
                document_reference=item.get("doc_ref", ""),
                mutation_entries=item.get("mutations", []),
                encumbrances=item.get("encumbrances", []),
                raw_data=item,
                confidence=0.9,
            ))
        return records


class KarnatakaPortal(BasePortalConnector):
    """Bhoomi Karnataka (RTC/Pahani) Connector.
    
    Portal: https://bhoomi.karnataka.gov.in
    Document: RTC (Record of Rights, Tenancy and Crops) / Pahani
    """

    state = PortalState.KARNATAKA

    def __init__(self, mock_mode: bool = True):
        config = PortalConfig(
            base_url="https://bhoomi.karnataka.gov.in",
            search_endpoint="/api/v1/rtc/search",
            document_endpoint="/api/v1/rtc/document",
            rate_limit_per_minute=25,
        )
        super().__init__(config, mock_mode)

    async def search_by_survey(self, survey_number: str, district: str, taluk: str, village: str, hobli: Optional[str] = None, **kwargs: Any) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)
            record = self._create_mock_record(survey_number, district, taluk, village)
            record.document_type = "RTC (Record of Rights, Tenancy and Crops)"
            record.document_reference = f"RTC/{district}/{taluk}/{village}/{survey_number}"
            record.land_type = "Dry / Wet / Garden"
            record.tenure = "Bhumidhari / Gair Bhumidhari"
            record.raw_data["phodi_khasra"] = f"{survey_number}/1"
            return PortalSearchResult(success=True, records=[record], query={"survey": survey_number})

        return PortalSearchResult(success=False, error="Karnataka Bhoomi API not publicly available", query={"survey": survey_number})

    async def search_by_owner(self, owner_name: str, district: str, taluk: str, village: Optional[str] = None) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)
            record = self._create_mock_record(f"OWNER-{owner_name[:10]}", district, taluk, village or "")
            record.owner_names = [owner_name]
            record.document_type = "RTC (Record of Rights, Tenancy and Crops)"
            return PortalSearchResult(success=True, records=[record], query={"owner": owner_name})

        return PortalSearchResult(success=False, error="Owner search not implemented", query={"owner": owner_name})

    async def get_mutation_history(self, survey_number: str, district: str, taluk: str, village: str) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)
            record = self._create_mock_record(survey_number, district, taluk, village)
            record.mutation_entries = [
                {"date": "2023-02-10", "type": "Transfer", "from": "Seller", "to": "Buyer", "doc_ref": f"MR/{survey_number}/2023", "extent": "1.5 Acres"},
                {"date": "2019-07-18", "type": "Partition", "from": "Joint Owners", "to": "Individual", "doc_ref": f"MR/{survey_number}/2019", "extent": "3.0 Acres"},
            ]
            return PortalSearchResult(success=True, records=[record], query={"survey": survey_number, "type": "mutation"})

        return PortalSearchResult(success=False, error="Mutation API not available", query={"survey": survey_number})

    async def get_encumbrance_certificate(self, survey_number: str, district: str, taluk: str, village: str, years: int = 30) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)
            record = self._create_mock_record(survey_number, district, taluk, village)
            record.encumbrances = [
                {"type": "Bank Charge", "bank": "Canara Bank", "amount": "30,00,000", "date": "2022-11-05", "status": "Active", "doc_ref": "BC/2022/001"},
            ]
            return PortalSearchResult(success=True, records=[record], query={"survey": survey_number, "type": "encumbrance", "years": years})

        return PortalSearchResult(success=False, error="EC API not available", query={"survey": survey_number})


class TamilNaduPortal(BasePortalConnector):
    """TNREGINET / Patta Chitta Connector.
    
    Portal: https://tnreginet.gov.in
    Documents: Patta (Ownership), Chitta (Area/Classification), Adangal (Cultivation)
    """

    state = PortalState.TAMIL_NADU

    def __init__(self, mock_mode: bool = True):
        config = PortalConfig(
            base_url="https://tnreginet.gov.in",
            search_endpoint="/api/v1/patta/search",
            document_endpoint="/api/v1/patta/document",
            rate_limit_per_minute=20,
        )
        super().__init__(config, mock_mode)

    async def search_by_survey(self, survey_number: str, district: str, taluk: str, village: str, hobli: Optional[str] = None, **kwargs: Any) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)
            record = self._create_mock_record(survey_number, district, taluk, village)
            record.document_type = "Patta + Chitta + Adangal"
            record.document_reference = f"PATTA/{district}/{taluk}/{village}/{survey_number}"
            record.land_type = "Nanjai / Punjai / Manai"
            record.tenure = "Ryotwari / Inam"
            record.area_formatted = f"{round(record.area_sqm / 4046.86, 2)} Acres ({round(record.area_sqm, 1)} Sq.M)"
            return PortalSearchResult(success=True, records=[record], query={"survey": survey_number})

        return PortalSearchResult(success=False, error="TNREGINET API not publicly available", query={"survey": survey_number})

    async def search_by_owner(self, owner_name: str, district: str, taluk: str, village: Optional[str] = None) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)
            record = self._create_mock_record(f"OWNER-{owner_name[:10]}", district, taluk, village or "")
            record.owner_names = [owner_name]
            record.document_type = "Patta"
            return PortalSearchResult(success=True, records=[record], query={"owner": owner_name})

        return PortalSearchResult(success=False, error="Owner search not implemented", query={"owner": owner_name})

    async def get_mutation_history(self, survey_number: str, district: str, taluk: str, village: str) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)
            record = self._create_mock_record(survey_number, district, taluk, village)
            record.mutation_entries = [
                {"date": "2021-09-25", "type": "Name Change", "from": "Old Name", "to": "New Name", "doc_ref": f"PATTA/{survey_number}/2021", "order": "Taluk Order 123/2021"},
                {"date": "2016-02-14", "type": "Subdivision", "from": "Parent Survey", "to": f"Child Surveys: {survey_number}/1, {survey_number}/2", "doc_ref": f"SUB/{survey_number}/2016"},
            ]
            return PortalSearchResult(success=True, records=[record], query={"survey": survey_number, "type": "mutation"})

        return PortalSearchResult(success=False, error="Mutation API not available", query={"survey": survey_number})

    async def get_encumbrance_certificate(self, survey_number: str, district: str, taluk: str, village: str, years: int = 30) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)
            record = self._create_mock_record(survey_number, district, taluk, village)
            record.encumbrances = [
                {"type": "Mortgage", "bank": "Indian Bank", "amount": "40,00,000", "date": "2022-03-15", "status": "Active", "doc_ref": "MORT/2022/001"},
                {"type": "Lease", "lessee": "Tamil Nadu Power Corp", "amount": "Annual: 2,00,000", "date": "2019-01-01", "status": "Active", "doc_ref": "LEASE/2019/001"},
            ]
            return PortalSearchResult(success=True, records=[record], query={"survey": survey_number, "type": "encumbrance", "years": years})

        return PortalSearchResult(success=False, error="EC API not available", query={"survey": survey_number})


class TelanganaPortal(BasePortalConnector):
    """Dharani / Maa Bhoomi Telangana Connector.
    
    Portal: https://dharani.telangana.gov.in
    Documents: Pattadar Passbook, Title Deed, ROR-1B
    """

    state = PortalState.TELANGANA

    def __init__(self, mock_mode: bool = True):
        config = PortalConfig(
            base_url="https://dharani.telangana.gov.in",
            search_endpoint="/api/v1/ror/search",
            document_endpoint="/api/v1/ror/document",
            rate_limit_per_minute=25,
        )
        super().__init__(config, mock_mode)

    async def search_by_survey(self, survey_number: str, district: str, taluk: str, village: str, hobli: Optional[str] = None, **kwargs: Any) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)
            record = self._create_mock_record(survey_number, district, taluk, village)
            record.document_type = "ROR-1B / Pattadar Passbook"
            record.document_reference = f"ROR1B/{district}/{taluk}/{village}/{survey_number}"
            record.land_type = "Assigned / Patta / Govt Land"
            record.tenure = "Pattadar / Assigned / Govt"
            record.area_formatted = f"{round(record.area_sqm / 4046.86, 2)} Acres ({round(record.area_sqm, 1)} Sq.M)"
            return PortalSearchResult(success=True, records=[record], query={"survey": survey_number})

        return PortalSearchResult(success=False, error="Dharani API not publicly available", query={"survey": survey_number})

    async def search_by_owner(self, owner_name: str, district: str, taluk: str, village: Optional[str] = None) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)
            record = self._create_mock_record(f"OWNER-{owner_name[:10]}", district, taluk, village or "")
            record.owner_names = [owner_name]
            record.document_type = "Pattadar Passbook"
            return PortalSearchResult(success=True, records=[record], query={"owner": owner_name})

        return PortalSearchResult(success=False, error="Owner search not implemented", query={"owner": owner_name})

    async def get_mutation_history(self, survey_number: str, district: str, taluk: str, village: str) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)
            record = self._create_mock_record(survey_number, district, taluk, village)
            record.mutation_entries = [
                {"date": "2022-12-01", "type": "Mutation", "from": "Previous Pattadar", "to": "Current Pattadar", "doc_ref": f"MUT/{survey_number}/2022", "extent": "2.5 Acres"},
            ]
            return PortalSearchResult(success=True, records=[record], query={"survey": survey_number, "type": "mutation"})

        return PortalSearchResult(success=False, error="Mutation API not available", query={"survey": survey_number})

    async def get_encumbrance_certificate(self, survey_number: str, district: str, taluk: str, village: str, years: int = 30) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)
            record = self._create_mock_record(survey_number, district, taluk, village)
            record.encumbrances = [
                {"type": "Agricultural Loan", "bank": "Telangana Grameena Bank", "amount": "10,00,000", "date": "2023-06-15", "status": "Active", "doc_ref": "AL/2023/001"},
            ]
            return PortalSearchResult(success=True, records=[record], query={"survey": survey_number, "type": "encumbrance", "years": years})

        return PortalSearchResult(success=False, error="EC API not available", query={"survey": survey_number})


class GujaratPortal(BasePortalConnector):
    """AnyROR / Bhulekh Gujarat Connector.
    
    Portal: https://anyror.gujarat.gov.in
    Documents: 7/12 (VF 7/12), 8A, Village Form 6, Property Card
    """

    state = PortalState.GUJARAT

    def __init__(self, mock_mode: bool = True):
        config = PortalConfig(
            base_url="https://anyror.gujarat.gov.in",
            search_endpoint="/api/v1/land/search",
            document_endpoint="/api/v1/land/document",
            rate_limit_per_minute=20,
        )
        super().__init__(config, mock_mode)

    async def search_by_survey(self, survey_number: str, district: str, taluk: str, village: str, hobli: Optional[str] = None, **kwargs: Any) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)
            record = self._create_mock_record(survey_number, district, taluk, village)
            record.document_type = "VF 7/12 (Satbara)"
            record.document_reference = f"VF712/{district}/{taluk}/{village}/{survey_number}"
            record.land_type = "Old Tenure / New Tenure / Gamtal"
            record.tenure = "Bhumidhar / Non-Bhumidhar"
            record.area_formatted = f"{round(record.area_sqm / 4046.86, 2)} Acres ({round(record.area_sqm, 1)} Sq.M)"
            return PortalSearchResult(success=True, records=[record], query={"survey": survey_number})

        return PortalSearchResult(success=False, error="AnyROR API not publicly available", query={"survey": survey_number})

    async def search_by_owner(self, owner_name: str, district: str, taluk: str, village: Optional[str] = None) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)
            record = self._create_mock_record(f"OWNER-{owner_name[:10]}", district, taluk, village or "")
            record.owner_names = [owner_name]
            record.document_type = "VF 7/12"
            return PortalSearchResult(success=True, records=[record], query={"owner": owner_name})

        return PortalSearchResult(success=False, error="Owner search not implemented", query={"owner": owner_name})

    async def get_mutation_history(self, survey_number: str, district: str, taluk: str, village: str) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)
            record = self._create_mock_record(survey_number, district, taluk, village)
            record.mutation_entries = [
                {"date": "2023-04-18", "type": "Varisu (Inheritance)", "from": "Deceased", "to": "Legal Heirs", "doc_ref": f"VARISU/{survey_number}/2023", "extent": "3.0 Acres"},
                {"date": "2017-08-22", "type": "Sale Deed", "from": "Seller", "to": "Buyer", "doc_ref": f"SALE/{survey_number}/2017", "extent": "3.0 Acres"},
            ]
            return PortalSearchResult(success=True, records=[record], query={"survey": survey_number, "type": "mutation"})

        return PortalSearchResult(success=False, error="Mutation API not available", query={"survey": survey_number})

    async def get_encumbrance_certificate(self, survey_number: str, district: str, taluk: str, village: str, years: int = 30) -> PortalSearchResult:
        await self._rate_limit()
        
        if self.mock_mode:
            await asyncio.sleep(0.1)
            record = self._create_mock_record(survey_number, district, taluk, village)
            record.encumbrances = [
                {"type": "Mortgage", "bank": "Bank of Baroda", "amount": "35,00,000", "date": "2022-09-10", "status": "Active", "doc_ref": "MORT/2022/001"},
            ]
            return PortalSearchResult(success=True, records=[record], query={"survey": survey_number, "type": "encumbrance", "years": years})

        return PortalSearchResult(success=False, error="EC API not available", query={"survey": survey_number})


# ============================================================================
# Connector Aliases
# ============================================================================

MahabhulekhConnector = MaharashtraPortal
BhoomiConnector = KarnatakaPortal
TNREGINETConnector = TamilNaduPortal
DharaniConnector = TelanganaPortal
AnyRoRConnector = GujaratPortal


# ============================================================================
# Portal Registry & Factory
# ============================================================================

_PORTAL_REGISTRY: Dict[PortalState, type] = {
    PortalState.MAHARASHTRA: MaharashtraPortal,
    PortalState.KARNATAKA: KarnatakaPortal,
    PortalState.TAMIL_NADU: TamilNaduPortal,
    PortalState.TELANGANA: TelanganaPortal,
    PortalState.GUJARAT: GujaratPortal,
}


def get_portal_connector(state: PortalState | str, mock_mode: bool = True) -> BasePortalConnector:
    """Factory function to get portal connector for a state."""
    if isinstance(state, str):
        state_clean = state.lower().strip().replace(" ", "_").replace("-", "_")
        for ps in PortalState:
            if ps.value == state_clean or ps.name.lower() == state_clean:
                state = ps
                break
        else:
            abbr_map = {
                "mh": PortalState.MAHARASHTRA,
                "ka": PortalState.KARNATAKA,
                "tn": PortalState.TAMIL_NADU,
                "ts": PortalState.TELANGANA,
                "tg": PortalState.TELANGANA,
                "gj": PortalState.GUJARAT,
            }
            if state_clean in abbr_map:
                state = abbr_map[state_clean]
            else:
                raise ValueError(f"No portal connector available for state: {state}")

    connector_class = _PORTAL_REGISTRY.get(state)
    if not connector_class:
        raise ValueError(f"No portal connector available for state: {state}")
    return connector_class(mock_mode=mock_mode)


class StatePortalFactory:
    """Factory for creating state portal connectors."""

    @staticmethod
    def get_connector(state: PortalState | str, mock_mode: bool = True) -> BasePortalConnector:
        return get_portal_connector(state, mock_mode=mock_mode)


async def search_all_portals(
    survey_number: str,
    district: str,
    taluk: str,
    village: str,
    states: Optional[List[PortalState]] = None,
    mock_mode: bool = True
) -> Dict[PortalState, PortalSearchResult]:
    """Search across multiple state portals in parallel."""
    if states is None:
        states = list(PortalState)
    
    async def search_state(state: PortalState) -> tuple:
        connector = get_portal_connector(state, mock_mode)
        try:
            result = await connector.search_by_survey(survey_number, district, taluk, village)
            return (state, result)
        finally:
            await connector.close()
    
    results = await asyncio.gather(*[search_state(s) for s in states], return_exceptions=True)
    
    output = {}
    for result in results:
        if isinstance(result, tuple):
            state, search_result = result
            output[state] = search_result
        elif isinstance(result, Exception):
            # Handle exception - find which state failed
            pass
    
    return output


async def get_comprehensive_land_report(
    survey_number: str,
    district: str,
    taluk: str,
    village: str,
    state: PortalState,
    mock_mode: bool = True
) -> Dict[str, Any]:
    """Get comprehensive land report from a state portal including mutations and encumbrances."""
    connector = get_portal_connector(state, mock_mode)
    
    try:
        # Parallel fetch of all data
        base_task = connector.search_by_survey(survey_number, district, taluk, village)
        mutation_task = connector.get_mutation_history(survey_number, district, taluk, village)
        ec_task = connector.get_encumbrance_certificate(survey_number, district, taluk, village, years=30)
        
        base_result, mutation_result, ec_result = await asyncio.gather(
            base_task, mutation_task, ec_task, return_exceptions=True
        )
        
        return {
            "state": state.value,
            "survey_number": survey_number,
            "location": {"district": district, "taluk": taluk, "village": village},
            "base_record": base_result.records[0] if isinstance(base_result, PortalSearchResult) and base_result.success and base_result.records else None,
            "mutation_history": mutation_result.records[0].mutation_entries if isinstance(mutation_result, PortalSearchResult) and mutation_result.success and mutation_result.records else [],
            "encumbrances": ec_result.records[0].encumbrances if isinstance(ec_result, PortalSearchResult) and ec_result.success and ec_result.records else [],
            "errors": {
                "base": base_result.error if isinstance(base_result, PortalSearchResult) and not base_result.success else None,
                "mutation": mutation_result.error if isinstance(mutation_result, PortalSearchResult) and not mutation_result.success else None,
                "encumbrance": ec_result.error if isinstance(ec_result, PortalSearchResult) and not ec_result.success else None,
            },
            "fetched_at": datetime.now(UTC).isoformat(),
            "mock_mode": mock_mode,
        }
    finally:
        await connector.close()


# ============================================================================
# Integration with Land Intelligence
# ============================================================================

def enrich_entities_with_portal_data(
    entities: List[Dict[str, Any]],
    district: str,
    taluk: str,
    village: str,
    state: PortalState,
    mock_mode: bool = True
) -> List[Dict[str, Any]]:
    """Enrich extracted entities with live portal data.
    
    This function can be called from the extraction pipeline to augment
    regex/LLM-extracted entities with official portal records.
    """
    # Extract survey numbers from entities
    survey_numbers = []
    for entity in entities:
        if entity.get("entity_type") in ("survey_number", "gat_number", "khasra_number", "cts_number"):
            survey_numbers.append(entity["value"])
    
    if not survey_numbers:
        return entities
    
    # For now, return original entities (async enrichment would need pipeline integration)
    # Full async integration would be done in the worker pipeline
    return entities


# ============================================================================
# Example Usage / Testing
# ============================================================================

async def _demo():
    """Demo function showing how to use the portal connectors."""
    # Test Maharashtra
    print("Testing Maharashtra Portal...")
    mh = MaharashtraPortal(mock_mode=True)
    result = await mh.search_by_survey("124/2", "Bangalore Urban", "Whitefield", "Varthur")
    print(f"  Success: {result.success}, Records: {len(result.records)}")
    if result.records:
        r = result.records[0]
        print(f"  Owner: {r.owner_names}, Area: {r.area_formatted}, Type: {r.document_type}")
    await mh.close()
    
    # Test Karnataka
    print("\nTesting Karnataka Portal...")
    ka = KarnatakaPortal(mock_mode=True)
    result = await ka.search_by_survey("45/1A", "Bangalore Urban", "Yelahanka", "Attur")
    print(f"  Success: {result.success}, Records: {len(result.records)}")
    if result.records:
        r = result.records[0]
        print(f"  Owner: {r.owner_names}, Area: {r.area_formatted}, Type: {r.document_type}")
    await ka.close()
    
    # Test Tamil Nadu
    print("\nTesting Tamil Nadu Portal...")
    tn = TamilNaduPortal(mock_mode=True)
    result = await tn.search_by_survey("203/2B", "Chennai", "Ambattur", "Ambattur")
    print(f"  Success: {result.success}, Records: {len(result.records)}")
    if result.records:
        r = result.records[0]
        print(f"  Owner: {r.owner_names}, Area: {r.area_formatted}, Type: {r.document_type}")
    await tn.close()
    
    # Test Telangana
    print("\nTesting Telangana Portal...")
    tg = TelanganaPortal(mock_mode=True)
    result = await tg.search_by_survey("150/3", "Hyderabad", "Shamshabad", "Mongal")
    print(f"  Success: {result.success}, Records: {len(result.records)}")
    if result.records:
        r = result.records[0]
        print(f"  Owner: {r.owner_names}, Area: {r.area_formatted}, Type: {r.document_type}")
    await tg.close()
    
    # Test Gujarat
    print("\nTesting Gujarat Portal...")
    gj = GujaratPortal(mock_mode=True)
    result = await gj.search_by_survey("456/1", "Ahmedabad", "Daskroi", "Bopal")
    print(f"  Success: {result.success}, Records: {len(result.records)}")
    if result.records:
        r = result.records[0]
        print(f"  Owner: {r.owner_names}, Area: {r.area_formatted}, Type: {r.document_type}")
    await gj.close()
    
    # Test comprehensive report
    print("\nTesting Comprehensive Report (Maharashtra)...")
    report = await get_comprehensive_land_report(
        "124/2", "Bangalore Urban", "Whitefield", "Varthur",
        PortalState.MAHARASHTRA, mock_mode=True
    )
    print(f"  Base Record: {report['base_record'] is not None}")
    print(f"  Mutations: {len(report['mutation_history'])}")
    print(f"  Encumbrances: {len(report['encumbrances'])}")


if __name__ == "__main__":
    asyncio.run(_demo())