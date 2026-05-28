from __future__ import annotations

import base64
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from arhiax_dx.config import Settings
from arhiax_dx.main import create_app


@pytest.fixture()
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture()
def specs_path(repo_root: Path) -> Path:
    return repo_root / "specs"


@pytest.fixture()
def private_key_b64() -> str:
    key = Ed25519PrivateKey.generate()
    raw = key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return base64.b64encode(raw).decode("ascii")


@pytest.fixture()
def settings(tmp_path: Path, specs_path: Path, private_key_b64: str) -> Settings:
    return Settings(
        environment="test",
        mode="test",
        ledger_path=tmp_path / "ledger.jsonl",
        install_manifest_path=tmp_path / "install" / "client-install-manifest.json",
        specs_path=specs_path,
        private_key_b64=private_key_b64,
        gemini_api_key="gemini-test-key",
        anthropic_api_key="anthropic-test-key",
        hic_webhook_url="https://hooks.test/hic",
        whatsapp_business_webhook="https://hooks.test/wa",
    )


@pytest.fixture()
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


@pytest.fixture()
def request_payload() -> dict:
    return {
        "requested_autonomy_level": "A1",
        "mandate": {
            "organization_name": "Cliente Demo",
            "domain": "diagnostico organizacional",
            "subprocess": "evaluacion de capacidades",
            "size_org": "250",
            "objective": "Diagnosticar cuellos de botella y producir recomendaciones ejecutivas",
        },
        "client": {
            "client_id": "client-001",
            "legal_name": "Cliente Demo S.A.S.",
            "authorized_boundary_id": "boundary-diagnostico-org",
            "data_residency": "CO",
        },
        "requested_tools": ["g01_receptor", "g10a_scoring", "g11a_bayesiano", "g14_qa_control"],
        "requested_operations": ["modelInvoke", "toolCall", "dataAccess", "interAgentCall"],
        "requested_data_scopes": ["organizational_context", "survey_responses", "report_outputs", "audit_log"],
        "processing_profile": {
            "store_raw_respondent_data": False,
            "publish_report": False,
            "issue_certificate": True,
            "retention_days": 30,
        },
        "simulation": {
            "current_weekday": 2,
            "current_hour": 10,
            "qa_score": 91,
            "irr_alpha": 0.82,
            "delta_sigma": 1.4,
        },
    }
