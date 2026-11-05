"""Offline tests for Responses API web-search result parsing."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.config import StateConfig
from src.search import OpenAIWebSearchProvider


class _FakeResponses:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] = {}

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.kwargs = kwargs
        sources = [
            SimpleNamespace(title="Official update", url="https://www.pa.gov/update?utm_source=test#section"),
            SimpleNamespace(title="Duplicate", url="https://www.pa.gov/update"),
        ]
        return SimpleNamespace(
            output_text="Discovery context only; fetch the page before using evidence.",
            output=[SimpleNamespace(type="web_search_call", action=SimpleNamespace(sources=sources))],
        )


class SearchProviderTests(unittest.TestCase):
    def test_returns_canonical_official_source_lead(self) -> None:
        responses = _FakeResponses()
        client = SimpleNamespace(responses=responses)
        provider = OpenAIWebSearchProvider("unused", "test-model", client=client)
        results = provider.search(StateConfig("Pennsylvania", ("pa.gov", "education.pa.gov")), 30)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].url, "https://www.pa.gov/update")
        self.assertEqual(results[0].source_domain, "www.pa.gov")
        self.assertEqual(results[0].source_type, "Official state source")
        self.assertIn("Discovery context", results[0].snippet)
        tools = responses.kwargs["tools"]
        self.assertEqual(tools[0]["filters"]["allowed_domains"], ["pa.gov", "education.pa.gov"])


if __name__ == "__main__":
    unittest.main()
