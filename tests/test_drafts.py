import tempfile
import unittest
from pathlib import Path

from mail_triage_agent.analyzer import Analysis
from mail_triage_agent.drafts import mark_sent, read_draft, write_reply_draft
from mail_triage_agent.filters import EmailMessage
from mail_triage_agent.trust import assess as assess_trust


class DraftsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.drafts_dir = Path(self.tmp.name) / "drafts"

    def tearDown(self):
        self.tmp.cleanup()

    def _message(self):
        return EmailMessage(
            uid="42",
            message_id="<xyz@example.com>",
            from_addr="alice@example.com",
            from_name="Alice",
            subject="Invoice due",
            date="Mon, 1 Sep 2026 10:00:00 +0000",
            body="Please pay the attached invoice by Friday.",
        )

    def _analysis(self):
        return Analysis(
            summary="Alice is asking for payment of an invoice.",
            category="invoice",
            priority="high",
            suggested_action="Pay the invoice or reply with a timeline.",
            needs_reply=True,
            reply_subject="Re: Invoice due",
            reply_body="Hi Alice,\n\nThanks for the reminder, I'll take care of it today.\n\nBest,\nRutkay",
        )

    def _clean_trust(self):
        return assess_trust("alice@example.com", "Alice", "", "spf=pass; dkim=pass; dmarc=pass")

    def test_write_and_read_round_trip(self):
        paths = write_reply_draft(self.drafts_dir, self._message(), self._analysis(), self._clean_trust())
        self.assertTrue(paths.reply_path.exists())
        self.assertTrue(paths.report_path.exists())

        frontmatter, body = read_draft(paths.reply_path)
        self.assertEqual(frontmatter["to"], "alice@example.com")
        self.assertEqual(frontmatter["status"], "pending")
        self.assertIn("Rutkay", body)

    def test_mark_sent_updates_status(self):
        paths = write_reply_draft(self.drafts_dir, self._message(), self._analysis(), self._clean_trust())
        mark_sent(paths.reply_path)
        frontmatter, _ = read_draft(paths.reply_path)
        self.assertEqual(frontmatter["status"], "sent")

    def test_no_reply_needed_leaves_placeholder_body(self):
        analysis = self._analysis()
        analysis.needs_reply = False
        analysis.reply_body = ""
        paths = write_reply_draft(self.drafts_dir, self._message(), analysis, self._clean_trust())
        _, body = read_draft(paths.reply_path)
        self.assertIn("did not think", body)

    def test_report_includes_clean_trust_section(self):
        paths = write_reply_draft(self.drafts_dir, self._message(), self._analysis(), self._clean_trust())
        report = paths.report_path.read_text(encoding="utf-8")
        self.assertIn("Sender trust check", report)
        self.assertIn("✅", report)
        self.assertNotIn("⚠️", report)

    def test_report_flags_suspicious_trust(self):
        suspicious_trust = assess_trust(
            "random@totally-different.example", "PayPal Support", "", "spf=fail; dkim=fail; dmarc=fail"
        )
        paths = write_reply_draft(self.drafts_dir, self._message(), self._analysis(), suspicious_trust)
        report = paths.report_path.read_text(encoding="utf-8")
        self.assertIn("⚠️", report)
        self.assertIn("SPF authentication FAILED", report)


if __name__ == "__main__":
    unittest.main()
