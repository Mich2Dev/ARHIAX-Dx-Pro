from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("DXPRO_RUNTIME_ROOT", str(ROOT))

from dxpro_runtime.catalog import DxProCatalog
from dxpro_runtime.config import load_config
from dxpro_runtime.diagnostics import DiagnosticService
from dxpro_runtime.evidence import EvidenceLedger
from dxpro_runtime.policy import PolicyEngine
from dxpro_runtime.runtime import DxProRuntime


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/run_fixture.py fixtures/run_step_permit.json")
        return 2
    fixture_path = (ROOT / sys.argv[1]).resolve()
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    config = load_config()
    runtime = DxProRuntime(
        policy_engine=PolicyEngine(config.policy_bundle_path, config.opa_url),
        ledger=EvidenceLedger(config.ledger_path, config.evidence_secret),
    )
    if "mandate" in payload and "client" in payload:
        response = DiagnosticService(config, DxProCatalog(), runtime).evaluate(payload)
        print(json.dumps(response, indent=2, ensure_ascii=False))
        return 0
    response = runtime.run_step(payload)
    print(json.dumps(response.to_dict(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
