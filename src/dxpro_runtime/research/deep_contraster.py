"""Deep research contrast for RGC hypothesis packs."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from ..llm_client import MODEL_SONNET, LlmClient
from ..prompts import SYSTEM_RGC_DEEP_RESEARCH_CONTRASTER
from .grey_sources import GreySourceClient
from .models import GreySource

logger = logging.getLogger(__name__)


@dataclass
class DeepResearchContraster:
    """Complements RGC hypotheses with grey-literature contrast."""

    llm_client: LlmClient | None
    grey_client: GreySourceClient | None = None

    def build(
        self,
        *,
        engagement_id: str,
        domain: str,
        pain_points: list[str],
        hypothesis_pack: dict[str, Any],
        provided_sources: list[dict[str, Any]] | None = None,
        urls: list[str] | None = None,
    ) -> dict[str, Any]:
        grey_client = self.grey_client or GreySourceClient()
        try:
            sources = grey_client.collect(provided_sources=provided_sources, urls=urls)
        finally:
            if self.grey_client is None:
                grey_client.close()

        if self.llm_client is None:
            return self._stub_pack(engagement_id, domain, pain_points, hypothesis_pack, sources)

        synthesized = self._synthesize_with_llm(
            engagement_id=engagement_id,
            domain=domain,
            pain_points=pain_points,
            hypothesis_pack=hypothesis_pack,
            sources=sources,
        )
        verified = verify_contrast_provenance(synthesized, hypothesis_pack, sources)
        verified["artifact_type"] = "deep_research_contrast_pack"
        verified["source_register"] = [s.to_dict() for s in sources]
        verified["llm_mode"] = "claude"
        verified["llm_model"] = MODEL_SONNET
        return verified

    def _synthesize_with_llm(
        self,
        *,
        engagement_id: str,
        domain: str,
        pain_points: list[str],
        hypothesis_pack: dict[str, Any],
        sources: list[GreySource],
    ) -> dict[str, Any]:
        user_payload = {
            "engagement_id": engagement_id,
            "domain": domain,
            "pain_points": pain_points,
            "hypothesis_pack": hypothesis_pack,
            "source_register": [s.to_dict() for s in sources],
            "instruction": (
                "Contrasta SOLO las hipotesis existentes. Cita unicamente source_ids "
                "presentes en source_register[*].id y hypothesis_ids presentes en "
                "hypothesis_pack.hypotheses[*].id."
            ),
        }
        return self.llm_client.complete(
            model=MODEL_SONNET,
            system=SYSTEM_RGC_DEEP_RESEARCH_CONTRASTER,
            user=json.dumps(user_payload, ensure_ascii=False),
        )

    def _stub_pack(
        self,
        engagement_id: str,
        domain: str,
        pain_points: list[str],
        hypothesis_pack: dict[str, Any],
        sources: list[GreySource],
    ) -> dict[str, Any]:
        return {
            "artifact_type": "deep_research_contrast_pack",
            "contrast_pack_version": "1.0",
            "engagement_id": engagement_id,
            "domain": domain,
            "pain_points": pain_points,
            "hypothesis_ids_reviewed": [
                h.get("id") for h in hypothesis_pack.get("hypotheses", []) if h.get("id")
            ],
            "contrast_matrix": [],
            "candidate_followup_hypotheses": [],
            "unsupported_claims": [],
            "recommended_hil_questions": [],
            "source_register": [s.to_dict() for s in sources],
            "provenance_check": {
                "accepted": 0,
                "rejected": 0,
                "rejected_details": [],
            },
            "notes_to_consultant": (
                "ANTHROPIC_API_KEY no configurada; se recolectaron fuentes grises, "
                "pero no se genero contraste sintetico."
            ),
            "llm_mode": "stub",
        }


def verify_contrast_provenance(
    pack: dict[str, Any],
    hypothesis_pack: dict[str, Any],
    sources: list[GreySource],
) -> dict[str, Any]:
    """Remove contrast rows that cite unavailable hypotheses or sources."""
    valid_hypothesis_ids = {h.get("id") for h in hypothesis_pack.get("hypotheses", []) if h.get("id")}
    valid_source_ids = {s.id for s in sources}

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for row in pack.get("contrast_matrix") or []:
        hypothesis_id = row.get("hypothesis_id")
        cited_sources = _row_source_ids(row)
        bad_sources = [source_id for source_id in cited_sources if source_id not in valid_source_ids]
        bad_hypothesis = hypothesis_id not in valid_hypothesis_ids

        if bad_hypothesis or bad_sources:
            rejected.append(
                {
                    "hypothesis_id": hypothesis_id,
                    "reason": "fabricated_or_out_of_scope_reference",
                    "invalid_hypothesis": hypothesis_id if bad_hypothesis else None,
                    "fabricated_source_ids": bad_sources,
                }
            )
            logger.warning(
                "rejecting contrast row for hypothesis=%s invalid_hypothesis=%s sources=%s",
                hypothesis_id,
                bad_hypothesis,
                bad_sources,
            )
            continue
        accepted.append(row)

    pack["contrast_matrix"] = accepted
    pack["provenance_check"] = {
        "accepted": len(accepted),
        "rejected": len(rejected),
        "rejected_details": rejected,
    }
    return pack


def _row_source_ids(row: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in ("supporting_source_ids", "contradicting_source_ids", "boundary_source_ids"):
        ids.extend(str(value) for value in (row.get(key) or []))
    return ids
