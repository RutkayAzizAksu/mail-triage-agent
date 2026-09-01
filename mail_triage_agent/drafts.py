from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import yaml

from .analyzer import Analysis
from .filters import EmailMessage


@dataclass
class DraftPaths:
    draft_id: str
    reply_path: Path
    report_path: Path


def _safe_slug(text: str, max_len: int = 40) -> str:
    slug = "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug[:max_len] or "email"


def write_report(drafts_dir: Path, draft_id: str, message: EmailMessage, analysis: Analysis) -> Path:
    drafts_dir.mkdir(parents=True, exist_ok=True)
    report_path = drafts_dir / f"{draft_id}.report.md"
    report_path.write_text(
        "\n".join(
            [
                f"# Mail Report — {message.subject}",
                "",
                f"- **From:** {message.from_name} <{message.from_addr}>",
                f"- **Date:** {message.date}",
                f"- **Category:** {analysis.category}",
                f"- **Priority:** {analysis.priority}",
                "",
                "## Summary",
                analysis.summary,
                "",
                "## Suggested action",
                analysis.suggested_action,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report_path


def write_reply_draft(drafts_dir: Path, message: EmailMessage, analysis: Analysis) -> DraftPaths:
    drafts_dir.mkdir(parents=True, exist_ok=True)
    draft_id = f"{uuid.uuid4().hex[:8]}-{_safe_slug(message.subject)}"

    report_path = write_report(drafts_dir, draft_id, message, analysis)

    reply_path = drafts_dir / f"{draft_id}.reply.md"
    frontmatter = {
        "to": message.from_addr,
        "subject": analysis.reply_subject or f"Re: {message.subject}",
        "in_reply_to": message.message_id,
        "references": message.message_id,
        "status": "pending",
    }
    content = "---\n" + yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False) + "---\n\n"
    content += analysis.reply_body or (
        "(Claude did not think this email needed a reply — edit this text yourself, "
        "or just leave this draft unsent.)\n"
    )
    reply_path.write_text(content, encoding="utf-8")

    return DraftPaths(draft_id=draft_id, reply_path=reply_path, report_path=report_path)


def read_draft(reply_path: Path) -> Tuple[dict, str]:
    raw = reply_path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        raise ValueError(f"Draft file {reply_path} is missing its YAML frontmatter (a '---' block at the top).")
    parts = raw.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"Draft file {reply_path} has a malformed YAML frontmatter block.")
    _, fm_text, body = parts
    frontmatter = yaml.safe_load(fm_text) or {}
    return frontmatter, body.strip()


def mark_sent(reply_path: Path) -> None:
    frontmatter, body = read_draft(reply_path)
    frontmatter["status"] = "sent"
    content = "---\n" + yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False) + "---\n\n" + body + "\n"
    reply_path.write_text(content, encoding="utf-8")
