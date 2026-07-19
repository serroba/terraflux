import unittest

from commodity import (
    UNKNOWN_COMMODITY,
    commodity_for,
    energy_content_gj,
    net_calorific_gj_per_t,
)


class CommodityTest(unittest.TestCase):
    def test_vessel_class_maps_to_commodity(self) -> None:
        self.assertEqual(commodity_for("crude_tanker"), "crude_oil")
        self.assertEqual(commodity_for("product_tanker"), "refined_products")
        self.assertEqual(commodity_for("lng_carrier"), "lng")

    def test_unmodelled_class_is_unknown(self) -> None:
        self.assertEqual(commodity_for("bulk_carrier"), UNKNOWN_COMMODITY)
        self.assertEqual(net_calorific_gj_per_t("bulk_carrier"), 0.0)
        self.assertEqual(energy_content_gj("bulk_carrier", 200_000), 0.0)

    def test_net_calorific_values_match_ipcc_defaults(self) -> None:
        # 2006 IPCC Guidelines, Vol. 2, Ch. 1, Table 1.2 (GJ/tonne).
        self.assertEqual(net_calorific_gj_per_t("crude_tanker"), 42.3)
        self.assertEqual(net_calorific_gj_per_t("product_tanker"), 44.3)
        self.assertEqual(net_calorific_gj_per_t("lng_carrier"), 48.0)

    def test_energy_content_is_capacity_times_ncv(self) -> None:
        self.assertAlmostEqual(
            energy_content_gj("crude_tanker", 320_000), 320_000 * 42.3
        )


if __name__ == "__main__":
    unittest.main()
