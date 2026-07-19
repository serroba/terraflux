import json
from pathlib import Path
from time import perf_counter

import duckdb
from duckdb.sqltypes import DOUBLE

from gate import HORMUZ_GATE

EXPERIMENT_DIR = Path(__file__).resolve().parent
TELEMETRY_FIXTURE = EXPERIMENT_DIR / "fixtures" / "telemetry.csv"
DATASET_DIR = EXPERIMENT_DIR / "data" / "crossings"
QUERY_DATE = "2026-07-17"


def main() -> None:
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    with duckdb.connect() as connection:
        # Derive the signed gate distance from raw coordinates in code, rather than
        # reading it from the fixture. The fixture's own signed_gate_distance_nm
        # column is now only a reference oracle (see test_gate.py).
        connection.create_function(
            "gate_distance_nm",
            lambda lat, lon: HORMUZ_GATE.signed_distance_nm(lat, lon),
            [DOUBLE, DOUBLE],
            DOUBLE,
        )

        connection.execute(
            f"""
            CREATE TABLE crossing_events AS
            WITH observations AS (
                SELECT
                    * EXCLUDE (signed_gate_distance_nm),
                    gate_distance_nm(latitude, longitude) AS signed_gate_distance_nm
                FROM read_csv(
                    '{TELEMETRY_FIXTURE.as_posix()}',
                    header = true,
                    timestampformat = '%Y-%m-%dT%H:%M:%SZ'
                )
            ),
            ordered_telemetry AS (
                SELECT
                    *,
                    lag(signed_gate_distance_nm) OVER (
                        PARTITION BY mmsi ORDER BY observed_at
                    ) AS previous_gate_distance_nm
                FROM observations
            )
            SELECT
                observed_at AS timestamp,
                CAST(observed_at AS DATE) AS event_date,
                mmsi,
                CASE
                    WHEN signed_gate_distance_nm > 0 THEN 'outbound'
                    ELSE 'inbound'
                END AS direction,
                vessel_class,
                capacity_dwt
            FROM ordered_telemetry
            WHERE previous_gate_distance_nm IS NOT NULL
              AND signed_gate_distance_nm != 0
              AND previous_gate_distance_nm != 0
              AND sign(signed_gate_distance_nm) != sign(previous_gate_distance_nm)
            """
        )

        connection.execute(
            f"""
            COPY crossing_events
            TO '{DATASET_DIR.as_posix()}' (
                FORMAT PARQUET,
                PARTITION_BY (event_date),
                OVERWRITE_OR_IGNORE
            )
            """
        )

        query_started = perf_counter()
        row = connection.execute(
            f"""
            SELECT
                CAST(event_date AS VARCHAR) AS event_date,
                count(*) AS observed_crossings,
                count(*) FILTER (WHERE direction = 'inbound') AS inbound_crossings,
                count(*) FILTER (WHERE direction = 'outbound') AS outbound_crossings,
                sum(capacity_dwt) AS observed_capacity_dwt
            FROM read_parquet(
                '{DATASET_DIR.as_posix()}/**/*.parquet',
                hive_partitioning = true
            )
            WHERE event_date = DATE '{QUERY_DATE}'
            GROUP BY event_date
            """
        ).fetchone()
        query_elapsed_ms = round((perf_counter() - query_started) * 1000, 3)

    if row is None:
        raise RuntimeError(f"No crossing events found for {QUERY_DATE}")

    keys = (
        "event_date",
        "observed_crossings",
        "inbound_crossings",
        "outbound_crossings",
        "observed_capacity_dwt",
    )
    result = dict(zip(keys, row, strict=True))
    query_partition = DATASET_DIR / f"event_date={QUERY_DATE}"
    result["query_elapsed_ms"] = query_elapsed_ms
    result["partition_bytes"] = sum(
        path.stat().st_size for path in query_partition.glob("*.parquet")
    )
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
