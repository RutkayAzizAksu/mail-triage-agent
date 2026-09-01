import unittest
from unittest import mock

from mail_triage_agent.analyzer import AnalyzerError, EmailAnalyzer
from mail_triage_agent.filters import EmailMessage


def make_message(**overrides):
    base = dict(
        uid="1",
        message_id="<abc@example.com>",
        from_addr="alice@example.com",
        from_name="Alice",
        subject="Invoice due",
        date="Mon, 1 Sep 2026 10:00:00 +0000",
        body="Please pay the attached invoice by Friday.",
    )
    base.update(overrides)
    return EmailMessage(**base)


VALID_RESPONSE = """{
  "summary": "Alice is asking for payment.",
  "category": "invoice",
  "priority": "high",
  "suggested_action": "Pay or reply with a timeline.",
  "needs_reply": true,
  "reply_subject": "Re: Invoice due",
  "reply_body": "Hi Alice, I'll take care of this today."
}"""


class EmailAnalyzerTest(unittest.TestCase):
    def test_rejects_unknown_provider(self):
        with self.assertRaises(AnalyzerError):
            EmailAnalyzer(provider="not-a-real-provider", api_key="x", model="x")

    def test_anthropic_provider_parses_json_response(self):
        analyzer = EmailAnalyzer(provider="anthropic", api_key="fake", model="claude-sonnet-5")
        with mock.patch.object(analyzer, "_call", return_value=VALID_RESPONSE):
            analysis = analyzer.analyze(make_message())
        self.assertEqual(analysis.category, "invoice")
        self.assertEqual(analysis.priority, "high")
        self.assertTrue(analysis.needs_reply)

    def test_openai_provider_parses_json_response(self):
        analyzer = EmailAnalyzer(provider="openai", api_key="fake", model="gpt-4o-mini")
        with mock.patch.object(analyzer, "_call", return_value=VALID_RESPONSE):
            analysis = analyzer.analyze(make_message())
        self.assertEqual(analysis.category, "invoice")

    def test_gemini_provider_parses_json_response(self):
        analyzer = EmailAnalyzer(provider="gemini", api_key="fake", model="gemini-2.5-flash")
        with mock.patch.object(analyzer, "_call", return_value=VALID_RESPONSE):
            analysis = analyzer.analyze(make_message())
        self.assertEqual(analysis.category, "invoice")

    def test_custom_provider_uses_configured_base_url(self):
        analyzer = EmailAnalyzer(
            provider="custom",
            api_key="fake",
            model="llama-3.3-70b-versatile",
            base_url="https://api.groq.com/openai/v1",
        )
        with mock.patch(
            "mail_triage_agent.analyzer._call_openai_compatible", return_value=VALID_RESPONSE
        ) as mocked:
            analysis = analyzer.analyze(make_message())
        mocked.assert_called_once()
        self.assertEqual(mocked.call_args.kwargs.get("base_url"), "https://api.groq.com/openai/v1")
        self.assertEqual(analysis.category, "invoice")

    def test_strips_markdown_json_fence(self):
        analyzer = EmailAnalyzer(provider="anthropic", api_key="fake", model="claude-sonnet-5")
        fenced = "```json\n" + VALID_RESPONSE + "\n```"
        with mock.patch.object(analyzer, "_call", return_value=fenced):
            analysis = analyzer.analyze(make_message())
        self.assertEqual(analysis.category, "invoice")

    def test_invalid_json_raises_analyzer_error(self):
        analyzer = EmailAnalyzer(provider="anthropic", api_key="fake", model="claude-sonnet-5")
        with mock.patch.object(analyzer, "_call", return_value="not json at all"):
            with self.assertRaises(AnalyzerError):
                analyzer.analyze(make_message())

    def test_trust_summary_is_included_in_prompt_context(self):
        analyzer = EmailAnalyzer(provider="anthropic", api_key="fake", model="claude-sonnet-5")
        with mock.patch.object(analyzer, "_call", return_value=VALID_RESPONSE) as mocked:
            analyzer.analyze(make_message(), trust_summary="2 warning(s) for example.com: SPF authentication FAILED")
        sent_content = mocked.call_args.args[0]
        self.assertIn("Sender-trust check", sent_content)
        self.assertIn("SPF authentication FAILED", sent_content)


if __name__ == "__main__":
    unittest.main()
