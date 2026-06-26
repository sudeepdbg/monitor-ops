
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import math
import re

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = Path(__file__).parent / "data"
RECOMMEND_THRESHOLD = 80
INVESTIGATE_THRESHOLD = 50
STALE_DOC_DAYS = 365

WORKFLOWS = ["Distribution", "Fulfillment", "Acquisition", "Inventory", "Localization", "Rights"]
PRODUCTS = ["Prism", "Domino", "Foundry MAM", "Pegasus", "Rally", "Distribute 2.0"]
INCIDENT_TYPES = ["Stuck Workflow", "Delivery Failure", "Metadata Issue", "Partner Configuration", "Visibility Gap", "Validation Failure"]

KEYWORDS = {
    "workflow": {
        "Distribution": ["delivery", "deliver", "partner", "redelivery", "amazon", "pvc", "distribute"],
        "Fulfillment": ["fulfillment", "domino", "package", "assembly"],
        "Acquisition": ["acquisition", "ingest", "source", "received"],
        "Inventory": ["inventory", "mam", "asset", "lock", "foundry"],
        "Localization": ["localization", "subtitle", "audio", "language", "caption"],
        "Rights": ["rights", "availability", "window", "territory", "visibility"],
    },
    "product": {
        "Prism": ["prism", "amazon", "pvc", "distribution"],
        "Domino": ["domino", "fulfillment"],
        "Foundry MAM": ["foundry", "mam", "asset"],
        "Pegasus": ["pegasus", "localization"],
        "Rally": ["rally", "rights"],
        "Distribute 2.0": ["distribute 2.0", "d2", "distribution"],
    },
    "incident_type": {
        "Stuck Workflow": ["stuck", "frozen", "blocked", "not moved", "waiting", "lock"],
        "Delivery Failure": ["delivery failed", "failed delivery", "delivery", "rejected", "redelivery"],
        "Metadata Issue": ["metadata", "territory", "language tag", "missing field"],
        "Partner Configuration": ["partner", "endpoint", "mapping", "configuration"],
        "Visibility Gap": ["visibility", "not visible", "availability missing"],
        "Validation Failure": ["validation", "validate", "conformance", "manifest validation"],
    },
}


def load_json(name: str) -> list:
    with open(DATA_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def keyword_score(text: str, options: Dict[str, List[str]]) -> tuple[str, float]:
    text_n = normalize(text)
    best, best_score = list(options.keys())[0], 0.0
    for label, words in options.items():
        raw = 0
        for w in words:
            w_n = normalize(w)
            if w_n in text_n:
                raw += 2 if len(w_n.split()) > 1 else 1
        score = min(1.0, raw / max(3, len(words) / 2))
        if score > best_score:
            best, best_score = label, score
    return best, best_score


def severity_from_text(text: str, incident_type: str) -> str:
    t = normalize(text)
    if any(x in t for x in ["outage", "all partners", "business critical", "p1"]):
        return "P1"
    if any(x in t for x in ["failed", "blocked", "stuck", "p2"]):
        return "P2"
    if incident_type in ["Delivery Failure", "Stuck Workflow"]:
        return "P2"
    if any(x in t for x in ["warning", "visibility", "p3"]):
        return "P3"
    return "P4"


def classify_ticket(ticket: Dict[str, Any]) -> Dict[str, Any]:
    text = f"{ticket.get('title','')} {ticket.get('description','')} {' '.join(ticket.get('logs', []))}"
    workflow, wf_s = keyword_score(text, KEYWORDS["workflow"])
    product, pr_s = keyword_score(text, KEYWORDS["product"])
    incident_type, it_s = keyword_score(text, KEYWORDS["incident_type"])
    severity = severity_from_text(text, incident_type)
    confidence = int(round((0.45 * wf_s + 0.30 * pr_s + 0.25 * it_s) * 100))
    if confidence == 0:
        confidence = 25
    return {
        "ticket": ticket.get("title"),
        "workflow": workflow,
        "product": product,
        "incident_type": incident_type,
        "severity": severity,
        "confidence": confidence,
    }


@dataclass
class VectorIndex:
    docs: List[Dict[str, Any]]
    kind: str
    vectorizer: TfidfVectorizer
    matrix: Any

    @classmethod
    def build(cls, docs: List[Dict[str, Any]], kind: str) -> "VectorIndex":
        def doc_text(d: Dict[str, Any]) -> str:
            fields = [d.get("title", ""), d.get("content", ""), d.get("resolution", ""), d.get("workflow", ""), d.get("product", ""), " ".join(d.get("tags", []))]
            return " ".join(fields)
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        matrix = vectorizer.fit_transform([doc_text(d) for d in docs])
        return cls(docs=docs, kind=kind, vectorizer=vectorizer, matrix=matrix)

    def search(self, query: str, top_k: int = 5, approved_only: bool = False) -> List[Dict[str, Any]]:
        q = self.vectorizer.transform([query])
        sims = cosine_similarity(q, self.matrix).flatten()
        ranked = np.argsort(sims)[::-1]
        out = []
        for idx in ranked[: max(top_k * 3, top_k)]:
            doc = self.docs[int(idx)]
            if approved_only and not doc.get("approved", True):
                continue
            score = float(sims[int(idx)])
            if score <= 0:
                continue
            out.append({"score": round(score, 3), **doc})
            if len(out) >= top_k:
                break
        return out


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


class Repo:
    def __init__(self) -> None:
        self.knowledge = load_json("knowledge.json")
        self.incidents = load_json("incidents.json")
        self.tickets = load_json("tickets.json")
        self.ownership = load_json("ownership.json")
        self.k_index = VectorIndex.build(self.knowledge, "knowledge")
        self.i_index = VectorIndex.build(self.incidents, "incidents")

    def find_ticket(self, ticket_id: str) -> Dict[str, Any]:
        for t in self.tickets:
            if t["id"] == ticket_id:
                return t
        raise HTTPException(status_code=404, detail="Ticket not found")

    def owner_for(self, workflow: str, product: str) -> Dict[str, str]:
        for o in self.ownership:
            if o["workflow"] == workflow and o["product"] == product:
                return o
        for o in self.ownership:
            if o["workflow"] == workflow:
                return o
        return {"workflow": workflow, "product": product, "owner_team": "Unknown", "l2": "MSC L2 Queue", "engineering": "Engineering Triage", "product": "Product Triage", "operations": "MSC Operations"}

repo = Repo()
app = FastAPI(title="MSC Monitor Ops API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def build_query(ticket: Dict[str, Any], classification: Dict[str, Any]) -> str:
    return " ".join([
        ticket.get("title", ""), ticket.get("description", ""), " ".join(ticket.get("logs", [])),
        classification["workflow"], classification["product"], classification["incident_type"]
    ])


def confidence_from_evidence(class_conf: int, knowledge_hits: List[Dict[str, Any]], incident_hits: List[Dict[str, Any]]) -> int:
    k = max([h["score"] for h in knowledge_hits], default=0)
    i = max([h["score"] for h in incident_hits], default=0)
    evidence_score = min(100, int(round((0.6 * k + 0.4 * i) * 140)))
    return int(round(0.55 * class_conf + 0.45 * evidence_score))


def similar_incidents_summary(hits: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not hits:
        return {"count": 0, "resolution_recurrence": 0, "outcome": "No similar incidents found"}
    resolved = [h for h in hits if h.get("resolved")]
    successful = [h for h in hits if h.get("resolution_success")]
    recurrence = int(round(len(successful) / len(hits) * 100))
    outcome = "Likely known issue" if recurrence >= 70 and len(hits) >= 2 else "Partially known issue"
    return {"count": len(hits), "resolved_count": len(resolved), "resolution_recurrence": recurrence, "outcome": outcome}


def doc_gap_flags(classification: Dict[str, Any], knowledge_hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flags = []
    approved_hits = [h for h in knowledge_hits if h.get("approved")]
    if not approved_hits:
        flags.append({"type": "Missing Coverage", "message": "No approved runbook/SOP/KB found for this issue pattern.", "action": "Create New Runbook Request"})
    for h in approved_hits:
        try:
            updated = datetime.fromisoformat(h["updated"])
            age_days = (datetime.now() - updated).days
            if age_days > STALE_DOC_DAYS:
                flags.append({"type": "Stale Documentation", "message": f"{h['title']} was last updated {age_days} days ago.", "action": "Review and refresh source"})
        except Exception:
            pass
    return flags


def compose_resolution(ticket: Dict[str, Any]) -> Dict[str, Any]:
    classification = classify_ticket(ticket)
    query = build_query(ticket, classification)
    knowledge_hits = repo.k_index.search(query, top_k=4, approved_only=True)
    incident_hits = repo.i_index.search(query, top_k=5, approved_only=False)
    final_conf = confidence_from_evidence(classification["confidence"], knowledge_hits, incident_hits)
    owner = repo.owner_for(classification["workflow"], classification["product"])
    sim = similar_incidents_summary(incident_hits)
    gaps = doc_gap_flags(classification, knowledge_hits)

    if knowledge_hits and final_conf >= RECOMMEND_THRESHOLD:
        mode = "Recommend"
        likely_cause = infer_likely_cause(classification, knowledge_hits, incident_hits)
        actions = recommended_actions(classification, knowledge_hits)
        escalation_reason = None
    elif knowledge_hits and final_conf >= INVESTIGATE_THRESHOLD:
        mode = "Suggest Investigation"
        likely_cause = "Potentially known issue, but confidence is below recommendation threshold. Human validation required."
        actions = investigation_actions(classification)
        escalation_reason = "Confidence between 50 and 80; provide investigation package instead of direct recommendation."
    else:
        mode = "Escalate"
        likely_cause = "Unknown or unsupported by approved evidence. No resolution recommendation generated."
        actions = ["Escalate with gathered context", "Request owner review", "Capture documentation gap if confirmed"]
        escalation_reason = "Approved evidence missing or confidence below threshold."

    sources = [{k: h[k] for k in ["id", "source", "title", "version", "updated", "owner"] if k in h} | {"score": h["score"]} for h in knowledge_hits]

    escalation_package = None
    if mode == "Escalate" or escalation_reason:
        escalation_package = {
            "ticket_summary": ticket.get("title"),
            "workflow": classification["workflow"],
            "service_owner": owner.get("owner_team"),
            "logs_reviewed": ticket.get("logs", []),
            "draft_guidance_for_review": actions,
            "similar_incidents": [h["id"] for h in incident_hits],
            "confidence_score": final_conf,
            "reason_for_escalation": escalation_reason or "Human review required",
            "routes": {"l2": owner.get("l2"), "engineering": owner.get("engineering"), "product": owner.get("product"), "operations": owner.get("operations")},
        }

    return {
        "ticket": ticket,
        "classification": classification,
        "similar_incidents": incident_hits,
        "similar_summary": sim,
        "monitor_context": ticket.get("monitor_context", {}),
        "assistant": {
            "mode": mode,
            "likely_cause": likely_cause,
            "recommended_actions": actions,
            "evidence": [summarize_evidence(h) for h in knowledge_hits[:3]],
            "sources": sources,
            "confidence": final_conf,
            "source_lineage": [f"{s['source']}::{s['id']}::{s.get('version','n/a')}" for s in sources],
            "unsupported_recommendation_blocked": not bool(knowledge_hits),
            "escalation_package": escalation_package,
        },
        "ownership": owner,
        "documentation_gaps": gaps,
    }


def infer_likely_cause(classification: Dict[str, Any], kh: List[Dict[str, Any]], ih: List[Dict[str, Any]]) -> str:
    if classification["incident_type"] == "Delivery Failure" and classification["product"] == "Prism":
        return "Delivery manifest validation failure or partner mapping issue based on matched approved sources and historical incidents."
    if classification["incident_type"] == "Stuck Workflow":
        return "Workflow is likely blocked by processing state, asset lock, or downstream dependency."
    if classification["incident_type"] == "Visibility Gap":
        return "Visibility gap likely tied to availability windows, territory mapping, or upstream rights feed completion."
    return f"Likely {classification['incident_type']} in {classification['workflow']} based on matched approved operational sources."


def recommended_actions(classification: Dict[str, Any], kh: List[Dict[str, Any]]) -> List[str]:
    incident = classification["incident_type"]
    if incident == "Delivery Failure":
        return ["Validate package status in MSC Monitor.", "Verify manifest generation and required metadata fields.", "Confirm partner mapping / endpoint configuration.", "Re-submit or retry workflow only after human approval."]
    if incident == "Stuck Workflow":
        return ["Check workflow current step and wait duration.", "Review recent deployment or active outage context.", "Validate lock or dependency state.", "Escalate to owning engineering team before cleanup actions."]
    if incident == "Visibility Gap":
        return ["Check availability windows and territory mappings.", "Confirm upstream feed completion.", "Route to workflow owner if feed and mappings are correct."]
    return ["Review matched runbook steps.", "Validate evidence against current ticket context.", "Proceed only with operator approval."]


def investigation_actions(classification: Dict[str, Any]) -> List[str]:
    return ["Review monitor context and logs.", "Compare with listed similar incidents.", "Validate source applicability and version.", "Escalate if owner or remediation path remains unclear."]


def summarize_evidence(hit: Dict[str, Any]) -> str:
    snippet = hit.get("content", "")[:220]
    return f"{hit.get('title')} ({hit.get('source')} {hit.get('version')}): {snippet}"


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "time": now_iso()}


@app.get("/tickets")
def tickets() -> List[Dict[str, Any]]:
    return repo.tickets


@app.get("/tickets/{ticket_id}")
def ticket(ticket_id: str) -> Dict[str, Any]:
    return compose_resolution(repo.find_ticket(ticket_id))


@app.post("/tickets/analyze")
def analyze(ticket: TicketInput) -> Dict[str, Any]:
    payload = ticket.model_dump()
    payload["id"] = payload.get("id") or f"MANUAL-{len(repo.tickets)+1:04d}"
    payload["created"] = now_iso()
    return compose_resolution(payload)


@app.post("/tickets/ingest")
def ingest(ticket: TicketInput) -> Dict[str, Any]:
    payload = ticket.model_dump()
    payload["id"] = payload.get("id") or f"TCK-{1000+len(repo.tickets)+1}"
    payload["created"] = now_iso()
    repo.tickets.append(payload)
    return compose_resolution(payload)


@app.get("/analytics")
def analytics() -> Dict[str, Any]:
    analyses = [compose_resolution(t) for t in repo.tickets]
    total = len(analyses)
    rec = sum(1 for a in analyses if a["assistant"]["mode"] == "Recommend")
    esc = sum(1 for a in analyses if a["assistant"]["mode"] == "Escalate")
    citation_coverage = sum(1 for a in analyses if a["assistant"]["sources"] or a["assistant"]["mode"] == "Escalate")
    gaps = [g for a in analyses for g in a["documentation_gaps"]]
    by_workflow = {}
    for a in analyses:
        wf = a["classification"]["workflow"]
        by_workflow.setdefault(wf, 0)
        by_workflow[wf] += 1
    return {
        "ticket_count": total,
        "recommendation_rate": round(rec / total * 100, 1) if total else 0,
        "escalation_rate": round(esc / total * 100, 1) if total else 0,
        "citation_coverage": round(citation_coverage / total * 100, 1) if total else 0,
        "unsupported_recommendations": 0,
        "documentation_gap_count": len(gaps),
        "workflow_distribution": by_workflow,
        "pilot_targets": {
            "mttr_reduction_target": "40-60% for repeatable incident categories after baseline validation",
            "escalation_reduction_target": "20-30% where approved runbooks and history exist",
            "citation_coverage_target": "100% generated recommendations include approved sources",
            "unsupported_recommendation_target": "0%",
        },
        "documentation_gaps": gaps,
    }


@app.post("/chat")
def chat(inp: ChatInput) -> Dict[str, Any]:
    analysis = compose_resolution(repo.find_ticket(inp.ticket_id))
    q = normalize(inp.question)
    if "why" in q or "fail" in q or "root" in q:
        answer = analysis["assistant"]["likely_cause"]
    elif "similar" in q or "case" in q:
        sims = analysis["similar_incidents"]
        answer = f"Found {len(sims)} similar cases. Resolution recurrence: {analysis['similar_summary'].get('resolution_recurrence',0)}%."
    elif "own" in q or "escalat" in q or "route" in q:
        o = analysis["ownership"]
        answer = f"Owner: {o.get('owner_team')}. Escalation: L2={o.get('l2')}, Engineering={o.get('engineering')}, Product={o.get('product')}."
    elif "source" in q or "evidence" in q or "citation" in q:
        answer = "Sources: " + "; ".join(analysis["assistant"]["source_lineage"]) if analysis["assistant"]["sources"] else "No approved source evidence found; escalation required."
    else:
        answer = "I can answer: why did this fail, show similar cases, who owns this workflow, and show evidence."
    return {"answer": answer, "confidence": analysis["assistant"]["confidence"], "mode": analysis["assistant"]["mode"], "sources": analysis["assistant"]["sources"]}
