# Monitoring and Update Workflow

```text
Official state sources / targeted web search / sector sources / manual URL
        ↓
Source retrieval
        ↓
Text/PDF extraction
        ↓
Materiality classification
        ↓
Schema-constrained extraction
        ↓
Validation + duplicate check
        ↓
Review_Queue
        ↓
Human approve / edit / reject
        ↓
Event_History + State_Status + Approved_Programs
        ↓
Tableau refresh
```

## Automated monitoring
Search and extraction can be automated, but authoritative current-state data remain analyst controlled.

## Manual URL ingestion
Manual mode accepts a supplied URL and reuses the same fetcher, classifier, extractor, validator, and deduplicator. It supports state override, multiple events, dry-run by default, and Review_Queue-only writes.

## Retrieval failure handling
Block-page detection should catch HTTP 401/403/429, Cloudflare challenges, captchas, and access-denied pages. A block page must not be classified as source content.

Fallbacks:
- OpenAI web-search retrieval context
- manual text/file ingestion

Retrieval method should be recorded as `direct_html`, `direct_pdf`, `web_search_fallback`, or `manual_text`.

## Publication gate
The AI pipeline must never directly overwrite `State_Status` or `Event_History` in the MVP. Human review is the publication gate.
