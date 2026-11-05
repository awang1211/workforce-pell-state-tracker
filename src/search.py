"""Search-provider abstraction and OpenAI Responses web-search provider."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .config import StateConfig
from .models import SearchResult


@dataclass(frozen=True, slots=True)
class FallbackEvidence:
    """Source-grounded context returned when a supplied page cannot be fetched."""

    title: str
    source_url: str
    source_domain: str
    text: str
    evidence_sufficient: bool
    reason: str


class SearchProvider(ABC):
    """Interface for locating source leads without coupling orchestration to a vendor."""

    @abstractmethod
    def search(self, state: StateConfig, lookback_days: int) -> list[SearchResult]:
        """Return recent Workforce Pell source leads for one state."""

    def search_blocked_url(
        self, url: str, page_title: str | None = None, state: str | None = None
    ) -> FallbackEvidence:
        """Find source-grounded context for an access-blocked supplied URL."""
        raise NotImplementedError("This search provider does not support blocked-URL fallback")


class NoopSearchProvider(SearchProvider):
    """Offline provider useful in tests and local plumbing checks."""

    def search(self, state: StateConfig, lookback_days: int) -> list[SearchResult]:
        del state, lookback_days
        return []


class OpenAIWebSearchProvider(SearchProvider):
    """Discover official source pages with Responses API hosted web search.

    Returned summaries are discovery context only. The pipeline must fetch each
    URL and extract evidence from the source page before creating a candidate.
    """

    def __init__(self, api_key: str, model: str, client: Any | None = None) -> None:
        if client is None:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
        self._client = client
        self._model = model

    def search(self, state: StateConfig, lookback_days: int) -> list[SearchResult]:
        domains = [_normalize_domain(domain) for domain in state.official_domains]
        response = self._client.responses.create(
            model=self._model,
            reasoning={"effort": "low"},
            tools=[{"type": "web_search", "filters": {"allowed_domains": domains}}],
            tool_choice="required",
            include=["web_search_call.action.sources"],
            input=(
                f"Find recent material implementation information about Workforce Pell or short-term Pell "
                f"for {state.name}, focusing on the last {lookback_days} days. Look for official guidance, "
                "rulemaking, application windows, submissions, approvals, eligible-program lists, deadlines, "
                "launches, delays, suspensions, or student access. Return concise context grounded in the sources."
            ),
        )
        context = str(getattr(response, "output_text", "")).strip()
        results: list[SearchResult] = []
        seen: set[str] = set()
        for source in _iter_sources(getattr(response, "output", [])):
            raw_url = str(_value(source, "url") or "").strip()
            if not raw_url:
                continue
            url = canonicalize_source_url(raw_url)
            if url in seen:
                continue
            seen.add(url)
            domain = urlsplit(url).netloc.lower()
            results.append(SearchResult(
                title=str(_value(source, "title") or domain),
                url=url,
                source_domain=domain,
                snippet=context[:2_000],
                source_type="Official state source" if _is_official_domain(domain, domains) else "Secondary source",
            ))
        return results

    def search_blocked_url(
        self, url: str, page_title: str | None = None, state: str | None = None
    ) -> FallbackEvidence:
        """Search for grounded context matching an exact blocked URL or its domain."""
        canonical = canonicalize_source_url(url)
        domain = urlsplit(canonical).netloc.lower()
        response = self._client.responses.create(
            model=self._model,
            reasoning={"effort": "low"},
            tools=[{"type": "web_search"}],
            tool_choice="required",
            include=["web_search_call.action.sources", "web_search_call.results"],
            input=(
                "Find verifiable information from or about this exact source page concerning Workforce Pell "
                "or short-term Pell implementation. Prioritize the exact URL, then the same domain and page title. "
                "State concrete implementation facts and dates only when supported by consulted sources. "
                f"URL: {canonical}\nPage title: {page_title or 'unknown'}\nState: {state or 'unknown'}"
            ),
        )
        context = str(getattr(response, "output_text", "")).strip()
        sources = list(_iter_sources(getattr(response, "output", [])))
        ranked = sorted(sources, key=lambda item: _fallback_source_score(item, canonical, domain, page_title), reverse=True)
        best = ranked[0] if ranked else None
        best_url = canonicalize_source_url(str(_value(best, "url") or "")) if best else canonical
        best_title = str(_value(best, "title") or page_title or domain) if best else (page_title or domain)
        best_domain = urlsplit(best_url).netloc.lower()
        score = _fallback_source_score(best, canonical, domain, page_title) if best else 0
        has_topic = "workforce pell" in context.lower() or "short-term pell" in context.lower()
        sufficient = bool(best and score >= 2 and has_topic and len(context) >= 120)
        reason = (
            "Matched source and substantive Workforce Pell context found"
            if sufficient
            else "Web search did not return enough matched, source-grounded evidence"
        )
        return FallbackEvidence(best_title, best_url, best_domain, context, sufficient, reason)


def canonicalize_source_url(url: str) -> str:
    """Remove fragments and tracking parameters without inventing a new destination."""
    parts = urlsplit(url.strip())
    query = [
        (key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}
    ]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", urlencode(query), ""))


def _iter_sources(output: Any) -> list[Any]:
    sources: list[Any] = []
    for item in output or []:
        if _value(item, "type") != "web_search_call":
            continue
        action = _value(item, "action")
        sources.extend(_value(action, "sources") or [])
    return sources


def _value(item: Any, key: str) -> Any:
    return item.get(key) if isinstance(item, dict) else getattr(item, key, None)


def _normalize_domain(domain: str) -> str:
    return domain.lower().removeprefix("https://").removeprefix("http://").strip("/")


def _is_official_domain(domain: str, official_domains: list[str]) -> bool:
    return any(domain == allowed or domain.endswith(f".{allowed}") for allowed in official_domains)


def _fallback_source_score(source: Any, canonical_url: str, domain: str, page_title: str | None) -> int:
    if source is None:
        return 0
    source_url = canonicalize_source_url(str(_value(source, "url") or ""))
    source_domain = urlsplit(source_url).netloc.lower()
    source_title = str(_value(source, "title") or "").casefold()
    score = 3 if source_url == canonical_url else 0
    if source_domain == domain or source_domain.endswith(f".{domain}"):
        score += 2
    if page_title and page_title.casefold() in source_title:
        score += 1
    return score
