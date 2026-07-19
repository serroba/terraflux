# Terraflux site (GitHub Pages)

This folder is the published Terraflux site. GitHub Pages serves it from `main`
(Settings → Pages → Deploy from a branch → `main` / `/docs`), so it is live at:

**<https://serroba.github.io/terraflux/>**

The site runs the read path **entirely in the browser**: static pages load DuckDB-WASM,
read the aggregate Parquet, and compute per-gate flux client-side — no query server.

- `index.html` — the **3D flux globe**: a night-Earth globe (globe.gl / Three.js) with a
  bar rising from each gate (height ∝ laden energy) and an animated arc tracing the laden
  flow. Drag to rotate; auto-rotates.
- `flat.html` — a 2D world **flux map** (d3-geo): each gate a bubble sized by laden
  energy with a flow arrow. A lighter-weight alternative view.
- `table.html` — the plain per-gate aggregate (the data proof). Matches the Python
  pipeline exactly (Hormuz ≈45.2 PJ, Malacca ≈32.2 PJ for 2026-07-17).
- `crossings.parquet`, `gates.json` — the generated aggregate artifacts the pages query.
- `.nojekyll` — serve files as-is (no Jekyll processing).

Only **aggregate** data is ever shipped to the client — never raw telemetry — which is
also the product's licensing-clean position.

## Rebuilding the data

The HTML is source-controlled; only the aggregate data files are generated. From the
experiment directory (`experiments/hormuz-flow`):

```sh
uv run generate_and_query.py   # derive crossings -> data/crossings/
uv run build_site.py           # write docs/crossings.parquet and docs/gates.json
```

Because Pages deploys from the branch, the generated `crossings.parquet` and
`gates.json` are committed here — publishing aggregate Parquet is exactly the product
model. Commit them after rebuilding.

## Preview locally

```sh
python3 -m http.server 8778 -d docs   # from the repo root
```

Then open <http://localhost:8778/>.

## Notes

- **DuckDB-WASM is pinned to 1.31.0** and the baseline `mvp` wasm is loaded explicitly
  rather than via `selectBundle()`: auto-selection can pick the exception-handling or
  threaded build, which needs cross-origin isolation (COOP/COEP) a plain static host
  (including Pages) does not provide. 1.31.0 also bundles the Parquet reader, so no
  download from `extensions.duckdb.org` is needed.
- The pages load DuckDB-WASM, globe.gl/Three.js, d3, and Earth textures from the jsDelivr
  and unpkg CDNs, so a browser with network access (and WebGL, for the globe) is required.
- No bundler or framework — plain static files. A future build step could pin and
  vendor these dependencies.
