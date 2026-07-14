#!/usr/bin/env python3
import json
import httpx

API = "http://localhost:8000"
c = httpx.Client(timeout=60)
r = c.post(f"{API}/auth/login", data={"username": "admin@arhiax.com", "password": "arhiax-admin-2026"})
c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
cid = "52b5edd2-9915-42d5-b54b-e7236255b568"
case = c.get(f"{API}/pro/cases/{cid}").json()
stages = case.get("stages") or case.get("pipeline_stages") or []
g06 = [s for s in stages if s.get("tool_name") == "g06_bpmn_architect"]
print("g06", len(g06), g06[0].get("status") if g06 else None)
if g06:
    print(json.dumps(g06[0].get("output") or {}, ensure_ascii=False)[:3000])
sym = (case.get("input_payload") or {}).get("symptom", "")
print("SYMPTOM:\n", sym)
# also run coherence helper if importable
try:
    from api.pipeline.pro_coherence import evaluate_agent_output_coherence, build_case_anchor
    anchor = build_case_anchor(case.get("input_payload") or {})
    print("ANCHOR", json.dumps(anchor, ensure_ascii=False)[:800])
    issues = evaluate_agent_output_coherence(
        "g06_bpmn_architect", g06[0].get("output") or {}, anchor
    )
    print("ISSUES", issues)
except Exception as e:
    print("coherence import fail", e)
