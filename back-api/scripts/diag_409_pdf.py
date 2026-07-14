#!/usr/bin/env python3
"""Diagnóstico 409 PDF — captura missing_sections reales."""
from __future__ import annotations

import json
from pathlib import Path

import httpx

API = "http://localhost:8000"
EMAIL = "admin@arhiax.com"
PASSWORD = "arhiax-admin-2026"
OUT = Path("/tmp/eval_congelada")
KNOWN = [
    "52b5edd2-9915-42d5-b54b-e7236255b568",  # Ivania
    "0e66621a-0a66-4b64-9422-54015c1f8af0",  # Finanzas
    "f2df5e00-896f-4bc7-98a8-30630c2c8a32",  # Agro
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    c = httpx.Client(timeout=180.0)
    r = c.post(f"{API}/auth/login", data={"username": EMAIL, "password": PASSWORD})
    r.raise_for_status()
    c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    lst = c.get(f"{API}/pro/cases").json()
    items = lst.get("items") or []
    print(f"cases={len(items)}")
    for it in items[:15]:
        print(f"  {it.get('case_id')} | {it.get('client_name')} | {it.get('case_status')} | {it.get('id')}")

    ids = list(KNOWN)
    for it in items:
        name = it.get("client_name") or ""
        if any(x in name for x in ("CD Global", "Ivania", "Finanzas Norte", "Agroindustrial", "Cauca")):
            if it.get("id") not in ids:
                ids.append(it["id"])

    report = []
    for cid in ids:
        d = c.get(f"{API}/pro/cases/{cid}")
        if d.status_code != 200:
            print("skip", cid, d.status_code)
            continue
        case = d.json()
        entry = {
            "uuid": cid,
            "ref": case.get("case_id"),
            "client": case.get("client_name"),
            "status_before": case.get("case_status"),
            "phenomenon": ((case.get("phenomenon") or {}).get("summary") or {}).get("phenomenon_named"),
            "score": ((case.get("fusion_result") or {}).get("scoring") or {}).get("overall_score"),
        }
        print("\n====", entry["client"], entry["status_before"], "====")

        g = c.post(f"{API}/pro/cases/{cid}/generate-deliverables")
        entry["gen_before_approve"] = {"status": g.status_code, "body": _body(g)}
        print("gen", g.status_code, str(entry["gen_before_approve"]["body"])[:400])

        if case.get("case_status") == "review_pending":
            a = c.post(
                f"{API}/pro/cases/{cid}/approval",
                json={"action": "approve", "comment": "diag-409", "reviewer_name": "auto"},
            )
            entry["approve"] = {"status": a.status_code, "body": _body(a)}
            print("approve", a.status_code)

        g2 = c.post(f"{API}/pro/cases/{cid}/generate-deliverables")
        entry["gen_after"] = {"status": g2.status_code, "body": _body(g2)}
        print("gen2", g2.status_code, str(entry["gen_after"]["body"])[:800])

        pdf = c.get(f"{API}/pro/cases/{cid}/download/pdf")
        if pdf.status_code == 200:
            entry["pdf"] = {"status": 200, "bytes": len(pdf.content), "magic": pdf.content[:4].decode("latin1", "ignore")}
            (OUT / f"{case.get('case_id','case')}.pdf").write_bytes(pdf.content)
        else:
            entry["pdf"] = {"status": pdf.status_code, "body": _body(pdf)}
        print("pdf", entry["pdf"])
        report.append(entry)

    path = OUT / "diag_409.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nWROTE", path)


def _body(resp: httpx.Response):
    try:
        return resp.json()
    except Exception:
        return resp.text[:800]


if __name__ == "__main__":
    main()
