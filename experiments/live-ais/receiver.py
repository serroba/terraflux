"""Collect live AIS observations from Digitraffic (Gulf of Finland).

Subscribes to Fintraffic's open marine AIS feed over MQTT-over-WebSockets, keeps
only vessel positions inside a Gulf-of-Finland bounding box, and writes them as a
telemetry CSV in the shape the flow pipeline expects
(observed_at, mmsi, latitude, longitude, ...).

Source: Digitraffic marine AIS, wss://meri.digitraffic.fi:443/mqtt, topic
`vessels-v2/+/location`. Licensed CC BY 4.0 (attribution: Fintraffic / Digitraffic).
Real-time positions only; no raw data is republished.

This is a local, minimal-infra first step. AIS position reports carry no deadweight
tonnage, so commodity/energy estimation (from ship type and dimensions) is a later
slice; this receiver just proves the real, licensing-clean pipe end to end.

Run: `uv run receiver.py --seconds 60 --out telemetry_live.csv`
"""

from __future__ import annotations

import argparse
import csv
import json
import ssl
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import paho.mqtt.client as mqtt

BROKER_HOST = "meri.digitraffic.fi"
BROKER_PORT = 443
WS_PATH = "/mqtt"
LOCATION_TOPIC = "vessels-v2/+/location"

# Gulf of Finland bounding box (lat_min, lat_max, lon_min, lon_max): the crude-oil
# corridor from the gulf entrance east toward Primorsk / Ust-Luga.
GOF_BBOX = (59.2, 60.5, 22.0, 28.5)


@dataclass
class Observation:
    observed_at: str
    mmsi: int
    latitude: float
    longitude: float
    sog: float | None
    cog: float | None


def _in_bbox(lat: float, lon: float) -> bool:
    lat_min, lat_max, lon_min, lon_max = GOF_BBOX
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def _parse_location(topic: str, payload: bytes) -> Observation | None:
    """Extract an Observation from a vessels-v2/<mmsi>/location message."""
    try:
        mmsi = int(topic.split("/")[1])
        msg = json.loads(payload)
    except (ValueError, IndexError, json.JSONDecodeError):
        return None

    # Digitraffic vessels-v2 location: lat/lon at top level, with a GeoJSON
    # geometry as a fallback. Be defensive about either shape.
    lat = msg.get("lat")
    lon = msg.get("lon")
    if lat is None or lon is None:
        coords = (msg.get("geometry") or {}).get("coordinates")
        if isinstance(coords, list) and len(coords) == 2:
            lon, lat = coords[0], coords[1]
    if lat is None or lon is None:
        return None

    ts = msg.get("timestampExternal") or msg.get("time")
    if isinstance(ts, (int, float)):
        # `time` is epoch seconds (10 digits); some fields are milliseconds (13).
        epoch_s = ts / 1000 if ts > 1e12 else ts
        observed_at = datetime.fromtimestamp(epoch_s, tz=UTC).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    else:
        observed_at = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    return Observation(
        observed_at=observed_at,
        mmsi=mmsi,
        latitude=float(lat),
        longitude=float(lon),
        sog=msg.get("sog"),
        cog=msg.get("cog"),
    )


def collect(seconds: int) -> list[Observation]:
    observations: list[Observation] = []
    raw_sample_printed = False

    def on_connect(client: mqtt.Client, *_: object) -> None:
        client.subscribe(LOCATION_TOPIC)
        print(f"connected; subscribed to {LOCATION_TOPIC}", file=sys.stderr)

    def on_message(_c: object, _u: object, message: mqtt.MQTTMessage) -> None:
        nonlocal raw_sample_printed
        if not raw_sample_printed:
            sample = message.payload[:240]
            print(f"raw sample [{message.topic}]: {sample!r}", file=sys.stderr)
            raw_sample_printed = True
        obs = _parse_location(message.topic, message.payload)
        if obs is not None and _in_bbox(obs.latitude, obs.longitude):
            observations.append(obs)

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        transport="websockets",
    )
    client.ws_set_options(path=WS_PATH)
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()
    time.sleep(seconds)
    client.loop_stop()
    client.disconnect()
    return observations


def write_csv(observations: list[Observation], path: str) -> None:
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["observed_at", "mmsi", "latitude", "longitude", "sog", "cog"])
        for o in observations:
            writer.writerow(
                [o.observed_at, o.mmsi, o.latitude, o.longitude, o.sog, o.cog]
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--out", default="telemetry_live.csv")
    args = parser.parse_args()

    started = time.perf_counter()
    observations = collect(args.seconds)
    elapsed = time.perf_counter() - started

    write_csv(observations, args.out)
    vessels = {o.mmsi for o in observations}
    print(
        json.dumps(
            {
                "seconds": round(elapsed, 1),
                "observations_in_bbox": len(observations),
                "distinct_vessels": len(vessels),
                "out": args.out,
            },
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
