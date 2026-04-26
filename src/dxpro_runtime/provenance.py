"""Signed provenance certificates for DX Pro decisions."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from typing import Any


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


class ProvenanceSigner:
    def __init__(self, secret: str, public_key_id: str = "dxpro-local-hmac") -> None:
        self.secret = secret.encode("utf-8")
        self.public_key_id = public_key_id

    def issue_certificate(
        self,
        *,
        trace_id: str,
        request_id: str,
        decision: dict[str, Any],
        rule_results: list[dict[str, Any]],
        evidence_hmac: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        unsigned = {
            "certificate_id": str(uuid.uuid4()),
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace_id,
            "request_id": request_id,
            "decision": decision,
            "rule_ids": [rule["rule_id"] for rule in rule_results],
            "evidence_hmac": evidence_hmac,
            "metadata": metadata,
            "public_key_id": self.public_key_id,
            "signature_algorithm": "HMAC-SHA256",
        }
        signature = hmac.new(self.secret, canonical_json(unsigned).encode("utf-8"), hashlib.sha256).hexdigest()
        return {**unsigned, "signature": signature}
