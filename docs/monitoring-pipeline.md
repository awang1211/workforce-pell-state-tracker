# Workforce Pell State Implementation Monitor

Local Python MVP for discovering material Workforce Pell implementation events in North Carolina, Iowa, Pennsylvania, Illinois, and California. The pipeline reads analyst-approved context from Google Sheets, detects candidate events, checks for duplicates, and stages new candidates for human review.

It can **only append to `Review_Queue`**. It contains no write method for `State_Status` or `Event_History`, and it does not publish approved events automatically.

## Review_Queue contract

The sheet must contain these headers in this order:

```text
Candidate_ID, State, Detected_Date, Proposed_Event_Date,
Source_Publication_Date, Date_Basis, Proposed_Event_Type, Proposed_Stage,
Proposed_Change, Source_Name, Source_URL, Source_Type, Evidence_Excerpt,
AI_Confidence, Duplicate_Check, Review_Status, Analyst_Comment, Reviewer,
Reviewed_Date, Publish_Action
```

`Proposed_Stage` is blank when the evidence cannot establish a stage. Stage 0 means only `0 - Not yet reviewed`; it is never used for uncertainty. A material event may retain the current stage with `stage_change = false` internally.

## Local setup

Requires Python 3.11 or newer.

```bash
cd workforce-pell-tracker
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Populate `.env` locally:

```dotenv
GOOGLE_SHEET_ID=your_spreadsheet_id
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
OPENAI_API_KEY=your_openai_api_key
OPENAI_SEARCH_MODEL=gpt-5.6-terra
OPENAI_MODEL=gpt-5-mini
LOG_LEVEL=INFO
```

Never commit `.env` or the service-account JSON file.

### Google configuration

1. Create or select a Google Cloud project.
2. Enable the Google Sheets API.
3. Create a service account and download its JSON key outside this repository.
4. Share the spreadsheet with the service-account email.
5. Create an OpenAI API key with access to the Responses API and a web-search-capable model.
6. Confirm the three tabs are named exactly `State_Status`, `Event_History`, and `Review_Queue`.

Google Sheets sharing is spreadsheet-wide, so application safety is enforced by `SafeSheetsGateway`: authoritative tabs are read-only and its only append operation hard-codes `Review_Queue`.

## Test

Tests use Python's standard-library test runner and do not call Google, search, or OpenAI APIs.

```bash
python -m unittest discover -s tests -v
```

## Run

Dry-run is the default. It performs live discovery and reads the sheet for deduplication, but prints candidates instead of writing them:

```bash
python -m src.main
```

After reviewing the printed output, explicitly enable Review_Queue appends:

```bash
python -m src.main --write
```

Change the discovery window if needed:

```bash
python -m src.main --lookback-days 30
```

Both run modes use potentially billable OpenAI Responses API calls for web discovery and structured extraction. Discovery uses official state domains as `allowed_domains`, preserves the source URLs returned by web search, and passes source context downstream only as a lead. Search summaries and snippets are never authoritative evidence: every URL is fetched separately before materiality assessment or candidate extraction. Do not run either command until all credentials are configured and API usage is approved. `--write` is the only mode that mutates the spreadsheet.

## Manual URL Ingestion

Use `--url` to ingest a specific HTML page or PDF. Normal direct retrieval does not invoke web search. The supplied URL is fetched directly, redirects are resolved, the final URL is canonicalized, and the same classifier, structured extractor, validator, duplicate checker, and Review_Queue-only writer used by automated discovery are reused.

If direct retrieval receives HTTP 401, 403, or 429, or detects a Cloudflare/captcha/bot-verification/access-denied page, that content is rejected before classification. Manual URL mode then uses OpenAI web search as a fallback, prioritizing the supplied URL, domain, and available title. Output clearly records `retrieval_method: web_search_fallback` and never represents the blocked page as directly fetched. If the fallback lacks sufficiently matched, source-grounded Workforce Pell evidence, the result is `Needs more evidence` and nothing is written.

Dry-run is the default:

```bash
python -m src.main --url "https://example.gov/workforce-pell"
```

If the page does not identify exactly one state, provide an explicit override:

```bash
python -m src.main \
  --url "https://labor.delaware.gov/workforce-pell" \
  --state "Delaware"
```

Append non-duplicate candidates to `Review_Queue` only after reviewing the dry-run output:

```bash
python -m src.main \
  --url "https://labor.delaware.gov/workforce-pell" \
  --state "Delaware" \
  --write
```

Manual output includes the original input URL, canonical final URL after redirects, inferred or overridden state, candidate rows, and exact/likely duplicates that were not appended. If state detection is ambiguous, no candidate is extracted or written until `--state` is supplied. If no material event is found, the command reports that outcome and writes nothing. Manual mode calls the web-search tool only when direct retrieval is explicitly detected as blocked.

For sources that are readable in a browser but consistently block automated retrieval, save the article text as a UTF-8 `.txt` file and ingest it with its public source URL:

```bash
python -m src.main \
  --text-file "/path/to/article.txt" \
  --source-url "https://example.com/article" \
  --state "Indiana"
```

This uses `retrieval_method: manual_text`, preserves the source URL separately, and is dry-run by default. To append validated, non-duplicate Pending candidates to `Review_Queue`:

```bash
python -m src.main \
  --text-file "/path/to/article.txt" \
  --source-url "https://example.com/article" \
  --state "Indiana" \
  --write
```

Retrieval provenance values are `direct_html`, `direct_pdf`, `web_search_fallback`, and `manual_text`.

## Module map

- `config.py`, `models.py`, `taxonomy.py`: configuration and typed schema
- `validation.py`: deterministic stage, date, and provenance rules
- `sheets.py`: read access plus Review_Queue-only append boundary
- `search.py`, `fetch.py`, `extract.py`: provider-neutral discovery, Responses API web search, and source processing
- `classify.py`: conservative materiality pre-filter
- `dedupe.py`: Event_History and Review_Queue comparisons
- `pipeline.py`, `main.py`: five-state orchestration and CLI
- `logging_config.py`: structured JSON logs
