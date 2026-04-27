"""Typed models for research evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Paper:
    """A scientific paper retrieved from OpenAlex / Semantic Scholar."""
    id: str
    title: str
    doi: str | None = None
    year: int | None = None
    authors: tuple[str, ...] = ()
    abstract: str = ""
    url: str | None = None
    citations: int = 0
    source: str = "openalex"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "doi": self.doi,
            "year": self.year,
            "authors": list(self.authors),
            "abstract": self.abstract,
            "url": self.url,
            "citations": self.citations,
            "source": self.source,
        }


@dataclass(frozen=True)
class Patent:
    """A patent retrieved from Lens.org or other patent databases."""
    id: str
    title: str
    publication_number: str
    abstract: str = ""
    inventors: tuple[str, ...] = ()
    assignees: tuple[str, ...] = ()
    publication_date: str | None = None
    jurisdiction: str | None = None
    url: str | None = None
    source: str = "lens"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "publication_number": self.publication_number,
            "abstract": self.abstract,
            "inventors": list(self.inventors),
            "assignees": list(self.assignees),
            "publication_date": self.publication_date,
            "jurisdiction": self.jurisdiction,
            "url": self.url,
            "source": self.source,
        }


@dataclass(frozen=True)
class ResearchEvidence:
    """Bundle of papers + patents retrieved for a single query."""
    query: str
    papers: tuple[Paper, ...] = ()
    patents: tuple[Patent, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "papers": [p.to_dict() for p in self.papers],
            "patents": [p.to_dict() for p in self.patents],
        }


@dataclass(frozen=True)
class GreySource:
    """A non-academic source used to contrast RGC hypotheses."""
    id: str
    title: str
    source_type: str = "grey"
    publisher: str | None = None
    url: str | None = None
    publication_date: str | None = None
    excerpt: str = ""
    content_hash_sha256: str | None = None
    retrieved_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "source_type": self.source_type,
            "publisher": self.publisher,
            "url": self.url,
            "publication_date": self.publication_date,
            "excerpt": self.excerpt,
            "content_hash_sha256": self.content_hash_sha256,
            "retrieved_at": self.retrieved_at,
        }


@dataclass
class Hypothesis:
    """A grounded hypothesis citing real papers and patents."""
    id: str  # H1, H2, ...
    statement: str
    paper_dois: list[str] = field(default_factory=list)
    patent_ids: list[str] = field(default_factory=list)
    triz_principle: str | None = None
    expected_delta: dict[str, Any] = field(default_factory=dict)
    applicability_context: str = ""
    confidence: str = "media"  # alta | media | baja

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "statement": self.statement,
            "evidence": {
                "paper_dois": self.paper_dois,
                "patent_ids": self.patent_ids,
                "triz_principle": self.triz_principle,
            },
            "expected_delta": self.expected_delta,
            "applicability_context": self.applicability_context,
            "confidence": self.confidence,
        }
