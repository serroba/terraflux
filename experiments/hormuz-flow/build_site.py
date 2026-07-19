"""Build the published site data for the docs/ folder (GitHub Pages).

Run ``generate_and_query.py`` first to populate ``data/crossings/``. This reads that
partitioned dataset and writes the aggregate artifacts the browser pages query:
``docs/crossings.parquet`` and ``docs/gates.json``.

The HTML in ``docs/`` is source-controlled; only these aggregate data files are
generated. GitHub Pages serves ``docs/`` from ``main``, so the generated files are
committed — publishing aggregate Parquet is exactly the product model. The derivation
still happens here, server-side; only aggregates reach the client.
"""

import json
from pathlib import Path

import duckdb

from gate import GATES

EXPERIMENT_DIR = Path(__file__).resolve().parent
DATASET_DIR = EXPERIMENT_DIR / "data" / "crossings"
REPO_ROOT = EXPERIMENT_DIR.parent.parent
DOCS_DIR = REPO_ROOT / "docs"
PARQUET_OUTPUT = DOCS_DIR / "crossings.parquet"
GATES_OUTPUT = DOCS_DIR / "gates.json"


def gates_metadata() -> list[dict[str, object]]:
    """Gate locations and outbound flow bearing, as the map plots them."""
    gates: list[dict[str, object]] = []
    for gate in GATES.values():
        lat, lon = gate.midpoint()
        gates.append(
            {
                "name": gate.name,
                "lat": lat,
                "lon": lon,
                "laden_direction": gate.laden_direction,
                "outbound_bearing_deg": round(gate.outbound_bearing_deg(), 1),
            }
        )
    return gates


def gates_json() -> str:
    """Serialized gate metadata, exactly as written to docs/gates.json."""
    return json.dumps(gates_metadata(), indent=2) + "\n"


def write_gates_json() -> None:
    """Emit gate locations and outbound flow bearing for the map to plot."""
    GATES_OUTPUT.write_text(gates_json())


def main() -> None:
    if not any(DATASET_DIR.glob("**/*.parquet")):
        raise SystemExit(
            "No Parquet found under data/crossings/. Run generate_and_query.py first."
        )

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    with duckdb.connect() as connection:
        connection.execute(
            f"""
            COPY (
                SELECT * FROM read_parquet(
                    '{DATASET_DIR.as_posix()}/**/*.parquet',
                    hive_partitioning = true
                )
            ) TO '{PARQUET_OUTPUT.as_posix()}' (FORMAT PARQUET)
            """
        )
    write_gates_json()
    print(f"wrote {PARQUET_OUTPUT} and {GATES_OUTPUT}")


if __name__ == "__main__":
    main()
