# ADR-003: Deterministic PostgreSQL Full-Text Search Retrieval over Vector/Embedding Infrastructure

**Status:** Accepted  
**Date:** 2026-11-11  

## Context
AI-assisted triage requires retrieving relevant troubleshooting runbook passages for an incident. While embedding-based dense retrieval (vector search using `pgvector` or external vector DBs) is popular, it adds external dependencies, non-deterministic embedding generation, vector indexing complexity, and opaque similarity scores that are difficult to debug and evaluate on structured technical documents without a demonstrated need.

## Decision
For the MVP, runbook passage retrieval is implemented using native PostgreSQL Full-Text Search (FTS) with:
1. Generated `tsvector` columns on Markdown runbook passages (`heading` + `passage_text`).
2. GIN indexing for fast search.
3. `websearch_to_tsquery` parsing for user and system search terms.
4. Deterministic scoring via `ts_rank` with service-specific weighting boost (`(runbook.service_id = :service_id) DESC`).
5. A strict filter requiring `runbook_versions.approval_status = 'approved'`. Draft and retired versions are never searched.
6. A labeled benchmark suite of 30-50 incident queries evaluated with Precision@K, Recall@K, and MRR.

Dense vector retrieval is deferred until keyword retrieval deficiencies are empirically measured and justified.

## Alternatives Considered
- `pgvector` extension: Requires custom PostgreSQL builds/extensions, embedding model inference overhead, and API keys.
- Standalone Vector Store (Chroma/Qdrant): Adds external service dependencies and network boundaries for a single-node local demo.

## Consequences
- **Positive:** Zero external dependencies, 100% deterministic local evaluation, transparent keyword match explanation, native transactional consistency.
- **Trade-off:** Synonyms or vocabulary mismatches require domain-specific terminology in queries or runbooks.

## Validation
Evaluated using `scripts/evaluation/evaluate_retrieval.py` on labeled incident queries.
