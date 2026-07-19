"""Flatten the derived crossings into a single Parquet for the browser spike.

Run ``generate_and_query.py`` first to populate ``data/crossings/``. This reads that
partitioned dataset and writes ``web/crossings.parquet`` — the file the DuckDB-WASM
page (``web/index.html``) queries directly in the browser.

Kept separate from the main pipeline so the browser experiment stays easy to remove:
it proves the read path (aggregate Parquet queried client-side), and the derivation
still happens here, server-side.
"""

from pathlib import Path

import duckdb

EXPERIMENT_DIR = Path(__file__).resolve().parent
DATASET_DIR = EXPERIMENT_DIR / "data" / "crossings"
WEB_DIR = EXPERIMENT_DIR / "web"
OUTPUT = WEB_DIR / "crossings.parquet"


def main() -> None:
    if not any(DATASET_DIR.glob("**/*.parquet")):
        raise SystemExit(
            "No Parquet found under data/crossings/. Run generate_and_query.py first."
        )

    WEB_DIR.mkdir(parents=True, exist_ok=True)
    with duckdb.connect() as connection:
        connection.execute(
            f"""
            COPY (
                SELECT * FROM read_parquet(
                    '{DATASET_DIR.as_posix()}/**/*.parquet',
                    hive_partitioning = true
                )
            ) TO '{OUTPUT.as_posix()}' (FORMAT PARQUET)
            """
        )
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
