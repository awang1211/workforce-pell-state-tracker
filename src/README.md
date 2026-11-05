# Monitoring Pipeline Source

The active Python/OpenAI monitoring pipeline currently lives in the local Codex project environment and should be copied into this directory.

Expected components:
- search provider abstraction
- OpenAI web-search provider
- source fetcher
- HTML/PDF extraction
- materiality classifier
- structured extractor
- validator
- duplicate detector
- Google Sheets gateway
- manual URL ingestion
- block-page / Cloudflare detection
- tests

Do not copy `.env` or service-account credentials into this folder.
