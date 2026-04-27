from __future__ import annotations

from typing import Any

from dxpro_runtime.research import DeepResearchContraster, GreySourceClient
from dxpro_runtime.research.deep_contraster import verify_contrast_provenance
from dxpro_runtime.research.models import GreySource


class _FakeLlmClient:
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    def complete(self, *, model: str, system: str, user: str) -> dict[str, Any]:
        self.calls.append({"model": model, "system": system, "user": user})
        return self._response


def _hypothesis_pack() -> dict[str, Any]:
    return {
        "hypothesis_pack_version": "1.0",
        "engagement_id": "eng-001",
        "domain": "service operations",
        "hypotheses": [
            {
                "id": "H1",
                "statement": "Introduce a mediator to reduce manual handoffs.",
                "evidence": {"paper_dois": ["10.real/mediator"], "patent_ids": []},
            }
        ],
    }


def test_grey_source_client_normalizes_and_dedupes_sources() -> None:
    client = GreySourceClient()
    sources = client.collect(
        provided_sources=[
            {
                "id": "grey-ops-001",
                "title": "Operations benchmark",
                "source_type": "consulting_report",
                "publisher": "Example Institute",
                "content": "Manual handoffs increase cycle time.",
            },
            {
                "id": "grey-ops-001",
                "title": "Duplicate",
                "content": "Should be deduped.",
            },
        ]
    )
    client.close()

    assert len(sources) == 1
    assert sources[0].id == "grey-ops-001"
    assert sources[0].content_hash_sha256 is not None
    assert "Manual handoffs" in sources[0].excerpt


def test_verify_contrast_provenance_rejects_fabricated_sources_and_hypotheses() -> None:
    sources = [GreySource(id="grey-1", title="Real source")]
    pack = {
        "contrast_matrix": [
            {
                "hypothesis_id": "H1",
                "support_level": "moderate",
                "supporting_source_ids": ["grey-1"],
                "contradicting_source_ids": [],
                "boundary_source_ids": [],
            },
            {
                "hypothesis_id": "H1",
                "support_level": "strong",
                "supporting_source_ids": ["grey-fake"],
            },
            {
                "hypothesis_id": "H999",
                "support_level": "weak",
                "supporting_source_ids": ["grey-1"],
            },
        ]
    }

    verified = verify_contrast_provenance(pack, _hypothesis_pack(), sources)

    assert len(verified["contrast_matrix"]) == 1
    assert verified["contrast_matrix"][0]["hypothesis_id"] == "H1"
    assert verified["provenance_check"]["accepted"] == 1
    assert verified["provenance_check"]["rejected"] == 2


def test_deep_research_stub_returns_sources_without_synthesis() -> None:
    builder = DeepResearchContraster(llm_client=None)
    pack = builder.build(
        engagement_id="eng-001",
        domain="service operations",
        pain_points=["manual handoff delays"],
        hypothesis_pack=_hypothesis_pack(),
        provided_sources=[
            {
                "id": "grey-ops-001",
                "title": "Operations benchmark",
                "source_type": "consulting_report",
                "content": "Manual handoffs increase cycle time.",
            }
        ],
    )

    assert pack["llm_mode"] == "stub"
    assert pack["artifact_type"] == "deep_research_contrast_pack"
    assert pack["hypothesis_ids_reviewed"] == ["H1"]
    assert pack["source_register"][0]["id"] == "grey-ops-001"


def test_deep_research_with_llm_keeps_only_grounded_contrast_rows() -> None:
    fake_llm = _FakeLlmClient(
        {
            "contrast_pack_version": "1.0",
            "engagement_id": "eng-001",
            "domain": "service operations",
            "hypothesis_ids_reviewed": ["H1"],
            "contrast_matrix": [
                {
                    "hypothesis_id": "H1",
                    "support_level": "moderate",
                    "supporting_source_ids": ["grey-ops-001"],
                    "contradicting_source_ids": [],
                    "boundary_source_ids": [],
                    "confidence_adjustment": "keep",
                    "requires_hil": False,
                },
                {
                    "hypothesis_id": "H1",
                    "support_level": "strong",
                    "supporting_source_ids": ["grey-invented"],
                    "confidence_adjustment": "raise",
                    "requires_hil": False,
                },
            ],
        }
    )
    builder = DeepResearchContraster(llm_client=fake_llm)
    pack = builder.build(
        engagement_id="eng-001",
        domain="service operations",
        pain_points=["manual handoff delays"],
        hypothesis_pack=_hypothesis_pack(),
        provided_sources=[
            {
                "id": "grey-ops-001",
                "title": "Operations benchmark",
                "content": "Manual handoffs increase cycle time.",
            }
        ],
    )

    assert pack["llm_mode"] == "claude"
    assert len(pack["contrast_matrix"]) == 1
    assert pack["contrast_matrix"][0]["supporting_source_ids"] == ["grey-ops-001"]
    assert pack["provenance_check"]["rejected"] == 1
