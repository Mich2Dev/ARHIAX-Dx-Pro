"""Grey-literature source handling for deep RGC contrast."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Protocol

import httpx

from .models import GreySource

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15.0
MAX_EXCERPT_CHARS = 6000


class _HttpClientLike(Protocol):
    def get(self, url: str, **kwargs: Any) -> httpx.Response: ...


class GreySourceClient:
    """Builds a normalized register of grey-literature sources."""

    def __init__(
        self,
        *,
        http_client: _HttpClientLike | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=timeout, follow_redirects=True)

    def collect(
        self,
        *,
        provided_sources: list[dict[str, Any]] | None = None,
        urls: list[str] | None = None,
        url_limit: int = 10,
    ) -> list[GreySource]:
        sources = [self._from_payload(raw) for raw in (provided_sources or []) if raw]
        sources.extend(self.fetch_urls(urls or [], limit=url_limit))
        return _dedupe_sources(sources)

    def fetch_urls(self, urls: list[str], *, limit: int = 10) -> list[GreySource]:
        out: list[GreySource] = []
        for url in urls[: max(0, min(limit, 25))]:
            try:
                response = self._client.get(url)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                logger.warning("grey source fetch failed for %s: %s", url, exc)
                continue

            text = _compact_text(response.text)
            out.append(
                GreySource(
                    id=_source_id(url=url, title=url, excerpt=text),
                    title=url,
                    source_type="web",
                    url=url,
                    excerpt=text[:MAX_EXCERPT_CHARS],
                    content_hash_sha256=_hash_text(response.text),
                    retrieved_at=_utc_now(),
                )
            )
        return out

    def close(self) -> None:
        if self._owns_client and isinstance(self._client, httpx.Client):
            self._client.close()

    def _from_payload(self, raw: dict[str, Any]) -> GreySource:
        title = str(raw.get("title") or raw.get("url") or "Untitled grey source").strip()
        excerpt = _compact_text(str(raw.get("excerpt") or raw.get("content") or ""))
        url = raw.get("url")
        content_hash = raw.get("content_hash_sha256") or _hash_text(excerpt)
        return GreySource(
            id=str(raw.get("id") or _source_id(url=url, title=title, excerpt=excerpt)),
            title=title,
            source_type=str(raw.get("source_type") or "grey"),
            publisher=raw.get("publisher"),
            url=url,
            publication_date=raw.get("publication_date"),
            excerpt=excerpt[:MAX_EXCERPT_CHARS],
            content_hash_sha256=content_hash,
            retrieved_at=raw.get("retrieved_at") or _utc_now(),
        )


def _dedupe_sources(sources: list[GreySource]) -> list[GreySource]:
    seen: set[str] = set()
    out: list[GreySource] = []
    for source in sources:
        key = (source.id or source.url or source.content_hash_sha256 or source.title).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(source)
    return out


def _source_id(*, url: Any, title: str, excerpt: str) -> str:
    raw = f"{url or ''}|{title}|{excerpt[:500]}".encode("utf-8")
    return f"grey-{hashlib.sha256(raw).hexdigest()[:16]}"


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _compact_text(text: str) -> str:
    return " ".join(text.split())


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
