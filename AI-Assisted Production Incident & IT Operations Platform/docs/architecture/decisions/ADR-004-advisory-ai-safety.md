# ADR-004: Advisory-Only AI Architecture with Immutable Runbook Grounding and Zero Execution Pathway

**Status:** Accepted  
**Date:** 2026-11-11  

## Context
OpsPilot integrates AI to assist on-call engineers with incident triage. Uncontrolled LLM integrations risk hallucinations, prompt injections, fabricated root causes, and accidental production damage if recommendations are coupled to automated execution tools (e.g. bash scripts, automated restarts, database mutations).

## Decision
We enforce strict architectural boundaries:
1. **Advisory Only:** Generated suggestions are strictly informational guidance presented as hypotheses (`possible_contributors`) and inspection steps (`suggested_checks`). OpsPilot provides ZERO automated execution tools, shell execution pathways, database mutation hooks, or autonomous remediation agents.
2. **Pre-Retrieval Grounding:** Runbook passages are retrieved server-side from approved runbook versions before recommendation generation. Callers cannot supply arbitrary text as trusted evidence.
3. **Citation Validation:** Every cited passage ID is structurally validated against:
   - Existence in `ops.runbook_passages`
   - Membership in the declared `runbook_version_id`
   - Version status being `approved`
   - Membership in the exact candidate set retrieved for the incident
4. **Insufficient Evidence Fallback:** If retrieval returns no relevant approved passages, or if evidence is insufficient, the system returns `insufficient_evidence: true` with zero invented citations and an explicit explanation of limitations.
5. **Human Review Gate:** Every recommendation requires human review (`approved` or `rejected` with notes). A recommendation can be reviewed at most once.

## Alternatives Considered
- Autonomous Remediation Agent: Unsafe for production operations; violates core safety guidelines.
- Unconstrained LLM Generation: High risk of hallucinated commands and non-existent procedures.

## Consequences
- **Positive:** Complete safety, provable grounding, clear human accountability, zero risk of autonomous production outages.
- **Trade-off:** Engineers must manually execute recommended checks in their operational tools.

## Validation
Verified via `tests/security/test_safety_boundaries.py` and `tests/unit/test_citation_validation.py`.
