from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class EmailMessage:
    uid: str
    message_id: str
    from_addr: str
    from_name: str
    subject: str
    date: str
    body: str


def matches(message: EmailMessage, senders: List[str], keywords: List[str], mode: str = "any") -> bool:
    """Return True if the message matches the configured sender/keyword filters.

    - If neither senders nor keywords are configured, nothing matches (there is
      nothing to filter on).
    - mode="any": match if the sender is in the list OR a keyword is found.
    - mode="all": if both filter types are configured, require both a sender and
      a keyword hit. If only one filter type is configured, behaves like "any".
    """
    if not senders and not keywords:
        return False

    sender_hit = any(s in message.from_addr.lower() for s in senders) if senders else False
    haystack = f"{message.subject}\n{message.body}".lower()
    keyword_hit = any(k in haystack for k in keywords) if keywords else False

    if mode == "all" and senders and keywords:
        return sender_hit and keyword_hit
    return sender_hit or keyword_hit
