# FACT/JACIE Inspector Checklist

> What an inspector verifies during a FACT/JACIE accreditation visit.
> Use this to validate that the audit trail is inspection-ready.

---

## 1. Traceability Walk-Through

The inspector selects a random DIN and traces it through the **entire lifecycle**:

```
Query: GET /audit?din={DIN}&limit=1000

Expected: Chronological list of ALL events for that DIN with NO GAPS.
```

### What They Check

| Check | Pass Criteria | How to Verify |
|-------|--------------|---------------|
| Receipt documented | `DIN_REGISTERED` exists with timestamp | Filter by action_type |
| Condition on receipt | `PRODUCT_CONDITION_CHECKED` exists with temperature, packaging fields | Check `details` payload |
| Testing ordered | `LAB_ORDER_SENT` exists with test codes | Verify LOINC codes match product type |
| Results received | `RESULTS_RECEIVED` for each ordered test | Count results vs orders |
| Release authorized | `PRODUCT_RELEASED` with `authorized_by` | Verify different actor than EIS |
| Release criteria | `RELEASE_CRITERIA_CHECKED` with all criteria met | Check `all_met: true` |
| Bedside verification | `EIS_VERIFIED` with product-patient match | Verify `product_match: true` |
| Infusion documented | `ADMINISTRATION_STARTED` + `ADMINISTRATION_COMPLETED` | Both must exist |
| **No gaps in timestamps** | Events are in chronological order | Sort by timestamp, no unexplained jumps |

### Red Flags (Automatic Deficiency)

- Missing events between receipt and administration
- `PRODUCT_RELEASED` without preceding `RELEASE_CRITERIA_CHECKED`
- `EIS_VERIFIED` and `PRODUCT_RELEASED` by the same actor (two-person rule violation)
- Timestamps out of order or backdated
- `ADMINISTRATION_STARTED` without `ADMINISTRATION_COMPLETED` (unless `ADVERSE_EVENT`)

---

## 2. Concurrent Recording

Inspectors verify that events were logged **in real-time**, not retroactively.

| Check | Pass Criteria |
|-------|--------------|
| Timestamp accuracy | `timestamp` is within seconds of the actual event |
| No batch insertions | Events have distinct timestamps (not all at once) |
| System clock sync | All timestamps use UTC or consistent timezone |

### Implementation Note

The current system uses `DEFAULT now()` at insertion time. This is acceptable as long as:
- Events are emitted synchronously from the node that performs the action
- The `timestamp` field reflects insertion time (which equals action time for synchronous writes)
- For async emission, the actual event time should be passed explicitly

---

## 3. Two-Person Verification

FACT/JACIE requires independent verification for critical steps.

| Critical Step | Requirement | How to Verify |
|--------------|-------------|---------------|
| **Product release** | Authorized by a qualified person (MD/DO) | `PRODUCT_RELEASED.details.authorized_by` is a credentialed person |
| **Bedside verification** | Different person than release authorizer | `EIS_VERIFIED.details.verified_by` != `PRODUCT_RELEASED.details.authorized_by` |
| **Config changes** | Two-signer approval | `CONFIG_PROPOSED.details.proposed_by` != `CONFIG_ACTIVATED.details.activated_by` |

---

## 4. Deviation Management

Every deviation from standard procedure must be documented.

| Deviation Type | Expected Events | Details Fields |
|---------------|----------------|----------------|
| Out-of-range result | `CLINICAL_ESCALATION` → `CLINICAL_ALERT_DRAFTED` → `ESCALATION_RESOLVED` | `test_code`, `result_value`, `threshold`, `resolution` |
| Failed lab order | `LAB_ORDER_RETRY` (1-3x) → `LAB_ORDER_ESCALATED` | `attempt_number`, `error`, `escalation_reason` |
| EIS verification hold | `EIS_HOLD` → (resolution) → `EIS_VERIFIED` or `EIS_REJECTED` | `reason`, `held_by` |
| Adverse event | `ADVERSE_EVENT` | `severity`, `symptoms`, `actions_taken` |
| Product condition failure | `PRODUCT_CONDITION_CHECKED` (outcome=failure) | `rejection_reason`, `temperature_celsius` |

### Inspector Expectation

For EVERY escalation, there MUST be a corresponding resolution:
- `CLINICAL_ESCALATION` → `ESCALATION_RESOLVED`
- `EIS_HOLD` → `EIS_VERIFIED` or `EIS_REJECTED`
- Unresolved escalations are a **deficiency**

---

## 5. Chain Integrity

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| Hash chain valid | `GET /audit/verify` or `verify_chain()` | `chain_valid: true`, `breaks: []` |
| No modified records | Database triggers prevent UPDATE/DELETE | Trigger functions active |
| Immutability | Attempt UPDATE on audit.audit_events | Must fail with "audit_events are immutable" |
| RBAC | `audit_writer` role check | Only INSERT + SELECT granted |

---

## 6. Record Retention

| Requirement | Source | Verification |
|-------------|--------|-------------|
| 10 years from administration | FDA 21 CFR 1271.55 | `retention_expiry = ADMINISTRATION_COMPLETED.timestamp + 10 years` |
| 10 years from disposition (if not administered) | FDA 21 CFR 1271.55 | `retention_expiry = PRODUCT_DISPOSED.timestamp + 10 years` or `CASE_VOIDED.timestamp + 10 years` |
| Accessible throughout period | FACT/JACIE | Records queryable via GET /audit at any time |
| Data integrity maintained | FACT/JACIE | Hash chain verification throughout retention |

---

## 7. Common Deficiencies (from Published JACIE Reports)

These are the most frequently cited deficiencies in FACT/JACIE inspections:

| Rank | Deficiency | Our Mitigation |
|------|-----------|----------------|
| 1 | Incomplete traceability records | Complete 34-event chain with no gaps |
| 2 | Missing signatures/responsible person | `actor` field on every event |
| 3 | Failure to document deviations | `CLINICAL_ESCALATION` + `ESCALATION_RESOLVED` pair |
| 4 | Inadequate review of quality indicators | `RELEASE_CRITERIA_CHECKED` with criteria list |
| 5 | Missing competency assessments | Outside system scope (handled by HR/QM system) |

---

## 8. Lifecycle Report Query

An inspector will request: _"Show me the complete history for DIN W1234260001234."_

The system should return (via `GET /audit?din=W1234260001234`):

```
seq  timestamp                    action_type                 actor              outcome
---  --------------------------  -------------------------   ----------------   --------
1    2026-03-15T08:00:00Z        NMDP_DOCUMENT_RECEIVED      system             success
2    2026-03-15T08:00:05Z        NMDP_DOCUMENT_EXTRACTED     system             success
3    2026-03-15T08:15:00Z        NMDP_DOCUMENT_CONFIRMED     j.smith@lsu.edu    success
4    2026-03-15T08:20:00Z        PRODUCT_CONDITION_CHECKED   j.smith@lsu.edu    success
5    2026-03-15T08:20:30Z        DIN_REGISTERED              system             success
6    2026-03-15T08:20:31Z        DONOR_CREATED               system             success
7    2026-03-15T08:20:32Z        LINK_CREATED                system             success
8    2026-03-15T08:21:00Z        LAB_ORDER_SENT              system             success
9    2026-03-15T08:21:05Z        LAB_ORDER_ACK               system             success
10   2026-03-15T10:30:00Z        RESULTS_RECEIVED            system             success
11   2026-03-15T10:30:01Z        RESULTS_VALIDATED           system             success
12   2026-03-15T10:35:00Z        RELEASE_CRITERIA_CHECKED    system             success
13   2026-03-15T10:40:00Z        PRODUCT_RELEASED            dr.jones@lsu.edu   success
14   2026-03-15T11:00:00Z        EIS_VERIFIED                nurse.k@lsu.edu    success
15   2026-03-15T11:05:00Z        ADMINISTRATION_STARTED      nurse.k@lsu.edu    success
16   2026-03-15T11:45:00Z        ADMINISTRATION_COMPLETED    nurse.k@lsu.edu    success
```

This represents the **gold standard** — no gaps, chronological, different actors for release vs administration.
