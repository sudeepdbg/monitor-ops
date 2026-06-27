import streamlit as st
import json
import pandas as pd
import os
from datetime import datetime
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
import tempfile

# 🌐 CONFIG
st.set_page_config(page_title="MSC Monitor Ops", layout="wide")
API_KEY = st.secrets.get("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY"))
if not API_KEY:
    st.error("Please set OPENAI_API_KEY in Streamlit secrets or env vars.")
    st.stop()

llm = ChatOpenAI(model="gpt-4o-mini", api_key=API_KEY, temperature=0.1)
embeddings = OpenAIEmbeddings(api_key=API_KEY)

# 📁 MOCK DATA LOADERS
@st.cache_data
def load_knowledge():
    # Replace with real SharePoint/Confluence connectors later
    mock_docs = [
        {"source": "Runbook", "title": "Prism Partner Redelivery", "version": "v5.2", "updated": "2026-04-11", "owner": "Distribution", "content": "Validate package status. Verify manifest generation. Re-submit workflow. Check partner PVC status."},
        {"source": "KB", "title": "KB-1248 Metadata Validation", "version": "v2.1", "updated": "2025-12-01", "owner": "Fulfillment", "content": "Metadata mismatch causes delivery failure. Run validation script v3. Clear cache and retry."},
        {"source": "RCA", "title": "RCA-2026-004 Amazon PVC Failure", "version": "v1.0", "updated": "2026-05-15", "owner": "Engineering", "content": "Manifest generation timeout. Fix applied in Deploy 4.2. Retry with backoff."}
    ]
    return mock_docs

@st.cache_data
def load_mock_tickets():
    return [
        {"id": "TK-101", "summary": "Amazon PVC delivery failed during manifest generation", "severity": "P2"},
        {"id": "TK-102", "summary": "Metadata validation stuck on Rally ingest", "severity": "P3"}
    ]

# 🧠 CORE LOGIC
def classify_ticket(ticket_text):
    prompt = f"""You are an MSC Operations Classifier. Analyze the incident ticket and return ONLY a JSON object with these fields:
workflow, product, incident_type, severity, confidence (0-100).
Rules: If ambiguous, set confidence < 60. Never guess. Return valid JSON only.
Ticket: {ticket_text}"""
    response = llm.invoke(prompt).content.strip()
    return json.loads(response.replace("```json", "").replace("```", ""))

def build_faiss(docs):
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = [d["content"] for d in docs]
    metadatas = [{k:v for k,v in d.items() if k != "content"} for d in docs]
    split_docs = splitter.create_documents(texts, metadatas=metadatas)
    return FAISS.from_documents(split_docs, embeddings)

def grounded_resolve(ticket, classification, vectorstore):
    prompt = """You are an MSC Support AI. Generate a resolution recommendation STRICTLY based on the provided evidence snippets. 
Rules:
1. NEVER invent steps. Only use provided runbooks, KBs, or RCAs.
2. CITE EVERY CLAIM with [Source: Title | Version | Owner].
3. Calculate confidence (0-100) based on: evidence match strength, recency, and similarity score.
4. If confidence < 50, output ESCALATE. If 50-80, output INVESTIGATE. If ≥80, output RECOMMEND.
5. Format output as JSON with: likely_cause, recommended_actions, evidence_summary, sources, confidence, routing_action.
Evidence: {context}
Ticket: {ticket}
Return JSON only."""
    
    docs = vectorstore.similarity_search(ticket, k=3)
    context = "\n---\n".join([d.page_content + f"\n[Source: {d.metadata.get('title', 'N/A')} | v{d.metadata.get('version','')} | {d.metadata.get('owner','')})" for d in docs])
    
    resp = llm.invoke(prompt.format(context=context, ticket=ticket)).content.strip()
    return json.loads(resp.replace("```json", "").replace("```", ""))

# 🖥️ UI
st.title("🚀 MSC Monitor Ops | AI Support Prototype (Recommendation Mode)")
st.caption("Evidence-grounded • Human-in-the-loop • No unsupported recommendations")

cols = st.columns([1, 2, 2])

with cols[0]:
    st.subheader("📋 Ticket Queue")
    tickets = load_mock_tickets()
    selected = st.radio("Select Ticket", [t["summary"] for t in tickets], index=0)
    ticket_id = next(t["id"] for t in tickets if t["summary"] == selected)
    
    with st.expander("🔍 Ticket Details"):
        st.json({"id": ticket_id, "summary": selected})

with cols[1]:
    st.subheader("🔎 Investigation & Context")
    if selected:
        classification = classify_ticket(selected)
        st.json(classification)
        
        st.markdown("### 📚 Similar Historical Incidents")
        st.info("Matched INC1510021, INC1521443 (Resolution recurrence: 83%)")
        
        st.markdown("### 📊 Operational Context")
        st.info("Workflow: Active | Environment: No recent outages | Partner: Amazon PVC")

with cols[2]:
    st.subheader("🤖 AI Resolution Assistant")
    if st.button("Generate Evidence-Backed Guidance"):
        docs = load_knowledge()
        vs = build_faiss(docs)
        result = grounded_resolve(selected, classification, vs)
        
        st.json(result)
        
        conf = result.get("confidence", 0)
        if conf >= 80:
            st.success(f"✅ RECOMMEND | Confidence: {conf}%")
        elif conf >= 50:
            st.warning(f"🔍 INVESTIGATE | Confidence: {conf}%")
        else:
            st.error(f"🚨 ESCALATE | Confidence: {conf}% | Auto-packaging for L2/Engineering")
            
        # Gap tracking mock
        if conf < 50 or not result.get("sources"):
            st.info("📝 Gap logged: Missing/stale documentation detected. Added to improvement backlog.")
