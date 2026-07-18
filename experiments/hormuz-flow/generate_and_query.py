import json
from pathlib import Path
from time import perf_counter

import duckdb


EXPERIMENT_DIR = Path(__file__).resolve().parent
DATASET_DIR = EXPERIMENT_DIR / "data" / "crossings"
QUERY_DATE = "2026-07-17"


def main() -> None:
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    with duckdb.connect() as connection:
        connection.execute(
            """
            CREATE TABLE crossing_events AS
            SELECT
                timestamp,
                CAST(timestamp AS DATE) AS event_date,
                mmsi,
                direction,
                vessel_class,
                capacity_dwt
            FROM (VALUES
                (TIMESTAMP '2026-07-16 23:48:00', 100000001, 'outbound', 'crude_tanker',   300000),
                (TIMESTAMP '2026-07-17 01:12:00', 100000002, 'outbound', 'crude_tanker',   320000),
                (TIMESTAMP '2026-07-17 04:35:00', 100000003, 'inbound',  'product_tanker', 115000),
                (TIMESTAMP '2026-07-17 09:07:00', 100000004, 'outbound', 'lng_carrier',    180000),
                (TIMESTAMP '2026-07-17 14:51:00', 100000005, 'inbound',  'crude_tanker',   305000),
                (TIMESTAMP '2026-07-17 20:16:00', 100000006, 'outbound', 'product_tanker', 520000),
                (TIMESTAMP '2026-07-18 02:23:00', 100000007, 'inbound',  'crude_tanker',   310000)
            ) AS events(timestamp, mmsi, direction, vessel_class, capacity_dwt)
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

    keys = (
        "event_date",
        "observed_crossings",
        "inbound_crossings",
        "outbound_crossings",
        "observed_capacity_dwt",
    )
    result = dict(zip(keys, row))
    query_partition = DATASET_DIR / f"event_date={QUERY_DATE}"
    result["query_elapsed_ms"] = query_elapsed_ms
    result["partition_bytes"] = sum(
        path.stat().st_size for path in query_partition.glob("*.parquet")
    )
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
