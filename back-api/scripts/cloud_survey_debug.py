#!/usr/bin/env python3
import httpx, re, json

BASE = "https://arhiax-dx-pro-187668243215.southamerica-east1.run.app"
API = BASE + "/api/backend"

# 1) Check JS bundle for API URL
html = httpx.get(BASE + "/dashboard-pro", timeout=30).text
chunks = re.findall(r"/_next/static/chunks/[^\"']+\.js", html)
found_localhost = found_backend = 0
for ch in chunks[:30]:
    js = httpx.get(BASE + ch, timeout=30).text
    if "localhost:8000" in js:
        found_localhost += 1
    if "/api/backend" in js:
        found_backend += 1
print("bundle chunks scanned:", min(30, len(chunks)))
print("chunks with localhost:8000:", found_localhost)
print("chunks with /api/backend:", found_backend)

# 2) Get Ivania case survey token
r = httpx.post(API + "/auth/login", data={"username": "admin@arhiax.com", "password": "arhiax-admin-2026"}, timeout=40)
h = {"Authorization": "Bearer " + r.json()["access_token"]}
cases = httpx.get(API + "/pro/cases", headers=h, timeout=40).json()["items"]
for c in cases:
    if "b957" in c.get("case_id", "") or "3046" in c.get("case_id", ""):
        d = httpx.get(API + f"/pro/cases/{c['id']}", headers=h, timeout=40).json()
        token = (d.get("survey") or {}).get("token")
        status = d.get("case_status")
        sstat = (d.get("survey") or {}).get("status")
        print("\n===", c["case_id"], d.get("client_name"), "===")
        print("case_status:", status, "| survey_status:", sstat, "| token:", token)
        if token:
            page = httpx.get(BASE + f"/survey/pro/{token}", timeout=40)
            print("survey page HTTP:", page.status_code)
            pub = httpx.get(API + f"/pro/survey/{token}", timeout=40)
            print("survey API HTTP:", pub.status_code, pub.text[:200])
            wrong = httpx.get(API + f"/survey/{token}", timeout=40)
            print("WRONG path /survey/{token} HTTP:", wrong.status_code, wrong.text[:120])
