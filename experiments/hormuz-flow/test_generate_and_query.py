import json
import subprocess
import sys
import unittest
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent


class HormuzFlowExperimentTest(unittest.TestCase):
    def test_daily_aggregate_is_deterministic(self) -> None:
        completed = subprocess.run(
            [sys.executable, "generate_and_query.py"],
            cwd=EXPERIMENT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)

        self.assertEqual(result["event_date"], "2026-07-17")
        self.assertEqual(result["observed_crossings"], 5)
        self.assertEqual(result["inbound_crossings"], 2)
        self.assertEqual(result["outbound_crossings"], 3)
        self.assertEqual(result["observed_capacity_dwt"], 1_440_000)
        # At Hormuz the laden (loaded) leg is outbound, so laden flux tracks the
        # three outbound crude/LNG transits, not the two ballast returns.
        self.assertEqual(result["laden_crossings"], 3)
        self.assertEqual(result["laden_capacity_dwt"], 1_020_000)
        self.assertGreaterEqual(result["query_elapsed_ms"], 0)
        self.assertGreater(result["partition_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
