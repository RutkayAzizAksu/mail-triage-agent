from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from .analyzer import AnalyzerError, EmailAnalyzer
from .config import ConfigError, load_config
from .drafts import write_reply_draft
from .filters import matches
from .imap_client import ImapClient, ImapError
from .smtp_sender import SmtpError, send_draft
from .state import ProcessedState
from .trust import assess as assess_trust


def cmd_check(args: argparse.Namespace) -> int:
    config = load_config(args.env_file)
    state = ProcessedState(config.state_file)
    analyzer = EmailAnalyzer(
        config.llm_provider, config.llm_api_key, config.llm_model, base_url=config.llm_base_url
    )

    created = 0
    scanned = 0
    with ImapClient(
        config.imap_host, config.imap_port, config.imap_user, config.imap_password, config.imap_folder
    ) as client:
        messages = client.fetch_recent(limit=args.limit, unseen_only=not args.include_seen)
        for message in messages:
            scanned += 1
            if state.is_processed(message.uid):
                continue

            if not matches(message, config.watch_senders, config.watch_keywords, config.match_mode):
                state.mark_processed(message.uid)
                continue

            print(f"[match] {message.from_addr} — {message.subject!r}")

            # Check sender trust (SPF/DKIM/DMARC, Reply-To mismatch, brand impersonation)
            # BEFORE analyzing/drafting, so the trust verdict can inform the draft.
            trust = assess_trust(
                message.from_addr, message.from_name, message.reply_to, message.authentication_results
            )
            trust_icon = "⚠️ " if trust.is_suspicious else "✅ "
            print(f"  {trust_icon}{trust.summary_line}")

            try:
                analysis = analyzer.analyze(message, trust_summary=trust.summary_line)
            except AnalyzerError as exc:
                print(f"  ! analysis failed, will retry next run: {exc}", file=sys.stderr)
                continue

            paths = write_reply_draft(config.drafts_dir, message, analysis, trust)
            print(f"  -> report: {paths.report_path.name}")
            print(f"  -> draft:  {paths.reply_path.name}")

            if config.mark_as_read:
                client.mark_seen(message.uid)
            state.mark_processed(message.uid)
            created += 1

    state.save()
    print(f"\nScanned {scanned} message(s), created {created} new draft(s) in {config.drafts_dir}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    config = load_config(args.env_file)
    if not config.drafts_dir.exists():
        print("No drafts yet. Run 'mail-triage-agent check' first.")
        return 0
    reply_files = sorted(config.drafts_dir.glob("*.reply.md"))
    if not reply_files:
        print("No drafts yet. Run 'mail-triage-agent check' first.")
        return 0
    for reply_path in reply_files:
        print(reply_path.name)
    return 0


def cmd_send(args: argparse.Namespace) -> int:
    config = load_config(args.env_file)
    reply_path = config.drafts_dir / args.draft
    if not reply_path.exists():
        reply_path = Path(args.draft)
    if not reply_path.exists():
        print(f"Draft not found: {args.draft}", file=sys.stderr)
        return 1

    try:
        to_addr = send_draft(
            reply_path,
            config.smtp_host,
            config.smtp_port,
            config.smtp_user,
            config.smtp_password,
            config.smtp_use_ssl,
        )
    except SmtpError as exc:
        print(f"Send failed: {exc}", file=sys.stderr)
        return 1

    print(f"Sent to {to_addr}.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mail-triage-agent",
        description="Filter incoming email by sender/keyword, analyze it with Claude, and prepare reply drafts for you to review and send.",
    )
    parser.add_argument("--env-file", default=None, help="Path to a .env file (default: .env in the current directory)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Fetch new matching emails, analyze them, and write reply drafts.")
    p_check.add_argument("--limit", type=int, default=50, help="Max number of recent messages to scan (default: 50)")
    p_check.add_argument("--include-seen", action="store_true", help="Also scan messages already marked as read")
    p_check.set_defaults(func=cmd_check)

    p_list = sub.add_parser("list", help="List pending draft files.")
    p_list.set_defaults(func=cmd_list)

    p_send = sub.add_parser("send", help="Send a (possibly edited) draft reply.")
    p_send.add_argument("draft", help="Draft filename (e.g. ab12cd34-invoice-due.reply.md) or full path")
    p_send.set_defaults(func=cmd_send)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except ImapError as exc:
        print(f"IMAP error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
