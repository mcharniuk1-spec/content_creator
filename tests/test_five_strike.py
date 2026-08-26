import unittest

from m2_engine.five_strike import FiveStrikeLedger


class FiveStrikeTests(unittest.TestCase):
    def test_retryable_failure_is_record_only_and_bounded(self):
        ledger = FiveStrikeLedger()
        decisions = [ledger.decide("yt:video-1:metrics", "timeout") for _ in range(5)]
        self.assertEqual([d.action for d in decisions[:4]], ["retry_record_only"] * 4)
        self.assertEqual(decisions[-1].action, "quarantine")
        self.assertEqual(decisions[-1].strike, 5)
        self.assertEqual(ledger.strike_count("yt:video-1:metrics"), 5)

    def test_non_retryable_failure_blocks_immediately(self):
        ledger = FiveStrikeLedger()
        decision = ledger.decide("ig:account-1:profile", "rights")
        self.assertEqual(decision.action, "block")
        self.assertEqual(decision.backoff_seconds, 0)

    def test_unknown_failure_quarantines(self):
        ledger = FiveStrikeLedger()
        decision = ledger.decide("tt:video-1:comments", "unexpected_payload")
        self.assertEqual(decision.action, "quarantine")
