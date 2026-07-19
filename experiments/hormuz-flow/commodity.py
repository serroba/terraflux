"""Commodity classification and energy content for maritime flow gates.

Maps a vessel class to the primary commodity it carries and that commodity's
energy content, so laden capacity can be expressed as an energy flux.

Energy content uses net calorific values (NCV) from the 2006 IPCC Guidelines for
National Greenhouse Gas Inventories, Volume 2 (Energy), Chapter 1, Table 1.2, in
GJ per tonne (the table is in TJ/Gg, which is numerically equal to GJ/tonne). NCV
excludes the latent heat of the water vapour formed in combustion, i.e. the energy
realistically available.

Two deliberate approximations, consistent with the project's "capacity is not cargo
carried" principle:

- `capacity_dwt` is deadweight tonnage, a capacity ceiling rather than actual cargo
  mass (DWT also covers bunkers, stores, and ballast water), so the energy figure is
  a capacity-based upper estimate, not measured throughput.
- For LNG carriers, deadweight tonnage is an especially rough proxy: LNG capacity is
  volumetric (m^3) and LNG is light (~0.45 t/m^3), so DWT overstates the carried
  mass. Refining this is left to a later slice.

Only liquid and gas fossil classes are modelled for now. Dry-bulk classes (coal,
iron ore) are ambiguous from vessel class alone and are deferred.
"""

from __future__ import annotations

UNKNOWN_COMMODITY = "unknown"

# Net calorific value in GJ per tonne. Source: 2006 IPCC Guidelines for National
# Greenhouse Gas Inventories, Vol. 2 (Energy), Ch. 1, Table 1.2.
_NET_CALORIFIC_GJ_PER_T: dict[str, float] = {
    "crude_oil": 42.3,
    "refined_products": 44.3,  # represented by motor gasoline
    "lng": 48.0,  # natural gas
}

_VESSEL_CLASS_TO_COMMODITY: dict[str, str] = {
    "crude_tanker": "crude_oil",
    "product_tanker": "refined_products",
    "lng_carrier": "lng",
}


def commodity_for(vessel_class: str) -> str:
    """Primary commodity carried by a vessel class, or ``unknown`` if unmodelled."""
    return _VESSEL_CLASS_TO_COMMODITY.get(vessel_class, UNKNOWN_COMMODITY)


def net_calorific_gj_per_t(vessel_class: str) -> float:
    """Net calorific value (GJ/tonne) for a vessel class's commodity, else 0.0."""
    return _NET_CALORIFIC_GJ_PER_T.get(commodity_for(vessel_class), 0.0)


def energy_content_gj(vessel_class: str, capacity_dwt: float) -> float:
    """Capacity-based energy content in GJ for a vessel of this class.

    A capacity-based upper estimate, not measured cargo energy. Zero for classes
    we do not model (non-fossil, or dry bulk).
    """
    return capacity_dwt * net_calorific_gj_per_t(vessel_class)
