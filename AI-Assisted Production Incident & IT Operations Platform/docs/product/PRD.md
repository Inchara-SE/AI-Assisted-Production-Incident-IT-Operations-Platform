# OpsPilot — Product Requirements Document (PRD)

**Document status:** Baseline for MVP implementation  
**Version:** 1.0  
**Last updated:** 11 November 2026  
**Product name:** OpsPilot  
**Product category:** Analytics-first IT operations platform with AI-assisted incident triage  
**Primary portfolio target:** Entry-level / early-career Analytics Engineer roles  

---

## 1. Executive summary

OpsPilot is a small, locally runnable IT operations platform that receives simulated application alerts, normalizes and correlates them into incidents, maps incidents to services, retrieves approved troubleshooting runbooks, and produces optional evidence-grounded triage recommendations for human review.

Its defining portfolio capability is the analytical platform built around the operational workflow. Operational events are persisted in PostgreSQL, transformed through dbt into tested facts, dimensions and analytical marts, and exposed through Metabase dashboards. The platform demonstrates how raw operational records become consistent, documented and decision-useful metrics.

AI is an assisting capability, not the product's source of truth. Recommendations must cite approved runbook versions and passages. When evidence is absent or insufficient, OpsPilot must say so. No recommendation can directly execute a production change or remediation.

### 1.1 Product positioning

> OpsPilot transforms IT operational events into trustworthy incident analytics and evidence-backed investigation guidance.

### 1.2 Product thesis

Operational incident data is useful only when its identity, lifecycle and business meaning are consistent. OpsPilot therefore treats event ingestion, incident correlation, lifecycle history, metric definitions, data quality and evidence traceability as first-class requirements.

### 1.3 MVP architecture in one sentence

A FastAPI application stores operational records in PostgreSQL `ops`; dbt reads those records and builds tested analytical models in PostgreSQL `analytics`; Metabase queries the analytical models; a retrieval-and-recommendation service searches approved runbooks and returns human-reviewable suggestions.

---

## 2. Background and problem statement

### 2.1 Primary user

The primary user is an **on-call engineer** who needs to understand an incoming incident and find an approved troubleshooting procedure quickly.

Secondary users are:

- IT operations analysts who investigate trends and operational performance.
- Service owners who want to understand the reliability of the services they own.
- Engineering managers who need consistent operational reporting.
- Administrators who maintain service metadata and approved runbooks.

### 2.2 Problems addressed

1. Alert, incident, service and troubleshooting information is fragmented.
2. Multiple alerts can describe the same active failure, creating noise and fragmented investigation context.
3. Incident lifecycle history and ownership are difficult to analyze consistently when state changes overwrite prior values.
4. Teams lack consistent definitions for response and resolution metrics.
5. Recurring operational problems and service-level hotspots are difficult to identify from raw events alone.
6. Troubleshooting knowledge is difficult to discover and recommendations can be unreliable when they are not grounded in approved sources.

### 2.3 Desired outcomes

OpsPilot should:

- Consolidate accepted alert events and preserve their event history.
- Correlate related alerts to incidents using transparent deterministic rules.
- Preserve incident lifecycle transitions and audit history.
- Make service ownership and dependencies discoverable.
- Transform operational records into documented analytical models.
- Provide governed operational metrics and dashboards.
- Retrieve approved runbook evidence and optionally generate suggestions that cite it.
- Provide repeatable evaluation results using deterministic synthetic data.

---

## 3. Goals, non-goals and product principles

### 3.1 MVP goals

| ID | Goal | Evidence of completion |
|---|---|---|
| G-01 | Reliable alert intake | Validated alerts are persisted; exact delivery retries are idempotent. |
| G-02 | Useful incident workflow | Related alert events can be correlated; lifecycle transitions are validated and recorded. |
| G-03 | Governed operational data | Operational tables have explicit keys, constraints and documented meanings. |
| G-04 | Analytics Engineering demonstration | dbt staging, intermediate, fact, dimension and mart models build successfully and have tests and documentation. |
| G-05 | Trustworthy metrics | KPI definitions, denominators, exclusions and edge cases are documented and tested. |
| G-06 | Decision-useful reporting | Metabase dashboards query curated analytical marts and reconcile to source records. |
| G-07 | Safe knowledge assistance | Recommendations cite approved runbook versions and passages or return insufficient evidence. |
| G-08 | Reproducible portfolio demonstration | A deterministic dataset and setup instructions allow a reviewer to reproduce key scenarios. |

### 3.2 Non-goals

The MVP will not:

- Connect to real production monitoring systems or production infrastructure.
- Execute remediation, shell commands, deployments, database changes or other operational actions.
- Claim that an LLM can reliably diagnose every incident or identify a root cause from incomplete evidence.
- Ingest secrets, credentials, access tokens or secret-bearing production logs.
- Implement a complex multi-tenant SaaS architecture.
- Implement enterprise SSO, on-call scheduling, paging, chat integrations or a full ITSM suite.
- Build a custom React frontend.
- Require a cloud warehouse, cloud account, paid LLM or vector database for the core MVP.
- Treat recommendation approval as proof that a recommendation was technically correct or effective.
- Infer service uptime or availability from incident records alone.

### 3.3 Product principles

1. **Preserve events:** Distinct accepted alert events remain individually queryable even when correlated to the same incident.
2. **Idempotent delivery:** Replaying the same source event must not create a second canonical alert-event record.
3. **Transparent correlation:** Incident grouping uses documented deterministic rules, not an opaque AI decision.
4. **History over overwrites:** State changes and human decisions are recorded as events.
5. **Metrics have contracts:** Every KPI has a grain, numerator, denominator, eligibility rule, exclusions and time semantics.
6. **Evidence before generation:** Retrieval happens before recommendation generation.
7. **Human accountability:** AI output is advisory and requires human review; it never executes.
8. **Reproducibility:** Synthetic data and evaluation cases use fixed seeds and known expected outcomes.
9. **Minimum sufficient infrastructure:** Add infrastructure only when it solves a demonstrated requirement.

---

## 4. Target users and user stories

### 4.1 On-call engineer

- As an on-call engineer, I want related alerts grouped into an incident so that I can investigate one coherent failure rather than several disconnected notifications.
- I want to see the service, severity, alert timeline and current incident state so that I can understand impact and ownership.
- I want to search approved runbooks so that I can find relevant troubleshooting instructions.
- I want a recommendation to show exact supporting sources and limitations so that I can judge whether it is safe and relevant.
- I want to approve or reject a recommendation with notes so that the outcome is auditable.

### 4.2 IT operations analyst

- As an analyst, I want consistent incident and alert data so that I can compare operational performance over time.
- I want documented MTTA, MTTR, recurrence and alert-correlation definitions so that reports are interpreted consistently.
- I want to filter dashboards by date, service, team and severity so that I can identify operational hotspots.

### 4.3 Service owner / engineering manager

- As a service owner, I want incidents and response metrics by service so that I can identify where operational attention is needed.
- I want to see recurring failures and incident severity patterns so that I can prioritize reliability work.

### 4.4 Administrator

- As an administrator, I want to maintain service metadata and approved runbook versions so that the application uses controlled operational knowledge.
- I want important configuration changes and user decisions recorded so that the system has an audit trail.

---

## 5. Key user journeys

### Journey A — Alert to incident

1. A simulator sends an alert to `POST /api/v1/alerts`.
2. The API validates the canonical payload and records an ingestion attempt.
3. The application checks the source event identity for an exact replay.
4. A new logical event is normalized and fingerprinted.
5. The incident service finds an appropriate active incident using the service, fingerprint and correlation window.
6. The event is attached to the incident, or a new incident is created.
7. A lifecycle transition and audit event are recorded where applicable.
8. The API returns the event ID, incident ID and ingestion outcome.

### Journey B — Incident lifecycle

1. An engineer lists incidents and filters by status, severity or service.
2. The engineer opens an incident and reviews its alert events and timeline.
3. The engineer acknowledges or begins investigating the incident.
4. The application validates the requested transition.
5. The application records the transition and actor.
6. The engineer resolves the incident or reopens it if a failure returns.

### Journey C — Evidence-grounded triage

1. An engineer requests a recommendation for an incident.
2. OpsPilot loads incident and service context.
3. The knowledge service retrieves relevant passages from approved runbook versions only.
4. A mock or configured LLM provider generates a structured suggestion using the incident context and retrieved evidence.
5. The application validates every cited runbook version and passage.
6. If evidence is not sufficient, the response explicitly indicates insufficient evidence.
7. The recommendation and its source references are persisted.
8. A human approves or rejects the recommendation and may provide notes.
9. No operational action is executed.

### Journey D — Operational analytics

1. Operational tables receive alert, incident, transition and recommendation records.
2. dbt reads the `ops` schema as sources.
3. dbt builds staging and intermediate models, then facts, dimensions and marts in `analytics`.
4. Tests validate keys, relationships, accepted values and business rules.
5. Metabase queries only curated analytical models for its dashboards.
6. An analyst filters by date, service, team or severity and investigates patterns.

---

## 6. MVP scope

### 6.1 Must-have

| Area | MVP capability |
|---|---|
| Alert intake | Canonical JSON API, schema validation, normalization, payload hash and ingestion-attempt tracking |
| Idempotency | Unique source event identity; exact replays do not create duplicate alert-event records |
| Correlation | Deterministic service + fingerprint + 15-minute event-time window |
| Incident management | Create, list, filter, detail, timeline, severity and status transitions |
| Service catalog | Services, teams, criticality, ownership and service dependencies |
| Audit | Status transitions, ingestion outcomes, recommendation generation/review and configuration actions |
| Synthetic data | Fixed-seed generator with labeled scenarios and historical timestamps |
| Analytics engineering | dbt sources, staging, intermediate, facts, dimensions, marts, tests and docs |
| Metrics | Incident volume, MTTA, MTTR, recurrence, repeat-alert share, delivery replay rate and recommendation acceptance |
| BI | Metabase dashboards built on `analytics` models |
| Knowledge | Versioned runbooks, approval status, passages and PostgreSQL full-text search |
| AI | Mock-first provider abstraction, structured recommendation and insufficient-evidence fallback |
| Grounding | Citation/source validation and immutable source-version references |
| Review | Human approve/reject with notes and audit record |
| Delivery | Docker Compose, CI checks, README, ERD, metric documentation and demo scenarios |

### 6.2 Should-have, after the core path works

- Optional real LLM provider integration.
- Basic JWT authentication and three application roles if not completed in the first pass.
- OpenTelemetry traces.
- Incremental dbt models only where volume or refresh time justifies them.
- dbt snapshots for a selected historical attribute such as service ownership, if the use case is demonstrated.
- Simple Streamlit operator view only if Swagger plus Metabase is insufficient for a coherent demo.

### 6.3 Explicitly deferred

- pgvector and embedding-based retrieval.
- Redis, RQ or Celery.
- Snowflake or BigQuery migration.
- Complex SCD Type 2 across every dimension.
- Multi-tenant isolation and PostgreSQL row-level security.
- React frontend.
- Real monitoring vendor integrations.
- Autonomous remediation or workflow execution.

---

## 7. Functional requirements

### FR-01 — Alert ingestion

The system shall expose `POST /api/v1/alerts` to accept the canonical alert payload.

**Acceptance criteria**

- Required fields and types are validated.
- Timestamps are stored as timezone-aware UTC timestamps.
- Invalid payloads receive a clear 4xx response and do not create canonical alert events.
- Each request attempt is recorded with an outcome, request identifier and payload hash, without storing secrets or unfiltered raw payloads.
- Valid logical events create one canonical `alert_events` row.

### FR-02 — Exact delivery idempotency

The system shall identify an exact source-event replay by `(source, source_event_id)`.

**Acceptance criteria**

- A unique database constraint protects canonical event identity.
- Replaying the same identity returns the existing event and incident reference.
- A replay creates an ingestion-attempt record with a duplicate-delivery outcome but does not create a second canonical alert event.
- Concurrent replays cannot create duplicate canonical events.

### FR-03 — Alert normalization and fingerprinting

The system shall normalize service, alert type, severity, resource and message fields and calculate a stable fingerprint.

**Acceptance criteria**

- Normalization is deterministic and covered by unit tests.
- The fingerprint is generated from documented stable fields; volatile values such as timestamps and request IDs are excluded.
- A version or documented change policy exists for fingerprint logic.

### FR-04 — Incident correlation and creation

The system shall correlate a distinct alert event to an appropriate active incident or create a new incident.

**MVP rule**

- Service ID and normalized fingerprint must match.
- Incident status must be active (`open`, `acknowledged` or `investigating`).
- The alert event timestamp must be within 15 minutes of the incident's most recent correlated alert-event timestamp. The implementation must document how out-of-order timestamps are handled.
- A transaction-level concurrency control mechanism must prevent simultaneous matching alerts from unnecessarily creating parallel incidents.
- A resolved incident is not an active grouping target.

**Acceptance criteria**

- Distinct source events with the same fingerprint are preserved as separate event rows.
- Correlated events point to the same incident.
- A new incident is created when no eligible active incident exists.
- Incident severity is the highest normalized severity among its accepted events, using a documented order.

### FR-05 — Incident lifecycle

The system shall support `open`, `acknowledged`, `investigating` and `resolved` states, with controlled reopening.

**Allowed transitions**

| From | To | Meaning |
|---|---|---|
| `open` | `acknowledged` | An operator has accepted ownership. |
| `open` | `investigating` | Operator starts investigation directly. |
| `acknowledged` | `investigating` | Investigation begins. |
| `acknowledged` | `resolved` | Incident is resolved without a separately recorded investigating state. |
| `investigating` | `resolved` | Investigation is complete. |
| `resolved` | `open` | Incident is explicitly reopened. |

All other transitions shall be rejected.

**Acceptance criteria**

- The status field cannot be changed through an unrestricted update endpoint.
- Every accepted transition records previous status, new status, actor and timestamp.
- First acknowledgement time is preserved.
- First resolution time is preserved.
- `resolved_at` is populated only while the current incident state is resolved; it is cleared on reopening and populated again on final resolution.
- `reopen_count` increments on each accepted reopen.

### FR-06 — Service catalog

The system shall maintain services, owning teams, criticality, environment and directed service dependencies.

**Acceptance criteria**

- Each service has a stable unique service key.
- Each service references an owning team where ownership is known.
- Self-dependencies and duplicate dependency pairs are rejected.
- Incident records reference a service.

### FR-07 — Runbook management and versioning

The system shall store logical runbooks and immutable published versions.

**Acceptance criteria**

- A runbook can have multiple versions.
- Only approved versions are eligible for retrieval.
- A published version and its passages cannot be edited in place; changes create a new version.
- Each version is split into identifiable passages.
- A runbook may be service-specific or marked as applicable across services.

### FR-08 — Runbook retrieval

The system shall expose `GET /api/v1/runbooks/search?q=...` and retrieve approved passages using PostgreSQL full-text search.

**Acceptance criteria**

- Search results include runbook ID, version ID, passage ID, title, passage text, rank and service association.
- Non-approved versions are excluded.
- Service-specific relevance can be used as a documented ranking boost.
- The API returns a bounded top-K result set.
- Search behavior is evaluated against a labeled test set.

### FR-09 — Recommendation generation

The system shall expose `POST /api/v1/incidents/{id}/recommendations`.

**Acceptance criteria**

- Recommendation generation uses incident context and retrieved approved evidence.
- The provider is isolated behind a common interface.
- A deterministic mock provider is available for tests and demos.
- The generated response follows a validated structured schema.
- Provider, model, prompt version, generation timestamp and outcome are recorded.
- Recommendations are clearly labeled as suggestions.

### FR-10 — Grounding and insufficient evidence

The system shall validate source references before persisting a recommendation as citation-valid.

**Acceptance criteria**

- Every cited passage exists and belongs to the cited runbook version.
- The referenced runbook version was approved and was among the retrieved evidence supplied to the generation step.
- Citation validation status is stored.
- When no adequate evidence is retrieved, the response states `insufficient_evidence = true` and does not invent a source.
- Citation existence is not presented as proof that the advice is correct; evidence support requires separate evaluation.

### FR-11 — Human review

The system shall expose `POST /api/v1/recommendations/{id}/review`.

**Acceptance criteria**

- A reviewer can approve or reject a recommendation and provide optional notes.
- Reviewer identity and timestamp are stored.
- The review outcome is append-only for the MVP; a recommendation can be reviewed once. A future re-review workflow requires a deliberate schema/API change.
- Review does not execute any operational action.

### FR-12 — Audit history

The system shall record security- and operation-relevant actions.

**Acceptance criteria**

- Incident transitions, alert ingestion outcomes, recommendation generation/review and service/runbook configuration changes produce audit records.
- Audit records include actor type, actor ID when applicable, action, entity reference, timestamp and safe metadata.
- The application database role cannot update or delete audit rows.
- Audit history is exposed in incident detail/timeline where relevant.

### FR-13 — Synthetic data generation

The system shall provide a deterministic synthetic-data generator.

**Acceptance criteria**

- The generator accepts a seed and configuration.
- It creates services, teams, runbooks, incidents, events, transitions and recommendation outcomes.
- It creates known scenarios: exact delivery retries, repeat fingerprints, recurrence, critical severity, long-running incidents, unresolved incidents and no-evidence incidents.
- The output is repeatable for the same seed and generator version.
- Generated records are clearly identified as synthetic.

### FR-14 — dbt analytical transformations

The analytics project shall transform operational sources into tested facts, dimensions and marts.

**Acceptance criteria**

- dbt sources are declared for required operational tables.
- Staging, intermediate and mart layers follow documented responsibilities.
- Each fact has an explicit grain.
- Primary keys, relationships, accepted values and critical business rules are tested.
- dbt documentation and lineage can be generated.
- The full MVP model build is reproducible locally and in CI.

### FR-15 — Governed metrics

The system shall define operational metrics centrally in dbt and document their contracts.

**Acceptance criteria**

- Every metric has a business definition, grain, formula, numerator, denominator, eligibility rule, exclusions and time semantics.
- The same definition is used by all relevant dashboards.
- Independent reconciliation tests cover key calculations.
- Incomplete or ineligible records are not silently treated as zero-duration outcomes.

### FR-16 — Analytics dashboards

Metabase shall provide curated dashboards using the `analytics` schema.

**Acceptance criteria**

- Executive overview, service performance, alert/incident analytics and recommendation-quality dashboards are available.
- Filters include date range and relevant service/team/severity dimensions.
- Dashboard totals reconcile to the underlying dbt marts.
- Dashboard labels make metric definitions and synthetic-data context clear.

### FR-17 — Authentication and roles

For the MVP, basic application authentication and role-based authorization are recommended, without enterprise SSO.

**Roles**

- `admin`: manage service catalog and runbooks; view all operational records.
- `on_call_engineer`: view incidents, update incident status, request recommendations and review recommendations.
- `analyst`: read incident and analytical information; no operational state changes.

**Acceptance criteria**

- API endpoints enforce permissions server-side.
- User identity is associated with human actions.
- Passwords are stored as strong password hashes, never plaintext.
- The default seeded demo users/credentials are documented as local-demo-only and are not production credentials.

### FR-18 — Operational quality and reproducibility

The project shall provide automated application, data, security and CI checks.

**Acceptance criteria**

- pytest covers core business logic and API behavior.
- dbt tests cover analytical contracts.
- Ruff runs in CI.
- CI executes relevant tests and `dbt build` against a test database or controlled CI service.
- Docker Compose provides a documented local startup path.
- Logs do not expose secret values or unrestricted raw payloads.

---

## 8. Canonical alert payload

The MVP API accepts a canonical payload similar to the following:

```json
{
  "source": "monitoring_simulator",
  "source_event_id": "evt_10001",
  "service_key": "payment-api",
  "alert_type": "high_latency",
  "severity": "critical",
  "occurred_at": "2026-11-10T10:30:00Z",
  "resource": "payment-node-01",
  "message": "API latency exceeded threshold",
  "metadata": {
    "observed_latency_ms": 3200,
    "threshold_ms": 1000
  }
}
```

### 8.1 Field rules

| Field | Required | Rule |
|---|---|---|
| `source` | Yes | Stable source identifier. |
| `source_event_id` | Yes | Stable logical event identifier within the source. Used for exact delivery idempotency. |
| `service_key` | Yes | Must resolve to an existing service. |
| `alert_type` | Yes | Normalized bounded string or controlled taxonomy. |
| `severity` | Yes | `critical`, `high`, `medium` or `low`. |
| `occurred_at` | Yes | ISO-8601 timestamp with timezone. |
| `resource` | No | Safe resource identifier. |
| `message` | Yes | Bounded, sanitized description; must not contain secrets. |
| `metadata` | No | Allow-listed JSON object with size and depth limits. |

The API shall not accept arbitrary secret-bearing log bundles. The payload is a simulator contract, not a generic log-ingestion endpoint.

---

## 9. Metric contracts

The metric layer is a core product capability. The definitions below are the MVP baseline and must be implemented consistently in dbt.

### 9.1 Incident volume

- **Meaning:** Number of distinct incidents created in the selected period.
- **Grain:** One incident.
- **Formula:** `COUNT(DISTINCT incident_id)` by incident creation date and selected dimensions.
- **Exclusions:** None beyond test/seed records explicitly filtered from the production-style demo view.

### 9.2 Mean Time to Acknowledge (MTTA)

- **Meaning:** Average elapsed time from incident creation to first acknowledgement.
- **Grain:** One acknowledged incident.
- **Formula:** `AVG(first_acknowledged_at - created_at)`.
- **Eligibility:** `first_acknowledged_at IS NOT NULL`.
- **Exclusions:** Unacknowledged incidents; negative or invalid durations fail data tests rather than being silently included.
- **Presentation:** Show eligible incident count alongside the average. A median may be presented as a companion statistic, not substituted without labeling.

### 9.3 Mean Time to Resolve (MTTR)

- **Meaning:** Average wall-clock time from incident creation to its latest successful resolution timestamp for incidents currently resolved.
- **Grain:** One currently resolved incident.
- **Formula:** `AVG(resolved_at - created_at)` where current status is `resolved`.
- **Eligibility:** Incident is currently resolved and has valid timestamps.
- **Reopening semantics:** Reopening clears current `resolved_at`; a later resolution sets it again. The metric uses the latest resolution time and therefore measures wall-clock time to final resolution, including time between a prior resolution and reopening. `first_resolved_at` and `reopen_count` remain available for separate analysis.
- **Presentation:** Show eligible resolved incident count alongside the average.

### 9.4 Recurrence rate

- **Meaning:** Share of eligible incidents that represent recurrence of the same service/fingerprint failure within seven days after a prior matching incident was resolved.
- **Grain:** One incident.
- **Recurring condition:** A prior incident exists for the same service and normalized fingerprint, was resolved before the new incident, and the new incident was created within seven days after that prior resolution.
- **Formula:** `recurring eligible incidents / all incidents with a complete seven-day observation window`.
- **Eligibility:** Exclude incidents created in the most recent seven days because their full observation window is not yet available. If a prior incident has not been resolved, it does not qualify as a post-resolution recurrence under this definition.
- **Interpretation:** This is an explicitly scoped repeat-failure proxy, not proof of common root cause.

### 9.5 Repeat-alert share (preferred name for the dashboard)

- **Meaning:** Share of accepted logical alert events that were correlated to an existing incident rather than creating the first event of a new incident.
- **Grain:** One accepted alert event.
- **Formula:** `accepted events marked as repeat/correlated / all accepted alert events`.
- **Important distinction:** These events are retained. This is not the percentage of rows physically discarded.

### 9.6 Delivery replay rate

- **Meaning:** Share of ingestion attempts identified as exact replays of an already accepted `(source, source_event_id)`.
- **Grain:** One ingestion attempt.
- **Formula:** `duplicate_delivery attempts / all validly evaluated ingestion attempts`.
- **Important distinction:** Replayed attempts are recorded in the ingestion-attempt table but do not create another canonical alert-event row.

### 9.7 Recommendation acceptance rate

- **Meaning:** Share of reviewed recommendations that reviewers approved.
- **Grain:** One reviewed recommendation.
- **Formula:** `approved recommendations / (approved + rejected recommendations)`.
- **Eligibility:** Exclude unreviewed recommendations.
- **Interpretation:** Approval is a human review outcome, not evidence of technical correctness or successful remediation.

### 9.8 Supporting quality measures

The MVP should also report:

- Citation validation rate: recommendations whose cited source references all pass structural validation / recommendations with at least one citation.
- Insufficient-evidence frequency: recommendations explicitly marked insufficient evidence / all successfully generated recommendations.
- Ingestion acceptance/rejection counts.
- dbt test results and source-to-mart reconciliation outcomes.

A citation validation pass only proves that references exist and are permitted; separate human-labeled evaluation is required to assess whether evidence actually supports the advice.

---

## 10. Data generation and evaluation requirements

### 10.1 Initial synthetic data targets

These are starter targets, not performance claims:

| Entity | Initial target |
|---|---:|
| Services | 10–20 |
| Teams | 5–8 |
| Alert events | 10,000–20,000 |
| Incidents | 500–1,500 |
| Runbooks | 20–40 |
| Recommendations | 200–500 |
| Historical range | Approximately 3 months |
| Labeled retrieval cases | 30–50 |

### 10.2 Scenario coverage

The generator must create:

- Exact delivery replays.
- Distinct events with repeated fingerprints.
- Related alerts from dependent services.
- Critical and low-severity incidents.
- Short- and long-running incidents.
- Unacknowledged and unresolved incidents.
- Reopened incidents.
- Post-resolution recurrence.
- Approved and rejected recommendations.
- Incidents with relevant runbooks.
- Incidents with no relevant runbooks.

### 10.3 Determinism

- Generator accepts a seed and version/configuration.
- Same seed and configuration produce the same logical dataset.
- Generated data is identified as synthetic.
- The generator documents its assumptions and scenario proportions.
- Tests use small deterministic fixtures; larger seed data is used for dashboards and the demo.

### 10.4 Retrieval evaluation

The labeled evaluation set shall define relevant runbook versions/passages for each test incident.

Report at least:

- Precision@K.
- Recall@K.
- Mean Reciprocal Rank (recommended).
- Results by incident category where sample size allows.

Do not present a small synthetic benchmark as a general measure of real-world enterprise retrieval quality.

### 10.5 Recommendation evaluation

Report separately:

- Structural citation validity.
- Human assessment of evidence support on a labeled sample.
- Completeness of required response fields.
- Correct insufficient-evidence behavior.
- Review approval/rejection outcomes.

### 10.6 Simulated triage-time comparison

If a baseline versus assistant-assisted triage comparison is included, use the same labeled scenarios and a repeatable protocol. Report sample size, timing method, median values and limitations. Do not claim real production MTTR improvement from a synthetic exercise.

---

## 11. User experience and application surfaces

The MVP does not require a custom full-featured frontend.

| Surface | Purpose |
|---|---|
| FastAPI Swagger/OpenAPI | Explore and exercise operational APIs. |
| Metabase | View analytical dashboards and filtered reporting. |
| Seed/simulator scripts | Produce repeatable alert and incident scenarios. |
| Optional Streamlit screen | Only if a small operator walkthrough is needed after core requirements are met. |

The incident API must expose enough information to inspect an incident, its events, transitions, recommendations and reviews without requiring a custom frontend.

---

## 12. Non-functional requirements

### 12.1 Reliability and correctness

- Database constraints enforce key invariants where practical.
- Exact event replay handling is safe under concurrent requests.
- Incident correlation is deterministic and concurrency-safe.
- Invalid lifecycle transitions are rejected.
- Analytical transformations are reproducible.
- Metric definitions are explicit and reconciliation-tested.

### 12.2 Performance

- The starter demo dataset should include up to approximately 20,000 alert events.
- API list endpoints use pagination and appropriate indexes.
- Runbook search returns a bounded top-K set.
- dbt and dashboard refresh times are measured and documented on the development environment used for the demo.
- Do not claim production-scale throughput from local synthetic testing.

### 12.3 Security and privacy

- Secrets are supplied through environment variables or secret stores and never committed.
- Logs must not contain passwords, tokens, secret-bearing metadata or unrestricted request payloads.
- Use least-privilege database roles.
- Application authorization is enforced server-side.
- Approved runbooks are the only retrieval corpus.
- Generated text is untrusted and never executed.
- Audit history is append-only for the application role.

### 12.4 Maintainability

- Application code is separated into API, schema, service, repository and model concerns.
- Alembic manages operational schema changes.
- dbt manages analytical transformations.
- Python code is formatted/linted with Ruff.
- Tests are grouped into unit, integration and security suites.
- Documentation is maintained with the code.

### 12.5 Reproducibility

- A new developer can follow the README to start the application locally.
- Docker Compose provides the supported local runtime.
- Synthetic data generation is deterministic.
- CI runs code quality checks, tests and dbt build.

---

## 13. Success criteria and definition of done

The MVP is ready for portfolio presentation when all of the following are true:

1. A reviewer can start the environment using documented instructions.
2. A valid synthetic alert can be submitted through the API.
3. Replaying the same source event does not create another canonical event.
4. A distinct alert with the same fingerprint is retained and can be correlated to the same eligible active incident.
5. Incident transitions are validated and visible in the timeline.
6. Service ownership and dependencies are visible in the operational model.
7. dbt builds the documented staging, intermediate, fact, dimension and mart models.
8. Required dbt tests pass on the demo dataset.
9. Metric definitions and edge cases are documented and reconciliation-tested.
10. Metabase dashboards query curated analytical marts and reconcile to them.
11. Runbook search returns approved passages with version and passage references.
12. A mock recommendation includes validated sources or returns insufficient evidence.
13. Human approval/rejection is stored and auditable.
14. Security tests cover authorization, payload validation, secret-safe logging and non-execution of suggestions.
15. README, architecture diagrams, ERD, data dictionary, metric contracts and evaluation report are present.
16. A short recorded demo demonstrates the key workflows.

---

## 14. Delivery roadmap and dependencies

| Phase | Deliverable | Exit criteria |
|---|---|---|
| 0. Product definition | PRD, MVP scope, architecture decisions | Requirements and boundaries agreed. |
| 1. Foundation | Repo, Python app, PostgreSQL, Docker, health check | API and DB run locally. |
| 2. Operational schema | Tables, constraints, migrations, ERD | Schema is reproducible through Alembic. |
| 3. Alert and incident workflow | Ingestion, idempotency, correlation, lifecycle APIs | Duplicate and lifecycle scenarios pass tests. |
| 4. Catalog and audit | Services, teams, dependencies, timeline and audit | Operator workflow has traceable history. |
| 5. Synthetic data | Fixed-seed generator and labeled scenarios | Demo data is reproducible. |
| 6. dbt | Sources, staging, intermediate, facts, dimensions, marts | dbt build and tests pass. |
| 7. Metrics | Metric contracts and reconciliation tests | KPI definitions are consistent and verified. |
| 8. BI | Metabase dashboards | Dashboards reconcile to marts. |
| 9. Retrieval | Versioned runbooks, FTS, labeled evaluation | Retrieval report is reproducible. |
| 10. AI assistance | Provider adapter, mock, citations, fallback | Grounded and insufficient-evidence scenarios pass. |
| 11. Quality and security | Reviews, auth, logs, CI, observability | Security and CI checks pass. |
| 12. Portfolio polish | README, diagrams, report and demo | New reviewer can understand and reproduce the MVP. |

### Critical path

Foundation → Operational schema → Alert/incident workflow → Synthetic data → dbt → Metrics → Metabase → Retrieval evaluation → AI assistance → Hardening and presentation.

Do not begin the real LLM integration before the deterministic operational workflow, analytical pipeline and mock recommendation path are working.

---

## 15. Assumptions and decisions to validate during implementation

The following are MVP design defaults. They should be revisited only when implementation or evaluation reveals a concrete problem.

| Topic | MVP default | Revisit when |
|---|---|---|
| Organization model | Single organization/workspace | A genuine multi-tenant requirement is introduced. |
| Operational/analytical storage | One PostgreSQL database, separate `ops` and `analytics` schemas | Workload isolation or volume justifies a separate warehouse. |
| Alert identity | `(source, source_event_id)` | A real source lacks stable event IDs. |
| Correlation window | 15 minutes | Labeled scenarios show poor grouping. |
| Fingerprint | Stable normalized service/alert/resource attributes; excludes timestamps and volatile IDs | More source-specific fingerprinting is needed. |
| Severity | `critical > high > medium > low` | Source taxonomies require mapping changes. |
| Recurrence window | Seven days after prior matching incident resolution | Business scenarios require another window. |
| Runbook retrieval | PostgreSQL full-text search | Evaluation demonstrates a material need for semantic retrieval. |
| LLM | Mock provider required; one real provider optional | API cost, availability or quality justifies a provider. |
| UI | Swagger + Metabase | Demo usability requires a small operator screen. |
| Background jobs | Synchronous MVP workflow | Latency or workload requires asynchronous processing. |
| Multi-tenancy/RLS | Out of MVP | More than one mutually isolated customer is required. |

### 15.1 Open items that must be recorded, not guessed

- Exact local compute specifications and acceptable runtime.
- Actual LLM provider and budget, if a real provider is enabled.
- Whether authentication is completed in MVP or kept as a documented local-demo limitation.
- Exact dashboard visual design.
- Final synthetic scenario distributions after initial evaluation.
- Any benchmark thresholds chosen after the first baseline run.

---

## 16. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Scope expands into a full ITSM product | MVP misses completion | Enforce must-have/deferred scope. |
| Backend dominates the portfolio | Weak Analytics Engineer signal | Prioritize dbt, metric contracts, data tests and BI as core deliverables. |
| Poor event identity or correlation logic | Misleading incident counts | Separate exact delivery idempotency from fingerprint correlation; test both. |
| Metric definitions are ambiguous | Dashboards disagree | Maintain centralized metric contracts and reconciliation tests. |
| Synthetic data looks unrealistic | Weak demonstration | Use deterministic causal scenarios and document assumptions. |
| AI fabricates unsupported advice | Unsafe or untrustworthy output | Retrieve approved passages, validate references, show uncertainty and retain human review. |
| LLM provider is unavailable or costly | Demo is unreliable | Make the mock provider a first-class deterministic implementation. |
| Too many infrastructure tools | More setup than product value | Start with PostgreSQL, FastAPI, dbt and Metabase. |
| Vibe-coded code is hard to maintain | Debugging and integration failures | Implement small tasks with tests, diffs and explicit acceptance criteria. |

---

## 17. Recruiter-facing narrative

The project should be presented as an Analytics Engineering portfolio project supported by a realistic operational application.

Recommended narrative:

> I built OpsPilot, an IT operations analytics platform that ingests and correlates synthetic alert events, preserves incident lifecycle history, and transforms operational records through dbt into tested dimensional models and governed metrics. I connected curated marts to Metabase dashboards and added a mock-first, evidence-grounded runbook assistant with source validation and human review. The project demonstrates data modeling, SQL transformations, metric governance, data quality, API design and safe AI integration.

The narrative must be updated to match what is actually implemented and measured. Do not claim deferred capabilities as completed.

---

## Appendix A — Suggested repository documentation

- `README.md`
- `docs/product/PRD.md`
- `docs/architecture/TAD.md`
- `docs/architecture/ERD.md`
- `docs/architecture/decisions/`
- `docs/data/data-dictionary.md`
- `docs/metrics/metric-definitions.md`
- `docs/evaluation/retrieval-evaluation.md`
- `docs/evaluation/recommendation-evaluation.md`
- `docs/evaluation/data-quality-report.md`
- `docs/demo/demo-script.md`

