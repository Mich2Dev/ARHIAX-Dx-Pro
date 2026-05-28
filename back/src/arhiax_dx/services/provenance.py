"""Certificate signing helpers for ARHIAX Dx."""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

from arhiax_dx.config import Settings
from arhiax_dx.models import CapabilityRecord, GovernanceDecision, RuleResult, SignedCertificate
from arhiax_dx.services.evidence import canonical_json


class ProvenanceSigner:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._private_key = self._load_private_key(settings.private_key_b64)

    def issue_certificate(self, execution_fingerprint: str, decision: GovernanceDecision, rules: list[RuleResult], records: list[CapabilityRecord], evidence_hash: str) -> SignedCertificate:
        certificate_id = str(uuid4())
        issued_at = datetime.now(timezone.utc)
        consulted_capabilities = [{"capability": record.capability, "observed_at": record.observed_at.isoformat(), "payload_hash": record.payload_hash} for record in records]
        unsigned = {
            "certificate_id": certificate_id,
            "issued_at": issued_at.isoformat(),
            "execution_fingerprint": execution_fingerprint,
            "decision": decision.status.value,
            "policy_bundles": decision.policy_bundles,
            "governance_metadata": self.settings.governance_metadata(),
            "consulted_capabilities": consulted_capabilities,
            "rules": [rule.model_dump(mode="json") for rule in rules],
            "evidence_hash": evidence_hash,
            "public_key_id": self.settings.public_key_id,
        }
        signature = self._private_key.sign(canonical_json(unsigned).encode("utf-8"))
        return SignedCertificate(signature=base64.b64encode(signature).decode("ascii"), **unsigned)

    def public_key_b64(self) -> str:
        public_bytes = self._private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        return base64.b64encode(public_bytes).decode("ascii")

    def key_material_preview(self) -> str:
        return hashlib.sha256(self.public_key_b64().encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _load_private_key(raw_value: str) -> Ed25519PrivateKey:
        if raw_value:
            return Ed25519PrivateKey.from_private_bytes(base64.b64decode(raw_value.encode("ascii")))
        return Ed25519PrivateKey.generate()
