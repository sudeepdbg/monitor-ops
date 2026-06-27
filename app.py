import streamlit as st
import backend

st.set_page_config(page_title="MSC Monitor Ops", layout="wide")


def badge(text, mode="neutral"):
    colors = {"success": ("#DCFCE7", "#166534"), "warning": ("#FEF9C3", "#854D0E"), "danger": ("#FEE2E2", "#991B1B"), "info": ("#DBEAFE", "#1E40AF"), "neutral": ("#F3F4F6", "#374151")}
    bg, fg = colors.get(mode, colors["neutral"])
    st.markdown("<span style='background:" + bg + ";color:" + fg + ";padding:4px 10px;border-radius:999px;font-size:12px;font-weight:600'>" + text + "</span>", unsafe_allow_html=True)


def mode_color(mode):
    return "success" if mode == "Recommend" else "warning" if mode == "Suggest Investigation" else "danger" if mode == "Escalate" else "neutral"


def status_color(status):
    return {"Open": "info", "Assigned": "warning", "Escalated": "danger", "Auto Resolved": "success"}.get(status, "neutral")


if "tickets" not in st.session_state:
    st.session_state.tickets = list(backend.list_tickets())
if "manual" not in st.session_state:
    st.session_state.manual = None

st.title("MSC Monitor Ops - AI Assisted Operations Support")
st.caption("Standalone Streamlit app: UI app.py + backend.py module. No localhost/FastAPI required.")

with st.sidebar:
    st.header("Prototype Controls")
    st.success("Standalone Streamlit deployment")
    st.caption("backend.py runs in-process")
    if st.button("Refresh App", use_container_width=True):
        st.rerun()
    st.divider()
    st.header("Manual Ticket Analysis")
    with st.form("manual_form"):
        source = st.selectbox("Source", ["Manual", "ServiceNow", "Jira", "E-Mail"])
        title = st.text_input("Title", "Amazon PVC delivery failed")
        desc = st.text_area("Description", "Delivery failed from Prism with manifest validation error and missing territory metadata.", height=110)
        logs = st.text_area("Logs, one per line", "manifest_validation_failed\nmissing territoryCode\npartner=Amazon PVC", height=90)
        submit = st.form_submit_button("Analyze Without Saving", use_container_width=True)
    if submit:
        st.session_state.manual = {"id": "MANUAL", "source": source, "status": "Open", "title": title, "description": desc, "created": "Manual", "requester": "Operator", "logs": [x.strip() for x in logs.splitlines() if x.strip()], "monitor_context": {"workflow_status": "Unknown", "processing_status": "Manual analysis", "current_step": "Operator supplied", "partner": "Manual"}}
        st.rerun()
    if st.session_state.manual and st.button("Exit Manual Analysis", use_container_width=True):
        st.session_state.manual = None
        st.rerun()
    with st.expander("Knowledge Library"):
        for k in backend.list_knowledge(True):
            st.write("- " + k["id"] + " | " + k["source"] + " " + k["version"] + " | " + k["title"])

left, center, right = st.columns([0.95, 1.55, 1.35], gap="large")

with left:
    st.subheader("Ticket Queue")
    if st.session_state.manual:
        badge("Manual Analysis Mode", "info")
        ticket = st.session_state.manual
    else:
        filt = st.radio("Status Filter", ["All", "Open", "Assigned", "Escalated", "Auto Resolved"], index=0)
        filtered_tickets = [ticket for ticket in st.session_state.tickets if filt == "All" or ticket.get("status") == filt]
        if not filtered_tickets:
            st.info("No tickets found for status: " + filt + ". Please select All/Open/Assigned/Escalated or use Manual Ticket Analysis.")
            st.stop()
        labels = [ticket["id"] + " | " + ticket.get("status", "Open") + " | " + ticket["title"] for ticket in filtered_tickets]
        selected = st.selectbox("Select Ticket", labels)
        selected_id = selected.split(" | ")[0]
        ticket = next((item for item in filtered_tickets if item["id"] == selected_id), filtered_tickets[0])
        st.markdown("#### Queue Items")
        for item in filtered_tickets:
            with st.container(border=True):
                st.write("**" + item["id"] + "**")
                st.write(item["title"])
                badge(item.get("status", "Open"), status_color(item.get("status", "Open")))

analysis = backend.analyze(ticket)
classification = analysis["classification"]
assistant = analysis["assistant"]
similar = analysis["similar_summary"]

with center:
    st.subheader("Ticket Investigation")
    with st.container(border=True):
        st.write("### " + ticket.get("id", "Manual") + " - " + ticket.get("title", ""))
        st.write(ticket.get("description", ""))
        st.caption("Source: " + str(ticket.get("source")) + " | Requester: " + str(ticket.get("requester")) + " | Created: " + str(ticket.get("created")))
    st.markdown("#### Classification")
    cols = st.columns(5)
    metrics = [("Workflow", classification["workflow"]), ("Product", classification["product"]), ("Type", classification["incident_type"]), ("Severity", classification["severity"]), ("Classifier", str(classification["confidence"]) + "%")]
    for col, metric in zip(cols, metrics):
        col.metric(metric[0], metric[1])
    st.markdown("#### Similar Incidents")
    cards = st.columns(3)
    cards[0].metric("Matches", similar["count"])
    cards[1].metric("Recurrence", str(similar["resolution_recurrence"]) + "%")
    cards[2].metric("Outcome", similar["outcome"])
    for inc in analysis["similar_incidents"]:
        with st.expander(inc["id"] + " - " + inc["title"] + " | score=" + str(inc["score"])):
            st.write("Resolution: " + str(inc.get("resolution")))
    st.markdown("#### Monitor Context")
    st.json(analysis["monitor_context"])
    st.markdown("#### Documentation Gap Signals")
    if analysis["documentation_gaps"]:
        for gap in analysis["documentation_gaps"]:
            st.warning(gap["type"] + ": " + gap["message"] + " -> " + gap["action"])
    else:
        st.success("No documentation gap detected.")

with right:
    st.subheader("AI Resolution Assistant")
    badge(assistant["mode"], mode_color(assistant["mode"]))
    st.metric("Guidance Confidence", str(assistant["confidence"]) + "%")
    if assistant["unsupported_recommendation_blocked"]:
        st.error("Unsupported recommendation blocked. Escalation required.")
    st.caption("Human approval required for all operational actions.")
    st.markdown("#### Likely Cause")
    st.write(assistant["likely_cause"])
    st.markdown("#### Recommended / Investigation Actions")
    for idx, action in enumerate(assistant["recommended_actions"], 1):
        st.write(str(idx) + ". " + action)
    st.markdown("#### Evidence")
    if assistant["evidence"]:
        for item in assistant["evidence"]:
            st.info(item)
    else:
        st.warning("No approved source evidence found.")
    st.markdown("#### Sources, Version, Lineage")
    if assistant["sources"]:
        st.dataframe(assistant["sources"], use_container_width=True, hide_index=True)
        st.code("\n".join(assistant["source_lineage"]), language="text")
    else:
        st.write("No eligible citations.")
    st.markdown("#### Ownership / Escalation")
    st.json(assistant["escalation_package"] if assistant["escalation_package"] else analysis["ownership"])
    st.markdown("#### Conversational Support")
    question = st.text_input("Ask about this ticket", "Why did this fail?")
    if st.button("Ask Assistant", use_container_width=True):
        response = backend.ask(ticket, question)
        st.write(response["answer"])
        st.caption("Mode: " + response["mode"] + " | Confidence: " + str(response["confidence"]) + "%")

st.divider()
st.subheader("Pilot Analytics")
analytics = backend.get_analytics(st.session_state.tickets)
analytics_cols = st.columns(6)
analytics_metrics = [("Tickets", analytics["ticket_count"]), ("Recommend", str(analytics["recommendation_rate"]) + "%"), ("Investigate", str(analytics["investigation_rate"]) + "%"), ("Escalate", str(analytics["escalation_rate"]) + "%"), ("Citation", str(analytics["citation_coverage"]) + "%"), ("Unsupported Recs", analytics["unsupported_recommendations"])]
for col, metric in zip(analytics_cols, analytics_metrics):
    col.metric(metric[0], metric[1])
with st.expander("Workflow Distribution"):
    st.json(analytics["workflow_distribution"])
with st.expander("Documentation Gaps"):
    st.json(analytics["documentation_gaps"])
with st.expander("Pilot Targets"):
    st.json(analytics["pilot_targets"])
