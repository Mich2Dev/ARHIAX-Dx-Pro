"""Builds a grounded hypothesis_pack from retrieved papers + patents.

Pipeline:
  1. Take pain_points (queries) + domain context.
  2. For each query, fetch papers (OpenAlex) and patents (Lens.org if configured).
  3. Hand the retrieved evidence to Claude with a hard-grounded prompt.
  4. Verify Claude's output: every cited DOI / patent must appear in retrieved evidence.
  5. Return a structured hypothesis_pack with provenance.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from ..llm_client import MODEL_SONNET, LlmClient
from ..prompts import SYSTEM_RGC_HYPOTHESIS_BUILDER
from .models import Paper, Patent, ResearchEvidence
from .sources import LensClient, OpenAlexClient

logger = logging.getLogger(__name__)


@dataclass
class HypothesisBuilder:
    """Orchestrates evidence retrieval + LLM synthesis with provenance check."""

    llm_client: LlmClient | None
    openalex: OpenAlexClient | None = None
    lens: LensClient | None = None
    papers_per_query: int = 5
    patents_per_query: int = 5

    def build(
        self,
        *,
        engagement_id: str,
        domain: str,
        pain_points: list[str],
    ) -> dict[str, Any]:
        evidence = self._gather_evidence(pain_points)
        all_papers = _dedupe_papers(p for ev in evidence for p in ev.papers)
        all_patents = _dedupe_patents(p for ev in evidence for p in ev.patents)

        if self.llm_client is None:
            return self._stub_pack(engagement_id, domain, evidence, all_papers, all_patents)

        synthesized = self._synthesize_with_llm(
            engagement_id=engagement_id,
            domain=domain,
            pain_points=pain_points,
            papers=all_papers,
            patents=all_patents,
        )
        verified = _verify_provenance(synthesized, all_papers, all_patents)
        verified["evidence"] = {
            "papers": [p.to_dict() for p in all_papers],
            "patents": [p.to_dict() for p in all_patents],
            "queries_executed": [ev.query for ev in evidence],
        }
        verified["llm_mode"] = "claude"
        verified["llm_model"] = MODEL_SONNET
        return verified

    # ------------------------------------------------------------------

    def _gather_evidence(self, queries: list[str]) -> list[ResearchEvidence]:
        results: list[ResearchEvidence] = []
        for query in queries:
            papers = (
                self.openalex.search_papers(query, limit=self.papers_per_query)
                if self.openalex
                else []
            )
            patents = (
                self.lens.search_patents(query, limit=self.patents_per_query)
                if self.lens
                else []
            )
            results.append(
                ResearchEvidence(
                    query=query,
                    papers=tuple(papers),
                    patents=tuple(patents),
                )
            )
        return results

    def _synthesize_with_llm(
        self,
        *,
        engagement_id: str,
        domain: str,
        pain_points: list[str],
        papers: list[Paper],
        patents: list[Patent],
    ) -> dict[str, Any]:
        user_payload = {
            "engagement_id": engagement_id,
            "domain": domain,
            "pain_points": pain_points,
            "evidence": {
                "papers": [p.to_dict() for p in papers],
                "patents": [p.to_dict() for p in patents],
            },
            "instruction": (
                "Sintetiza un hypothesis_pack siguiendo el formato del system prompt. "
                "Cita SOLO DOIs y patent_ids que estén en evidence.papers/patents."
            ),
        }
        return self.llm_client.complete(
            model=MODEL_SONNET,
            system=SYSTEM_RGC_HYPOTHESIS_BUILDER,
            user=json.dumps(user_payload, ensure_ascii=False),
        )

    def _stub_pack(
        self,
        engagement_id: str,
        domain: str,
        evidence: list[ResearchEvidence],
        papers: list[Paper],
        patents: list[Patent],
    ) -> dict[str, Any]:
        """Fallback when no LLM is configured: return raw evidence, no synthesis."""
        return {
            "hypothesis_pack_version": "1.0",
            "engagement_id": engagement_id,
            "domain": domain,
            "hypotheses": [],
            "unsupported_pains": [],
            "evidence_summary": {
                "papers_consulted": len(papers),
                "patents_consulted": len(patents),
                "papers_cited": 0,
                "patents_cited": 0,
            },
            "evidence": {
                "papers": [p.to_dict() for p in papers],
                "patents": [p.to_dict() for p in patents],
                "queries_executed": [ev.query for ev in evidence],
            },
            "notes_to_consultant": (
                "ANTHROPIC_API_KEY no configurada — solo se devolvieron las fuentes "
                "recolectadas, sin síntesis de hipótesis."
            ),
            "llm_mode": "stub",
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def build_hypothesis_pack(
    *,
    engagement_id: str,
    domain: str,
    pain_points: list[str],
    llm_client: LlmClient | None = None,
    openalex: OpenAlexClient | None = None,
    lens: LensClient | None = None,
) -> dict[str, Any]:
    """Convenience constructor — builds and runs in one call."""
    builder = HypothesisBuilder(
        llm_client=llm_client,
        openalex=openalex or OpenAlexClient(),
        lens=lens or LensClient(),
    )
    try:
        return builder.build(
            engagement_id=engagement_id,
            domain=domain,
            pain_points=pain_points,
        )
    finally:
        if openalex is None:
            builder.openalex.close()  # type: ignore[union-attr]
        if lens is None:
            builder.lens.close()  # type: ignore[union-attr]


def _dedupe_papers(papers) -> list[Paper]:
    seen: set[str] = set()
    out: list[Paper] = []
    for p in papers:
        key = (p.doi or p.id or p.title).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _dedupe_patents(patents) -> list[Patent]:
    seen: set[str] = set()
    out: list[Patent] = []
    for p in patents:
        key = (p.publication_number or p.id).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _verify_provenance(
    pack: dict[str, Any],
    papers: list[Paper],
    patents: list[Patent],
) -> dict[str, Any]:
    """Strip any hypothesis citing DOIs/patents not in the retrieved evidence."""
    valid_dois = {p.doi for p in papers if p.doi}
    valid_patent_ids = {p.publication_number for p in patents if p.publication_number}

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for hyp in pack.get("hypotheses") or []:
        evidence = hyp.get("evidence") or {}
        cited_dois = list(evidence.get("paper_dois") or [])
        cited_patents = list(evidence.get("patent_ids") or [])

        bad_dois = [d for d in cited_dois if d not in valid_dois]
        bad_patents = [p for p in cited_patents if p not in valid_patent_ids]

        if bad_dois or bad_patents:
            rejected.append(
                {
                    "hypothesis_id": hyp.get("id"),
                    "reason": "fabricated_evidence",
                    "fabricated_dois": bad_dois,
                    "fabricated_patent_ids": bad_patents,
                }
            )
            logger.warning(
                "rejecting hypothesis %s with fabricated evidence: dois=%s patents=%s",
                hyp.get("id"),
                bad_dois,
                bad_patents,
            )
            continue
        accepted.append(hyp)

    pack["hypotheses"] = accepted
    pack["provenance_check"] = {
        "accepted": len(accepted),
        "rejected": len(rejected),
        "rejected_details": rejected,
    }
    return pack
