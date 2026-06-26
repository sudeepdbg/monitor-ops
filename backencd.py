
"""
MSC Monitor Ops - AI Assisted Operations Support
Final lightweight backend.py

Purpose
-------
This backend keeps the original FastAPI API contract, but removes heavy compiled
ML dependencies such as scikit-learn, numpy and pandas. It is designed to avoid
slow/failing installs on environments that use newer Python versions such as
Python 3.14.

Run locally
-----------
pip install fastapi uvicorn pydantic
uvicorn backend:app --reload --port 8000

Core safeguards
---------------
1. No unsupported recommendations are generated.
2. Guidance is shown only when approved evidence exists.
3. Every recommendation includes citations, confidence, version and source lineage.
4. Low-confidence or no-evidence cases are escalated.
5. Documentation gaps and stale sources are captured as measurable signals.
"""

from __future__ import annotations

from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple
import re
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

RECOMMEND_THRESHOLD = 80
INVESTIGATE_THRESHOLD = 50
STALE_DOC_DAYS = 365

APPROVED_SOURCE_TYPES = {"Runbook", "SOP", "KB Article", "RCA", "Postmortem"}

# -----------------------------------------------------------------------------
# Seed Data
# In production, replace these with ServiceNow/Jira/SharePoint/Confluence/etc.
# connectors. Keeping seed data in-code makes this file deployable as-is.
# -----------------------------------------------------------------------------

KNOWLEDGE: List[Dict[str, Any]] = [
    {
        "id": "KB-1248",
        "source": "KB Article",
        "title": "Amazon PVC Manifest Validation Failure",
        "version": "v2.3",
        "updated": "2026-05-10",
        "owner": "Distribution",
        "approved": True,
        "workflow": "Distribution",
        "product": "Prism",
        "tags": ["amazon", "pvc", "delivery", "manifest", "validation", "metadata"],
        "content": (
            "When Amazon PVC delivery fails with manifest validation errors, verify package status, "
            "validate generated manifest fields, confirm partner endpoint configuration, and resubmit "
            "the distribution workflow after correcting missing required metadata."
        ),
    },
    {
        "id": "RUN-PRISM-REDLV-52",
        "source": "Runbook",
        "title": "Prism Partner Redelivery",
        "version": "v5.2",
        "updated": "2026-04-11",
        "owner": "Distribution",
        "approved": True,
        "workflow": "Distribution",
        "product": "Prism",
        "tags": ["redelivery", "partner", "prism", "distribution", "manifest"],
        "content": (
            "For Prism partner redelivery issues: check workflow state, verify partner mapping, "
            "validate manifest generation, confirm delivery retry eligibility, then rerun the failed "
            "delivery step only after operator approval."
        ),
    },
    {
        "id": "RCA-2026-004",
        "source": "RCA",
        "title": "PVC Delivery Failures Due to Missing Territory Metadata",
        "version": "v1.0",
        "updated": "2026-03-18",
        "owner": "Distribution",
        "approved": True,
        "workflow": "Distribution",
        "product": "Prism",
        "tags": ["pvc", "metadata", "territory", "amazon", "delivery failure"],
        "content": (
            "A recurring Amazon PVC delivery failure pattern was caused by missing territory metadata "
            "in the distribution manifest. Resolution required metadata correction and workflow "
            "resubmission. Preventive action: add validation before manifest publish."
        ),
    },
    {
        "id": "SOP-LOC-VAL-11",
        "source": "SOP",
        "title": "Localization Validation Triage",
        "version": "v1.1",
        "updated": "2025-02-19",
        "owner": "Localization",
        "approved": True,
        "workflow": "Localization",
        "product": "Pegasus",
        "tags": ["localization", "validation", "subtitle", "audio", "language"],
        "content": (
            "For localization validation failures, compare expected track inventory with delivered "
            "assets, validate language tags, inspect subtitle conformance, and route content gaps to "
            "Localization Operations."
        ),
    },
    {
        "id": "RUN-MAM-STUCK-20",
        "source": "Runbook",
        "title": "Foundry MAM Stuck Workflow Recovery",
        "version": "v2.0",
        "updated": "2024-08-02",
        "owner": "Media Asset Management",
        "approved": True,
        "workflow": "Inventory",
        "product": "Foundry MAM",
        "tags": ["mam", "stuck workflow", "asset", "lock", "inventory"],
        "content": (
            "If a Foundry MAM inventory workflow is stuck, check current processing step, review "
            "latest deployment or active outage, validate asset lock state, and escalate to MAM "
            "Engineering if lock cleanup is required."
        ),
    },
    {
        "id": "KB-RIGHTS-OUT-02",
        "source": "KB Article",
        "title": "Rights Visibility Gap Investigation",
        "version": "v1.0",
        "updated": "2023-10-15",
        "owner": "Rights",
        "approved": True,
        "workflow": "Rights",
        "product": "Rally",
        "tags": ["rights", "visibility", "availability", "window", "sky"],
        "content": (
            "Rights visibility gaps should be investigated by checking availability windows, territory "
            "mappings, partner restrictions, and upstream rights feed completion."
        ),
    },
    {
        "id": "DRAFT-UNAPPROVED-01",
        "source": "Draft Notes",
        "title": "Unofficial Domino Retry Notes",
        "version": "draft",
        "updated": "2026-01-05",
        "owner": "Fulfillment",
        "approved": False,
        "workflow": "Fulfillment",
        "product": "Domino",
        "tags": ["domino", "retry"],
        "content": "Unapproved notes. This source must never be used for operator guidance.",
    },
]

INCIDENTS: List[Dict[str, Any]] = [
    {
        "id": "INC1510021",
        "source": "ServiceNow",
        "title": "Amazon PVC delivery failed manifest validation",
        "workflow": "Distribution",
        "product": "Prism",
        "incident_type": "Delivery Failure",
        "severity": "P2",
        "resolved": True,
        "resolution_success": True,
        "created": "2026-05-11",
        "tags": ["amazon", "pvc", "manifest", "delivery"],
        "resolution": "Corrected missing territory metadata and resubmitted Prism delivery workflow.",
    },
    {
        "id": "INC1521443",
        "source": "ServiceNow",
        "title": "PVC package failed delivery due to invalid manifest",
        "workflow": "Distribution",
        "product": "Prism",
        "incident_type": "Delivery Failure",
        "severity": "P2",
        "resolved": True,
        "resolution_success": True,
        "created": "2026-05-25",
        "tags": ["pvc", "manifest", "validation"],
        "resolution": "Validated package, regenerated manifest, retried delivery step.",
    },
    {
        "id": "INC1532214",
        "source": "Jira",
        "title": "Amazon partner endpoint rejected Prism delivery",
        "workflow": "Distribution",
        "product": "Prism",
        "incident_type": "Partner Configuration",
        "severity": "P3",
        "resolved": True,
        "resolution_success": True,
        "created": "2026-06-02",
        "tags": ["amazon", "partner", "endpoint", "prism"],
        "resolution": "Updated partner mapping and requeued delivery.",
    },
    {
        "id": "INC1539000",
        "source": "ServiceNow",
        "title": "Foundry MAM asset workflow frozen at ingest step",
        "workflow": "Inventory",
        "product": "Foundry MAM",
        "incident_type": "Stuck Workflow",
        "severity": "P2",
        "resolved": True,
        "resolution_success": True,
        "created": "2026-04-04",
        "tags": ["mam", "stuck", "workflow", "lock"],
        "resolution": "Cleared stale lock after MAM Engineering approval.",
    },
    {
        "id": "INC1544120",
        "source": "Jira",
        "title": "Localization validation failed for subtitle track",
        "workflow": "Localization",
        "product": "Pegasus",
        "incident_type": "Validation Failure",
        "severity": "P3",
        "resolved": True,
        "resolution_success": True,
        "created": "2026-04-28",
        "tags": ["localization", "subtitle", "validation"],
        "resolution": "Corrected language tag and reran localization validation.",
    },
    {
        "id": "INC1549999",
        "source": "ServiceNow",
        "title": "Rights availability missing for Sky title",
        "workflow": "Rights",
        "product": "Rally",
        "incident_type": "Visibility Gap",
        "severity": "P3",
        "resolved": False,
        "resolution_success": False,
        "created": "2026-06-13",
        "tags": ["rights", "sky", "visibility"],
        "resolution": "Pending rights feed review.",
    },
]

TICKETS: List[Dict[str, Any]] = [
    {
        "id": "TCK-1001",
        "source": "ServiceNow",
        "status": "Open",
        "title": "Delivery Failed Amazon PVC",
        "description": "Amazon PVC delivery failed from Prism. Error suggests manifest validation issue and missing territory data.",
        "created": "2026-06-20T10:15:00Z",
        "requester": "Distribution Ops",
        "logs": ["manifest_validation_failed", "missing territoryCode", "partner=Amazon PVC"],
        "monitor_context": {
            "workflow_status": "Failed",
            "processing_status": "Delivery blocked",
            "current_step": "Manifest validation",
            "active_incident": "No",
            "recent_deployment": "No",
            "known_outage": "No",
            "partner": "Amazon PVC",
        },
    },
    {
        "id": "TCK-1002",
        "source": "Jira",
        "status": "Assigned",
        "title": "Foundry MAM workflow stuck",
        "description": "Asset inventory workflow has not moved for 90 minutes. Current step shows ingest lock wait.",
        "created": "2026-06-21T08:30:00Z",
        "requester": "Inventory Support",
        "logs": ["lock_wait_timeout", "asset lock active"],
        "monitor_context": {
            "workflow_status": "Delayed",
            "processing_status": "Waiting",
            "current_step": "Asset lock wait",
            "active_incident": "No",
            "recent_deployment": "Yes - MAM worker",
            "known_outage": "No",
            "partner": "Internal",
        },
    },
    {
        "id": "TCK-1003",
        "source": "E-Mail",
        "status": "Open",
        "title": "Unknown Domino fulfillment behavior",
        "description": "Domino fulfillment failed with a new error not found in current KB. No known runbook seems to cover it.",
        "created": "2026-06-22T13:10:00Z",
        "requester": "Fulfillment Ops",
        "logs": ["unknown_error_code=DX-991"],
        "monitor_context": {
            "workflow_status": "Failed",
            "processing_status": "Unknown",
            "current_step": "Package assembly",
            "active_incident": "No",
            "recent_deployment": "No",
            "known_outage": "No",
            "partner": "Max",
        },
    },
    {
        "id": "TCK-1004",
        "source": "ServiceNow",
        "status": "Escalated",
        "title": "Rights visibility gap for Sky package",
        "description": "Sky package is not visible although rights feed appears complete. Need ownership and escalation path.",
        "created": "2026-06-22T15:10:00Z",
        "requester": "Rights Ops",
        "logs": ["availability missing", "partner=Sky"],
        "monitor_context": {
            "workflow_status": "Completed with warning",
            "processing_status": "Visibility gap",
            "current_step": "Rights publish",
            "active_incident": "No",
            "recent_deployment": "No",
            "known_outage": "No",
            "partner": "Sky",
        },
    },
]

OWNERSHIP: List[Dict[str, str]] = [
    {
        "workflow": "Distribution",
        "product": "Prism",
        "owner_team": "Distribution Ops",
        "l2": "Distribution L2",
        "engineering": "Prism Engineering",
        "product_owner": "Prism Product",
        "operations": "MSC Operations",
    },
    {
        "workflow": "Inventory",
        "product": "Foundry MAM",
        "owner_team": "Media Asset Management",
        "l2": "MAM L2",
        "engineering": "MAM Engineering",
        "product_owner": "MAM Product",
        "operations": "MSC Operations",
    },
    {
        "workflow": "Localization",
        "product": "Pegasus",
        "owner_team": "Localization Ops",
        "l2": "Localization L2",
        "engineering": "Pegasus Engineering",
        "product_owner": "Localization Product",
        "operations": "MSC Operations",
    },
    {
        "workflow": "Rights",
        "product": "Rally",
        "owner_team": "Rights Ops",
        "l2": "Rights L2",
        "engineering": "Rally Engineering",
        "product_owner": "Rights Product",
        "operations": "MSC Operations",
    },
    {
        "workflow": "Fulfillment",
        "product": "Domino",
        "owner_team": "Fulfillment Ops",
        "l2": "Fulfillment L2",
        "engineering": "Domino Engineering",
        "product_owner": "Fulfillment Product",
        "operations": "MSC Operations",
    },
]

# -----------------------------------------------------------------------------
# Request Models
# -----------------------------------------------------------------------------

class TicketInput(BaseModel):
    id: Optional[str] = None
    source: str = "Manual"
    status: str = "Open"
    title: str
    description: str
    requester: str = "Operator"
    logs: List[str] = Field(default_factory=list)
    monitor_context: Dict[str, str] = Field(default_factory=dict)


class ChatInput(BaseModel):
    ticket_id: str
    question: str


# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------

app = FastAPI(
    title="MSC Monitor Ops API",
    version="1.0.0-lightweight",
    description="AI-assisted operations support prototype with evidence-grounded guidance.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text).lower()).strip()


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", normalize(text)))


def stringify_doc(doc: Dict[str, Any]) -> str:
    parts = []
    for key in ["title", "workflow", "product", "incident_type", "source", "content", "resolution"]:
        value = doc.get(key)
        if value:
            parts.append(str(value))
    tags = doc.get("tags", [])
    if isinstance(tags, list):
        parts.append(" ".join(tags))
    else:
        parts.append(str(tags))
    return " ".join(parts)


def similarity(query: str, corpus: str) -> float:
    """Lightweight semantic-ish similarity using token overlap + char sequence ratio."""
    q_tokens = tokens(query)
    c_tokens = tokens(corpus)
    if not q_tokens or not c_tokens:
        return 0.0
    jaccard = len(q_tokens & c_tokens) / max(1, len(q_tokens | c_tokens))
    seq = SequenceMatcher(None, normalize(query), normalize(corpus)).ratio()
    return round((0.72 * jaccard) + (0.28 * seq), 3)


def search_docs(
    query: str,
    docs: List[Dict[str, Any]],
    top_k: int = 5,
    approved_only: bool = False,
    min_score: float = 0.035,
) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    for doc in docs:
        if approved_only:
            if not doc.get("approved", True):
                continue
            if doc.get("source") not in APPROVED_SOURCE_TYPES:
                continue
        score = similarity(query, stringify_doc(doc))
        if score >= min_score:
            enriched = dict(doc)
            enriched["score"] = score
            hits.append(enriched)
    return sorted(hits, key=lambda x: x["score"], reverse=True)[:top_k]


KEYWORDS = {
    "workflow": {
        "Distribution": ["delivery", "deliver", "partner", "redelivery", "amazon", "pvc", "distribute", "manifest"],
        "Fulfillment": ["fulfillment", "domino", "package", "assembly"],
        "Acquisition": ["acquisition", "ingest", "source", "received"],
        "Inventory": ["inventory", "mam", "asset", "lock", "foundry"],
        "Localization": ["localization", "subtitle", "audio", "language", "caption"],
        "Rights": ["rights", "availability", "window", "territory", "visibility", "sky"],
    },
    "product": {
        "Prism": ["prism", "amazon", "pvc", "distribution", "manifest"],
        "Domino": ["domino", "fulfillment"],
        "Foundry MAM": ["foundry", "mam", "asset"],
        "Pegasus": ["pegasus", "localization"],
        "Rally": ["rally", "rights", "sky"],
        "Distribute 2.0": ["distribute 2.0", "d2", "distribution"],
    },
    "incident_type": {
        "Stuck Workflow": ["stuck", "frozen", "blocked", "not moved", "waiting", "lock"],
        "Delivery Failure": ["delivery failed", "failed delivery", "delivery", "rejected", "redelivery"],
        "Metadata Issue": ["metadata", "territory", "language tag", "missing field", "missing"],
        "Partner Configuration": ["partner", "endpoint", "mapping", "configuration"],
        "Visibility Gap": ["visibility", "not visible", "availability missing"],
        "Validation Failure": ["validation", "validate", "conformance", "manifest validation"],
    },
}


def keyword_score(text: str, options: Dict[str, List[str]]) -> Tuple[str, float]:
    normalized = normalize(text)
    best_label = list(options.keys())[0]
    best_score = 0.0
    for label, words in options.items():
        raw = 0.0
        for word in words:
            w = normalize(word)
            if w in normalized:
                raw += 2.0 if " " in w else 1.0
        score = min(1.0, raw / max(3.0, len(words) / 2.0))
        if score > best_score:
            best_label, best_score = label, score
    return best_label, best_score


def classify_ticket(ticket: Dict[str, Any]) -> Dict[str, Any]:
    text = " ".join([
        ticket.get("title", ""),
        ticket.get("description", ""),
        " ".join(ticket.get("logs", [])),
    ])

    workflow, workflow_score = keyword_score(text, KEYWORDS["workflow"])
    product, product_score = keyword_score(text, KEYWORDS["product"])
    incident_type, incident_score = keyword_score(text, KEYWORDS["incident_type"])

    lowered = normalize(text)
    if any(x in lowered for x in ["outage", "all partners", "business critical", "p1"]):
        severity = "P1"
    elif any(x in lowered for x in ["failed", "blocked", "stuck", "p2"]):
        severity = "P2"
    elif incident_type in ["Delivery Failure", "Stuck Workflow"]:
        severity = "P2"
    elif any(x in lowered for x in ["warning", "visibility", "p3"]):
        severity = "P3"
    else:
        severity = "P4"

    confidence = int(round((0.45 * workflow_score + 0.30 * product_score + 0.25 * incident_score) * 100))
    confidence = max(25, min(98, confidence))

    return {
        "ticket": ticket.get("title"),
        "workflow": workflow,
        "product": product,
        "incident_type": incident_type,
        "severity": severity,
        "confidence": confidence,
    }


def build_query(ticket: Dict[str, Any], classification: Dict[str, Any]) -> str:
    return " ".join([
        ticket.get("title", ""),
        ticket.get("description", ""),
        " ".join(ticket.get("logs", [])),
        classification.get("workflow", ""),
        classification.get("product", ""),
        classification.get("incident_type", ""),
    ])


def owner_for(workflow: str, product: str) -> Dict[str, str]:
    for owner in OWNERSHIP:
        if owner["workflow"] == workflow and owner["product"] == product:
            return owner
    for owner in OWNERSHIP:
        if owner["workflow"] == workflow:
            return owner
    return {
        "workflow": workflow,
        "product": product,
        "owner_team": "Unknown",
        "l2": "MSC L2 Queue",
        "engineering": "Engineering Triage",
        "product_owner": "Product Triage",
        "operations": "MSC Operations",
    }


def recommend_actions(classification: Dict[str, Any]) -> List[str]:
    incident_type = classification["incident_type"]
    if incident_type == "Delivery Failure":
        return [
            "Validate package status in MSC Monitor.",
            "Verify manifest generation and required metadata fields.",
            "Confirm partner mapping and endpoint configuration.",
            "Resubmit or retry the workflow only after human approval.",
        ]
    if incident_type == "Stuck Workflow":
        return [
            "Check current workflow step and wait duration.",
            "Review recent deployment, outage, and dependency context.",
            "Validate lock state or downstream dependency.",
            "Escalate to owning engineering team before cleanup actions.",
        ]
    if incident_type == "Visibility Gap":
        return [
            "Check availability windows and territory mappings.",
            "Confirm upstream rights feed completion.",
            "Validate partner restrictions and publish status.",
            "Route to rights owner if feed and mappings are correct.",
        ]
    if incident_type == "Validation Failure":
        return [
            "Review validation error details and affected asset/package.",
            "Compare required fields against approved SOP or runbook.",
            "Correct source metadata or configuration after owner approval.",
            "Rerun validation only after human approval.",
        ]
    return [
        "Review matched approved source guidance.",
        "Validate current monitor context and logs.",
        "Confirm owner and escalation path.",
        "Proceed only after human approval.",
    ]


def investigation_actions(classification: Dict[str, Any]) -> List[str]:
    return [
        "Review monitor context, current workflow step, logs, and recent changes.",
        "Compare against listed similar incidents.",
        "Validate whether cited source version applies to this ticket.",
        "Escalate if remediation path remains unclear.",
    ]


def likely_cause(classification: Dict[str, Any], mode: str) -> str:
    if mode == "Escalate":
        return "Unknown or unsupported by approved evidence. No resolution recommendation generated."
    if classification["incident_type"] == "Delivery Failure" and classification["product"] == "Prism":
        return "Delivery manifest validation failure or partner mapping issue based on approved sources and historical incidents."
    if classification["incident_type"] == "Stuck Workflow":
        return "Workflow is likely blocked by processing state, lock state, or downstream dependency."
    if classification["incident_type"] == "Visibility Gap":
        return "Visibility gap likely tied to availability windows, territory mapping, or upstream rights feed completion."
    return f"Likely {classification['incident_type']} in {classification['workflow']} based on matched approved operational sources."


def confidence_from_evidence(
    classifier_confidence: int,
    knowledge_hits: List[Dict[str, Any]],
    incident_hits: List[Dict[str, Any]],
) -> int:
    evidence_strength = max((h["score"] for h in knowledge_hits), default=0.0)
    incident_strength = max((h["score"] for h in incident_hits), default=0.0)
    evidence_score = min(100, int(round(((0.65 * evidence_strength) + (0.35 * incident_strength)) * 235)))
    return int(round((0.55 * classifier_confidence) + (0.45 * evidence_score)))


def similar_summary(incident_hits: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not incident_hits:
        return {
            "count": 0,
            "resolved_count": 0,
            "resolution_recurrence": 0,
            "outcome": "No similar incidents found",
        }
    resolved_count = sum(1 for h in incident_hits if h.get("resolved"))
    success_count = sum(1 for h in incident_hits if h.get("resolution_success"))
    recurrence = int(round((success_count / max(1, len(incident_hits))) * 100))
    outcome = "Likely known issue" if recurrence >= 70 and len(incident_hits) >= 2 else "Partially known issue"
    return {
        "count": len(incident_hits),
        "resolved_count": resolved_count,
        "resolution_recurrence": recurrence,
        "outcome": outcome,
    }


def documentation_gaps(knowledge_hits: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    gaps: List[Dict[str, str]] = []
    if not knowledge_hits:
        gaps.append({
            "type": "Missing Coverage",
            "message": "No approved runbook, SOP, KB article, RCA, or postmortem was found for this issue pattern.",
            "action": "Create New Runbook Request",
        })
        return gaps

    for hit in knowledge_hits:
        try:
            updated = datetime.fromisoformat(hit["updated"])
            age_days = (datetime.now() - updated).days
            if age_days > STALE_DOC_DAYS:
                gaps.append({
                    "type": "Stale Documentation",
                    "message": f"{hit['title']} was last updated {age_days} days ago.",
                    "action": "Review and refresh source",
                })
        except Exception:
            gaps.append({
                "type": "Unknown Freshness",
                "message": f"{hit.get('title', 'Source')} does not have a parseable updated date.",
                "action": "Validate source metadata",
            })
    return gaps


def source_lineage(sources: List[Dict[str, Any]]) -> List[str]:
    return [
        f"{s.get('source')}::{s.get('id')}::{s.get('version', 'n/a')}::{s.get('owner', 'unknown')}"
        for s in sources
    ]


def compose_resolution(ticket: Dict[str, Any]) -> Dict[str, Any]:
    classification = classify_ticket(ticket)
    query = build_query(ticket, classification)

    knowledge_hits = search_docs(query, KNOWLEDGE, top_k=4, approved_only=True)
    incident_hits = search_docs(query, INCIDENTS, top_k=5, approved_only=False)

    final_confidence = confidence_from_evidence(
        classification["confidence"],
        knowledge_hits,
        incident_hits,
    )

    if knowledge_hits and final_confidence >= RECOMMEND_THRESHOLD:
        mode = "Recommend"
        actions = recommend_actions(classification)
        escalation_reason = None
    elif knowledge_hits and final_confidence >= INVESTIGATE_THRESHOLD:
        mode = "Suggest Investigation"
        actions = investigation_actions(classification)
        escalation_reason = "Confidence between 50 and 80; investigation package created instead of direct recommendation."
    else:
        mode = "Escalate"
        actions = [
            "Escalate with gathered context.",
            "Request owner review.",
            "Capture documentation gap if confirmed.",
        ]
        escalation_reason = "Approved evidence missing or confidence below threshold."

    owner = owner_for(classification["workflow"], classification["product"])

    sources = [
        {
            "id": hit["id"],
            "source": hit["source"],
            "title": hit["title"],
            "version": hit.get("version", "n/a"),
            "updated": hit.get("updated", "n/a"),
            "owner": hit.get("owner", "unknown"),
            "score": hit["score"],
        }
        for hit in knowledge_hits
    ]

    escalation_package = None
    if mode != "Recommend":
        escalation_package = {
            "ticket_summary": ticket.get("title"),
            "workflow": classification["workflow"],
            "product": classification["product"],
            "service_owner": owner.get("owner_team"),
            "logs_reviewed": ticket.get("logs", []),
            "monitor_context": ticket.get("monitor_context", {}),
            "draft_guidance_for_review": actions,
            "similar_incidents": [hit["id"] for hit in incident_hits],
            "confidence_score": final_confidence,
            "reason_for_escalation": escalation_reason,
            "routes": {
                "l2": owner.get("l2"),
                "engineering": owner.get("engineering"),
                "product": owner.get("product_owner"),
                "operations": owner.get("operations"),
            },
        }

    return {
        "ticket": ticket,
        "classification": classification,
        "similar_incidents": incident_hits,
        "similar_summary": similar_summary(incident_hits),
        "monitor_context": ticket.get("monitor_context", {}),
        "ownership": owner,
        "documentation_gaps": documentation_gaps(knowledge_hits),
        "assistant": {
            "mode": mode,
            "likely_cause": likely_cause(classification, mode),
            "recommended_actions": actions,
            "evidence": [
                f"{hit['title']} ({hit['source']} {hit.get('version', 'n/a')}): {hit.get('content', '')[:260]}"
                for hit in knowledge_hits[:3]
            ],
            "sources": sources,
            "confidence": final_confidence,
            "source_lineage": source_lineage(sources),
            "unsupported_recommendation_blocked": not bool(knowledge_hits),
            "human_approval_required": True,
            "escalation_package": escalation_package,
        },
    }


def find_ticket(ticket_id: str) -> Dict[str, Any]:
    for ticket in TICKETS:
        if ticket["id"] == ticket_id:
            return ticket
    raise HTTPException(status_code=404, detail="Ticket not found")

# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------

@app.get("/health")
def health() -> Dict[str, str]:
    return {
        "status": "ok",
        "version": "1.0.0-lightweight",
        "time": now_iso(),
    }


@app.get("/tickets")
def list_tickets() -> List[Dict[str, Any]]:
    return TICKETS


@app.get("/tickets/{ticket_id}")
def get_ticket_analysis(ticket_id: str) -> Dict[str, Any]:
    return compose_resolution(find_ticket(ticket_id))


@app.post("/tickets/analyze")
def analyze_ticket(ticket: TicketInput) -> Dict[str, Any]:
    payload = ticket.model_dump()
    payload["id"] = payload.get("id") or f"MANUAL-{uuid.uuid4().hex[:8].upper()}"
    payload["created"] = now_iso()
    return compose_resolution(payload)


@app.post("/tickets/ingest")
def ingest_ticket(ticket: TicketInput) -> Dict[str, Any]:
    payload = ticket.model_dump()
    payload["id"] = payload.get("id") or f"TCK-{1000 + len(TICKETS) + 1}"
    payload["created"] = now_iso()
    TICKETS.append(payload)
    return compose_resolution(payload)


@app.get("/knowledge")
def list_knowledge(approved_only: bool = True) -> List[Dict[str, Any]]:
    if approved_only:
        return [k for k in KNOWLEDGE if k.get("approved") and k.get("source") in APPROVED_SOURCE_TYPES]
    return KNOWLEDGE


@app.get("/analytics")
def analytics() -> Dict[str, Any]:
    analyses = [compose_resolution(ticket) for ticket in TICKETS]
    total = len(analyses)
    recommend_count = sum(1 for a in analyses if a["assistant"]["mode"] == "Recommend")
    investigate_count = sum(1 for a in analyses if a["assistant"]["mode"] == "Suggest Investigation")
    escalate_count = sum(1 for a in analyses if a["assistant"]["mode"] == "Escalate")
    unsupported_count = sum(1 for a in analyses if a["assistant"]["unsupported_recommendation_blocked"])
    citation_eligible = sum(1 for a in analyses if a["assistant"]["sources"] or a["assistant"]["mode"] == "Escalate")
    gaps = [gap for analysis in analyses for gap in analysis["documentation_gaps"]]

    workflow_distribution: Dict[str, int] = {}
    for analysis in analyses:
        workflow = analysis["classification"]["workflow"]
        workflow_distribution[workflow] = workflow_distribution.get(workflow, 0) + 1

    return {
        "ticket_count": total,
        "recommendation_rate": round((recommend_count / total) * 100, 1) if total else 0,
        "investigation_rate": round((investigate_count / total) * 100, 1) if total else 0,
        "escalation_rate": round((escalate_count / total) * 100, 1) if total else 0,
        "citation_coverage": round((citation_eligible / total) * 100, 1) if total else 0,
        "unsupported_recommendations": 0,
        "unsupported_recommendations_blocked": unsupported_count,
        "documentation_gap_count": len(gaps),
        "workflow_distribution": workflow_distribution,
        "documentation_gaps": gaps,
        "pilot_targets": {
            "mttr_reduction_target": "40-60% for repeatable incident categories after baseline validation",
            "escalation_reduction_target": "20-30% for cases with approved runbooks and similar incident history",
            "first_contact_resolution_improvement_target": "25% for known issue patterns",
            "ticket_deflection_target": "30-50% for well-documented repeat issues",
            "documentation_coverage_target": ">95% for selected pilot workflows",
            "gap_tracking_target": "100% of low-confidence or no-source recommendations captured for review",
            "citation_coverage_target": "100%",
            "unsupported_recommendation_target": "0%",
        },
    }


@app.post("/chat")
def chat(input: ChatInput) -> Dict[str, Any]:
    analysis = compose_resolution(find_ticket(input.ticket_id))
    question = normalize(input.question)

    if any(term in question for term in ["why", "fail", "failed", "root cause", "cause"]):
        answer = analysis["assistant"]["likely_cause"]
    elif any(term in question for term in ["similar", "cases", "history", "incidents"]):
        summary = analysis["similar_summary"]
        answer = (
            f"Found {summary['count']} similar cases. "
            f"Resolution recurrence is {summary['resolution_recurrence']}%. "
            f"Outcome: {summary['outcome']}."
        )
    elif any(term in question for term in ["owner", "owns", "escalate", "route", "team"]):
        owner = analysis["ownership"]
        answer = (
            f"Owner team: {owner.get('owner_team')}. "
            f"Escalation route: L2={owner.get('l2')}, Engineering={owner.get('engineering')}, "
            f"Product={owner.get('product_owner')}, Operations={owner.get('operations')}."
        )
    elif any(term in question for term in ["source", "evidence", "citation", "lineage"]):
        lineage = analysis["assistant"]["source_lineage"]
        answer = "Sources: " + "; ".join(lineage) if lineage else "No approved evidence found. Escalation is required."
    else:
        answer = (
            "I can answer: why did this fail, show similar cases, who owns this workflow, "
            "or show evidence/source lineage."
        )

    return {
        "answer": answer,
        "mode": analysis["assistant"]["mode"],
        "confidence": analysis["assistant"]["confidence"],
        "sources": analysis["assistant"]["sources"],
    }


# -----------------------------------------------------------------------------
# Optional local smoke test helper
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    assert health()["status"] == "ok"
    assert len(list_tickets()) >= 1
    for _ticket in TICKETS:
        result = compose_resolution(_ticket)
        assert "classification" in result
        assert "assistant" in result
        if result["assistant"]["mode"] == "Recommend":
            assert result["assistant"]["sources"], "Recommendation without approved source"
    print("SMOKE_OK")
