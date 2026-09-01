# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Multi-provider AI support: `LLM_PROVIDER` now selects between `anthropic`
  (default), `openai`, `gemini` (free tier available), and `custom` (any
  OpenAI-compatible endpoint — Groq, OpenRouter, a local Ollama server,
  etc.), so anyone can bring their own API key, including free ones. Only
  the selected provider's key/model is required.
- Sender trust check: every matched email is checked for SPF/DKIM/DMARC
  authentication, Reply-To vs. From domain mismatches, and display-name
  brand-impersonation heuristics *before* it's analyzed or drafted. The
  verdict is written to `report.md` and passed to the AI provider so the
  drafted reply reflects it.

## [0.1.0] - 2026-09-01

### Added
- Initial release: IMAP/SMTP inbox watcher with sender/keyword filtering
  (works with any standard IMAP/SMTP provider — Gmail, Outlook, Yahoo,
  iCloud, corporate mail servers).
- Claude-based email analysis (summary, category, priority, suggested
  action) via the Anthropic API.
- Editable Markdown draft replies with a YAML frontmatter header (`to`,
  `subject`, `in_reply_to`, `references`, `status`).
- `check` / `list` / `send` CLI commands. No mail is ever sent automatically.
- Local state tracking (`data/state.json`) so re-running `check` never
  creates duplicate drafts.
- Unit tests plus mocked end-to-end smoke tests covering the full
  fetch → filter → analyze → draft → send pipeline.
