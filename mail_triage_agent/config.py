from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

_DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-5",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash",
}


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def _split_list(raw: str) -> List[str]:
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


@dataclass
class Config:
    imap_host: str
    imap_port: int
    imap_user: str
    imap_password: str
    imap_folder: str

    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_use_ssl: bool

    llm_provider: str
    llm_api_key: str
    llm_model: str
    llm_base_url: Optional[str]

    watch_senders: List[str]
    watch_keywords: List[str]
    match_mode: str  # "any" or "all"

    mark_as_read: bool
    data_dir: Path

    @property
    def drafts_dir(self) -> Path:
        return self.data_dir / "drafts"

    @property
    def state_file(self) -> Path:
        return self.data_dir / "state.json"


def load_config(env_file: Optional[str] = None) -> Config:
    load_dotenv(dotenv_path=env_file, override=False)

    def require(name: str) -> str:
        value = os.environ.get(name, "").strip()
        if not value:
            raise ConfigError(
                f"Missing required environment variable: {name}. "
                "Copy .env.example to .env and fill it in."
            )
        return value

    watch_senders = _split_list(os.environ.get("WATCH_SENDERS", ""))
    watch_keywords = _split_list(os.environ.get("WATCH_KEYWORDS", ""))
    if not watch_senders and not watch_keywords:
        raise ConfigError(
            "Set at least one of WATCH_SENDERS or WATCH_KEYWORDS in your .env file, "
            "otherwise the agent has nothing to filter on."
        )

    llm_provider = os.environ.get("LLM_PROVIDER", "anthropic").strip().lower()
    llm_base_url: Optional[str] = None

    if llm_provider == "anthropic":
        llm_api_key = require("ANTHROPIC_API_KEY")
        llm_model = os.environ.get("ANTHROPIC_MODEL", "").strip() or _DEFAULT_MODELS["anthropic"]
    elif llm_provider == "openai":
        llm_api_key = require("OPENAI_API_KEY")
        llm_model = os.environ.get("OPENAI_MODEL", "").strip() or _DEFAULT_MODELS["openai"]
    elif llm_provider == "gemini":
        # Free tier available at https://aistudio.google.com/apikey
        llm_api_key = require("GEMINI_API_KEY")
        llm_model = os.environ.get("GEMINI_MODEL", "").strip() or _DEFAULT_MODELS["gemini"]
    elif llm_provider == "custom":
        # Any OpenAI-compatible endpoint: Groq, OpenRouter, Together, a local
        # Ollama/LM Studio server, etc. — many of these have free tiers.
        llm_api_key = require("CUSTOM_API_KEY")
        llm_base_url = require("CUSTOM_BASE_URL")
        llm_model = require("CUSTOM_MODEL")
    else:
        raise ConfigError(
            f"Unknown LLM_PROVIDER {llm_provider!r} in your .env file. "
            "Supported providers: anthropic, openai, gemini, custom."
        )

    imap_user = require("IMAP_USER")
    imap_password = require("IMAP_PASSWORD")
    data_dir = Path(os.environ.get("DATA_DIR", "./data")).expanduser().resolve()

    return Config(
        imap_host=require("IMAP_HOST"),
        imap_port=int(os.environ.get("IMAP_PORT", "993")),
        imap_user=imap_user,
        imap_password=imap_password,
        imap_folder=os.environ.get("IMAP_FOLDER", "INBOX"),
        smtp_host=require("SMTP_HOST"),
        smtp_port=int(os.environ.get("SMTP_PORT", "587")),
        smtp_user=os.environ.get("SMTP_USER", "").strip() or imap_user,
        smtp_password=os.environ.get("SMTP_PASSWORD", "").strip() or imap_password,
        smtp_use_ssl=os.environ.get("SMTP_USE_SSL", "false").lower() == "true",
        llm_provider=llm_provider,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
        llm_base_url=llm_base_url,
        watch_senders=watch_senders,
        watch_keywords=watch_keywords,
        match_mode=os.environ.get("MATCH_MODE", "any").lower(),
        mark_as_read=os.environ.get("MARK_AS_READ", "false").lower() == "true",
        data_dir=data_dir,
    )
