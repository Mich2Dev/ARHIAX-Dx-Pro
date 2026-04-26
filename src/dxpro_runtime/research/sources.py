"""External research sources: OpenAlex (papers, free) and Lens.org (patents).

Both clients accept an injectable httpx.Client so tests can stub the network.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Protocol

import httpx

from .models import Paper, Patent

logger = logging.getLogger(__name__)

OPENALEX_BASE_URL = "https://api.openalex.org"
LENS_BASE_URL = "https://api.lens.org"
DEFAULT_TIMEOUT = 15.0


class _HttpClientLike(Protocol):
    def get(self, url: str, **kwargs: Any) -> httpx.Response: ...
    def post(self, url: str, **kwargs: Any) -> httpx.Response: ...


# ---------------------------------------------------------------------------
# OpenAlex — open, no API key required, generous rate limit
# ---------------------------------------------------------------------------


class OpenAlexClient:
    """Thin wrapper over OpenAlex /works search."""

    def __init__(
        self,
        *,
        http_client: _HttpClientLike | None = None,
        contact_email: str | None = None,
        base_url: str = OPENALEX_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        # OpenAlex asks for a contact email in User-Agent for the polite pool.
        self._email = contact_email or os.getenv("OPENALEX_CONTACT_EMAIL")
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=timeout)

    def search_papers(self, query: str, *, limit: int = 5) -> list[Paper]:
        params = {
            "search": query,
            "per-page": max(1, min(limit, 25)),
            "select": "id,title,doi,publication_year,authorships,abstract_inverted_index,cited_by_count,primary_location",
        }
        if self._email:
            params["mailto"] = self._email

        try:
            response = self._client.get(f"{self._base}/works", params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("openalex search failed: %s", exc)
            return []

        works = response.json().get("results", [])
        return [self._parse_work(w) for w in works if w]

    def close(self) -> None:
        if self._owns_client and isinstance(self._client, httpx.Client):
            self._client.close()

    def _parse_work(self, raw: dict[str, Any]) -> Paper:
        authors = tuple(
            (a.get("author") or {}).get("display_name") or ""
            for a in (raw.get("authorships") or [])
        )
        return Paper(
            id=str(raw.get("id") or ""),
            title=str(raw.get("title") or "").strip(),
            doi=_extract_doi(raw.get("doi")),
            year=raw.get("publication_year"),
            authors=tuple(a for a in authors if a),
            abstract=_reconstruct_abstract(raw.get("abstract_inverted_index")),
            url=(raw.get("primary_location") or {}).get("landing_page_url"),
            citations=int(raw.get("cited_by_count") or 0),
            source="openalex",
        )


# ---------------------------------------------------------------------------
# Lens.org — patents. Requires bearer token (LENS_API_TOKEN). No-op if absent.
# ---------------------------------------------------------------------------


class LensClient:
    """Patent search via Lens.org REST API.

    Lens.org requires a free academic account + API token. When the token is
    not set, `search_patents()` returns an empty list and logs a warning —
    the system stays functional without patent evidence.
    """

    def __init__(
        self,
        *,
        api_token: str | None = None,
        http_client: _HttpClientLike | None = None,
        base_url: str = LENS_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._token = api_token or os.getenv("LENS_API_TOKEN")
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=timeout)

    @property
    def is_configured(self) -> bool:
        return bool(self._token)

    def search_patents(self, query: str, *, limit: int = 5) -> list[Patent]:
        if not self._token:
            logger.info("LENS_API_TOKEN is not set; skipping patent search.")
            return []

        body = {
            "query": {"match": {"title": query}},
            "size": max(1, min(limit, 20)),
            "include": [
                "lens_id",
                "biblio.invention_title",
                "biblio.publication_reference",
                "biblio.parties",
                "abstract",
                "jurisdiction",
                "date_published",
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        try:
            response = self._client.post(
                f"{self._base}/patent/search",
                json=body,
                headers=headers,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("lens.org search failed: %s", exc)
            return []

        data = response.json().get("data") or []
        return [self._parse_patent(p) for p in data if p]

    def close(self) -> None:
        if self._owns_client and isinstance(self._client, httpx.Client):
            self._client.close()

    def _parse_patent(self, raw: dict[str, Any]) -> Patent:
        biblio = raw.get("biblio") or {}
        title_block = biblio.get("invention_title") or []
        title = ""
        if isinstance(title_block, list) and title_block:
            title = str((title_block[0] or {}).get("text") or "")
        elif isinstance(title_block, dict):
            title = str(title_block.get("text") or "")

        publication_ref = biblio.get("publication_reference") or {}
        doc_number = str(publication_ref.get("doc_number") or "")
        country = str(publication_ref.get("country") or "")
        publication_number = f"{country}-{doc_number}" if country and doc_number else doc_number

        parties = biblio.get("parties") or {}
        inventors = tuple(
            str((p.get("extracted_name") or {}).get("value") or "")
            for p in (parties.get("inventors") or [])
        )
        assignees = tuple(
            str((p.get("extracted_name") or {}).get("value") or "")
            for p in (parties.get("applicants") or [])
        )

        abstract_block = raw.get("abstract") or []
        abstract = ""
        if isinstance(abstract_block, list) and abstract_block:
            abstract = str((abstract_block[0] or {}).get("text") or "")

        return Patent(
            id=str(raw.get("lens_id") or ""),
            title=title.strip(),
            publication_number=publication_number,
            abstract=abstract.strip(),
            inventors=tuple(i for i in inventors if i),
            assignees=tuple(a for a in assignees if a),
            publication_date=raw.get("date_published"),
            jurisdiction=raw.get("jurisdiction"),
            url=f"https://www.lens.org/lens/patent/{raw.get('lens_id')}" if raw.get("lens_id") else None,
            source="lens",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_doi(value: Any) -> str | None:
    if not value:
        return None
    text = str(value)
    if text.startswith("https://doi.org/"):
        return text.replace("https://doi.org/", "", 1)
    return text


def _reconstruct_abstract(inverted: dict[str, list[int]] | None) -> str:
    """OpenAlex stores abstracts as inverted indexes; flatten back to text."""
    if not inverted or not isinstance(inverted, dict):
        return ""
    positions: dict[int, str] = {}
    for word, indexes in inverted.items():
        for idx in indexes or []:
            positions[idx] = word
    if not positions:
        return ""
    return " ".join(positions[i] for i in sorted(positions))
