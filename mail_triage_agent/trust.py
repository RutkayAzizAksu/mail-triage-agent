from __future__ import annotations

import re
from dataclasses import dataclass, field
from email.utils import parseaddr
from typing import List

# Brand names commonly impersonated in display-name spoofing (e.g. "PayPal Support"
# from a domain that has nothing to do with paypal.com). Not exhaustive — a heuristic,
# not a threat-intel database.
_WATCHED_BRANDS = [
    "paypal", "amazon", "apple", "microsoft", "google", "netflix",
    "dhl", "fedex", "ups", "stripe", "docusign", "linkedin",
    "facebook", "instagram", "whatsapp", "revolut", "bank",
]


@dataclass
class TrustCheck:
    sender_domain: str
    spf: str  # "pass" | "fail" | "unknown"
    dkim: str
    dmarc: str
    reply_to_mismatch: bool
    impersonated_brand: str  # brand name if display-name impersonation suspected, else ""
    warnings: List[str] = field(default_factory=list)

    @property
    def is_suspicious(self) -> bool:
        return bool(self.warnings)

    @property
    def summary_line(self) -> str:
        if not self.warnings:
            return (
                f"No red flags for {self.sender_domain} "
                f"(SPF={self.spf}, DKIM={self.dkim}, DMARC={self.dmarc})."
            )
        return f"{len(self.warnings)} warning(s) for {self.sender_domain}: " + "; ".join(self.warnings)


def _parse_authentication_results(raw: str) -> dict:
    result = {"spf": "unknown", "dkim": "unknown", "dmarc": "unknown"}
    for key in result:
        m = re.search(rf"\b{key}=(\w+)", raw, re.IGNORECASE)
        if m:
            result[key] = m.group(1).lower()
    return result


def assess(from_addr: str, from_name: str, reply_to: str, authentication_results: str) -> TrustCheck:
    """Heuristic, deterministic sender-trust check. Not a guarantee — a first pass
    that surfaces the same red flags a careful human would check by hand:
    SPF/DKIM/DMARC authentication, Reply-To mismatches, and brand impersonation
    in the display name.
    """
    domain = from_addr.split("@")[-1].lower() if "@" in from_addr else "unknown"
    warnings: List[str] = []

    auth = _parse_authentication_results(authentication_results)
    for key in ("spf", "dkim", "dmarc"):
        if auth[key] == "fail":
            warnings.append(f"{key.upper()} authentication FAILED")

    reply_to_addr = parseaddr(reply_to)[1].lower() if reply_to else ""
    reply_to_domain = reply_to_addr.split("@")[-1] if "@" in reply_to_addr else ""
    reply_to_mismatch = bool(reply_to_domain) and reply_to_domain != domain
    if reply_to_mismatch:
        warnings.append(f"Reply-To domain ({reply_to_domain}) differs from From domain ({domain})")

    impersonated_brand = ""
    name_lower = (from_name or "").lower()
    for brand in _WATCHED_BRANDS:
        if brand in name_lower and brand not in domain:
            impersonated_brand = brand
            warnings.append(
                f"Display name mentions '{brand}' but the sending domain ({domain}) doesn't match"
            )
            break

    return TrustCheck(
        sender_domain=domain,
        spf=auth["spf"],
        dkim=auth["dkim"],
        dmarc=auth["dmarc"],
        reply_to_mismatch=reply_to_mismatch,
        impersonated_brand=impersonated_brand,
        warnings=warnings,
    )
