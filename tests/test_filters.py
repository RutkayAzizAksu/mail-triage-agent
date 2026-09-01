import unittest

from mail_triage_agent.filters import EmailMessage, matches


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


class MatchesTest(unittest.TestCase):
    def test_sender_match(self):
        msg = make_message()
        self.assertTrue(matches(msg, ["alice@example.com"], [], "any"))

    def test_keyword_match_in_subject(self):
        msg = make_message()
        self.assertTrue(matches(msg, [], ["invoice"], "any"))

    def test_keyword_match_in_body(self):
        msg = make_message(subject="Hello")
        self.assertTrue(matches(msg, [], ["pay"], "any"))

    def test_no_match(self):
        msg = make_message(from_addr="bob@example.com", subject="Lunch?", body="Free at noon?")
        self.assertFalse(matches(msg, ["alice@example.com"], ["invoice"], "any"))

    def test_all_mode_requires_both(self):
        msg = make_message(from_addr="bob@example.com")
        self.assertFalse(matches(msg, ["alice@example.com"], ["invoice"], "all"))
        msg2 = make_message(from_addr="alice@example.com")
        self.assertTrue(matches(msg2, ["alice@example.com"], ["invoice"], "all"))

    def test_all_mode_falls_back_to_any_when_only_one_filter_set(self):
        msg = make_message()
        self.assertTrue(matches(msg, ["alice@example.com"], [], "all"))

    def test_no_filters_configured_means_no_match(self):
        msg = make_message()
        self.assertFalse(matches(msg, [], [], "any"))

    def test_sender_match_is_case_insensitive(self):
        msg = make_message(from_addr="Alice@Example.com")
        self.assertTrue(matches(msg, ["alice@example.com"], [], "any"))


if __name__ == "__main__":
    unittest.main()
