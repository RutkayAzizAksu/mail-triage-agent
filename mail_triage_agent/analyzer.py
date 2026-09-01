from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from .filters import EmailMessage

SYSTEM_PROMPT = """You are an email triage assistant. You will be given the contents of one email,
plus a deterministic sender-trust check (SPF/DKIM/DMARC authentication, Reply-To mismatch, and
brand-impersonation heuristics) that was already computed for you — trust that check's verdict,
don't re-derive it yourself. Factor it into suggested_action and the drafted reply (e.g. urge caution
before clicking links or replying with sensitive info if the trust check raised warnings).

Respond with ONLY a JSON object (no markdown fences, no extra text) with exactly these fields:

{
  "summary": "1-3 sentence summary of what the email is about",
  "category": "one short label, e.g. 'customer question', 'invoice', 'meeting request', 'spam-like', 'FYI'",
  "priority": "low | medium | high",
  "suggested_action": "what the recipient should do about this email, in 1-2 sentences",
  "needs_reply": true or false,
  "reply_subject": "a suitable 'Re: ...' subject line (empty string if needs_reply is false)",
  "reply_body": "a complete, polite draft reply in the same language as the original email (empty string if needs_reply is false)"
}
"""

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
_KNOWN_PROVIDERS = {"anthropic", "openai", "gemini", "custom"}


@dataclass
class Analysis:
    summary: str
    category: str
    priority: str
    suggested_action: str
    needs_reply: bool
    reply_subject: str
    reply_body: str


class AnalyzerError(RuntimeError):
    """Raised when the LLM API call fails or returns something we can't parse."""


def _call_anthropic(api_key: str, model: str, user_content: str) -> str:
    import anthropic  # imported lazily so users who don't use this provider don't need it installed

    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
    except anthropic.APIError as exc:
        raise AnalyzerError(f"Anthropic API call failed: {exc}") from exc

    return "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()


def _call_openai_compatible(api_key: str, model: str, user_content: str, base_url: Optional[str] = None) -> str:
    """Works with the official OpenAI API and any OpenAI-compatible chat-completions
    endpoint: Gemini (Google's own compatibility layer), Groq, OpenRouter, Together,
    DeepSeek, a local Ollama/LM Studio server, etc. — just point base_url at it."""
    import openai  # imported lazily so users who don't use this provider don't need it installed

    client = openai.OpenAI(api_key=api_key, base_url=base_url) if base_url else openai.OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=model,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
    except openai.OpenAIError as exc:
        raise AnalyzerError(f"API call to {base_url or 'api.openai.com'} failed: {exc}") from exc

    return (response.choices[0].message.content or "").strip()


class EmailAnalyzer:
    """Analyzes an email using whichever LLM provider the user configured
    (bring your own API key): Anthropic Claude, OpenAI, Google Gemini, or any
    other OpenAI-compatible API (Groq, OpenRouter, a local Ollama server, ...)."""

    def __init__(self, provider: str, api_key: str, model: str, base_url: Optional[str] = None):
        provider = provider.strip().lower()
        if provider not in _KNOWN_PROVIDERS:
            raise AnalyzerError(
                f"Unknown LLM_PROVIDER {provider!r}. Supported providers: {', '.join(sorted(_KNOWN_PROVIDERS))}."
            )
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def _call(self, user_content: str) -> str:
        if self.provider == "anthropic":
            return _call_anthropic(self.api_key, self.model, user_content)
        if self.provider == "gemini":
            return _call_openai_compatible(self.api_key, self.model, user_content, base_url=_GEMINI_BASE_URL)
        # "openai" (base_url=None -> api.openai.com) and "custom" (base_url from config)
        # both speak the same OpenAI-compatible chat-completions shape.
        return _call_openai_compatible(self.api_key, self.model, user_content, base_url=self.base_url)

    def analyze(self, message: EmailMessage, trust_summary: str = "") -> Analysis:
        user_content = (
            f"From: {message.from_name} <{message.from_addr}>\n"
            f"Subject: {message.subject}\n"
            f"Date: {message.date}\n"
        )
        if trust_summary:
            user_content += f"Sender-trust check: {trust_summary}\n"
        user_content += f"\n{message.body[:8000]}"

        text = self._call(user_content)

        # Models sometimes wrap JSON in ```json fences despite instructions; strip them defensively.
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AnalyzerError(f"{self.provider} did not return valid JSON: {text[:500]!r}") from exc

        return Analysis(
            summary=str(data.get("summary", "")),
            category=str(data.get("category", "")),
            priority=str(data.get("priority", "medium")),
            suggested_action=str(data.get("suggested_action", "")),
            needs_reply=bool(data.get("needs_reply", False)),
            reply_subject=str(data.get("reply_subject", "")),
            reply_body=str(data.get("reply_body", "")),
        )
