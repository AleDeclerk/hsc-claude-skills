---
name: fact-jacie-audit
description: >
  Generate, validate, and verify FACT/JACIE-compliant audit events that cover the
  complete chain of custody for hematopoietic stem cell products (receipt through
  infusion/disposal). Use this skill whenever the user works on audit event emission,
  chain of custody tracking, compliance verification, inspection preparation,
  record retention policies, quality management, or any code that touches
  audit.audit_events, AuditActionType, emit_event(), write_audit_event(), or
  verify_chain(). Also trigger when the user mentions "FACT", "JACIE", "audit trail",
  "chain of custody", "traceability", "inspection readiness", "accreditation",
  "quality audit", "record retention", "10-year retention", "FDA 21 CFR 1271",
  "adverse event", "deviation", "nonconformance", "CAPA", or "inspector".
  Watch for missing events in the chain (receipt → testing → release → infusion),
  schema CHECK constraint mismatches, and incomplete details payloads.
---

# FACT/JACIE Audit Trail Skill

Generate audit events that satisfy FACT-JACIE International Standards (9th Edition) and FDA 21 CFR 1271.55 for HCT/P chain of custody traceability.

## Regulatory Framework

| Standard | Requirement |
|----------|------------|
| **FACT-JACIE 9th Ed** | Complete chain of custody from receipt → administration/disposal |
| **FDA 21 CFR 1271.55** | Records retained **10 years** from administration (or disposition/expiration) |
| **"Shall"** = mandatory for accreditation | **"Should"** = recommended best practice |

## Chain of Custody — Complete Event Lifecycle

An inspector expects to trace **every product** through these phases with **no gaps**:

```
RECEIPT ──→ TESTING ──→ RELEASE ──→ ADMINISTRATION ──→ CLOSE
  │            │           │              │               │
  ├ NMDP_DOCUMENT_RECEIVED  ├ LAB_ORDER_SENT   ├ RELEASE_CRITERIA_CHECKED  ├ ADMINISTRATION_STARTED   ├ PRODUCT_DISPOSED
  ├ NMDP_DOCUMENT_EXTRACTED ├ LAB_ORDER_ACK    ├ PRODUCT_RELEASED         ├ ADMINISTRATION_COMPLETED ├ CASE_VOIDED
  ├ NMDP_DOCUMENT_CONFIRMED ├ RESULTS_RECEIVED ├ PRODUCT_REJECTED         ├ ADVERSE_EVENT
  ├ DIN_REGISTERED          ├ RESULTS_VALIDATED
  ├ DONOR_CREATED           ├ RESULTS_DUPLICATE
  ├ LINK_CREATED            ├ CLINICAL_ESCALATION
  ├ PRODUCT_CONDITION_CHECKED├ ESCALATION_RESOLVED
  │                         ├ CLINICAL_ALERT_DRAFTED
  │                         ├ CLINICAL_ALERT_APPROVED
```

## Mandatory Event Reference (34 Total)

See `references/chain_of_custody.md` for the complete table with:
- All 34 action_types (24 existing + 10 missing)
- Required `details` payload fields per event
- `resource_type` and expected `outcome` values
- FACT/JACIE standard section references
- Priority classification (HIGH/MEDIUM)

## Current Codebase State

### Existing Events (24) — in CHECK constraint
`DIN_REGISTERED`, `DONOR_CREATED`, `LINK_CREATED`, `LINK_ACCESSED`,
`LAB_ORDER_SENT`, `LAB_ORDER_ACK`, `LAB_ORDER_RETRY`, `LAB_ORDER_ESCALATED`,
`RESULTS_RECEIVED`, `RESULTS_DUPLICATE`, `CLINICAL_ESCALATION`,
`ESCALATION_RESOLVED`, `PRODUCT_RELEASED`, `PRODUCT_REJECTED`,
`EIS_VERIFIED`, `EIS_REJECTED`, `EIS_HOLD`, `CASE_VOIDED`,
`NMDP_DOCS_INGESTED`, `NMDP_MANUAL_REVIEW`, `CLINICAL_ALERT_DRAFTED`,
`CLINICAL_ALERT_APPROVED`, `CONFIG_PROPOSED`, `CONFIG_ACTIVATED`,
`SYSTEM_UNAVAILABLE`, `SYSTEM_RESTORED`

### Missing Events (10) — MUST be added for FACT/JACIE compliance
| Event | Phase | Priority | Why |
|-------|-------|----------|-----|
| `NMDP_DOCUMENT_RECEIVED` | Receipt | HIGH | Inspector checks document receipt timestamp |
| `NMDP_DOCUMENT_EXTRACTED` | Receipt | MEDIUM | AI extraction is a processing step |
| `NMDP_DOCUMENT_CONFIRMED` | Receipt | HIGH | Human review of AI extraction is critical |
| `PRODUCT_CONDITION_CHECKED` | Receipt | HIGH | Inspector specifically verifies condition-on-receipt |
| `RESULTS_VALIDATED` | Testing | MEDIUM | Distinct from RESULTS_RECEIVED — explicit validation step |
| `RELEASE_CRITERIA_CHECKED` | Release | HIGH | Pre-release checklist must be documented |
| `ADMINISTRATION_STARTED` | Admin | HIGH | Infusion start is distinct from EIS verification |
| `ADMINISTRATION_COMPLETED` | Admin | HIGH | Infusion end required for traceability |
| `ADVERSE_EVENT` | Admin | HIGH | Mandatory adverse event reporting |
| `PRODUCT_DISPOSED` | Close | MEDIUM | Required when product is not administered |

### Known Bugs
See `references/known_bugs.md` for:
- `PHYSICAL_INSPECTION_FAILED` emitted but NOT in CHECK constraint
- `NMDP_DOCS_INGESTED` / `NMDP_MANUAL_REVIEW` should be renamed for clarity
- Incomplete `details` payloads missing inspector-required fields

## Audit Record Requirements

Every audit event **SHALL** include (per FACT-JACIE Standards §Records):

| Field | Maps To | Rule |
|-------|---------|------|
| Date/time | `timestamp` | Concurrent with event (not retroactive) |
| Responsible person | `actor` | Email or system identifier |
| Product identifier | `resource_id` | DIN (ISBT-128) |
| Action description | `action_type` | From the 34 allowed values |
| Outcome | `outcome` | `success`, `failure`, `escalated`, `blocked` |
| Action-specific data | `details` (JSONB) | Varies per event — see reference |

**Immutability rules** (already implemented):
- Records are append-only (INSERT triggers block UPDATE/DELETE/TRUNCATE)
- SHA-256 chained hashes provide tamper evidence
- `audit_writer` role has INSERT + SELECT only

## What an Inspector Checks

See `references/inspector_checklist.md` for the full checklist. Key areas:

1. **No gaps** — Every DIN has a complete lifecycle from receipt to outcome
2. **Concurrent timestamps** — Events logged in real-time, not backdated
3. **Two-person verification** — Release and bedside verification by different actors
4. **Deviations documented** — Every out-of-range result has escalation + resolution
5. **Chain integrity** — `verify_chain()` returns `chain_valid: true`
6. **10-year retention** — Records accessible for the full FDA-required period

## Key File Paths

| File | Purpose |
|------|---------|
| `src/agents/audit/listener.py` | `emit_event()` — primary audit entrypoint |
| `src/agents/audit/writer.py` | `write_audit_event()` + SHA-256 hash computation |
| `src/agents/audit/verifier.py` | `verify_chain()` — chain integrity check |
| `src/models/audit_event.py` | `AuditEvent` Pydantic model |
| `src/api/audit.py` | GET /audit query endpoint |
| `src/db/migrations/versions/0002_create_audit_schema.py` | Schema + CHECK constraint |
| `tests/unit/agents/test_audit_writer.py` | Writer unit tests |

## Rules

1. **NEVER** skip an audit event — every state transition MUST emit
2. **NEVER** emit an action_type not in the CHECK constraint — add it to the migration first
3. **ALWAYS** include the required `details` fields for each event type (see reference)
4. **ALWAYS** use `resource_type='din'` for product events, `'system'` for system events
5. **ALWAYS** capture `actor` as the person performing the action, not the system
6. **NEVER** put MRN in `details` — use `mrn_hash` (SHA-256) for LINK_* events only
7. **Timestamps** must reflect when the event actually occurred, not when it was written
8. When adding new events: update CHECK constraint in migration, emit in node, add test
