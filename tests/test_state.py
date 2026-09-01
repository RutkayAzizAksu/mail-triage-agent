import tempfile
import unittest
from pathlib import Path

from mail_triage_agent.state import ProcessedState


class ProcessedStateTest(unittest.TestCase):
    def test_mark_and_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "state.json"

            state = ProcessedState(state_file)
            self.assertFalse(state.is_processed("123"))
            state.mark_processed("123")
            self.assertTrue(state.is_processed("123"))
            state.save()

            reloaded = ProcessedState(state_file)
            self.assertTrue(reloaded.is_processed("123"))
            self.assertFalse(reloaded.is_processed("456"))


if __name__ == "__main__":
    unittest.main()
