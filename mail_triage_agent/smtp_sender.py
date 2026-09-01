from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from pathlib import Path

from .drafts import mark_sent, read_draft


class SmtpError(RuntimeError):
    """Raised when sending a draft over SMTP fails."""


def send_draft(
    reply_path: Path,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    use_ssl: bool = False,
) -> str:
    frontmatter, body = read_draft(reply_path)

    if frontmatter.get("status") == "sent":
        raise SmtpError(f"Draft {reply_path.name} was already marked as sent. Delete the file if you want to resend it.")

    to_addr = frontmatter.get("to")
    subject = frontmatter.get("subject", "")
    if not to_addr:
        raise SmtpError(f"Draft {reply_path.name} has no 'to' address in its frontmatter.")
    if not body.strip():
        raise SmtpError(f"Draft {reply_path.name} has an empty body — nothing to send.")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_addr
    if frontmatter.get("in_reply_to"):
        msg["In-Reply-To"] = frontmatter["in_reply_to"]
    if frontmatter.get("references"):
        msg["References"] = frontmatter["references"]

    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
    except (smtplib.SMTPException, OSError) as exc:
        raise SmtpError(f"Could not connect to SMTP server {smtp_host}:{smtp_port}: {exc}") from exc

    try:
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, [to_addr], msg.as_string())
    except smtplib.SMTPException as exc:
        raise SmtpError(
            f"Could not send via {smtp_host}:{smtp_port} as {smtp_user}. "
            "Check SMTP_USER/SMTP_PASSWORD in your .env file (most providers require an app-specific password). "
            f"Original error: {exc}"
        ) from exc
    finally:
        server.quit()

    mark_sent(reply_path)
    return to_addr
