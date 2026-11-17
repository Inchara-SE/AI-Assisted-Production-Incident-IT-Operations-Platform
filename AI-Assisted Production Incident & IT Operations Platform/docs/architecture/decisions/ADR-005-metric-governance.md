# ADR-005: Metric Governance and dbt Intermediate Transformation Layer

**Status:** Accepted  
**Date:** 2026-11-11  

## Context
Operational incident reporting frequently suffers from inconsistent metric calculations (e.g., conflicting MTTR numbers between teams due to different handling of reopened incidents, varying denominators for recurrence rates, or conflating deduplication with delivery replays). BI tools querying raw operational tables directly reproduce these discrepancies.

## Decision
We enforce a single source of truth for all analytical KPIs via a governed dbt transformation hierarchy:
1. **Staging (`stg_*`):** Type casting, column renaming, and light cleansing only. No business logic.
2. **Intermediate (`int_*`):** Canonical reusable business logic:
   - `int_incident_lifecycle.sql`: Reopen-aware resolution logic, derivation of first vs latest timestamps.
   - `int_incident_response_times.sql`: Explicit eligibility flags (`is_mtta_eligible`, `is_mttr_eligible`), duration calculations in seconds, rejection of negative durations.
   - `int_incident_recurrence.sql`: Strict 7-day post-resolution matching by service and fingerprint. Incidents lacking the full 7-day post-creation observation window are excluded from the denominator.
   - `int_alert_correlation.sql`: Repeat alert classification preserving individual accepted events.
   - `int_recommendation_outcomes.sql`: Joins recommendations with human reviews, calculating acceptance rates excluding unreviewed items.
3. **Marts (`fct_*`, `dim_*`, `mart_*`):** Final dimensional models and aggregate reporting marts consumed by Metabase. Metabase queries only curated marts or approved dimensional models and never implements ad-hoc KPI logic in SQL cards.

## Alternatives Considered
- Direct Metabase SQL Questions on `ops`: Spreads un-tested KPI SQL across multiple dashboard cards; leads to metric drift.
- Logic inside Python API: Hides analytical calculations from data analysts, prevents dimensional modeling in BI.

## Consequences
- **Positive:** Tested, documented, governed metric layer; identical numbers across all dashboards; clear data lineage.
- **Trade-off:** New metrics or dimensional changes require updating dbt models and running `dbt build`.

## Validation
Verified via dbt singular tests (`dbt/tests/`) and independent metric reconciliation script (`scripts/evaluation/reconcile_metrics.py`).
