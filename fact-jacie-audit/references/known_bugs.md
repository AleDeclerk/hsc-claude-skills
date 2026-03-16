# Known Bugs & Gaps — FACT/JACIE Audit Compliance

> Issues found by comparing the current codebase against FACT/JACIE requirements.
> Each bug includes the file, the problem, and the fix.

---

## Bug 1: PHYSICAL_INSPECTION_FAILED Not in CHECK Constraint

**Severity:** HIGH — Runtime INSERT will fail with CHECK constraint violation
**File:** `src/agents/orchestration/nodes/results.py`
**Schema:** `src/db/migrations/versions/0002_create_audit_schema.py`

### Problem

`results.py` emits `PHYSICAL_INSPECTION_FAILED` but this action_type is NOT in the CHECK constraint:

```python
# results.py (current — emits invalid action_type)
await emit_event(
    actor="system",
    action_type="PHYSICAL_INSPECTION_FAILED",  # NOT IN CHECK CONSTRAINT
    resource_type="din",
    resource_id=state["din"],
    outcome="failure",
    details={...},
)
```

### Fix

**Option A (Recommended):** Replace with `PRODUCT_CONDITION_CHECKED` (outcome=failure) — aligns with FACT/JACIE terminology and the new event we're adding anyway.

```python
# results.py (fixed)
await emit_event(
    actor="system",
    action_type="PRODUCT_CONDITION_CHECKED",
    resource_type="din",
    resource_id=state["din"],
    outcome="failure",
    details={
        "temperature_celsius": state.get("temperature"),
        "packaging_intact": False,
        "seal_intact": state.get("seal_intact"),
        "visual_appearance": state.get("visual_appearance"),
        "accepted": False,
        "rejection_reason": state.get("rejection_reason", "Physical inspection failed"),
    },
)
```

**Option B:** Add `PHYSICAL_INSPECTION_FAILED` to the CHECK constraint. Less preferred because it creates a non-standard event name that doesn't map to FACT/JACIE terminology.

### Test

```python
def test_physical_inspection_emits_product_condition_checked():
    """PRODUCT_CONDITION_CHECKED with outcome=failure replaces PHYSICAL_INSPECTION_FAILED."""
    # Verify the action_type is PRODUCT_CONDITION_CHECKED, not PHYSICAL_INSPECTION_FAILED
    # Verify outcome is "failure"
    # Verify details include rejection_reason
```

---

## Bug 2: NMDP Event Naming Inconsistency

**Severity:** MEDIUM — Not a runtime error but confusing for inspectors and developers
**Files:** `src/api/nmdp.py`, `src/db/migrations/versions/0002_create_audit_schema.py`

### Problem

Current names don't clearly map to the FACT/JACIE chain of custody phases:
- `NMDP_DOCS_INGESTED` — ambiguous (ingested by whom? the AI? the system?)
- `NMDP_MANUAL_REVIEW` — ambiguous (review requested? review completed?)

### Recommended Mapping

| Current | Proposed Replacement | Rationale |
|---------|---------------------|-----------|
| `NMDP_DOCS_INGESTED` | `NMDP_DOCUMENT_EXTRACTED` | Clarifies that AI extraction completed |
| `NMDP_MANUAL_REVIEW` | `NMDP_DOCUMENT_CONFIRMED` | Clarifies that human confirmed the extraction |

Plus add `NMDP_DOCUMENT_RECEIVED` as a new event for the moment the PDF arrives (before extraction).

### Migration Strategy

Since audit events are immutable, existing records with old names cannot be updated. Options:
1. **New migration** that adds new names to CHECK constraint while keeping old ones (backward compatible)
2. Document the mapping in the codebase so queries can handle both old and new names
3. Future queries should use `action_type IN ('NMDP_DOCS_INGESTED', 'NMDP_DOCUMENT_EXTRACTED')` for the extraction step

---

## Bug 3: Missing `details` Fields

**Severity:** MEDIUM — Events are emitted but with insufficient information for inspectors
**Files:** Multiple node files

### Problem

Several existing events emit minimal `details` payloads that don't include fields an inspector would expect.

### Specific Gaps

| Event | Current `details` | Missing Fields |
|-------|------------------|----------------|
| `DIN_REGISTERED` | `{"din": "..."}` | `product_type`, `collection_date` |
| `LAB_ORDER_SENT` | `{"order_id": "..."}` | `test_codes` (list of LOINC), `destination` |
| `RESULTS_RECEIVED` | `{"test_code": "...", "value": "..."}` | `units`, `reference_range`, `interpretation` |
| `PRODUCT_RELEASED` | `{"authorized_by": "..."}` | `role`, `basis` (criteria list) |
| `EIS_VERIFIED` | `{"verified_by": "..."}` | `patient_id_method`, `product_match` |
| `CASE_VOIDED` | `{"reason": "..."}` | `voided_by`, `authorization` |

### Fix Pattern

Each node's `emit_event()` call should be enriched. Example for `PRODUCT_RELEASED`:

```python
# Before (insufficient)
await emit_event(
    actor=state["releasing_physician"],
    action_type="PRODUCT_RELEASED",
    resource_type="din",
    resource_id=state["din"],
    outcome="success",
    details={"authorized_by": state["releasing_physician"]},
)

# After (FACT/JACIE compliant)
await emit_event(
    actor=state["releasing_physician"],
    action_type="PRODUCT_RELEASED",
    resource_type="din",
    resource_id=state["din"],
    outcome="success",
    details={
        "authorized_by": state["releasing_physician"],
        "role": "MD",
        "basis": [
            {"criterion": "all_tests_complete", "met": True},
            {"criterion": "no_unresolved_escalations", "met": True},
            {"criterion": "eis_data_matches", "met": True},
        ],
    },
)
```

---

## Bug 4: 10 Missing Events in CHECK Constraint

**Severity:** HIGH — Cannot emit these events until migration is updated
**File:** `src/db/migrations/versions/0002_create_audit_schema.py`

### Problem

The CHECK constraint only allows 24 action_types. The following 10 must be added:

```sql
'NMDP_DOCUMENT_RECEIVED',
'NMDP_DOCUMENT_EXTRACTED',
'NMDP_DOCUMENT_CONFIRMED',
'PRODUCT_CONDITION_CHECKED',
'RESULTS_VALIDATED',
'RELEASE_CRITERIA_CHECKED',
'ADMINISTRATION_STARTED',
'ADMINISTRATION_COMPLETED',
'ADVERSE_EVENT',
'PRODUCT_DISPOSED'
```

### Fix

Create new Alembic migration `0005_add_fact_jacie_audit_events.py` (or next sequential number):

```python
"""Add FACT/JACIE chain of custody audit events."""

def upgrade():
    op.execute("""
        ALTER TABLE audit.audit_events
        DROP CONSTRAINT IF EXISTS audit_events_action_type_check;

        ALTER TABLE audit.audit_events
        ADD CONSTRAINT audit_events_action_type_check
        CHECK (action_type IN (
            -- Existing (24)
            'DIN_REGISTERED', 'DONOR_CREATED', 'LINK_CREATED', 'LINK_ACCESSED',
            'LAB_ORDER_SENT', 'LAB_ORDER_ACK', 'LAB_ORDER_RETRY', 'LAB_ORDER_ESCALATED',
            'RESULTS_RECEIVED', 'RESULTS_DUPLICATE',
            'CLINICAL_ESCALATION', 'ESCALATION_RESOLVED',
            'PRODUCT_RELEASED', 'PRODUCT_REJECTED',
            'EIS_VERIFIED', 'EIS_REJECTED', 'EIS_HOLD',
            'CASE_VOIDED',
            'NMDP_DOCS_INGESTED', 'NMDP_MANUAL_REVIEW',
            'CLINICAL_ALERT_DRAFTED', 'CLINICAL_ALERT_APPROVED',
            'CONFIG_PROPOSED', 'CONFIG_ACTIVATED',
            'SYSTEM_UNAVAILABLE', 'SYSTEM_RESTORED',
            -- New FACT/JACIE events (10)
            'NMDP_DOCUMENT_RECEIVED',
            'NMDP_DOCUMENT_EXTRACTED',
            'NMDP_DOCUMENT_CONFIRMED',
            'PRODUCT_CONDITION_CHECKED',
            'RESULTS_VALIDATED',
            'RELEASE_CRITERIA_CHECKED',
            'ADMINISTRATION_STARTED',
            'ADMINISTRATION_COMPLETED',
            'ADVERSE_EVENT',
            'PRODUCT_DISPOSED'
        ));
    """)

def downgrade():
    # Restore original constraint (without new events)
    ...
```

---

## Bug 5: Unused Action Types

**Severity:** LOW — Not a bug but indicates incomplete implementation
**File:** `src/db/migrations/versions/0002_create_audit_schema.py`

### Problem

Two action_types are defined in the CHECK constraint but never emitted:
- `LAB_ORDER_RETRY` — defined but no retry logic emits it
- `LINK_ACCESSED` — defined but link access doesn't emit it

### Fix

These should be emitted when the corresponding actions occur:
- `LAB_ORDER_RETRY`: Emit in the retry handler when a failed lab order is retried
- `LINK_ACCESSED`: Emit when `get_mrn_by_din()` or equivalent is called

---

## Summary: Implementation Priority

| Priority | Bug | Effort |
|----------|-----|--------|
| **P0** | Bug 4: Add 10 events to CHECK constraint (migration) | Small — SQL only |
| **P0** | Bug 1: Fix PHYSICAL_INSPECTION_FAILED → PRODUCT_CONDITION_CHECKED | Small — rename + enrich details |
| **P1** | Bug 3: Enrich `details` payloads across all nodes | Medium — touch each node file |
| **P2** | Bug 2: NMDP event naming (backward-compatible addition) | Small — add new names, keep old |
| **P3** | Bug 5: Emit unused action types | Small — add emit calls |
