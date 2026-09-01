from __future__ import annotations

import json
from dataclasses import dataclass

import anthropic

from .filters import EmailMessage

SYSTEM_PROMPT = """You are an email triage assistant. You will be given the contents of one email.
Analyze it and propose a reply. Respond with ONLY a JSON object (no markdown fences, no extra text)
with exactly these fields:

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
    """Raised when the Claude API call fails or returns something we can't parse."""


class EmailAnalyzer:
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def analyze(self, message: EmailMessage) -> Analysis:
        user_content = (
            f"From: {message.from_name} <{message.from_addr}>\n"
            f"Subject: {message.subject}\n"
            f"Date: {message.date}\n\n"
            f"{message.body[:8000]}"
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
        except anthropic.APIError as exc:
            raise AnalyzerError(f"Anthropic API call failed: {exc}") from exc

        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ).strip()

        # Claude sometimes wraps JSON in ```json fences despite instructions; strip them defensively.
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AnalyzerError(f"Claude did not return valid JSON: {text[:500]!r}") from exc

        return Analysis(
            summary=str(data.get("summary", "")),
            category=str(data.get("category", "")),
            priority=str(data.get("priority", "medium")),
            suggested_action=str(data.get("suggested_action", "")),
            needs_reply=bool(data.get("needs_reply", False)),
            reply_subject=str(data.get("reply_subject", "")),
            reply_body=str(data.get("reply_body", "")),
        )
