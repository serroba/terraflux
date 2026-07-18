# Terraflux

Terraflux is an exploratory observatory for the flows that connect our planet.

The long-term idea is to make large transport systems legible as changing flows rather
than collections of individual assets: maritime trade first, with other physical networks
potentially following later.

## First experiment

Measure observed aggregate maritime flow through one geographic gate, initially the
Strait of Hormuz.

The first useful result should be a small, reproducible daily series such as:

- observed crossings by direction
- crossings by broad vessel class
- estimated carrying capacity
- data coverage and confidence indicators

This is not intended to be a vessel-tracking product. Published outputs should favour
aggregates and clearly distinguish observed AIS activity from total real-world traffic.

## Working principles

- Make one small, verifiable change at a time.
- Prefer reversible decisions while the problem is still being explored.
- Start with one corridor and one end-to-end path before generalising.
- Keep raw observations, derived events, and published aggregates conceptually separate.
- Treat provenance, licensing, coverage, and uncertainty as product features.
- Add infrastructure and tooling only when the current experiment requires them.
- Let repository structure emerge from real components instead of designing a monorepo
  in advance.

## Status

Foundation only. No production architecture, cloud services, languages, or data
providers have been selected yet.

## Experiments

- [`hormuz-flow`](experiments/hormuz-flow/README.md): a local DuckDB and Parquet proof
  of concept for daily aggregate flow queries.
