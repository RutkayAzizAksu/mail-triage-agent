import unittest

from mail_triage_agent.trust import assess


class TrustCheckTest(unittest.TestCase):
    def test_clean_message_has_no_warnings(self):
        # Modeled on a real "Link <notifications@link.com>" verification email
        # with SPF/DKIM/DMARC all passing.
        result = assess(
            from_addr="notifications@link.com",
            from_name="Link",
            reply_to="",
            authentication_results=(
                "spf=pass smtp.mailfrom=link.com; "
                "dkim=pass header.d=link.com; "
                "dmarc=pass header.from=link.com"
            ),
        )
        self.assertFalse(result.is_suspicious)
        self.assertEqual(result.spf, "pass")
        self.assertEqual(result.dkim, "pass")
        self.assertEqual(result.dmarc, "pass")
        self.assertEqual(result.warnings, [])

    def test_failed_dmarc_is_flagged(self):
        result = assess(
            from_addr="billing@totally-not-a-bank.example",
            from_name="Your Bank",
            reply_to="",
            authentication_results="spf=fail; dkim=fail; dmarc=fail",
        )
        self.assertTrue(result.is_suspicious)
        self.assertIn("SPF authentication FAILED", result.warnings)
        self.assertIn("DKIM authentication FAILED", result.warnings)
        self.assertIn("DMARC authentication FAILED", result.warnings)

    def test_reply_to_mismatch_is_flagged(self):
        result = assess(
            from_addr="support@example.com",
            from_name="Support",
            reply_to="attacker@other-domain.example",
            authentication_results="spf=pass; dkim=pass; dmarc=pass",
        )
        self.assertTrue(result.reply_to_mismatch)
        self.assertTrue(result.is_suspicious)

    def test_brand_impersonation_in_display_name_is_flagged(self):
        result = assess(
            from_addr="random123@totally-different-domain.example",
            from_name="PayPal Support",
            reply_to="",
            authentication_results="",
        )
        self.assertEqual(result.impersonated_brand, "paypal")
        self.assertTrue(result.is_suspicious)

    def test_matching_brand_domain_is_not_flagged(self):
        result = assess(
            from_addr="service@paypal.com",
            from_name="PayPal",
            reply_to="",
            authentication_results="spf=pass; dkim=pass; dmarc=pass",
        )
        self.assertEqual(result.impersonated_brand, "")
        self.assertFalse(result.is_suspicious)

    def test_unknown_auth_results_dont_count_as_failure(self):
        # Some mail servers don't attach Authentication-Results at all.
        result = assess(
            from_addr="someone@example.com",
            from_name="Someone",
            reply_to="",
            authentication_results="",
        )
        self.assertEqual(result.spf, "unknown")
        self.assertFalse(result.is_suspicious)


if __name__ == "__main__":
    unittest.main()
