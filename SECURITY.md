# Security Policy

Mail Triage Agent reads your inbox over IMAP, calls the Anthropic API with
matching email content, and can send mail over SMTP — please review the code
before running it against a real mailbox, which is good practice for any tool
that touches your inbox and credentials.

## Design notes relevant to security

- **No automatic sending.** Every outgoing reply requires an explicit
  `mail-triage-agent send <draft>` run by the user; `check` only ever reads
  mail and writes local draft files.
- **Credentials stay local.** `IMAP_PASSWORD`, `SMTP_PASSWORD`, and
  `ANTHROPIC_API_KEY` are read only from your local `.env` file (git-ignored
  by default) and are never logged, written to a draft/report file, or sent
  anywhere except to the mail server and Anthropic API you configured.
- **Filtered scope.** Only messages matching your `WATCH_SENDERS` /
  `WATCH_KEYWORDS` are ever sent to the Anthropic API for analysis; everything
  else is left untouched on the mail server.

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
