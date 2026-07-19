"""Planar geometry for a maritime flow gate.

A gate is a line segment between two geographic endpoints. The signed distance of
an observation is its perpendicular distance, in nautical miles, from that line:
positive on the outbound side and negative on the inbound side. A vessel crosses
the gate when that sign changes between consecutive observations.

This implementation is intentionally *planar* (flat-earth). Over the few nautical
miles that span a strait, projecting latitude/longitude onto a locally Cartesian
grid is accurate enough to decide which side of a line a point is on. Geodesic
distance, gate buffers, noisy trajectories, interpolation, and lingering vessels
are deliberately out of scope here and left to a later spatial experiment (see the
project README).
"""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, degrees, hypot, radians

# One degree of latitude is ~60 nautical miles anywhere on the globe. One degree
# of longitude shrinks by cos(latitude) as you move away from the equator.
NM_PER_DEGREE_LATITUDE = 60.0


@dataclass(frozen=True)
class Gate:
    """A flow gate defined by two geographic endpoints (start -> end).

    ``laden_direction`` records which crossing direction is expected to be laden
    (cargo-carrying) at this gate. At an exporting chokepoint like Hormuz, vessels
    leave loaded and return in ballast, so the outbound direction is laden. This is
    a coarse per-gate proxy; a later slice can refine laden state from reported
    draught.
    """

    name: str
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    laden_direction: str

    def is_laden(self, direction: str) -> bool:
        """Whether a crossing in ``direction`` is treated as laden at this gate."""
        return direction == self.laden_direction

    def midpoint(self) -> tuple[float, float]:
        """Midpoint of the gate line as ``(lat, lon)`` — where to plot the gate."""
        return (
            (self.start_lat + self.end_lat) / 2.0,
            (self.start_lon + self.end_lon) / 2.0,
        )

    def outbound_bearing_deg(self) -> float:
        """Compass bearing (0=N, 90=E) of the outbound side of the gate.

        Laden vessels flow toward the positive ("outbound") side, which lies to the
        left of the start->end gate vector. This returns the bearing of that flow so
        a map can draw a direction arrow.
        """
        lat0 = (self.start_lat + self.end_lat) / 2.0
        lon_scale = NM_PER_DEGREE_LATITUDE * cos(radians(lat0))
        gate_east = (self.end_lon - self.start_lon) * lon_scale
        gate_north = (self.end_lat - self.start_lat) * NM_PER_DEGREE_LATITUDE
        # Left normal of (east, north) is (-north, east); it points to the positive
        # side (see signed_distance_nm). Bearing is measured clockwise from north.
        outbound_east, outbound_north = -gate_north, gate_east
        return degrees(atan2(outbound_east, outbound_north)) % 360.0

    def signed_distance_nm(self, lat: float, lon: float) -> float:
        """Signed perpendicular distance from the gate line, in nautical miles.

        Positive on the outbound side, negative on the inbound side, and ~0 on the
        line itself. Uses an equirectangular projection centred on the gate, so
        longitude degrees are scaled by the cosine of the local latitude.

        Sign is the sign of the 2D cross product of the gate vector (start -> end)
        with the vector from the gate start to the point. Whether a given side is
        "outbound" therefore depends on the endpoint order; the endpoints below are
        ordered so that the Gulf-of-Oman side is positive.
        """
        lat0 = (self.start_lat + self.end_lat) / 2.0
        lon_scale = NM_PER_DEGREE_LATITUDE * cos(radians(lat0))

        # Local planar coordinates (nm) relative to the gate start. The choice of
        # origin cancels out in the cross product, so start-as-origin is fine.
        gate_x = (self.end_lon - self.start_lon) * lon_scale
        gate_y = (self.end_lat - self.start_lat) * NM_PER_DEGREE_LATITUDE
        point_x = (lon - self.start_lon) * lon_scale
        point_y = (lat - self.start_lat) * NM_PER_DEGREE_LATITUDE

        gate_length = hypot(gate_x, gate_y)
        if gate_length == 0.0:
            raise ValueError(f"Gate {self.name!r} has zero length")

        cross = gate_x * point_y - gate_y * point_x
        return cross / gate_length


# Illustrative synthetic gate for the Strait of Hormuz. These coordinates are a
# short line across the strait chosen for this experiment; they are not a surveyed
# traffic boundary. The endpoint order makes the Gulf-of-Oman (outbound) side
# positive and the Persian-Gulf (inbound) side negative.
HORMUZ_GATE = Gate(
    name="strait_of_hormuz",
    start_lat=26.60,
    start_lon=56.19,
    end_lat=26.55,
    end_lon=56.25,
    # Hormuz is a crude/LNG export chokepoint: loaded vessels head outbound to the
    # Gulf of Oman; inbound vessels return in ballast.
    laden_direction="outbound",
)

# Illustrative synthetic gate for the Strait of Malacca. As with Hormuz, these are
# chosen coordinates, not a surveyed boundary. Tankers bound for East Asian importers
# transit laden toward the positive ("outbound") side and return in ballast.
MALACCA_GATE = Gate(
    name="strait_of_malacca",
    start_lat=2.60,
    start_lon=101.20,
    end_lat=2.40,
    end_lon=101.45,
    laden_direction="outbound",
)

# Registry of the gates the experiment measures, keyed by gate name. The pipeline
# processes each gate against its own telemetry fixture.
GATES: dict[str, Gate] = {
    HORMUZ_GATE.name: HORMUZ_GATE,
    MALACCA_GATE.name: MALACCA_GATE,
}
