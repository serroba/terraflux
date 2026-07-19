import json
import shutil
from pathlib import Path
from time import perf_counter

import duckdb
from duckdb.sqltypes import BIGINT, DOUBLE, VARCHAR

from commodity import commodity_for, energy_content_gj
from gate import GATES, Gate

EXPERIMENT_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = EXPERIMENT_DIR / "fixtures"
DATASET_DIR = EXPERIMENT_DIR / "data" / "crossings"
QUERY_DATE = "2026-07-17"

# Fields of a per-gate daily aggregate row, in query column order (after the gate
# name, which is used as the result key).
AGGREGATE_KEYS = (
    "event_date",
    "observed_crossings",
    "inbound_crossings",
    "outbound_crossings",
    "observed_capacity_dwt",
    "laden_crossings",
    "laden_capacity_dwt",
    "observed_energy_gj",
)


def write_gate_crossings(gate: Gate) -> None:
    """Derive crossing events for one gate from its fixture and write Parquet.

    Events are partitioned by gate and event_date so every gate contributes to a
    single date-partitioned dataset the daily query reads back at once.
    """
    fixture = FIXTURES_DIR / f"{gate.name}.csv"
    with duckdb.connect() as connection:
        # Signed gate distance is gate-specific, so bind the UDF to this gate.
        connection.create_function(
            "gate_distance_nm",
            lambda lat, lon: gate.signed_distance_nm(lat, lon),
            [DOUBLE, DOUBLE],
            DOUBLE,
        )
        connection.create_function("commodity_for", commodity_for, [VARCHAR], VARCHAR)
        connection.create_function(
            "energy_content_gj", energy_content_gj, [VARCHAR, BIGINT], DOUBLE
        )

        connection.execute(
            f"""
            CREATE TABLE crossing_events AS
            WITH observations AS (
                SELECT
                    * EXCLUDE (signed_gate_distance_nm),
                    gate_distance_nm(latitude, longitude) AS signed_gate_distance_nm
                FROM read_csv(
                    '{fixture.as_posix()}',
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
            ),
            crossings AS (
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
            )
            SELECT
                '{gate.name}' AS gate,
                *,
                direction = '{gate.laden_direction}' AS laden,
                'direction' AS laden_method,
                commodity_for(vessel_class) AS commodity,
                energy_content_gj(vessel_class, capacity_dwt) AS energy_gj
            FROM crossings
            """
        )

        connection.execute(
            f"""
            COPY crossing_events
            TO '{DATASET_DIR.as_posix()}' (
                FORMAT PARQUET,
                PARTITION_BY (gate, event_date),
                OVERWRITE_OR_IGNORE
            )
            """
        )


def query_daily_flux() -> list[tuple]:
    """Aggregate one day of flux per gate directly from the Parquet dataset."""
    with duckdb.connect() as connection:
        return connection.execute(
            f"""
            SELECT
                gate,
                CAST(event_date AS VARCHAR) AS event_date,
                count(*) AS observed_crossings,
                count(*) FILTER (WHERE direction = 'inbound') AS inbound_crossings,
                count(*) FILTER (WHERE direction = 'outbound') AS outbound_crossings,
                sum(capacity_dwt) AS observed_capacity_dwt,
                count(*) FILTER (WHERE laden) AS laden_crossings,
                sum(capacity_dwt) FILTER (WHERE laden) AS laden_capacity_dwt,
                CAST(round(sum(energy_gj) FILTER (WHERE laden)) AS BIGINT)
                    AS observed_energy_gj
            FROM read_parquet(
                '{DATASET_DIR.as_posix()}/**/*.parquet',
                hive_partitioning = true
            )
            WHERE event_date = DATE '{QUERY_DATE}'
            GROUP BY gate, event_date
            ORDER BY gate
            """
        ).fetchall()


def main() -> None:
    # Rebuild the dataset from scratch so results never depend on stale partitions
    # from an earlier run (data/ is disposable and Git-ignored).
    shutil.rmtree(DATASET_DIR, ignore_errors=True)
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    for gate in GATES.values():
        write_gate_crossings(gate)

    query_started = perf_counter()
    rows = query_daily_flux()
    query_elapsed_ms = round((perf_counter() - query_started) * 1000, 3)

    if not rows:
        raise RuntimeError(f"No crossing events found for {QUERY_DATE}")

    gates_result = {}
    for row in rows:
        gate_name = row[0]
        aggregate = dict(zip(AGGREGATE_KEYS, row[1:], strict=True))
        partition = DATASET_DIR / f"gate={gate_name}" / f"event_date={QUERY_DATE}"
        aggregate["partition_bytes"] = sum(
            path.stat().st_size for path in partition.glob("*.parquet")
        )
        gates_result[gate_name] = aggregate

    result = {
        "query_date": QUERY_DATE,
        "query_elapsed_ms": query_elapsed_ms,
        "gates": gates_result,
    }
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
