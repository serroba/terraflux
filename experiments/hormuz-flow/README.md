# Hormuz flow experiment

This experiment tests one architectural idea: keep durable analytical data as
partitioned Parquet and use an ephemeral DuckDB process to calculate aggregates.

It starts with a checked-in synthetic telemetry fixture. Each observation carries a
latitude and longitude. The signed distance from a predefined gate is computed in code
(`gate.py`): negative on the inbound side, positive on the outbound side. A vessel
crossing is derived when consecutive observations for its MMSI change sign.

The gate is defined as a line segment between two coordinates, and the signed distance
is a planar (flat-earth) perpendicular distance in nautical miles. Over the few miles
that span the strait this is accurate enough to decide which side a point is on.
Geodesic distance, gate buffers, noisy trajectories, interpolation, out-of-order
messages, and lingering vessels are deliberately left to a later spatial experiment.

The fixture still carries a hand-authored `signed_gate_distance_nm` column. It is no
longer the source of truth; it records the *intended* side for each observation and is
used only as a reference oracle in `test_gate.py`, which asserts the computed geometry
agrees with it on sign for every row.

## Run

From this directory:

```sh
uv run generate_and_query.py
```

The script reads `fixtures/telemetry.csv`, derives crossing events, writes them to
`data/crossings/event_date=.../*.parquet`, queries one day directly from those files,
and prints the aggregate plus basic execution diagnostics as JSON.

The aggregate portion of the output is deterministic:

```json
{"event_date":"2026-07-17","observed_crossings":5,"inbound_crossings":2,"outbound_crossings":3,"observed_capacity_dwt":1440000}
```

`query_elapsed_ms` and `partition_bytes` provide an initial local baseline. Elapsed time
will vary between runs.

The generated `data/` directory is disposable and ignored by Git.

## Verify

```sh
uv run ruff check .          # lint
uv run ruff format --check . # formatting
uv run mypy .                # type check
uv run python -m unittest discover -p "test_*.py"  # tests
```

The tests run both the end-to-end determinism test (`test_generate_and_query.py`) and
the gate-geometry tests (`test_gate.py`). All four checks above run for every pull
request and every push to `main`.
