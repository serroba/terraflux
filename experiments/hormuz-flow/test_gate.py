import csv
import unittest
from math import copysign
from pathlib import Path

from gate import HORMUZ_GATE, Gate

EXPERIMENT_DIR = Path(__file__).resolve().parent
TELEMETRY_FIXTURE = EXPERIMENT_DIR / "fixtures" / "telemetry.csv"


class GateGeometryTest(unittest.TestCase):
    def test_sign_matches_side_of_line(self) -> None:
        # A point clearly on the outbound (higher lat/lon) side is positive; a
        # point clearly on the inbound side is negative.
        self.assertGreater(HORMUZ_GATE.signed_distance_nm(26.586, 56.240), 0.0)
        self.assertLess(HORMUZ_GATE.signed_distance_nm(26.559, 56.208), 0.0)

    def test_point_on_the_line_is_approximately_zero(self) -> None:
        midpoint_lat = (HORMUZ_GATE.start_lat + HORMUZ_GATE.end_lat) / 2.0
        midpoint_lon = (HORMUZ_GATE.start_lon + HORMUZ_GATE.end_lon) / 2.0
        distance = HORMUZ_GATE.signed_distance_nm(midpoint_lat, midpoint_lon)
        self.assertAlmostEqual(distance, 0.0, places=6)

    def test_zero_length_gate_is_rejected(self) -> None:
        degenerate = Gate("point", 26.5, 56.2, 26.5, 56.2, laden_direction="outbound")
        with self.assertRaises(ValueError):
            degenerate.signed_distance_nm(26.5, 56.2)

    def test_is_laden_matches_gate_direction(self) -> None:
        self.assertEqual(HORMUZ_GATE.laden_direction, "outbound")
        self.assertTrue(HORMUZ_GATE.is_laden("outbound"))
        self.assertFalse(HORMUZ_GATE.is_laden("inbound"))

    def test_computed_sign_matches_fixture_oracle(self) -> None:
        # The fixture still carries a hand-authored signed_gate_distance_nm. It is
        # no longer the source of truth, but it records the intended side for each
        # observation, so the computed geometry must agree with it on sign.
        with TELEMETRY_FIXTURE.open(newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 15)
        for row in rows:
            computed = HORMUZ_GATE.signed_distance_nm(
                float(row["latitude"]), float(row["longitude"])
            )
            expected = float(row["signed_gate_distance_nm"])
            self.assertEqual(
                copysign(1.0, computed),
                copysign(1.0, expected),
                msg=(
                    f"mmsi {row['mmsi']} at {row['observed_at']}: computed "
                    f"{computed:.3f} nm disagrees on sign with oracle {expected}"
                ),
            )


if __name__ == "__main__":
    unittest.main()
