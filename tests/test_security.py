"""Tests for the production-grade security layer."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dxpro_runtime.api import create_app
from dxpro_runtime.auth import API_KEY_HEADER, ApiKeyAuth
from dxpro_runtime.config import RuntimeConfig, load_config
from dxpro_runtime.rate_limit import RateLimiter


_VALID_KEY = "test-api-key-with-sufficient-entropy-aaaa"
_OTHER_KEY = "another-api-key-with-sufficient-entropy-bb"
_STRONG_SECRET = "test-evidence-secret-with-32-plus-characters"


def _build_client(
    tmp_path: Path,
    *,
    api_keys: tuple[str, ...] = (),
    env: str = "development",
    rate_limit_per_minute: int = 60,
    rate_limit_burst: int | None = None,
) -> TestClient:
    config = RuntimeConfig(
        root_dir=tmp_path,
        ledger_path=tmp_path / "evidence.jsonl",
        evidence_secret=_STRONG_SECRET,
        policy_bundle_path=tmp_path / "missing-bundle",
        case_store_root=tmp_path / "cases",
        export_root=tmp_path / "exports",
        env=env,
        api_keys=api_keys,
        rate_limit_per_minute=rate_limit_per_minute,
        rate_limit_burst=rate_limit_burst,
    )
    return TestClient(create_app(config))


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def test_no_auth_required_when_no_keys_configured_in_dev(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    assert client.get("/v1/compliance/posture").status_code == 200


def test_health_endpoints_are_always_public(tmp_path: Path) -> None:
    client = _build_client(tmp_path, api_keys=(_VALID_KEY,))
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200
    assert client.get("/").status_code == 200


def test_protected_endpoint_rejects_missing_api_key(tmp_path: Path) -> None:
    client = _build_client(tmp_path, api_keys=(_VALID_KEY,))
    response = client.get("/v1/compliance/posture")
    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "missing_api_key"


def test_protected_endpoint_rejects_wrong_api_key(tmp_path: Path) -> None:
    client = _build_client(tmp_path, api_keys=(_VALID_KEY,))
    response = client.get(
        "/v1/compliance/posture",
        headers={API_KEY_HEADER: "wrong-key"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "invalid_api_key"


def test_protected_endpoint_accepts_valid_api_key(tmp_path: Path) -> None:
    client = _build_client(tmp_path, api_keys=(_VALID_KEY, _OTHER_KEY))
    for key in (_VALID_KEY, _OTHER_KEY):
        response = client.get(
            "/v1/compliance/posture",
            headers={API_KEY_HEADER: key},
        )
        assert response.status_code == 200, f"key {key} should be accepted"


def test_api_key_fingerprint_is_deterministic_and_short() -> None:
    fp = ApiKeyAuth.fingerprint(_VALID_KEY)
    assert fp == ApiKeyAuth.fingerprint(_VALID_KEY)
    assert len(fp) == 12
    assert _VALID_KEY not in fp  # never leaks the key


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

def test_rate_limiter_blocks_when_capacity_exhausted() -> None:
    limiter = RateLimiter(requests_per_minute=60, burst=2)
    limiter.check("client-A")
    limiter.check("client-A")
    with pytest.raises(Exception) as exc:
        limiter.check("client-A")
    assert exc.value.status_code == 429


def test_rate_limiter_isolates_per_identifier() -> None:
    limiter = RateLimiter(requests_per_minute=60, burst=1)
    limiter.check("client-A")
    limiter.check("client-B")  # B has its own bucket
    with pytest.raises(Exception):
        limiter.check("client-A")


def test_rate_limit_returns_429_via_http(tmp_path: Path) -> None:
    client = _build_client(
        tmp_path,
        api_keys=(_VALID_KEY,),
        rate_limit_per_minute=60,
        rate_limit_burst=2,
    )
    headers = {API_KEY_HEADER: _VALID_KEY}

    assert client.get("/v1/compliance/posture", headers=headers).status_code == 200
    assert client.get("/v1/compliance/posture", headers=headers).status_code == 200
    response = client.get("/v1/compliance/posture", headers=headers)
    assert response.status_code == 429
    assert "Retry-After" in response.headers


# ---------------------------------------------------------------------------
# Production-mode hardening
# ---------------------------------------------------------------------------

def test_production_rejects_default_evidence_secret(monkeypatch) -> None:
    monkeypatch.setenv("DXPRO_ENV", "production")
    monkeypatch.delenv("DXPRO_EVIDENCE_SECRET", raising=False)
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    with pytest.raises(RuntimeError, match="DXPRO_EVIDENCE_SECRET"):
        load_config()


def test_production_rejects_short_evidence_secret(monkeypatch) -> None:
    monkeypatch.setenv("DXPRO_ENV", "production")
    monkeypatch.setenv("DXPRO_EVIDENCE_SECRET", "too-short")
    monkeypatch.setenv("DXPRO_API_KEYS", _VALID_KEY)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    with pytest.raises(RuntimeError, match="32 characters"):
        load_config()


def test_production_requires_api_keys(monkeypatch) -> None:
    monkeypatch.setenv("DXPRO_ENV", "production")
    monkeypatch.setenv("DXPRO_EVIDENCE_SECRET", _STRONG_SECRET)
    monkeypatch.delenv("DXPRO_API_KEYS", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    with pytest.raises(RuntimeError, match="DXPRO_API_KEYS"):
        load_config()


def test_production_requires_anthropic_api_key(monkeypatch) -> None:
    monkeypatch.setenv("DXPRO_ENV", "production")
    monkeypatch.setenv("DXPRO_EVIDENCE_SECRET", _STRONG_SECRET)
    monkeypatch.setenv("DXPRO_API_KEYS", _VALID_KEY)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        load_config()


def test_production_with_full_config_loads(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DXPRO_ENV", "production")
    monkeypatch.setenv("DXPRO_EVIDENCE_SECRET", _STRONG_SECRET)
    monkeypatch.setenv("DXPRO_API_KEYS", f"{_VALID_KEY},{_OTHER_KEY}")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-12345")
    monkeypatch.setenv("DXPRO_RUNTIME_ROOT", str(tmp_path))
    monkeypatch.delenv("VAULT_ADDR", raising=False)

    config = load_config()
    assert config.is_production
    assert config.api_keys == (_VALID_KEY, _OTHER_KEY)
    assert config.anthropic_api_key == "sk-test-12345"


def test_protected_endpoint_returns_503_when_prod_misconfigured(tmp_path: Path) -> None:
    """Production env with no API keys configured surfaces 503, not 401."""
    config = RuntimeConfig(
        root_dir=tmp_path,
        ledger_path=tmp_path / "evidence.jsonl",
        evidence_secret=_STRONG_SECRET,
        policy_bundle_path=tmp_path / "missing-bundle",
        case_store_root=tmp_path / "cases",
        export_root=tmp_path / "exports",
        env="production",
        api_keys=(),
    )
    client = TestClient(create_app(config))
    response = client.get("/v1/compliance/posture")
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "auth_misconfigured"
