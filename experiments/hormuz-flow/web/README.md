# Browser flux (DuckDB-WASM spike)

A spike testing one architectural idea: **the read path can run entirely in the
browser.** Instead of a query server, a static page loads DuckDB-WASM, reads the
aggregate Parquet the Python pipeline produced, and computes the same per-gate flux
client-side.

This mirrors a plausible production shape for Terraflux:

```
server / offline (heavy)                         browser (no query backend)
derive crossings -> publish aggregate  ────────► DuckDB-WASM reads aggregate
Parquet to object storage                        Parquet over HTTP, runs the SQL
```

Only **aggregate** Parquet is ever shipped to the client — never raw telemetry — which
keeps the product's "aggregates only" boundary intact.

## Run it

From the experiment directory (`experiments/hormuz-flow`):

```sh
uv run generate_and_query.py     # derive crossings -> data/crossings/
uv run export_web_parquet.py     # flatten them into web/crossings.parquet
python3 -m http.server 8777 -d web
```

Then open <http://localhost:8777/>. The page prints the per-gate aggregate; it matches
the Python pipeline exactly (Hormuz ≈45.2 PJ, Malacca ≈32.2 PJ for 2026-07-17).

`web/crossings.parquet` is generated and Git-ignored.

## Notes

- **DuckDB-WASM is pinned to 1.31.0** and the baseline `mvp` wasm is loaded explicitly
  rather than via `selectBundle()`. Auto-selection can pick the exception-handling or
  threaded build, which needs cross-origin isolation (COOP/COEP headers) that a plain
  static host does not send. 1.31.0 also bundles the Parquet reader into core, so no
  extension download from `extensions.duckdb.org` is needed.
- Loading the DuckDB-WASM bundle requires network access to the jsDelivr CDN.
- This is a spike, not a build: no bundler, no framework. A real read/viz layer would
  pin dependencies through a build step and likely add a map.
- The same SQL runs here and in `generate_and_query.py`, so the browser and server
  cannot silently disagree.
