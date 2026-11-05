"""Command-line entry point for the Workforce Pell monitoring MVP."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import Settings, load_states
from .extract import OpenAICandidateExtractor, TextExtractor
from .fetch import SourceFetcher
from .logging_config import configure_logging
from .pipeline import WorkforcePellPipeline
from .search import OpenAIWebSearchProvider
from .sheets import GoogleApiBackend, SafeSheetsGateway

PROJECT_ROOT = Path(__file__).parents[1]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Discover Workforce Pell candidates for analyst review")
    parser.add_argument("--write", action="store_true", help="Append validated candidates to Review_Queue")
    parser.add_argument("--lookback-days", type=int, default=90)
    ingestion = parser.add_mutually_exclusive_group()
    ingestion.add_argument("--url", help="Ingest one source URL; web search is fallback-only if blocked")
    ingestion.add_argument("--text-file", help="Ingest article text from a local UTF-8 file")
    parser.add_argument("--source-url", help="Original public source URL for --text-file")
    parser.add_argument("--state", help="Explicit U.S. state override for manual ingestion")
    return parser


def main() -> None:
    """Validate live configuration and run; default behavior is a no-write dry run."""
    args = _parser().parse_args()
    if args.state and not (args.url or args.text_file):
        raise SystemExit("--state can be used only with --url or --text-file")
    if args.text_file and not args.source_url:
        raise SystemExit("--source-url is required with --text-file")
    if args.source_url and not args.text_file:
        raise SystemExit("--source-url can be used only with --text-file")
    settings = Settings.from_environment(PROJECT_ROOT / ".env")
    configure_logging(settings.log_level)
    required = {
        "GOOGLE_SHEET_ID": settings.google_sheet_id,
        "GOOGLE_APPLICATION_CREDENTIALS": settings.google_credentials_path,
        "OPENAI_API_KEY": settings.openai_api_key,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise SystemExit("Missing required configuration: " + ", ".join(missing))

    backend = GoogleApiBackend(settings.google_credentials_path or "")
    sheets = SafeSheetsGateway(settings.google_sheet_id or "", backend)
    search_provider = OpenAIWebSearchProvider(settings.openai_api_key or "", settings.openai_search_model)
    pipeline = WorkforcePellPipeline(
        search_provider,
        SourceFetcher(), TextExtractor(),
        OpenAICandidateExtractor(settings.openai_api_key or "", settings.openai_model),
        sheets, args.lookback_days,
    )
    if args.url:
        result = pipeline.ingest_url(args.url, state_override=args.state, dry_run=not args.write)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    elif args.text_file:
        text = Path(args.text_file).expanduser().read_text(encoding="utf-8")
        result = pipeline.ingest_text(
            text,
            args.source_url,
            state_override=args.state,
            dry_run=not args.write,
            source_name=Path(args.text_file).name,
        )
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        candidates = pipeline.run(load_states(PROJECT_ROOT / "config" / "states.json"), dry_run=not args.write)
        print(json.dumps([candidate.to_review_queue_dict() for candidate in candidates], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
