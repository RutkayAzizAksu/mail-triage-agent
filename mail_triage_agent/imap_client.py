from __future__ import annotations

import email
import imaplib
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parseaddr
from typing import List, Optional

from .filters import EmailMessage


class ImapError(RuntimeError):
    """Raised when connecting to or reading from the IMAP server fails."""


def _decode(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _extract_body(msg: Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition") or "")
            if content_type == "text/plain" and "attachment" not in disposition:
                charset = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                try:
                    return payload.decode(charset, errors="replace")
                except (LookupError, UnicodeDecodeError):
                    return payload.decode("utf-8", errors="replace")
        return ""

    charset = msg.get_content_charset() or "utf-8"
    payload = msg.get_payload(decode=True)
    if payload is None:
        return ""
    try:
        return payload.decode(charset, errors="replace")
    except (LookupError, UnicodeDecodeError):
        return payload.decode("utf-8", errors="replace")


class ImapClient:
    """Thin wrapper around imaplib that works with any standard IMAP4-over-SSL server
    (Gmail, Outlook/Microsoft 365, Yahoo, iCloud, and most corporate mail servers)."""

    def __init__(self, host: str, port: int, user: str, password: str, folder: str = "INBOX"):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.folder = folder
        self._conn: Optional[imaplib.IMAP4_SSL] = None

    def __enter__(self) -> "ImapClient":
        try:
            self._conn = imaplib.IMAP4_SSL(self.host, self.port)
            self._conn.login(self.user, self.password)
        except (imaplib.IMAP4.error, OSError) as exc:
            raise ImapError(
                f"Could not connect/login to {self.host}:{self.port} as {self.user}. "
                "Check IMAP_HOST/IMAP_PORT/IMAP_USER/IMAP_PASSWORD in your .env file "
                "(most providers require an app-specific password, not your normal login password). "
                f"Original error: {exc}"
            ) from exc

        status, _ = self._conn.select(self.folder)
        if status != "OK":
            raise ImapError(f"Could not select IMAP folder {self.folder!r}. Check IMAP_FOLDER in your .env file.")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            try:
                self._conn.logout()
            except Exception:
                pass

    def fetch_recent(self, limit: int = 50, unseen_only: bool = True) -> List[EmailMessage]:
        assert self._conn is not None, "ImapClient must be used as a context manager (with ImapClient(...) as client:)"
        criteria = "UNSEEN" if unseen_only else "ALL"
        status, data = self._conn.search(None, criteria)
        if status != "OK":
            raise ImapError(f"IMAP SEARCH failed with status {status!r}")

        uids = data[0].split() if data and data[0] else []
        uids = uids[-limit:]

        messages: List[EmailMessage] = []
        for uid in uids:
            status, msg_data = self._conn.fetch(uid, "(RFC822)")
            if status != "OK" or not msg_data or msg_data[0] is None:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            from_name, from_addr = parseaddr(_decode(msg.get("From")))
            messages.append(
                EmailMessage(
                    uid=uid.decode(),
                    message_id=_decode(msg.get("Message-ID")) or "",
                    from_addr=from_addr.lower(),
                    from_name=from_name or from_addr,
                    subject=_decode(msg.get("Subject")),
                    date=_decode(msg.get("Date")),
                    body=_extract_body(msg).strip(),
                    reply_to=_decode(msg.get("Reply-To")) or "",
                    authentication_results=_decode(msg.get("Authentication-Results")) or "",
                )
            )
        return messages

    def mark_seen(self, uid: str) -> None:
        assert self._conn is not None, "ImapClient must be used as a context manager (with ImapClient(...) as client:)"
        self._conn.store(uid, "+FLAGS", "\\Seen")
