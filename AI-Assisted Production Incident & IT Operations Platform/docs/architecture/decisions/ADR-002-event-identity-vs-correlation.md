# ADR-002: Distinct Delivery Replay Identity vs Alert Correlation Fingerprint

**Status:** Accepted  
**Date:** 2026-11-11  

## Context
A critical failure mode in IT operations and incident platforms is conflating a network/transport retry (an identical delivery of the same alert) with a distinct recurring alert occurrence (a repeated signal of an active failure). Conflating these two concepts leads to corrupted incident counts, falsified alert volume metrics, and inaccurate deduplication reporting.

## Decision
We enforce a strict technical separation across three levels:
1. **Delivery Attempt (`ops.alert_ingestion_attempts`):** Every incoming HTTP POST request received at `/api/v1/alerts` records an attempt row with a SHA-256 payload hash and outcome (`accepted`, `duplicate_delivery`, or `rejected`).
2. **Canonical Alert Event Identity (`ops.alert_events`):** Logical event uniqueness is enforced by a database unique constraint on `(source, source_event_id)`. If an incoming payload matches an existing `(source, source_event_id)`, it is classified as an exact delivery replay: the ingestion attempt is recorded as `duplicate_delivery`, and the existing canonical event/incident reference is returned with HTTP 200 without inserting a duplicate `alert_events` row.
3. **Correlation Fingerprint (`fingerprint`):** Distinct logical events with different `source_event_id` values but identical normalized signatures (`service_key` + `alert_type` + `severity` + `resource`) are persisted as distinct rows in `ops.alert_events` with `is_repeat_alert = true`, and correlated to the existing eligible active incident if within the 15-minute event window.

## Alternatives Considered
1. **Drop Repeated Fingerprints at the Gateway:** Drops historical operational signal; prevents calculation of repeat-alert share and true failure duration.
2. **Treat All Retries as New Alert Events:** Artificially inflates alert volume, corrupts MTTA/MTTR, and misrepresents simulator network replays as real operational failures.

## Consequences
- **Positive:** Enables accurate, independent calculation of **Delivery Replay Rate** (transport idempotency) and **Repeat-Alert Share** (signal correlation efficiency).
- **Trade-off:** Requires a two-stage concurrency check in the ingestion pipeline (checking source event identity before correlation locking).

## Validation
Verified via `tests/unit/test_idempotency.py`, `tests/unit/test_correlation.py`, and metric reconciliation fixtures.
