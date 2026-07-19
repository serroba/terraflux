# Terraflux

Terraflux is an exploratory observatory for the flows that connect our planet.

This README is the project brief and agent handoff. It records the intent, current
technical hypothesis, completed work, unresolved decisions, and recommended next steps.

## Vision

Terraflux should make large transport systems legible as changing flows rather than as
collections of individual assets.

The initial domain is maritime trade. Ships are observations moving through a network;
ports and regions are nodes; straits, canals, and route segments are flow gates. The
product should answer questions such as:

- How much observed tanker activity passed through the Strait of Hormuz today?
- Is outbound capacity above or below its recent baseline?
- Did flow change, or did telemetry coverage deteriorate?
- How are disruptions changing the wider maritime network?

The long-term visual idea is closer to Windy than MarineTraffic: aggregate intensity,
direction, trends, and eventually animated flow fields rather than individual vessel
dots. Maritime transport is the first layer; electricity, pipelines, aviation, rail, or
other physical networks could fit the same abstraction later.

## Product boundaries

Terraflux is not intended to be a vessel-tracking product. The useful output is an
aggregate, for example:

- observed crossings per day and direction
- crossings by broad vessel class
- estimated carrying capacity such as DWT per day
- normalized flow relative to a moving baseline
- coverage, confidence, and observation-gap indicators

Results must be described as **observed telemetry activity**, not exact total traffic or
commodity volume. AIS can be incomplete, stale, disabled, incorrectly classified, or
biased by receiver coverage. Capacity is not the same as cargo carried.

Publishing aggregates also creates a cleaner licensing and product position than
republishing raw vessel locations. Data retention, commercial use, derived-data rights,
and redistribution rights still need explicit confirmation before using a live provider.

## First objective

Build one small, reproducible end-to-end measurement of daily aggregate maritime flow
through the Strait of Hormuz.

The sequence being explored is:

```text
telemetry observations
        ↓
signed relationship to a geographic gate
        ↓
crossing events
        ↓
date-partitioned Parquet
        ↓
DuckDB aggregate query
        ↓
small JSON result
```

Start with this one gate and one analytical result. Generalization to multiple gates,
global H3 cells, vector fields, APIs, and visualizations should follow evidence from the
working slice rather than precede it.

## Architectural hypothesis

The current hypothesis is deliberately simple:

- Google Cloud Storage becomes the durable analytical record.
- Raw or normalized telemetry is written in reasonably sized time chunks, not one
  object per message.
- Periodic processing produces query-friendly, date-partitioned Parquet.
- DuckDB runs as an embedded, ephemeral query engine inside compute and reads Parquet
  directly from object storage.
- Bounded transformations may fit Cloud Run functions or jobs.
- A persistent AIS WebSocket receiver is more likely to require a Cloud Run service or
  worker-style process than a short-lived function.
- Durable state never depends on a container filesystem or a shared writable `.duckdb`
  file in object storage.

This has only been tested locally. No GCP project or cloud resources have been created.
Cloud Storage, Cloud Run, deployment tooling, IAM, regions, and service boundaries are
hypotheses rather than committed production choices.

Python is currently used only for the local experiment. Go, Python, and TypeScript may
all become appropriate as real components emerge. Do not create a monorepo framework or
choose repository-wide tooling until at least two real components require it.

## What exists today

The [`hormuz-flow`](experiments/hormuz-flow/README.md) experiment is a tested local slice.
It currently:

1. Reads 15 synthetic telemetry observations from
   `experiments/hormuz-flow/fixtures/telemetry.csv`.
2. Computes each observation's signed distance from a coordinate-defined gate in code
   (`experiments/hormuz-flow/gate.py`), using a planar approximation.
3. Orders observations by MMSI and time.
4. Detects a crossing when consecutive signed gate distances change sign.
5. Assigns direction from the side entered.
6. Tags each crossing laden or ballast from the gate's expected laden direction
   (Hormuz is an exporter, so outbound is laden).
7. Classifies each vessel's commodity and converts laden capacity to energy using
   published net calorific values (`experiments/hormuz-flow/commodity.py`).
8. Writes derived events as date-partitioned Parquet under the ignored `data/` folder.
9. Queries one day directly from those Parquet files with DuckDB.
10. Prints a JSON aggregate plus local timing and partition-size diagnostics.

The deterministic result for 2026-07-17 is:

```json
{
  "event_date": "2026-07-17",
  "observed_crossings": 5,
  "inbound_crossings": 2,
  "outbound_crossings": 3,
  "observed_capacity_dwt": 1440000,
  "laden_crossings": 3,
  "laden_capacity_dwt": 1020000,
  "observed_energy_gj": 45212000
}
```

Laden flux counts only the loaded legs (the three outbound crude/LNG transits),
excluding the empty ballast returns. `observed_energy_gj` converts that laden capacity
to energy via per-commodity net calorific values (2006 IPCC Guidelines) — so the day
reads as roughly 45 PJ of fossil energy leaving the Gulf. It is a capacity-based upper
estimate, not measured cargo energy.

The signed gate distance is now computed from each observation's latitude and
longitude against a coordinate-defined gate (`experiments/hormuz-flow/gate.py`), using
a planar approximation. The fixture retains its original `signed_gate_distance_nm`
column only as a reference oracle: a test asserts the computed geometry agrees with it
on sign for every row. Geodesic accuracy, gate buffers, and noisy trajectories remain
intentionally unresolved.

GitHub Actions runs the deterministic experiment test for every pull request and every
push to `main`. The workflow has read-only repository permissions and installs the
locked DuckDB dependency with `uv`.

## Run locally

Requirements: `uv` and a supported Python version.

```sh
cd experiments/hormuz-flow
uv run generate_and_query.py
uv run python -m unittest discover -p "test_*.py"
```

Generated Parquet and virtual-environment files are ignored by Git.

## Completed iterations

- PR #1 established the project brief and local DuckDB/Parquet experiment.
- PR #2 added deterministic tests and the GitHub Actions validation gate.
- PR #3 moved synthetic input into a telemetry fixture and derived crossings from
  consecutive observations.
- A later change replaced the fixture-supplied signed gate distance with a
  coordinate-defined gate and an in-code planar geometry calculation, keeping the
  five-crossing daily result and adding direct geometry tests.

PRs #1–#3 were validated and merged; at that point local `main` was synchronized with
`origin/main` at merge commit `4a0d7e3`.

## Recommended next iterations

Continue with one reviewable change per pull request. The in-code planar gate geometry
described above is now done. Likely follow-ups are:

- harden the planar assumption: assess geodesic calculations, noisy trajectories, gate
  buffers, interpolation, deduplication, out-of-order messages, and vessels lingering
  near the line
- add coverage-quality metrics to the daily result
- separate raw observation, enriched observation, crossing-event, and aggregate schemas
- write source telemetry to chunked Parquet before deriving events
- repeat the same query against a private development GCS bucket
- package the query as a small stateless Cloud Run endpoint or job
- evaluate a live AIS source and its license before retaining real messages

Do not begin with global ingestion, historical backfill, a public map, Kubernetes, a
shared database service, or multiple languages. Those choices are not needed to answer
the next question.

## Working principles

- Make one small, verifiable change at a time.
- Use a pull request and passing checks for every iteration.
- Prefer reversible decisions while the problem is still being explored.
- Start with one corridor and one end-to-end path before generalizing.
- Keep observations, enriched telemetry, derived events, and published aggregates
  conceptually separate.
- Treat provenance, licensing, coverage, and uncertainty as product features.
- Preserve raw inputs so derived results can be replayed when algorithms change.
- Add infrastructure and tooling only when the current experiment requires them.
- Let repository structure emerge from real components instead of designing a monorepo
  in advance.
