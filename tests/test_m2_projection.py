import tempfile
import unittest
from pathlib import Path

from m2_orchestrator.projection import Outbox, plan
from m2_orchestrator.state import StateError


class ProjectionTests(unittest.TestCase):
    def test_owner_fields_and_newer_edits_are_protected(self):
        with self.assertRaises(StateError):
            plan("r", "a", {"Status": "Proposed"}, {"Status": "Taking"})
        a = plan("r", "a", {"Metric": 2}, {"Metric": 3}, {"Metric": 1})
        self.assertEqual(a["state"], "CONFLICT")

    def test_uncertain_create_cannot_be_resent_and_readback_is_required(self):
        with tempfile.TemporaryDirectory() as d:
            o = Outbox(Path(d)/"outbox.sqlite")
            a = plan("r", "a", {"Name": "test", "Views": None})
            self.assertEqual(o.stage(a), "STAGED")
            o.dispatch(a["key"])
            o.uncertain(a["key"])
            with self.assertRaises(StateError):
                o.dispatch(a["key"])
            with self.assertRaises(StateError):
                o.verify(a["key"], "page", {"Name": "test", "Views": 0})
            self.assertFalse(o.summary()["complete"])
            o.verify(a["key"], "page", {"Name": "test", "Views": None})
            self.assertTrue(o.summary()["complete"])
            self.assertEqual(o.stage(a), "VERIFIED")

    def test_number_readback_normalizes_without_coercing_null_or_boolean(self):
        with tempfile.TemporaryDirectory() as d:
            o = Outbox(Path(d)/"outbox.sqlite")
            a = plan("r", "a", {"Views": 1, "Saves": None, "Quarantine": ""})
            o.stage(a); o.dispatch(a["key"])
            with self.assertRaises(StateError):
                o.verify(a["key"], "page", {"Views": True, "Saves": None})
            with self.assertRaises(StateError):
                o.verify(a["key"], "page", {"Views": 1, "Saves": 0})
            o.verify(a["key"], "page", {"Views": 1.0, "Saves": None, "Quarantine": None})

    def test_update_preflight_detects_intervening_edit(self):
        with tempfile.TemporaryDirectory() as d:
            o = Outbox(Path(d)/"outbox.sqlite")
            a = plan("r", "a", {"Metric": 2}, {"Metric": 1}, {"Metric": 1})
            o.stage(a)
            with self.assertRaises(StateError):
                o.dispatch(a["key"], {"Metric": 9})
            self.assertEqual(o.dispatch(a["key"], {"Metric": 1})["state"], "STAGED")


if __name__ == '__main__':
    unittest.main()
