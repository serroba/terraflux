# Hormuz flow experiment

This experiment tests one architectural idea: keep durable analytical data as
partitioned Parquet and use an ephemeral DuckDB process to calculate aggregates.

It deliberately starts with synthetic, already-detected crossing events. Identifying a
crossing from raw AIS positions is a separate experiment.

## Run

From this directory:

```sh
uv run generate_and_query.py
```

The script writes deterministic events to `data/crossings/event_date=.../*.parquet`,
queries one day directly from those files, and prints the aggregate plus basic execution
diagnostics as JSON.

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
