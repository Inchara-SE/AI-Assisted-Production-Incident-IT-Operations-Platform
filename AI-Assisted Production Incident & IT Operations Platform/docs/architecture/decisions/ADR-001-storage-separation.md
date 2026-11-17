# ADR-001: Separation of Operational (`ops`) and Analytical (`analytics`) Schemas in a Single PostgreSQL Database

**Status:** Accepted  
**Date:** 2026-11-11  

## Context
OpsPilot requires a reliable transactional datastore for operational alert ingestion, incident management, and runbook retrieval, alongside a dedicated analytical layer for dbt transformations and Metabase business intelligence queries. Operating two separate database clusters (e.g., PostgreSQL for OLTP and Snowflake/BigQuery for OLAP) would introduce excessive operational overhead, network latency, local setup friction, and cloud account/cost requirements for a local portfolio MVP.

## Decision
We utilize a single PostgreSQL 16+ database instance divided into two distinct, governed schemas with strict least-privilege role boundaries:
1. `ops`: Operational tables owned by Alembic migrations and written/read by the FastAPI application (`opspilot_app`).
2. `analytics`: Analytical tables, views, dimensions, facts, and marts owned and built exclusively by dbt Core (`opspilot_dbt`).

Metabase connects via `opspilot_metabase`, a read-only role granted `SELECT` privileges only on objects in the `analytics` schema, with zero read or write access to `ops`. The FastAPI application role has no write permissions in `analytics`.

## Alternatives Considered
1. **Separate Cloud Warehouse (BigQuery / Snowflake):** Adds credential and billing overhead, breaks zero-cost local reproducibility.
2. **SQLite for OLTP + DuckDB for OLAP:** Lacks native PostgreSQL full-text search (`tsvector`, `ts_rank`), transactional concurrency locks (`pg_advisory_xact_lock`), and native Metabase live connection without plugins.
3. **Single Unpartitioned `public` Schema:** Violates separation of concerns, allows Metabase direct access to un-modeled OLTP data, and lacks schema-level permission boundaries.

## Consequences
- **Positive:** Zero cloud cost, one-click `docker compose up -d postgres` local setup, transparent permission boundaries, clean dbt source-to-target contract.
- **Trade-off:** Analytical transformations share database compute and storage with operational ingestion. For the target MVP scale (up to 20,000 alert events and 1,500 incidents), this load is negligible on modern hardware.

## Validation
Verified through PostgreSQL role grant scripts (`infra/docker/init-db.sql`) and automated connection permission tests.
