"""Tests for the research module: source clients + hypothesis builder."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from dxpro_runtime.research import (
    HypothesisBuilder,
    LensClient,
    OpenAlexClient,
)
from dxpro_runtime.research.hypothesis_builder import _verify_provenance
from dxpro_runtime.research.models import Paper, Patent


# ---------------------------------------------------------------------------
# Helpers — fake httpx clients without going to the network
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "fake error",
                request=httpx.Request("GET", "http://test"),
                response=httpx.Response(self.status_code),
            )

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeHttpClient:
    def __init__(
        self,
        get_payload: dict[str, Any] | None = None,
        post_payload: dict[str, Any] | None = None,
        status_code: int = 200,
    ) -> None:
        self._get_payload = get_payload or {}
        self._post_payload = post_payload or {}
        self._status = status_code
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append(("GET", {"url": url, **kwargs}))
        return _FakeResponse(self._get_payload, self._status)

    def post(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append(("POST", {"url": url, **kwargs}))
        return _FakeResponse(self._post_payload, self._status)


# ---------------------------------------------------------------------------
# OpenAlexClient
# ---------------------------------------------------------------------------


def test_openalex_parses_works_into_papers() -> None:
    payload = {
        "results": [
            {
                "id": "https://openalex.org/W123",
                "title": "Reducing manual handoffs in service ops",
                "doi": "https://doi.org/10.1234/abc",
                "publication_year": 2023,
                "authorships": [
                    {"author": {"display_name": "Ada Lovelace"}},
                    {"author": {"display_name": "Alan Turing"}},
                ],
                "abstract_inverted_index": {"Reducing": [0], "handoffs": [1]},
                "cited_by_count": 42,
                "primary_location": {"landing_page_url": "https://example.com/p1"},
            }
        ]
    }
    client = OpenAlexClient(http_client=_FakeHttpClient(get_payload=payload))
    papers = client.search_papers("manual handoff reduction", limit=5)

    assert len(papers) == 1
    paper = papers[0]
    assert paper.doi == "10.1234/abc"
    assert paper.year == 2023
    assert "Ada Lovelace" in paper.authors
    assert paper.citations == 42
    assert "Reducing" in paper.abstract


def test_openalex_returns_empty_on_http_error() -> None:
    client = OpenAlexClient(http_client=_FakeHttpClient(status_code=503))
    assert client.search_papers("anything") == []


# ---------------------------------------------------------------------------
# LensClient
# ---------------------------------------------------------------------------


def test_lens_returns_empty_when_token_missing(monkeypatch) -> None:
    monkeypatch.delenv("LENS_API_TOKEN", raising=False)
    client = LensClient(http_client=_FakeHttpClient())
    assert client.is_configured is False
    assert client.search_patents("any query") == []


def test_lens_parses_patent_response() -> None:
    payload = {
        "data": [
            {
                "lens_id": "000-000-001",
                "biblio": {
                    "invention_title": [{"text": "Automated triage system"}],
                    "publication_reference": {"country": "US", "doc_number": "12345678"},
                    "parties": {
                        "inventors": [{"extracted_name": {"value": "Jane Doe"}}],
                        "applicants": [{"extracted_name": {"value": "ACME Corp"}}],
                    },
                },
                "abstract": [{"text": "An automated triage routes incoming requests..."}],
                "jurisdiction": "US",
                "date_published": "2023-05-01",
            }
        ]
    }
    client = LensClient(api_token="fake", http_client=_FakeHttpClient(post_payload=payload))
    patents = client.search_patents("automated triage", limit=5)

    assert len(patents) == 1
    patent = patents[0]
    assert patent.publication_number == "US-12345678"
    assert "Jane Doe" in patent.inventors
    assert "ACME Corp" in patent.assignees
    assert patent.jurisdiction == "US"


# ---------------------------------------------------------------------------
# Provenance check — the anti-hallucination guard
# ---------------------------------------------------------------------------


def test_verify_provenance_rejects_fabricated_dois() -> None:
    papers = [Paper(id="P1", title="Real paper", doi="10.real/doi")]
    pack = {
        "hypotheses": [
            {
                "id": "H1",
                "statement": "Should be kept",
                "evidence": {"paper_dois": ["10.real/doi"], "patent_ids": []},
            },
            {
                "id": "H2",
                "statement": "Should be rejected — fabricated DOI",
                "evidence": {"paper_dois": ["10.invented/fake"], "patent_ids": []},
            },
        ]
    }
    verified = _verify_provenance(pack, papers, [])
    assert len(verified["hypotheses"]) == 1
    assert verified["hypotheses"][0]["id"] == "H1"
    assert verified["provenance_check"]["rejected"] == 1
    assert "10.invented/fake" in verified["provenance_check"]["rejected_details"][0]["fabricated_dois"]


def test_verify_provenance_rejects_fabricated_patents() -> None:
    patents = [Patent(id="L1", title="Real patent", publication_number="US-1-A")]
    pack = {
        "hypotheses": [
            {
                "id": "H1",
                "statement": "ok",
                "evidence": {"paper_dois": [], "patent_ids": ["US-1-A"]},
            },
            {
                "id": "H2",
                "statement": "fabricated patent id",
                "evidence": {"paper_dois": [], "patent_ids": ["US-99999-Z"]},
            },
        ]
    }
    verified = _verify_provenance(pack, [], patents)
    accepted_ids = [h["id"] for h in verified["hypotheses"]]
    assert "H1" in accepted_ids
    assert "H2" not in accepted_ids


# ---------------------------------------------------------------------------
# HypothesisBuilder — stub mode (no LLM)
# ---------------------------------------------------------------------------


def test_builder_stub_mode_returns_evidence_without_synthesis() -> None:
    fake_openalex_payload = {
        "results": [
            {
                "id": "https://openalex.org/W1",
                "title": "Process automation reduces lead time",
                "doi": "https://doi.org/10.1/auto",
                "publication_year": 2022,
                "authorships": [],
                "abstract_inverted_index": {},
                "cited_by_count": 5,
            }
        ]
    }
    builder = HypothesisBuilder(
        llm_client=None,  # stub mode
        openalex=OpenAlexClient(http_client=_FakeHttpClient(get_payload=fake_openalex_payload)),
        lens=LensClient(http_client=_FakeHttpClient()),  # no token, returns []
    )
    pack = builder.build(
        engagement_id="eng-001",
        domain="loan operations",
        pain_points=["manual handoff delays"],
    )

    assert pack["llm_mode"] == "stub"
    assert pack["hypotheses"] == []
    assert pack["evidence_summary"]["papers_consulted"] == 1
    assert pack["evidence_summary"]["patents_consulted"] == 0
    assert pack["evidence"]["papers"][0]["doi"] == "10.1/auto"


# ---------------------------------------------------------------------------
# HypothesisBuilder — claude mode with stub LLM
# ---------------------------------------------------------------------------


class _FakeLlmClient:
    """Returns whatever payload it was constructed with."""

    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    def complete(self, *, model: str, system: str, user: str) -> dict[str, Any]:
        self.calls.append({"model": model, "system": system, "user": user})
        return self._response


def test_builder_with_llm_keeps_grounded_hypotheses() -> None:
    fake_openalex_payload = {
        "results": [
            {
                "id": "https://openalex.org/W1",
                "title": "Mediator pattern reduces handoffs",
                "doi": "https://doi.org/10.real/mediator",
                "publication_year": 2024,
                "authorships": [],
                "abstract_inverted_index": {},
                "cited_by_count": 12,
            }
        ]
    }
    fake_llm_response = {
        "hypothesis_pack_version": "1.0",
        "engagement_id": "eng-002",
        "domain": "service ops",
        "hypotheses": [
            {
                "id": "H1",
                "statement": "Introduce a mediator to absorb manual handoffs.",
                "evidence": {
                    "paper_dois": ["10.real/mediator"],
                    "patent_ids": [],
                    "triz_principle": "Mediador (24)",
                },
                "expected_delta": {
                    "kpi": "lead_time",
                    "direction": "decrease",
                    "magnitude_estimated": "15-25%",
                    "confidence": "media",
                },
                "applicability_context": "process with 2+ manual handoffs",
                "confidence": "media",
            },
            {
                "id": "H2",
                "statement": "Hypothesis with fabricated DOI — should be removed.",
                "evidence": {
                    "paper_dois": ["10.fake/invented"],
                    "patent_ids": [],
                },
                "expected_delta": {},
                "applicability_context": "",
                "confidence": "baja",
            },
        ],
        "evidence_summary": {
            "papers_consulted": 1,
            "patents_consulted": 0,
            "papers_cited": 1,
            "patents_cited": 0,
        },
    }

    builder = HypothesisBuilder(
        llm_client=_FakeLlmClient(fake_llm_response),
        openalex=OpenAlexClient(http_client=_FakeHttpClient(get_payload=fake_openalex_payload)),
        lens=LensClient(http_client=_FakeHttpClient()),
    )
    pack = builder.build(
        engagement_id="eng-002",
        domain="service ops",
        pain_points=["manual handoff between agent and back office"],
    )

    assert pack["llm_mode"] == "claude"
    assert len(pack["hypotheses"]) == 1, "fabricated H2 should have been stripped"
    assert pack["hypotheses"][0]["id"] == "H1"
    assert pack["provenance_check"]["accepted"] == 1
    assert pack["provenance_check"]["rejected"] == 1
    assert pack["evidence"]["papers"][0]["doi"] == "10.real/mediator"
