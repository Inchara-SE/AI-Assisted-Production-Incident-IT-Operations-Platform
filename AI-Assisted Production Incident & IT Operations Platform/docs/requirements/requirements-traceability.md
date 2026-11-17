# OpsPilot — Requirements Traceability Matrix

**Version:** 1.0  
**Last Updated:** 2026-11-11  
**Status:** In Progress / Active

This document traces every requirement from `OpsPilot_PRD.md` and `OpsPilot_TAD.md` to its implementation files, models, services, API routes, database constraints, dbt models, and automated tests.

---

## 1. Functional Requirements Traceability

| Req ID | Requirement Summary | PRD / TAD Section | Implementation Module / Model | Automated Test(s) | Status |
|---|---|---|---|---|---|
| **FR-01** | Alert Ingestion API (`POST /api/v1/alerts`), canonical schema validation, UTC timestamps, attempt recording, payload hash | PRD §7, §8; TAD §10.2 | `app/schemas/alert.py`, `app/api/v1/alerts.py`, `app/services/alert_ingestion.py`, `app/models/alert_event.py` | `tests/unit/test_alert_payload.py`, `tests/integration/test_alert_ingestion.py` | Implemented |
| **FR-02** | Exact Delivery Idempotency via `(source, source_event_id)` uniqueness; return existing canonical event, mark attempt `duplicate_delivery` | PRD §7; TAD §8.3, §10.2 | `app/models/alert_event.py` (UniqueConstraint), `app/services/alert_ingestion.py`, `app/repositories/alert_repository.py` | `tests/unit/test_idempotency.py`, `tests/integration/test_exact_replay.py` | Implemented |
| **FR-03** | Alert Normalization & Fingerprinting (service + type + severity + resource), versioned, stable, unit-tested | PRD §7; TAD §8.4 | `app/services/fingerprint.py`, `app/schemas/alert.py` | `tests/unit/test_fingerprint.py` | Implemented |
| **FR-04** | Incident Correlation: active status, matching service+fingerprint, 15-min event window, max severity retention | PRD §7; TAD §8.4, §9.3 | `app/services/alert_ingestion.py`, `app/repositories/incident_repository.py`, `app/models/incident.py` | `tests/unit/test_correlation.py`, `tests/integration/test_correlation_window.py` | Implemented |
| **FR-05** | Incident Lifecycle State Machine: allowed transitions only, server-side from_status derive, first_ack/first_res/res_at timestamps, reopen count | PRD §7; TAD §9.1, §9.2, §10.4 | `app/services/incident_lifecycle.py`, `app/models/incident.py`, `app/models/incident_transition.py`, `app/api/v1/incidents.py` | `tests/unit/test_lifecycle_transitions.py`, `tests/integration/test_incident_lifecycle.py` | Implemented |
| **FR-06** | Service Catalog: services, teams, criticality, directed dependencies (no self, no duplicate) | PRD §7; TAD §7.5, §7.6, §10.1 | `app/models/service.py`, `app/models/team.py`, `app/repositories/catalog_repository.py`, `app/services/catalog.py`, `app/api/v1/services.py` | `tests/unit/test_service_catalog.py`, `tests/integration/test_services.py` | Implemented |
| **FR-07** | Versioned Runbooks: logical runbooks, immutable approved versions, passage extraction with ordinals/headings | PRD §7; TAD §7.11-7.13, §12.1-12.2 | `app/models/runbook.py`, `app/services/runbook_management.py`, `app/api/v1/runbooks.py` | `tests/unit/test_runbook_passages.py`, `tests/integration/test_runbooks.py` | Implemented |
| **FR-08** | Full-Text Search Retrieval: approved versions only, service boost, deterministic ranking, diagnostic score | PRD §7; TAD §12.3, §10.5 | `app/services/runbook_retrieval.py`, `app/repositories/runbook_repository.py`, `app/api/v1/runbooks.py` | `tests/unit/test_runbook_search.py`, `tests/integration/test_retrieval.py` | Implemented |
| **FR-09** | Recommendation Generation: advisory suggestion, structured schema, provider abstraction | PRD §7; TAD §10.6-10.7, §13.1-13.3 | `app/providers/base.py`, `app/providers/mock_provider.py`, `app/services/recommendation.py`, `app/schemas/recommendation.py`, `app/api/v1/recommendations.py` | `tests/unit/test_mock_provider.py`, `tests/integration/test_recommendations.py` | Implemented |
| **FR-10** | Grounding & Citation Validation: passage exists in version, version approved, retrieved in candidate set; insufficient evidence fallback | PRD §7; TAD §10.7, §13.4-13.5 | `app/services/citation_validation.py`, `app/services/recommendation.py`, `app/models/recommendation.py` | `tests/unit/test_citation_validation.py`, `tests/integration/test_grounding.py` | Implemented |
| **FR-11** | Human Review: approve/reject with notes, 1 review per recommendation, reviewer derived from auth, no execution path | PRD §7; TAD §7.16, §10.8, §13.4 | `app/models/recommendation.py` (UniqueConstraint), `app/services/recommendation.py`, `app/api/v1/recommendations.py` | `tests/unit/test_human_review.py`, `tests/integration/test_review.py` | Implemented |
| **FR-12** | Audit History: append-only for app role, tracks transitions, ingestion, recommendations, reviews, config changes | PRD §7; TAD §7.17, §17.4 | `app/models/audit.py`, `app/repositories/audit_repository.py`, `app/services/audit.py` | `tests/unit/test_audit.py`, `tests/security/test_audit_immutability.py` | Implemented |
| **FR-13** | Deterministic Synthetic Data Generator: fixed seed (42), targets 10-20 services, 5-8 teams, incidents, events, runbooks, replays, cascades | PRD §7, §10; TAD §21 | `scripts/generate_data/generate_incidents.py`, `scripts/seed_demo_data.py` | `tests/unit/test_synthetic_generator.py` | Implemented |
| **FR-14** | dbt Analytics Transformation: sources, staging (stg_*), intermediate (int_*), facts (fct_*), dims (dim_*), marts (mart_*) | PRD §7; TAD §14 | `dbt/models/` (staging, intermediate, marts/core, marts/reporting) | `dbt test`, singular tests in `dbt/tests/` | Implemented |
| **FR-15** | Governed Operational Metrics: MTTA, MTTR, Recurrence Rate (7-day window), Repeat-Alert Share, Delivery Replay Rate, Acceptance Rate | PRD §9; TAD §15 | `dbt/models/intermediate/int_incident_response_times.sql`, `int_incident_recurrence.sql`, `fct_incidents.sql`, marts | `scripts/evaluation/reconcile_metrics.py`, singular tests in `dbt/tests/` | Implemented |
| **FR-16** | Analytics Dashboards: Metabase configs/SQL for 4 dashboards (Executive, Service, Alert/Incident, Recommendation Quality) | PRD §7; TAD §16 | `docs/data/metabase-dashboards.md`, `infra/docker/init-db.sql` | Verification scripts | Implemented |
| **FR-17** | Authentication & RBAC: Argon2id hash, JWT bearer tokens, roles (admin, on_call_engineer, analyst), derive actor from token | PRD §7; TAD §17.1-17.2 | `app/core/security.py`, `app/api/v1/auth.py`, `app/models/user.py`, `app/models/role.py` | `tests/unit/test_security.py`, `tests/security/test_authorization.py` | Implemented |
| **FR-18** | Operational Quality, Safety, Docker, CI: Docker Compose, GitHub Actions, Ruff, secret-redacted logging, no execution pathways | PRD §7, §12; TAD §18, §19, §20 | `docker-compose.yml`, `Dockerfile`, `.github/workflows/ci.yml`, `app/core/logging.py` | `tests/security/test_safety_boundaries.py`, Ruff linter | Implemented |

---

## 2. Non-Functional & Safety Constraints Traceability

| Constraint ID | Constraint Summary | Source Section | Implementation / Enforcement Mechanism | Verification |
|---|---|---|---|---|
| **NFR-SEC-01** | Advisory AI Only (Zero Execution Pathway) | PRD §3.2, TAD §1.2, §13.4 | Recommendation text is treated as purely informative JSON; no bash/exec/eval/subprocess or remote API tool bindings exist. | `tests/security/test_safety_boundaries.py` |
| **NFR-SEC-02** | Secret Redaction in Structured Logs | PRD §12.3, TAD §18.1 | `app/core/logging.py` filters sensitive keys (`password`, `token`, `secret`, `authorization`, `cookie`, `key`). | `tests/security/test_secret_redaction.py` |
| **NFR-SEC-03** | Least Privilege DB Boundaries (`ops` vs `analytics`) | TAD §4.1-4.2 | `infra/docker/init-db.sql` sets up 4 separate roles: `opspilot_migrator`, `opspilot_app`, `opspilot_dbt`, `opspilot_metabase`. | DB permissions test / scripts |
| **NFR-SEC-04** | Audit Row Immutability | PRD §7, TAD §17.4 | DB role `opspilot_app` is granted `INSERT, SELECT` on `ops.audit_events` only (no UPDATE, no DELETE). | `tests/security/test_audit_immutability.py` |
| **NFR-MET-01** | Delivery Replay Rate vs Repeat-Alert Share Separation | PRD §9.5, §9.6; TAD §2.1 | `fct_alert_ingestion_attempts.is_duplicate_delivery` vs `fct_alert_events.is_repeat_alert`. Exact replay never creates an `alert_events` row. | `tests/unit/test_metric_reconciliation.py` |
| **NFR-MET-02** | Reopen Lifecycle MTTR Invariant | PRD §9.3; TAD §9.2 | Reopen increments `reopen_count`, clears current `resolved_at`, keeps `first_resolved_at`. Final resolution updates `resolved_at`. MTTR uses latest `resolved_at`. | `tests/unit/test_lifecycle_transitions.py` |
| **NFR-MET-03** | 7-Day Recurrence Observation Window | PRD §9.4; TAD §15.4 | Incidents within last 7 days are excluded from denominator since full observation window is incomplete. | `dbt/tests/assert_recurrence_eligibility.sql`, reconciliation tests |
