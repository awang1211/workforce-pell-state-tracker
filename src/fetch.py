"""HTTP source fetching with bounded size and canonical URL preservation."""

from __future__ import annotations

from dataclasses import dataclass
import re


BLOCK_STATUSES = frozenset({401, 403, 429})
BLOCK_MARKERS = (
    "attention required", "sorry, you have been blocked", "cloudflare ray id",
    "cf-chl-", "challenge-platform", "captcha", "verify you are human",
    "bot verification", "access denied", "checking your browser",
)


class RetrievalBlocked(RuntimeError):
    """Raised when a response is an authentication, rate-limit, or bot challenge page."""

    def __init__(self, url: str, status_code: int, reason: str, page_title: str | None = None) -> None:
        super().__init__(f"Blocked retrieval ({status_code}): {reason}")
        self.url = url
        self.status_code = status_code
        self.reason = reason
        self.page_title = page_title


@dataclass(frozen=True, slots=True)
class FetchedSource:
    """Raw source response needed by the text extractor."""

    requested_url: str
    final_url: str
    content_type: str
    content: bytes


class SourceFetcher:
    """Fetch public sources with time and response-size limits."""

    def __init__(self, timeout: float = 30.0, max_bytes: int = 15_000_000) -> None:
        self._timeout = timeout
        self._max_bytes = max_bytes

    def fetch(self, url: str) -> FetchedSource:
        import requests
        response = requests.get(
            url,
            timeout=self._timeout,
            headers={"User-Agent": "WorkforcePellMonitor/0.1 (+research monitoring)"},
        )
        blocked_reason = detect_block_page(
            response.status_code,
            response.headers.get("Content-Type", "").lower(),
            response.content,
        )
        if blocked_reason:
            raise RetrievalBlocked(
                response.url,
                response.status_code,
                blocked_reason,
                _usable_page_title(response.content),
            )
        response.raise_for_status()
        if len(response.content) > self._max_bytes:
            raise ValueError(f"Source exceeds {self._max_bytes} byte limit")
        return FetchedSource(
            requested_url=url,
            final_url=response.url,
            content_type=response.headers.get("Content-Type", "").lower(),
            content=response.content,
        )


def detect_block_page(status_code: int, content_type: str, content: bytes) -> str | None:
    """Return a block reason for HTTP denial or recognizable challenge content."""
    if status_code in BLOCK_STATUSES:
        return f"HTTP {status_code} access response"
    if "html" not in content_type and not content.lstrip().startswith(b"<"):
        return None
    text = content[:500_000].decode("utf-8", errors="ignore").lower()
    marker = next((item for item in BLOCK_MARKERS if item in text), None)
    if marker:
        return f"Block/challenge marker detected: {marker}"
    return None


def _usable_page_title(content: bytes) -> str | None:
    text = content[:100_000].decode("utf-8", errors="ignore")
    match = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    title = re.sub(r"\s+", " ", match.group(1)).strip()
    return None if any(marker in title.lower() for marker in BLOCK_MARKERS) else title
