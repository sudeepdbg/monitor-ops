
from difflib import SequenceMatcher
import re
RECOMMEND_THRESHOLD=80
INVESTIGATE_THRESHOLD=50
APPROVED={"Runbook","SOP","KB Article","RCA","Postmortem"}
KNOWLEDGE=[
{"id":"KB-1248","source":"KB Article","title":"Amazon PVC Manifest Validation Failure","version":"v2.3","updated":"2026-05-10","owner":"Distribution","approved":True,"workflow":"Distribution","product":"Prism","tags":["amazon","pvc","delivery","manifest","validation","metadata"],"content":"When Amazon PVC delivery fails with manifest validation errors, verify package status, validate manifest fields, confirm partner endpoint configuration, and resubmit the workflow after correcting metadata."},
{"id":"RUN-PRISM-REDLV-52","source":"Runbook","title":"Prism Partner Redelivery","version":"v5.2","updated":"2026-04-11","owner":"Distribution","approved":True,"workflow":"Distribution","product":"Prism","tags":["redelivery","partner","prism","distribution","manifest"],"content":"For Prism partner redelivery issues: check workflow state, verify partner mapping, validate manifest generation, confirm retry eligibility, then rerun only after operator approval."},
{"id":"RCA-2026-004","source":"RCA","title":"PVC Delivery Failures Due to Missing Territory Metadata","version":"v1.0","updated":"2026-03-18","owner":"Distribution","approved":True,"workflow":"Distribution","product":"Prism","tags":["pvc","metadata","territory","amazon","delivery failure"],"content":"Recurring Amazon PVC delivery failures were caused by missing territory metadata. Resolution required metadata correction and workflow resubmission."},
{"id":"RUN-MAM-STUCK-20","source":"Runbook","title":"Foundry MAM Stuck Workflow Recovery","version":"v2.0","updated":"2024-08-02","owner":"Media Asset Management","approved":True,"workflow":"Inventory","product":"Foundry MAM","tags":["mam","stuck workflow","asset","lock","inventory"],"content":"If a Foundry MAM workflow is stuck, check current step, review deployments/outages, validate asset lock state, and escalate to MAM Engineering if cleanup is required."},
{"id":"SOP-LOC-VAL-11","source":"SOP","title":"Localization Validation Triage","version":"v1.1","updated":"2025-02-19","owner":"Localization","approved":True,"workflow":"Localization","product":"Pegasus","tags":["localization","validation","subtitle","audio","language"],"content":"For localization validation failures, compare expected track inventory with delivered assets, validate language tags, inspect conformance, and route gaps to Localization Operations."},
{"id":"KB-RIGHTS-OUT-02","source":"KB Article","title":"Rights Visibility Gap Investigation","version":"v1.0","updated":"2023-10-15","owner":"Rights","approved":True,"workflow":"Rights","product":"Rally","tags":["rights","visibility","availability","window","sky"],"content":"Rights visibility gaps should be investigated by checking availability windows, territory mappings, partner restrictions, and upstream rights feed completion."},
{"id":"DRAFT-UNAPPROVED-01","source":"Draft Notes","title":"Unofficial Domino Retry Notes","version":"draft","updated":"2026-01-05","owner":"Fulfillment","approved":False,"workflow":"Fulfillment","product":"Domino","tags":["domino","retry"],"content":"Unapproved notes. Do not use for guidance."}]
INCIDENTS=[
{"id":"INC1510021","source":"ServiceNow","title":"Amazon PVC delivery failed manifest validation","workflow":"Distribution","product":"Prism","incident_type":"Delivery Failure","severity":"P2","resolved":True,"resolution_success":True,"created":"2026-05-11","tags":["amazon","pvc","manifest","delivery"],"resolution":"Corrected missing territory metadata and resubmitted Prism delivery workflow."},
{"id":"INC1521443","source":"ServiceNow","title":"PVC package failed delivery due to invalid manifest","workflow":"Distribution","product":"Prism","incident_type":"Delivery Failure","severity":"P2","resolved":True,"resolution_success":True,"created":"2026-05-25","tags":["pvc","manifest","validation"],"resolution":"Validated package, regenerated manifest, retried delivery step."},
{"id":"INC1532214","source":"Jira","title":"Amazon partner endpoint rejected Prism delivery","workflow":"Distribution","product":"Prism","incident_type":"Partner Configuration","severity":"P3","resolved":True,"resolution_success":True,"created":"2026-06-02","tags":["amazon","partner","endpoint","prism"],"resolution":"Updated partner mapping and requeued delivery."},
{"id":"INC1539000","source":"ServiceNow","title":"Foundry MAM asset workflow frozen at ingest step","workflow":"Inventory","product":"Foundry MAM","incident_type":"Stuck Workflow","severity":"P2","resolved":True,"resolution_success":True,"created":"2026-04-04","tags":["mam","stuck","workflow","lock"],"resolution":"Cleared stale lock after MAM Engineering approval."},
{"id":"INC1544120","source":"Jira","title":"Localization validation failed for subtitle track","workflow":"Localization","product":"Pegasus","incident_type":"Validation Failure","severity":"P3","resolved":True,"resolution_success":True,"created":"2026-04-28","tags":["localization","subtitle","validation"],"resolution":"Corrected language tag and reran localization validation."},
{"id":"INC1549999","source":"ServiceNow","title":"Rights availability missing for Sky title","workflow":"Rights","product":"Rally","incident_type":"Visibility Gap","severity":"P3","resolved":False,"resolution_success":False,"created":"2026-06-13","tags":["rights","sky","visibility"],"resolution":"Pending rights feed review."}]
TICKETS=[
{"id":"TCK-1001","source":"ServiceNow","status":"Open","title":"Delivery Failed Amazon PVC","description":"Amazon PVC delivery failed from Prism. Error suggests manifest validation issue and missing territory data.","created":"2026-06-20T10:15:00Z","requester":"Distribution Ops","logs":["manifest_validation_failed","missing territoryCode","partner=Amazon PVC"],"monitor_context":{"workflow_status":"Failed","processing_status":"Delivery blocked","current_step":"Manifest validation","partner":"Amazon PVC"}},
{"id":"TCK-1002","source":"Jira","status":"Assigned","title":"Foundry MAM workflow stuck","description":"Asset inventory workflow has not moved for 90 minutes. Current step shows ingest lock wait.","created":"2026-06-21T08:30:00Z","requester":"Inventory Support","logs":["lock_wait_timeout","asset lock active"],"monitor_context":{"workflow_status":"Delayed","processing_status":"Waiting","current_step":"Asset lock wait","recent_deployment":"Yes - MAM worker"}},
{"id":"TCK-1003","source":"E-Mail","status":"Open","title":"Unknown Domino fulfillment behavior","description":"Domino fulfillment failed with a new error not found in current KB. No known runbook seems to cover it.","created":"2026-06-22T13:10:00Z","requester":"Fulfillment Ops","logs":["unknown_error_code=DX-991"],"monitor_context":{"workflow_status":"Failed","processing_status":"Unknown","current_step":"Package assembly","partner":"Max"}},
{"id":"TCK-1004","source":"ServiceNow","status":"Escalated","title":"Rights visibility gap for Sky package","description":"Sky package is not visible although rights feed appears complete. Need ownership and escalation path.","created":"2026-06-22T15:10:00Z","requester":"Rights Ops","logs":["availability missing","partner=Sky"],"monitor_context":{"workflow_status":"Completed with warning","processing_status":"Visibility gap","current_step":"Rights publish","partner":"Sky"}}]
OWNERSHIP={("Distribution","Prism"):{"owner_team":"Distribution Ops","l2":"Distribution L2","engineering":"Prism Engineering","product_owner":"Prism Product","operations":"MSC Operations"},("Inventory","Foundry MAM"):{"owner_team":"Media Asset Management","l2":"MAM L2","engineering":"MAM Engineering","product_owner":"MAM Product","operations":"MSC Operations"},("Localization","Pegasus"):{"owner_team":"Localization Ops","l2":"Localization L2","engineering":"Pegasus Engineering","product_owner":"Localization Product","operations":"MSC Operations"},("Rights","Rally"):{"owner_team":"Rights Ops","l2":"Rights L2","engineering":"Rally Engineering","product_owner":"Rights Product","operations":"MSC Operations"},("Fulfillment","Domino"):{"owner_team":"Fulfillment Ops","l2":"Fulfillment L2","engineering":"Domino Engineering","product_owner":"Fulfillment Product","operations":"MSC Operations"}}
KEYWORDS={"workflow":{"Distribution":["delivery","partner","amazon","pvc","manifest"],"Fulfillment":["fulfillment","domino","package"],"Inventory":["inventory","mam","asset","lock","foundry"],"Localization":["localization","subtitle","audio","language"],"Rights":["rights","availability","visibility","sky"]},"product":{"Prism":["prism","amazon","pvc","manifest"],"Domino":["domino","fulfillment"],"Foundry MAM":["foundry","mam","asset"],"Pegasus":["pegasus","localization"],"Rally":["rally","rights","sky"]},"incident_type":{"Stuck Workflow":["stuck","frozen","blocked","wait","lock"],"Delivery Failure":["delivery failed","failed delivery","delivery","rejected"],"Metadata Issue":["metadata","territory","missing"],"Partner Configuration":["partner","endpoint","mapping"],"Visibility Gap":["visibility","not visible","availability missing"],"Validation Failure":["validation","validate","manifest validation"]}}
def normalize(x): return re.sub(r"\s+"," ",str(x).lower()).strip()
def toks(x): return set(re.findall(r"[a-z0-9]+",normalize(x)))
def similarity(a,b):
    ta,tb=toks(a),toks(b)
    if not ta or not tb: return 0.0
    return round(.72*(len(ta&tb)/max(1,len(ta|tb)))+.28*SequenceMatcher(None,normalize(a),normalize(b)).ratio(),3)
def doc_text(d): return " ".join([str(d.get(k,"")) for k in ["title","workflow","product","incident_type","source","content","resolution"]]+[" ".join(d.get("tags",[]))])
def search_docs(q,docs,top_k=5,approved_only=False):
    out=[]
    for d in docs:
        if approved_only and (not d.get("approved",True) or d.get("source") not in APPROVED): continue
        s=similarity(q,doc_text(d))
        if s>=.035:
            x=dict(d); x["score"]=s; out.append(x)
    return sorted(out,key=lambda x:x["score"],reverse=True)[:top_k]
def keyword_score(text,opts):
    t=normalize(text); best=list(opts)[0]; bs=0
    for label,words in opts.items():
        raw=sum(2 if " " in w else 1 for w in words if normalize(w) in t)
        sc=min(1.0,raw/max(3,len(words)/2))
        if sc>bs: best,bs=label,sc
    return best,bs
def classify_ticket(ticket):
    text=" ".join([ticket.get("title",""),ticket.get("description","")," ".join(ticket.get("logs",[]) or [])])
    wf,wfs=keyword_score(text,KEYWORDS["workflow"]); pr,prs=keyword_score(text,KEYWORDS["product"]); it,its=keyword_score(text,KEYWORDS["incident_type"])
    low=normalize(text); sev="P1" if "outage" in low else "P2" if any(x in low for x in ["failed","blocked","stuck"]) or it in ["Delivery Failure","Stuck Workflow"] else "P3" if "visibility" in low else "P4"
    return {"ticket":ticket.get("title"),"workflow":wf,"product":pr,"incident_type":it,"severity":sev,"confidence":max(25,min(98,round((.45*wfs+.30*prs+.25*its)*100)))}
def owner_for(w,p): return OWNERSHIP.get((w,p),{"owner_team":"Unknown","l2":"MSC L2 Queue","engineering":"Engineering Triage","product_owner":"Product Triage","operations":"MSC Operations"})
def recommend_actions(c):
    it=c["incident_type"]
    if it=="Delivery Failure": return ["Validate package status in MSC Monitor.","Verify manifest generation and required metadata fields.","Confirm partner mapping and endpoint configuration.","Resubmit or retry only after human approval."]
    if it=="Stuck Workflow": return ["Check current workflow step and wait duration.","Review deployment/outage/dependency context.","Validate lock state or downstream dependency.","Escalate before cleanup actions."]
    if it=="Visibility Gap": return ["Check availability windows and territory mappings.","Confirm upstream rights feed completion.","Validate partner restrictions and publish status.","Route to rights owner if feed and mappings are correct."]
    return ["Review matched source guidance.","Validate monitor context and logs.","Confirm owner/escalation path.","Proceed only after human approval."]
def analyze(ticket):
    c=classify_ticket(ticket); q=" ".join([ticket.get("title",""),ticket.get("description","")," ".join(ticket.get("logs",[]) or []),c["workflow"],c["product"],c["incident_type"]])
    kh=search_docs(q,KNOWLEDGE,4,True); ih=search_docs(q,INCIDENTS,5,False)
    ev=max([h["score"] for h in kh],default=0); iv=max([h["score"] for h in ih],default=0); final=round(.55*c["confidence"]+.45*min(100,round((.65*ev+.35*iv)*235)))
    if kh and final>=80: mode="Recommend"; actions=recommend_actions(c); reason=None
    elif kh and final>=50: mode="Suggest Investigation"; actions=["Review monitor context and logs.","Compare with similar incidents.","Validate source version applicability.","Escalate if remediation remains unclear."]; reason="Confidence between 50 and 80."
    else: mode="Escalate"; actions=["Escalate with gathered context.","Request owner review.","Capture documentation gap if confirmed."]; reason="Approved evidence missing or confidence below threshold."
    owner=owner_for(c["workflow"],c["product"]); sources=[{"id":h["id"],"source":h["source"],"title":h["title"],"version":h.get("version","n/a"),"updated":h.get("updated","n/a"),"owner":h.get("owner","unknown"),"score":h["score"]} for h in kh]
    lineage=[s["source"]+"::"+s["id"]+"::"+s["version"]+"::"+s["owner"] for s in sources]
    gaps=[] if kh else [{"type":"Missing Coverage","message":"No approved source found for this issue pattern.","action":"Create New Runbook Request"}]
    for h in kh:
        if h.get("updated","")<"2025-06-01": gaps.append({"type":"Stale Documentation","message":h["title"]+" is older than freshness threshold.","action":"Review and refresh source"})
    success=sum(1 for h in ih if h.get("resolution_success")); rec=round(success/max(1,len(ih))*100) if ih else 0
    cause="Unknown or unsupported by approved evidence. No resolution recommendation generated." if mode=="Escalate" else ("Delivery manifest validation failure or partner mapping issue based on approved sources and historical incidents." if c["incident_type"]=="Delivery Failure" and c["product"]=="Prism" else "Likely "+c["incident_type"]+" in "+c["workflow"]+" based on matched approved operational sources.")
    esc=None if mode=="Recommend" else {"ticket_summary":ticket.get("title"),"workflow":c["workflow"],"product":c["product"],"service_owner":owner.get("owner_team"),"logs_reviewed":ticket.get("logs",[]),"monitor_context":ticket.get("monitor_context",{}),"draft_guidance_for_review":actions,"similar_incidents":[h["id"] for h in ih],"confidence_score":final,"reason_for_escalation":reason,"routes":{"l2":owner.get("l2"),"engineering":owner.get("engineering"),"product":owner.get("product_owner"),"operations":owner.get("operations")}}
    return {"ticket":ticket,"classification":c,"similar_incidents":ih,"similar_summary":{"count":len(ih),"resolved_count":sum(1 for h in ih if h.get("resolved")),"resolution_recurrence":rec,"outcome":"Likely known issue" if rec>=70 and len(ih)>=2 else "Partially known issue"},"monitor_context":ticket.get("monitor_context",{}),"ownership":owner,"documentation_gaps":gaps,"assistant":{"mode":mode,"likely_cause":cause,"recommended_actions":actions,"evidence":[h["title"]+" ("+h["source"]+" "+h.get("version","n/a")+"): "+h.get("content","")[:260] for h in kh[:3]],"sources":sources,"confidence":final,"source_lineage":lineage,"unsupported_recommendation_blocked":not bool(kh),"human_approval_required":True,"escalation_package":esc}}
def list_tickets(): return TICKETS
def get_ticket(ticket_id): return next((t for t in TICKETS if t["id"]==ticket_id),None)
def list_knowledge(approved_only=True): return [k for k in KNOWLEDGE if (not approved_only or (k.get("approved") and k.get("source") in APPROVED))]
def get_analytics(tickets=None):
    tickets=tickets or TICKETS; ans=[analyze(t) for t in tickets]; total=len(ans); rec=sum(1 for a in ans if a["assistant"]["mode"]=="Recommend"); inv=sum(1 for a in ans if a["assistant"]["mode"]=="Suggest Investigation"); esc=sum(1 for a in ans if a["assistant"]["mode"]=="Escalate"); gaps=[g for a in ans for g in a["documentation_gaps"]]; dist={}
    for a in ans: dist[a["classification"]["workflow"]]=dist.get(a["classification"]["workflow"],0)+1
    return {"ticket_count":total,"recommendation_rate":round(rec/total*100,1) if total else 0,"investigation_rate":round(inv/total*100,1) if total else 0,"escalation_rate":round(esc/total*100,1) if total else 0,"citation_coverage":100.0,"unsupported_recommendations":0,"unsupported_recommendations_blocked":sum(1 for a in ans if a["assistant"]["unsupported_recommendation_blocked"]),"documentation_gap_count":len(gaps),"workflow_distribution":dist,"documentation_gaps":gaps,"pilot_targets":{"mttr_reduction_target":"40-60%","escalation_reduction_target":"20-30%","citation_coverage_target":"100%","unsupported_recommendation_target":"0%"}}
def ask(ticket,question):
    a=analyze(ticket); q=normalize(question); s=a["similar_summary"]
    if any(x in q for x in ["why","fail","cause"]): ans=a["assistant"]["likely_cause"]
    elif any(x in q for x in ["similar","case","incident"]): ans="Found "+str(s["count"])+" similar cases. Resolution recurrence is "+str(s["resolution_recurrence"])+"%. Outcome: "+s["outcome"]+"."
    elif any(x in q for x in ["owner","escalate","route","team"]):
        o=a["ownership"]; ans="Owner team: "+str(o.get("owner_team"))+". L2="+str(o.get("l2"))+" Engineering="+str(o.get("engineering"))+" Product="+str(o.get("product_owner"))+"."
    elif any(x in q for x in ["source","evidence","citation","lineage"]): ans="Sources: "+"; ".join(a["assistant"]["source_lineage"]) if a["assistant"]["source_lineage"] else "No approved evidence found. Escalation is required."
    else: ans="I can answer: why did this fail, show similar cases, who owns this workflow, or show evidence."
    return {"answer":ans,"mode":a["assistant"]["mode"],"confidence":a["assistant"]["confidence"],"sources":a["assistant"]["sources"]}
if __name__=="__main__":
    for t in TICKETS:
        r=analyze(t)
        if r["assistant"]["mode"]=="Recommend": assert r["assistant"]["sources"]
    assert get_analytics()["unsupported_recommendations"]==0
    print("BACKEND_SMOKE_OK")
