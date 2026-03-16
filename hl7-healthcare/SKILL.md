---
name: hl7-healthcare
description: >
  Generate, validate, parse, and transmit HL7 v2 messages for healthcare interoperability workflows.
  Use this skill whenever the user needs to work with HL7 messages of any type — including ADT^A04
  (patient/donor registration), ORM^O01 (lab orders), ORU^R01 (results), and ACK (acknowledgments).
  Also trigger for MLLP transport, SoftBank/Epic/Beaker integration, anonymous donor workflows,
  ISBT-128 product registration, or any task involving healthcare system messaging, HL7 segment
  construction, field mapping, or clinical interoperability. Even if the user just says "build an
  HL7 message" or "send a result to Epic", use this skill.
---

# HL7 Healthcare Interoperability Skill

Generates, validates, parses, and transmits HL7 v2.x messages. Designed for clinical lab, 
stem cell, and hospital integration workflows — including anonymous donor handling (FACT/JACIE, FDA 21 CFR Part 1271).

---

## Supported Message Types

| Message       | Trigger Event        | Use Case                                      |
|---------------|----------------------|-----------------------------------------------|
| ADT^A04       | Register patient     | Anonymous donor registration in SoftBank      |
| ORM^O01       | Lab order            | Test panel generation in Epic Beaker          |
| ORU^R01       | Observation result   | Results from SoftBank → Epic chart routing    |
| ACK           | Acknowledgment       | MLLP response validation                      |

---

## Quick Start

### 1. Generate a message

```bash
# ADT^A04 — anonymous donor registration
python scripts/generate_adt_a04.py \
  --din "W000055508D001" \
  --donor-id "DONOR-2026-0042" \
  --sending-app "VERITAS" \
  --sending-facility "LSU_SCL" \
  --receiving-app "SOFTBANK" \
  --receiving-facility "LSU"

# ORM^O01 — lab order panel
python scripts/generate_orm_o01.py \
  --donor-id "DONOR-2026-0042" \
  --din "W000055508D001" \
  --product-type "PBSC" \
  --output orders.hl7

# ORU^R01 — results routing to Epic
python scripts/generate_oru_r01.py \
  --donor-id "DONOR-2026-0042" \
  --recipient-mrn "MRN123456" \
  --din "W000055508D001" \
  --results results.json \
  --output oru_result.hl7
```

### 2. Validate a message

```bash
python scripts/validate_hl7.py --file message.hl7
python scripts/validate_hl7.py --stdin < message.hl7
```

### 3. Parse / inspect a message

```bash
python scripts/parse_hl7.py --file message.hl7 --segment PID
python scripts/parse_hl7.py --file message.hl7 --all
```

### 4. Send via MLLP

```bash
python scripts/mllp_sender.py \
  --host softbank.lsu.edu \
  --port 2575 \
  --file message.hl7 \
  --timeout 10
```

<<<<<<< HEAD
### 5. Receive incoming messages (MLLP listener)

```bash
# Listen continuously — responds to each incoming message with ACK
python scripts/mllp_listener.py \
  --host 0.0.0.0 \
  --port 2575 \
  --timeout 30 \
  --json

# Accept exactly one message then exit (useful in scripts/pipelines)
python scripts/mllp_listener.py --port 2575 --once
```

### 6. Register a donor (feature-flag aware)

```bash
# Phase 1 — SoftBank backend (default)
DONOR_BACKEND=softbank python scripts/donor_registration.py \
  --din "W000055508D001" \
  --donor-id "DONOR-2026-0042" \
  --json

# --backend argument takes precedence over DONOR_BACKEND env var
python scripts/donor_registration.py \
  --backend softbank \
  --din "W000055508D001" \
  --donor-id "DONOR-2026-0042"
=======
### 5. Listen for incoming MLLP messages (server mode)

```bash
# Continuous listener — receives ORU^R01 results pushed by SoftBank (INT-05)
python scripts/mllp_listener.py --host 0.0.0.0 --port 2575

# Accept one message then exit (useful in pipelines)
python scripts/mllp_listener.py --port 2575 --once --json
```

### 6. Register a donor (feature-flag adapter)

```bash
# Phase 1 (current) — routes to SoftBank via ADT^A04
DONOR_BACKEND=softbank python scripts/donor_registration.py \
  --din W000055508D001 \
  --donor-id DONOR-2026-0042

# --backend argument takes precedence over env var
python scripts/donor_registration.py \
  --backend softbank \
  --din W000055508D001 \
  --donor-id DONOR-2026-0042 \
  --json
>>>>>>> 9634376 (feat: skill-creator evals — 100% with-skill, CB panel fix, improved assertions)
```

---

## Anonymous Donor Rules (LSU / FDA 21 CFR Part 1271)

When registering an anonymous HSC donor, **strictly follow these field rules**:

| PID Field     | Value                      | Reason                            |
|---------------|----------------------------|-----------------------------------|
| PID-3 (ID)    | DIN as primary, Donor ID as secondary | ICCBBA traceability    |
| PID-5 (Name)  | `ANONYMOUS^DONOR`          | No real name — regulatory         |
| PID-7 (DOB)   | `00010101`                 | Placeholder — no real DOB         |
| PID-8 (Sex)   | `U`                        | Unknown — no real sex             |
| PID-19 (SSN)  | *empty*                    | Never populate                    |

The recipient's MRN must **never appear** in any ADT or ORM segment. It lives only in the 
encrypted linking table, hashed as SHA-256 in audit events.

---

## Product Order Panels (LOINC Codes)

LOINC codes differ by HSC product type. Using the wrong panel is a patient safety issue.

See `references/product_panels.md` for the complete tables:

| Product | Notes |
|---------|-------|
| **PBSC** — Peripheral Blood Stem Cells | CD34+, ABO, Rh, WBC, sterility + infectious disease markers |
| **BM** — Bone Marrow | Same as PBSC minus CD3+; includes sterility |
| **CB** — Cord Blood | Same as BM plus HbF (4576-5), TNC (26498-6), unit volume (20612-7) |

Tests marked **NMDP — do not reorder** arrive pre-populated from registry documentation.
Do not issue duplicate lab orders; import via ORU^R01.

---

## HL7 Segment Reference

For full field-by-field documentation of each message type:
- ADT^A04 → `references/adt_a04.md`
- ORM^O01 and ORU^R01 → `references/orm_oru_reference.md`

---

## Listening & ACK Processing

The agent must listen for inbound ORU^R01 messages pushed by SoftBank (integration point INT-05).
Use `mllp_listener.py` to run a TCP server that receives, acknowledges, and logs these results.

| ACK Code | Meaning              | Listener Behavior                              |
|----------|----------------------|------------------------------------------------|
| `AA`     | Application Accept   | Logs success as structured JSON, exits 0       |
| `AE`     | Application Error    | Logs error with raw content, triggers retry callback, exits 1 |
| `AR`     | Application Reject   | Logs rejection, escalates to Lab Supervisor, exits 1 |

Exit codes from `mllp_listener.py`:
- `0` — AA (message accepted)
- `1` — AE or AR (message rejected or error)
- `2` — Network error (timeout, connection refused)

For full MLLP framing specification, connection flow diagrams, and retry guidance, see
`references/mllp_protocol.md`.

---

## Phase 2 — SoftDonor Migration

In Phase 1 (current), donor records are registered in SoftBank as ADT^A04 phantom patient records.

In Phase 2 (post October 2026), LSU will deploy **SoftDonor** — an SCC Soft Computer module
built specifically for donor data, eliminating the phantom patient workaround.

The `donor_registration.py` adapter provides a clean switch between backends:

```bash
# Phase 1 — current
DONOR_BACKEND=softbank python scripts/donor_registration.py --din ... --donor-id ...

# Phase 2 — stub, raises NotImplementedError until API spec arrives
DONOR_BACKEND=softdonor python scripts/donor_registration.py --din ... --donor-id ...
# ERROR: SoftDonor API spec pending discovery call with SCC Soft Computer.
#        Set DONOR_BACKEND=softbank until Phase 2.
```

When SoftDonor is ready, implement `register_donor_softdonor()` in `donor_registration.py`
and remove the `NotImplementedError`. No changes to any other script are required.

---

## Listening & ACK Processing

`mllp_listener.py` opens a TCP server and processes inbound MLLP messages
(e.g. ORU^R01 pushed by SoftBank — INT-05). For each received message it:

1. Unwraps the MLLP frame (`<VT> ... <FS><CR>`)
2. Parses the MSH segment (message type, control ID, sender)
3. Responds with an MLLP-framed ACK immediately
4. Logs the result as structured JSON (when `--json` is set) or plain text

ACK code behaviour:

| Code | Meaning           | Action                                       |
|------|-------------------|----------------------------------------------|
| AA   | Application Accept | Log success; exit 0 (with `--once`)          |
| AE   | Application Error  | Log error with raw content; exit 1           |
| AR   | Application Reject | Log error with raw content; exit 1           |

Network errors (timeout, bind failure) exit with code 2.

---

## Phase 2 — SoftDonor Migration

In Phase 1 (current), donors are registered as phantom patients in SoftBank
via ADT^A04. `donor_registration.py` wraps this with a feature flag so the
backend can be swapped without breaking in-flight cases.

**Feature flag:** `DONOR_BACKEND` environment variable (or `--backend` argument)

| Value       | Behaviour                                                    |
|-------------|--------------------------------------------------------------|
| `softbank`  | Default. Delegates to `generate_adt_a04.py` logic.          |
| `softdonor` | Raises `NotImplementedError` — Phase 2 stub (post Oct 2026) |

When `softdonor` is requested, the error message is:

```
SoftDonor API spec pending discovery call with SCC Soft Computer.
Set DONOR_BACKEND=softbank until Phase 2.
```

Do not implement SoftDonor logic until the API spec is received from
SCC Soft Computer and the Phase 2 timeline is confirmed.

---

## MLLP Framing

HL7 v2 over TCP uses MLLP (Minimal Lower Layer Protocol) framing:

```
<VT> [HL7 message bytes] <FS><CR>
```

- `<VT>` = `0x0B` — Start Block character
- `<FS>` = `0x1C` — End Data character  
- `<CR>` = `0x0D` — Carriage Return

The `mllp_sender.py` script handles framing automatically. For raw integration, see `references/mllp_protocol.md`.

---

## Validation Rules

`validate_hl7.py` checks:
1. MSH segment present and correctly delimited (`|^~\&`)
2. Message type in supported set
3. Required segments present for message type
4. PID-3 (Patient ID) non-empty
5. Timestamp format valid (YYYYMMDDHHMMSS)
6. For ADT^A04 anonymous donor: PID-5 must be `ANONYMOUS^DONOR`, PID-7 must be `00010101`
7. No MRN-like identifiers in ORM/ADT segments (anonymous donor safety check)
8. ACK code parsing (AA=accepted, AE=error, AR=rejected)

---

## Error Handling

All scripts exit with:
- `0` — success
- `1` — validation error (message printed to stderr)
- `2` — network/MLLP error
- `3` — parse error

Scripts log to stdout in structured JSON when `--json` flag is passed, useful for agent integration.

---

## File Layout

```
hl7-healthcare/
├── SKILL.md                    ← You are here
├── scripts/
│   ├── generate_adt_a04.py     ← Build ADT^A04 messages
│   ├── generate_orm_o01.py     ← Build ORM^O01 lab order panels
│   ├── generate_oru_r01.py     ← Build ORU^R01 result messages (with DIN OBX/NTE)
│   ├── validate_hl7.py         ← Validate any HL7 v2 message
│   ├── parse_hl7.py            ← Parse and inspect HL7 messages
│   ├── mllp_sender.py          ← Transmit via MLLP over TCP (outbound)
<<<<<<< HEAD
│   ├── mllp_listener.py        ← Receive via MLLP over TCP (inbound, ACK)
│   └── donor_registration.py   ← Feature-flag adapter: SoftBank vs SoftDonor
├── references/
│   ├── adt_a04.md              ← ADT^A04 field reference
│   ├── orm_o01.md              ← ORM^O01 field reference
│   ├── oru_r01.md              ← ORU^R01 field reference (incl. Epic/WellSky custom fields)
│   ├── product_panels.md       ← LOINC order panels for PBSC, BM, CB
│   └── mllp_protocol.md        ← MLLP framing specification
=======
│   ├── mllp_listener.py        ← Receive MLLP messages over TCP (inbound, ACK server)
│   └── donor_registration.py   ← Feature-flag adapter: SoftBank (Phase 1) / SoftDonor (Phase 2)
├── references/
│   ├── adt_a04.md              ← ADT^A04 field reference
│   ├── orm_oru_reference.md    ← ORM^O01 and ORU^R01 field reference
│   ├── product_panels.md       ← HSC product-type order sets (PBSC / BM / CB)
│   └── mllp_protocol.md        ← MLLP framing specification and retry guidance
>>>>>>> 9634376 (feat: skill-creator evals — 100% with-skill, CB panel fix, improved assertions)
└── examples/
    ├── anonymous_donor_registration.hl7
    ├── lab_order_panel_pbsc.hl7
    └── results_routing_to_epic.hl7
```
