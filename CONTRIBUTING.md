# Contributing to Mail Triage Agent

Thanks for considering a contribution!

## Getting started

```bash
git clone https://github.com/RutkayAzizAksu/mail-triage-agent.git
cd mail-triage-agent

python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
python -m unittest discover -s tests -v
```

## Making a change

- Keep pull requests focused on a single change.
- Add or update tests in `tests/` for any behavior change — PRs without test
  coverage for new logic will be asked to add it.
- Match the existing style: type-annotated, `from __future__ import annotations`,
  dataclasses for data, small single-purpose modules (`imap_client.py`,
  `analyzer.py`, `drafts.py`, `smtp_sender.py`, `cli.py`).
- Update `README.md` if you change user-facing behavior (CLI flags, `.env`
  variables, file formats, etc.).
- Never commit real credentials, a real `.env` file, or real email content —
  see [SECURITY.md](SECURITY.md).

## Before opening a PR

```bash
python -m py_compile mail_triage_agent/*.py tests/*.py
python -m unittest discover -s tests -v
```

Both must pass — CI runs the same checks on Python 3.9–3.13.

## Reporting bugs / requesting features

Please use the issue templates and include your Python version and mail
provider. Redact any real email addresses, credentials, or message content.

## Security issues

Please don't open a public issue for security vulnerabilities — see
[SECURITY.md](SECURITY.md) for how to report them privately.
