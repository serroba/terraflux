import unittest

from receiver import _in_bbox, _parse_location

# A real vessels-v2/<mmsi>/location payload captured from the live feed.
SAMPLE_TOPIC = "vessels-v2/354290000/location"
SAMPLE_PAYLOAD = (
    b'{"cog":192.3,"heading":197,"lat":60.255225,"lon":28.79921,'
    b'"navStat":0,"posAcc":true,"raim":false,"rot":0,"sog":6.2,"time":1784458597}'
)


class ParseLocationTest(unittest.TestCase):
    def test_parses_a_real_location_message(self) -> None:
        obs = _parse_location(SAMPLE_TOPIC, SAMPLE_PAYLOAD)
        assert obs is not None
        self.assertEqual(obs.mmsi, 354290000)
        self.assertAlmostEqual(obs.latitude, 60.255225)
        self.assertAlmostEqual(obs.longitude, 28.79921)
        self.assertEqual(obs.sog, 6.2)
        self.assertEqual(obs.cog, 192.3)

    def test_epoch_seconds_timestamp_is_not_misread_as_millis(self) -> None:
        obs = _parse_location(SAMPLE_TOPIC, SAMPLE_PAYLOAD)
        assert obs is not None
        # time=1784458597 is epoch seconds (year 2026), not milliseconds (1970).
        self.assertTrue(obs.observed_at.startswith("2026-"), obs.observed_at)

    def test_bad_payload_returns_none(self) -> None:
        self.assertIsNone(_parse_location(SAMPLE_TOPIC, b"not json"))
        self.assertIsNone(_parse_location("bad/topic", SAMPLE_PAYLOAD))
        self.assertIsNone(_parse_location(SAMPLE_TOPIC, b'{"sog":1.0}'))


class BoundingBoxTest(unittest.TestCase):
    def test_gulf_of_finland_point_is_inside(self) -> None:
        self.assertTrue(_in_bbox(59.9, 25.0))

    def test_points_outside_are_rejected(self) -> None:
        self.assertFalse(_in_bbox(26.5, 56.2))  # Strait of Hormuz
        self.assertFalse(_in_bbox(59.9, 10.0))  # west of the gulf


if __name__ == "__main__":
    unittest.main()
