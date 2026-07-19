# Live AIS receiver (Digitraffic, Gulf of Finland)

The first step off synthetic fixtures and onto **real** data. This receiver subscribes
to Fintraffic's open marine AIS feed and lands live vessel positions in the same
telemetry schema the flow pipeline uses.

## Source and licence

- **Digitraffic marine AIS** (Fintraffic), `wss://meri.digitraffic.fi:443/mqtt`, topic
  `vessels-v2/+/location` — MQTT over WebSockets, TLS, no authentication.
- Licensed **CC BY 4.0**. Any published product must attribute
  **"Fintraffic / Digitraffic"** and link the source. This licence permits publishing
  derived and aggregate data commercially — which is why it was chosen over feeds whose
  terms are non-commercial or silent on derived redistribution.
- Coverage is the Baltic / Gulf of Finland (terrestrial). The gulf is a genuine crude-oil
  chokepoint (exports via Primorsk / Ust-Luga), so it is a real first gate — not a global
  feed. Global chokepoints (Hormuz, Malacca) need a separately-licensed source.

## Run

```sh
uv run receiver.py --seconds 60 --out telemetry_live.csv
```

It collects positions inside a Gulf-of-Finland bounding box for the given window and
writes `observed_at, mmsi, latitude, longitude, sog, cog`. Prints a JSON summary
(observations kept, distinct vessels).

## Raw data is never committed

`telemetry_live.csv` and any raw capture are Git-ignored. The product boundary is to
publish **aggregates only**, never raw vessel positions — committing raw AIS would
breach both that boundary and the spirit of the redistribution terms.

## Known gap: capacity / energy

AIS position reports carry **no deadweight tonnage**. The energy model
(`capacity_dwt × net calorific value`) therefore cannot run on raw positions. Estimating
capacity from AIS ship type and dimensions (from `vessels-v2/<mmsi>/metadata`) is a
later slice; this receiver only proves the real, licensing-clean ingestion path.

## Verify

```sh
uv run ruff check .
uv run ruff format --check .
uv run ty check .
uv run python -m unittest discover -p "test_*.py"
```

The tests cover the pure parser and bounding-box filter (no network). Running
`receiver.py` itself needs live network access to the Digitraffic broker.
