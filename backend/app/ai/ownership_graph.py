"""13-30 Year Ownership Chain Directed Acyclic Graph (DAG) & Title Break Analyzer.

Reconstructs chronological legal title flow across 13 to 30+ years, tracks encumbrance
timelines, and detects title breaks, missing link deeds, and unregistered charges.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class LinkType(str, Enum):
    SALE_DEED = "SALE_DEED"
    PARTITION_DEED = "PARTITION_DEED"
    GIFT_DEED = "GIFT_DEED"
    INHERITANCE_MUTATION = "INHERITANCE_MUTATION"
    MORTGAGE_CHARGE = "MORTGAGE_CHARGE"
    RELEASE_DEED = "RELEASE_DEED"
    COURT_DECREE = "COURT_DECREE"
    RELINQUISHMENT = "RELINQUISHMENT"
    SETTLEMENT = "SETTLEMENT"
    GOVT_GRANT = "GOVT_GRANT"


CONVEYANCE_TYPES = {
    LinkType.SALE_DEED,
    LinkType.PARTITION_DEED,
    LinkType.GIFT_DEED,
    LinkType.INHERITANCE_MUTATION,
    LinkType.COURT_DECREE,
    LinkType.RELINQUISHMENT,
    LinkType.SETTLEMENT,
    LinkType.GOVT_GRANT,
}

ENCUMBRANCE_TYPES = {
    LinkType.MORTGAGE_CHARGE,
    LinkType.RELEASE_DEED,
}


class TitleBreakSeverity(str, Enum):
    CRITICAL = "CRITICAL"  # Fatal title defect (e.g. total lack of conveyance, pending stay)
    HIGH = "HIGH"          # Severe break (e.g. missing intermediate sale deed)
    MEDIUM = "MEDIUM"      # Discrepancy (e.g. missing mutation entry, survey number sub-division)
    LOW = "LOW"            # Procedural defect (e.g. minor spelling difference in party name)


@dataclass
class TitleBreakAlert:
    id: str
    severity: TitleBreakSeverity
    break_type: str
    title: str
    description: str
    affected_nodes: List[str]
    period: Optional[str] = None
    recommended_remedy: str = ""
    evidence_source: Optional[str] = None


@dataclass
class OwnershipNode:
    id: str
    label: str
    node_type: str  # PERSON | ENTITY | FINANCIAL_INSTITUTION | GOVERNMENT | PROPERTY
    holding_extent: Optional[str] = None
    year_acquired: Optional[int] = None
    verified_identity: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OwnershipEdge:
    id: str
    source_id: str
    target_id: str
    link_type: LinkType
    event_date: Optional[str] = None
    document_number: Optional[str] = None
    sro_location: Optional[str] = None
    consideration_amount: Optional[str] = None
    confidence: float = 0.9
    evidence: List[Dict[str, Any]] = field(default_factory=list)


class OwnershipChainAnalyzer:
    """Reconstructs and analyzes multi-decade ownership chain graphs."""

    @classmethod
    def build_chain_dag(
        cls,
        case_id: str,
        events: List[Dict[str, Any]],
        entities: List[Dict[str, Any]],
        risks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build DAG nodes, edges, chronological sequence, and detect breaks."""
        nodes: Dict[str, OwnershipNode] = {}
        edges: List[OwnershipEdge] = []
        breaks: List[TitleBreakAlert] = []

        # Sort timeline events chronologically
        sorted_events = sorted(
            events,
            key=lambda e: str(e.get("event_date") or e.get("sort_date") or "1900-01-01"),
        )

        for i, ev in enumerate(sorted_events):
            from_owner = ev.get("from_owner") or ev.get("transferor") or "Prior Owner"
            to_owner = ev.get("to_owner") or ev.get("transferee") or "Subsequent Owner"
            t_type_raw = (ev.get("transaction_type") or "SALE").upper()
            
            # Map transaction type
            link_type = LinkType.SALE_DEED
            if "PARTITION" in t_type_raw:
                link_type = LinkType.PARTITION_DEED
            elif "GIFT" in t_type_raw:
                link_type = LinkType.GIFT_DEED
            elif "INHERIT" in t_type_raw or "MUTATION" in t_type_raw:
                link_type = LinkType.INHERITANCE_MUTATION
            elif "MORTGAGE" in t_type_raw or "CHARGE" in t_type_raw:
                link_type = LinkType.MORTGAGE_CHARGE
            elif "RELEASE" in t_type_raw or "RECONVEYANCE" in t_type_raw:
                link_type = LinkType.RELEASE_DEED
            elif "COURT" in t_type_raw or "DECREE" in t_type_raw:
                link_type = LinkType.COURT_DECREE

            src_id = f"node_{abs(hash(from_owner)) % 100000}"
            tgt_id = f"node_{abs(hash(to_owner)) % 100000}"

            src_node_type = "FINANCIAL_INSTITUTION" if link_type == LinkType.RELEASE_DEED else "PERSON"
            tgt_node_type = "FINANCIAL_INSTITUTION" if link_type == LinkType.MORTGAGE_CHARGE else "PERSON"

            if src_id not in nodes:
                nodes[src_id] = OwnershipNode(id=src_id, label=from_owner, node_type=src_node_type)
            if tgt_id not in nodes:
                nodes[tgt_id] = OwnershipNode(id=tgt_id, label=to_owner, node_type=tgt_node_type)

            edge_id = f"edge_{i}_{src_id}_{tgt_id}"
            edges.append(OwnershipEdge(
                id=edge_id,
                source_id=src_id,
                target_id=tgt_id,
                link_type=link_type,
                event_date=ev.get("event_date") or ev.get("sort_date"),
                document_number=ev.get("document_number"),
                sro_location=ev.get("sro"),
                consideration_amount=ev.get("consideration"),
                confidence=0.95 if ev.get("verified") else 0.85,
                evidence=[{
                    "document_name": ev.get("document_name", "Document"),
                    "page_number": ev.get("page_number", 1),
                    "source_text": ev.get("description", ""),
                    "citation": f"[Doc: {ev.get('document_name', 'Document')}, Pg: {ev.get('page_number', 1)}]",
                }],
            ))

        # Separate conveyance / title transfer events from encumbrances
        conveyance_events = [
            ev for ev in sorted_events
            if not any(kw in (ev.get("transaction_type") or "").upper() for kw in ("MORTGAGE", "CHARGE", "RELEASE", "RECONVEYANCE"))
        ]

        # 1. Check for title chain continuity breaks ONLY on conveyance sequence
        if len(conveyance_events) >= 2:
            for idx in range(len(conveyance_events) - 1):
                curr_ev = conveyance_events[idx]
                next_ev = conveyance_events[idx + 1]
                
                curr_buyer = (curr_ev.get("to_owner") or "").strip().lower()
                next_seller = (next_ev.get("from_owner") or "").strip().lower()

                if curr_buyer and next_seller and curr_buyer != next_seller:
                    # Check for partial name match (e.g. John Doe vs John A. Doe)
                    if not (curr_buyer in next_seller or next_seller in curr_buyer):
                        breaks.append(TitleBreakAlert(
                            id=f"break_{idx}",
                            severity=TitleBreakSeverity.HIGH,
                            break_type="MISSING_INTERMEDIATE_LINK",
                            title="Unbroken Title Chain Discontinuity",
                            description=(
                                f"Gap in ownership flow: '{curr_ev.get('to_owner')}' acquired title on {curr_ev.get('event_date')}, "
                                f"but subsequent conveyance on {next_ev.get('event_date')} is executed by '{next_ev.get('from_owner')}'. "
                                "Missing intermediate registered link deed or succession certificate."
                            ),
                            affected_nodes=[curr_buyer, next_seller],
                            period=f"{curr_ev.get('event_date')} to {next_ev.get('event_date')}",
                            recommended_remedy="Call for certified copies of intervening Link Deeds from SRO.",
                        ))

        # 2. Directed Cycle Detection (DFS/Tarjan) to catch circular title transfers (e.g. A -> B -> C -> A)
        conveyance_adj: Dict[str, List[str]] = {nid: [] for nid in nodes}
        for e in edges:
            if e.link_type in CONVEYANCE_TYPES:
                conveyance_adj[e.source_id].append(e.target_id)

        visited_state: Dict[str, int] = {nid: 0 for nid in nodes}  # 0=unvisited, 1=visiting (on stack), 2=visited
        path: List[str] = []
        cycle_detected_paths: List[List[str]] = []

        def dfs_cycle(u: str):
            visited_state[u] = 1
            path.append(u)
            for v in conveyance_adj.get(u, []):
                if v == u:
                    cycle_detected_paths.append([u, u])
                elif visited_state.get(v, 0) == 1:
                    # Cycle found
                    cycle_idx = path.index(v)
                    cycle_detected_paths.append(path[cycle_idx:] + [v])
                elif visited_state.get(v, 0) == 0:
                    dfs_cycle(v)
            path.pop()
            visited_state[u] = 2

        for nid in list(nodes.keys()):
            if visited_state.get(nid, 0) == 0:
                dfs_cycle(nid)

        for c_idx, cycle_nodes in enumerate(cycle_detected_paths):
            labels = [nodes[nid].label for nid in cycle_nodes if nid in nodes]
            cycle_desc = " -> ".join(labels) if labels else "Unknown nodes"
            breaks.append(TitleBreakAlert(
                id=f"break_cycle_{c_idx}",
                severity=TitleBreakSeverity.CRITICAL,
                break_type="CIRCULAR_TRANSFER_DETECTED",
                title="Circular Title Transfer Detected",
                description=f"Circular conveyance cycle detected: {cycle_desc}. Title cannot legally transfer in a closed loop cycle without invalidating bona fide ownership flow.",
                affected_nodes=cycle_nodes,
                recommended_remedy="Investigate sham transactions, title fraud, or cross-conveyance validity.",
            ))

        # 3. Institution/lender-specific mortgage matching
        active_mortgages: Dict[str, List[Dict[str, Any]]] = {}

        for ev in sorted_events:
            t_type = (ev.get("transaction_type") or "").upper()
            if "MORTGAGE" in t_type or "CHARGE" in t_type:
                lender = (ev.get("bank") or ev.get("lender") or ev.get("to_owner") or ev.get("financial_institution") or "Unknown Lender").strip()
                lender_key = re.sub(r"[^a-zA-Z0-9]", "", lender.lower())
                if lender_key not in active_mortgages:
                    active_mortgages[lender_key] = []
                active_mortgages[lender_key].append({
                    "lender_name": lender,
                    "event": ev,
                })
            elif "RELEASE" in t_type or "RECONVEYANCE" in t_type:
                releasing_lender = (ev.get("bank") or ev.get("lender") or ev.get("from_owner") or ev.get("financial_institution") or "").strip()
                releasing_key = re.sub(r"[^a-zA-Z0-9]", "", releasing_lender.lower())
                
                # Match and discharge
                matched_key = None
                if releasing_key in active_mortgages and active_mortgages[releasing_key]:
                    matched_key = releasing_key
                else:
                    for k in list(active_mortgages.keys()):
                        if active_mortgages[k] and (k in releasing_key or releasing_key in k):
                            matched_key = k
                            break
                
                if matched_key:
                    active_mortgages[matched_key].pop(0)
                    if not active_mortgages[matched_key]:
                        del active_mortgages[matched_key]

        for lender_key, unreleased_list in active_mortgages.items():
            for m_idx, m_item in enumerate(unreleased_list):
                lender_name = m_item["lender_name"]
                m_ev = m_item["event"]
                breaks.append(TitleBreakAlert(
                    id=f"break_mortgage_{lender_key}_{m_idx}",
                    severity=TitleBreakSeverity.CRITICAL,
                    break_type="UNRELEASED_ENCUMBRANCE",
                    title=f"Active Undischarged Mortgage Detected ({lender_name})",
                    description=(
                        f"Recorded mortgage charge in favor of '{lender_name}' on {m_ev.get('event_date', 'recorded date')} "
                        "is not accompanied by a registered Deed of Reconveyance/Release."
                    ),
                    affected_nodes=[m_ev.get("from_owner") or "Mortgagor", lender_name],
                    period=str(m_ev.get("event_date", "")),
                    recommended_remedy=f"Obtain Bank No-Objection Certificate (NOC) from {lender_name} and register Deed of Release.",
                ))

        # Calculate search span in years
        search_years = 30
        if sorted_events:
            try:
                d_first = int(str(sorted_events[0].get("event_date", "1994"))[:4])
                d_last = int(str(sorted_events[-1].get("event_date", "2024"))[:4])
                search_years = max(1, d_last - d_first)
            except Exception:
                search_years = 30

        has_critical = any(b.severity == TitleBreakSeverity.CRITICAL for b in breaks)
        has_circular = any(b.break_type == "CIRCULAR_TRANSFER_DETECTED" for b in breaks)

        if has_circular or has_critical:
            title_status = "DEFECTIVE"
        elif len(breaks) == 0:
            title_status = "CLEAR"
        else:
            title_status = "CONDITIONAL"

        return {
            "case_id": case_id,
            "search_span_years": search_years,
            "is_30_year_search_complete": search_years >= 30,
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "type": n.node_type,
                    "holding_extent": n.holding_extent,
                }
                for n in nodes.values()
            ],
            "edges": [
                {
                    "id": e.id,
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "link_type": e.link_type.value,
                    "event_date": e.event_date,
                    "document_number": e.document_number,
                    "sro": e.sro_location,
                    "consideration": e.consideration_amount,
                    "confidence": e.confidence,
                    "evidence": e.evidence,
                }
                for e in edges
            ],
            "timeline": sorted_events,
            "gaps": [
                {
                    "id": b.id,
                    "severity": b.severity.value,
                    "break_type": b.break_type,
                    "title": b.title,
                    "description": b.description,
                    "period": b.period,
                    "remedy": b.recommended_remedy,
                }
                for b in breaks
            ],
            "title_status": title_status,
        }
