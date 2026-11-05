"""Configuration loading from JSON and environment variables."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

@dataclass(frozen=True, slots=True)
class StateConfig:
    """Search configuration for one pilot state."""

    name: str
    official_domains: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings; secrets are read only from the environment."""

    google_sheet_id: str | None
    google_credentials_path: str | None
    openai_api_key: str | None
    openai_model: str
    openai_search_model: str
    log_level: str

    @classmethod
    def from_environment(cls, env_file: Path | None = None) -> "Settings":
        from dotenv import load_dotenv
        load_dotenv(env_file)
        return cls(
            google_sheet_id=os.getenv("GOOGLE_SHEET_ID"),
            google_credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            openai_search_model=os.getenv("OPENAI_SEARCH_MODEL", "gpt-5.6-terra"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


def load_states(path: Path) -> list[StateConfig]:
    """Load and validate the five-state pilot configuration."""
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    states = [StateConfig(item["name"], tuple(item["official_domains"])) for item in raw["states"]]
    if len(states) != 5:
        raise ValueError("The MVP configuration must contain exactly five pilot states")
    return states
