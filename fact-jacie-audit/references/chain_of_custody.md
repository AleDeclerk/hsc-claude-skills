# FACT/JACIE Chain of Custody — Complete Event Reference

> 34 audit events covering the full product lifecycle from receipt to close.
> Events marked **NEW** are missing from the current codebase and must be added.

---

## Phase 1: RECEIPT

Events from product arrival through registration.

| # | action_type | Status | resource_type | outcome | Required `details` Fields | FACT/JACIE Ref |
|---|-------------|--------|---------------|---------|---------------------------|----------------|
| 1 | `NMDP_DOCUMENT_RECEIVED` | **NEW** | din | success | `document_type`, `sender`, `page_count`, `received_method` (fax/upload/email) | §Records — receipt of accompanying documentation |
| 2 | `NMDP_DOCUMENT_EXTRACTED` | **NEW** | din | success/failure | `extraction_method` ("claude-sonnet"), `fields_extracted` (list), `confidence_scores` | §Processing — documentation of each step |
| 3 | `NMDP_DOCUMENT_CONFIRMED` | **NEW** | din | success/failure | `reviewer` (person who confirmed), `fields_confirmed` (list), `discrepancies` (list or null) | §QM — human review of automated processes |
| 4 | `NMDP_DOCS_INGESTED` | Exists | din | success | `document_type`, `field_count`, `extraction_method` | Already emitted in `src/api/nmdp.py` |
| 5 | `NMDP_MANUAL_REVIEW` | Exists | din | success | `reason`, `fields_flagged` | Already emitted in `src/api/nmdp.py` |
| 6 | `PRODUCT_CONDITION_CHECKED` | **NEW** | din | success/failure | `temperature_celsius`, `packaging_intact` (bool), `seal_intact` (bool), `visual_appearance`, `accepted` (bool), `rejection_reason` (if rejected) | §C4 — condition on receipt SHALL be documented |
| 7 | `DIN_REGISTERED` | Exists | din | success | `din`, `product_type`, `collection_date` | §Traceability — unique product identifier |
| 8 | `DONOR_CREATED` | Exists | donor_id | success | `donor_id` | §Records — donor record |
| 9 | `LINK_CREATED` | Exists | din | success | `donor_id` (+ `mrn_hash` field) | §Traceability — donor-product linkage |
| 10 | `LINK_ACCESSED` | Exists | din | success | `accessor`, `purpose` | Privacy audit — MRN access tracking |

---

## Phase 2: TESTING

Events from lab order through result interpretation.

| # | action_type | Status | resource_type | outcome | Required `details` Fields | FACT/JACIE Ref |
|---|-------------|--------|---------------|---------|---------------------------|----------------|
| 11 | `LAB_ORDER_SENT` | Exists | din | success | `order_id`, `test_codes` (list of LOINC), `destination` | §Testing — each test ordered |
| 12 | `LAB_ORDER_ACK` | Exists | din | success | `order_id`, `ack_code` | §Testing — order confirmation |
| 13 | `LAB_ORDER_RETRY` | Exists | din | failure | `order_id`, `attempt_number`, `error` | §Deviations — failed orders |
| 14 | `LAB_ORDER_ESCALATED` | Exists | din | escalated | `order_id`, `attempts`, `escalation_reason` | §Deviations — permanent failure |
| 15 | `RESULTS_RECEIVED` | Exists | din | success | `test_code`, `result_value`, `units`, `reference_range`, `interpretation` | §Testing — results with interpretation |
| 16 | `RESULTS_VALIDATED` | **NEW** | din | success/failure | `test_code`, `result_value`, `validation_rules_applied` (list), `passed` (bool), `validator` (person or "system") | §QM — explicit validation distinct from receipt |
| 17 | `RESULTS_DUPLICATE` | Exists | din | success | `test_code`, `original_message_id`, `duplicate_message_id` | §Records — duplicate handling |
| 18 | `CLINICAL_ESCALATION` | Exists | din | escalated | `test_code`, `result_value`, `threshold`, `direction` ("above"/"below") | §Deviations — nonconformance |
| 19 | `CLINICAL_ALERT_DRAFTED` | Exists | din | success | `alert_summary`, `model_used` | §QM — alert documentation |
| 20 | `CLINICAL_ALERT_APPROVED` | Exists | din | success | `approver`, `alert_id` | §QM — clinician review |
| 21 | `ESCALATION_RESOLVED` | Exists | din | success | `resolution`, `resolved_by`, `action_taken` | §Deviations — resolution documentation |

---

## Phase 3: RELEASE

Events from pre-release criteria check through authorization.

| # | action_type | Status | resource_type | outcome | Required `details` Fields | FACT/JACIE Ref |
|---|-------------|--------|---------------|---------|---------------------------|----------------|
| 22 | `RELEASE_CRITERIA_CHECKED` | **NEW** | din | success/failure | `criteria` (list of {name, met: bool}), `all_met` (bool), `checker` (person or "system") | §Release — criteria verification SHALL be documented |
| 23 | `PRODUCT_RELEASED` | Exists | din | success | `authorized_by`, `role`, `basis` (list of criteria met) | §Release — two-person authorization |
| 24 | `PRODUCT_REJECTED` | Exists | din | success | `rejected_by`, `reason`, `disposition` | §Release — rejection decision |

---

## Phase 4: ADMINISTRATION (Bedside)

Events from EIS verification through infusion completion.

| # | action_type | Status | resource_type | outcome | Required `details` Fields | FACT/JACIE Ref |
|---|-------------|--------|---------------|---------|---------------------------|----------------|
| 25 | `EIS_VERIFIED` | Exists | din | success | `verified_by`, `patient_id_method`, `product_match` (bool) | §Admin — product-patient matching |
| 26 | `EIS_HOLD` | Exists | din | blocked | `reason`, `held_by` | §Admin — verification hold |
| 27 | `EIS_REJECTED` | Exists | din | blocked | `reason`, `rejected_by` | §Admin — verification rejection |
| 28 | `ADMINISTRATION_STARTED` | **NEW** | din | success | `administered_by`, `start_time` (ISO 8601), `route`, `location` | §Admin — infusion start is distinct from verification |
| 29 | `ADMINISTRATION_COMPLETED` | **NEW** | din | success | `administered_by`, `end_time` (ISO 8601), `volume_infused_ml`, `complications` (list or null) | §Admin — infusion completion |
| 30 | `ADVERSE_EVENT` | **NEW** | din | failure | `event_type` (e.g. "transfusion_reaction"), `severity` ("mild"/"moderate"/"severe"/"fatal"), `onset_time`, `symptoms` (list), `actions_taken` (list), `reported_by` | §AE — mandatory adverse event reporting |

---

## Phase 5: CLOSE

Events for product disposition and case closure.

| # | action_type | Status | resource_type | outcome | Required `details` Fields | FACT/JACIE Ref |
|---|-------------|--------|---------------|---------|---------------------------|----------------|
| 31 | `PRODUCT_DISPOSED` | **NEW** | din | success | `disposal_method`, `disposal_reason`, `authorized_by`, `witness` | §Disposal — documented destruction |
| 32 | `CASE_VOIDED` | Exists | din | success | `reason`, `voided_by` | §Records — case voiding |

---

## Phase: SYSTEM (Cross-cutting)

| # | action_type | Status | resource_type | outcome | Required `details` Fields | FACT/JACIE Ref |
|---|-------------|--------|---------------|---------|---------------------------|----------------|
| 33 | `CONFIG_PROPOSED` | Exists | config | success | `config_version`, `proposed_by`, `changes` | §QM — config change control |
| 34 | `CONFIG_ACTIVATED` | Exists | config | success | `config_version`, `activated_by`, `second_signer` | §QM — two-person config approval |
| 35 | `SYSTEM_UNAVAILABLE` | Exists | system | failure | `component`, `reason`, `impact` | §QM — system downtime |
| 36 | `SYSTEM_RESTORED` | Exists | system | success | `component`, `downtime_minutes` | §QM — system recovery |

---

## Event Naming Conventions

| Convention | Example | Rule |
|-----------|---------|------|
| Noun_Verb (past participle) | `PRODUCT_RELEASED` | Standard for completed actions |
| System prefix | `SYSTEM_UNAVAILABLE` | For infrastructure events |
| Service prefix | `NMDP_DOCUMENT_RECEIVED` | For external service events |
| No abbreviations | `ADMINISTRATION_STARTED` not `ADMIN_START` | Clarity over brevity |

## Resource Type Rules

| resource_type | When to Use |
|---------------|-------------|
| `din` | Any event related to a specific product (most events) |
| `donor_id` | Donor record creation (DONOR_CREATED only) |
| `config` | Configuration changes (CONFIG_PROPOSED, CONFIG_ACTIVATED) |
| `system` | Infrastructure events (SYSTEM_UNAVAILABLE, SYSTEM_RESTORED) |

## Outcome Rules

| outcome | When to Use |
|---------|-------------|
| `success` | Action completed as expected |
| `failure` | Action failed (condition check failed, adverse event, system down) |
| `escalated` | Action requires human intervention (out-of-range, permanent failure) |
| `blocked` | Action blocked pending resolution (EIS hold, EIS rejection) |
