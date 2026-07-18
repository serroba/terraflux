# Hormuz flow experiment

This experiment tests one architectural idea: keep durable analytical data as
partitioned Parquet and use an ephemeral DuckDB process to calculate aggregates.

It starts with a checked-in synthetic telemetry fixture. Each observation includes a
signed distance from a predefined gate: negative on the inbound side and positive on
the outbound side. A vessel crossing is derived when consecutive observations for its
MMSI change sign.

Computing that signed distance from raw AIS coordinates and a geographic gate is a
separate spatial experiment. Keeping it explicit here gives us a clean boundary without
pretending the geometric problem is already solved.

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
uv run python -m unittest discover -p "test_*.py"
```

The same verification runs for every pull request and every push to `main`.
