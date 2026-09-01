# Security Policy

Mail Triage Agent reads your inbox over IMAP, calls your configured AI
provider's API with matching email content, and can send mail over SMTP —
please review the code before running it against a real mailbox, which is
good practice for any tool that touches your inbox and credentials.

## Design notes relevant to security

- **No automatic sending.** Every outgoing reply requires an explicit
  `mail-triage-agent send <draft>` run by the user; `check` only ever reads
  mail and writes local draft files.
- **Credentials stay local.** `IMAP_PASSWORD`, `SMTP_PASSWORD`, and your AI
  provider's API key (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`,
  or `CUSTOM_API_KEY`, depending on `LLM_PROVIDER`) are read only from your
  local `.env` file (git-ignored by default) and are never logged, written to
  a draft/report file, or sent anywhere except to the mail server and the AI
  provider you configured.
- **Filtered scope.** Only messages matching your `WATCH_SENDERS` /
  `WATCH_KEYWORDS` are ever sent to your configured AI provider for analysis;
  everything else is left untouched on the mail server.
- **Sender trust check.** The trust check (SPF/DKIM/DMARC, Reply-To
  mismatch, brand-impersonation heuristics) is entirely local and
  deterministic — it doesn't call any external service.

## Reporting a vulnerability

If you find a security issue — e.g. a way credentials or email content could
leak, or a path that sends mail without explicit user action — please report
it privately rather than opening a public issue:

- Open a [GitHub Security Advisory](https://github.com/RutkayAzizAksu/mail-triage-agent/security/advisories/new)
  on this repository, or
- Contact the maintainer via the email on the
  [GitHub profile](https://github.com/RutkayAzizAksu).

Please include steps to reproduce and the potential impact. We'll aim to
acknowledge reports within a few days.
