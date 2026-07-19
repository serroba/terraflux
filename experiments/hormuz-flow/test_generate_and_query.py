import json
import subprocess
import sys
import unittest
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent


class FlowExperimentTest(unittest.TestCase):
    def setUp(self) -> None:
        completed = subprocess.run(
            [sys.executable, "generate_and_query.py"],
            cwd=EXPERIMENT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
        self.result = json.loads(completed.stdout)

    def test_top_level_shape(self) -> None:
        self.assertEqual(self.result["query_date"], "2026-07-17")
        self.assertGreaterEqual(self.result["query_elapsed_ms"], 0)
        self.assertEqual(
            set(self.result["gates"]),
            {"strait_of_hormuz", "strait_of_malacca"},
        )

    def test_hormuz_daily_aggregate_is_deterministic(self) -> None:
        hormuz = self.result["gates"]["strait_of_hormuz"]
        self.assertEqual(hormuz["event_date"], "2026-07-17")
        self.assertEqual(hormuz["observed_crossings"], 5)
        self.assertEqual(hormuz["inbound_crossings"], 2)
        self.assertEqual(hormuz["outbound_crossings"], 3)
        self.assertEqual(hormuz["observed_capacity_dwt"], 1_440_000)
        # At Hormuz the laden (loaded) leg is outbound, so laden flux tracks the
        # three outbound crude/LNG transits, not the two ballast returns.
        self.assertEqual(hormuz["laden_crossings"], 3)
        self.assertEqual(hormuz["laden_capacity_dwt"], 1_020_000)
        # Laden capacity converted to energy via per-commodity net calorific values:
        # 320k*42.3 (crude) + 180k*48.0 (LNG) + 520k*44.3 (products) GJ.
        self.assertEqual(hormuz["observed_energy_gj"], 45_212_000)
        self.assertGreater(hormuz["partition_bytes"], 0)

    def test_malacca_daily_aggregate_is_deterministic(self) -> None:
        malacca = self.result["gates"]["strait_of_malacca"]
        self.assertEqual(malacca["event_date"], "2026-07-17")
        self.assertEqual(malacca["observed_crossings"], 4)
        self.assertEqual(malacca["inbound_crossings"], 1)
        self.assertEqual(malacca["outbound_crossings"], 3)
        self.assertEqual(malacca["observed_capacity_dwt"], 830_000)
        self.assertEqual(malacca["laden_crossings"], 3)
        self.assertEqual(malacca["laden_capacity_dwt"], 740_000)
        # 280k*42.3 (crude) + 160k*48.0 (LNG) + 300k*42.3 (crude) GJ.
        self.assertEqual(malacca["observed_energy_gj"], 32_214_000)
        self.assertGreater(malacca["partition_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
