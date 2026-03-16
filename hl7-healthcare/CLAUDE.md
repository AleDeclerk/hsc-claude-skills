# CLAUDE.md — hl7-healthcare skill context

## What this repo is

A Claude skill (SKILL.md + Python scripts) that teaches Claude how to build,
validate, and transmit HL7 v2 messages for the LSU Stem Cell Lab HSC
orchestration project (Veritas Automata). It is not production code — it is
a reusable reference that Claude reads when building the real agent.

---

## Project: LSU Stem Cell Lab — HSC Orchestration Agent

LSU collects and infuses Hematopoietic Stem Cell (HSC) products from
**anonymous external donors** (NMDP, international registries). Federal
regulation (FDA 21 CFR Part 1271, FACT/JACIE) requires strict donor
anonymity — donors can never be registered as patients with a real MRN.

The Veritas Automata agent automates the full workflow:
intake → lab orders → results → bedside infusion verification.

### Key systems
- **SoftBank** — Lab Information System (LIS), receives donor registrations
- **Epic Beaker** — Lab orders and results
- **Epic** — Recipient patient chart
- **WellSky** — HL7 middleware between agent and Epic

### Critical rule
The recipient's MRN must **never** appear in any ADT or ORM segment.
It lives only in an encrypted linking table, stored as SHA-256 in audit logs.

---

## The 5 gaps this project must fix

### GAP 1 — Missing MLLP bidirectional listener
**File to create:** `scripts/mllp_listener.py`

**Why it exists:** `mllp_sender.py` only sends messages outbound. But
SoftBank actively *pushes* ORU^R01 result messages to the agent (INT-05).
The agent needs a TCP server listening on a port to receive them and
respond with ACK — otherwise lab results never arrive and the workflow
blocks at US-006.

**What to build:**
- TCP server, default port 2575, configurable via --port
- Receives MLLP-framed HL7 (VT + message bytes + FS + CR)
- Parses ACK response code: AA (accepted), AE (error), AR (rejected)
- AA → logs success as structured JSON
- AE/AR → logs error with raw content, triggers retry callback
- Flags: --host, --port, --timeout, --json
- Exit codes: 0 (AA), 1 (AE/AR), 2 (network error)

**User stories:** US-006 (result validation), INT-05 (SoftBank → Agent)

---

### GAP 2 — ORU^R01 missing custom OBX fields for Epic/WellSky
**Files to update:** `scripts/generate_oru_r01.py`, `references/oru_r01.md`

**Why it exists:** When routing donor results to the recipient's Epic chart
(US-007), Epic needs to know the result belongs to a donor product, not
the patient. Without custom OBX fields, results appear as the patient's
own labs — a compliance and safety violation.

**What to build:**
- Add OBX segment: DIN in OBX-3 using local code `DIN^Donor Product Identifier^L`
- OBX-5 (value) = the DIN string
- Add NTE segment after OBX with report header: `Donor Product — DIN {din}`
- Document the WellSky field mapping in `references/oru_r01.md` under
  new section `## Epic/WellSky Custom Fields`

**User stories:** US-007 (results routing), INT-07 (Agent → Epic HL7)

---

### GAP 3 — No SoftDonor feature flag adapter
**File to create:** `scripts/donor_registration.py`

**Why it exists:** Today donor records go to SoftBank via ADT^A04 (Phase 1).
In Phase 2 (post October 2026), LSU will deploy SoftDonor — a module built
specifically for donor data, eliminating the phantom patient workaround.
The agent needs a clean switch between backends without breaking in-flight cases.

**What to build:**
- Reads config flag DONOR_BACKEND from env var or --backend argument
- Values: "softbank" | "softdonor"
- softbank → delegates to existing generate_adt_a04.py logic
- softdonor → raises NotImplementedError with exact message:
  "SoftDonor API spec pending discovery call with SCC Soft Computer.
   Set DONOR_BACKEND=softbank until Phase 2."
- Logs which backend was used in structured JSON
- Update SKILL.md with new section `## Phase 2 — SoftDonor Migration`

**User stories:** US-003 (donor registration), US-012 (SoftDonor migration)

---

### GAP 4 — Missing product panels for Bone Marrow and Cord Blood
**File to create:** `references/product_panels.md`

**Why it exists:** SKILL.md has a LOINC table only for PBSC (peripheral blood
stem cells). But LSU also processes Bone Marrow (BM) and Cord Blood (CB)
products, which require different test panels. Without this, Claude would
order the wrong tests for BM and CB products — a patient safety issue.

**What to build:**
- Table for PBSC (copy from current SKILL.md LOINC section)
- Table for Bone Marrow (BM): CD34+ 18207-3, ABO 883-9, Rh 10331-7,
  WBC 6690-2, sterility 600-7, plus all infectious disease markers
  (CMV IgG 13949-3, HIV-1/2 7917-8, HBsAg 5196-1, HCV 16128-1,
  HTLV-I/II 31201-7, Syphilis 20507-0)
- Table for Cord Blood (CB): same as BM plus HbF (fetal hemoglobin)
  LOINC 4576-5, TNC (total nucleated cell count) LOINC 26498-6, unit volume
- Each product table must mark tests that can come pre-populated from
  NMDP documentation as "NMDP — do not reorder"
- Update SKILL.md to remove inline LOINC table and reference this file instead

**User stories:** US-004 (NMDP doc ingestion), US-005 (lab order generation)

---

### GAP 5 — SKILL.md not updated to reflect new components
**File to update:** `SKILL.md`

**Why it exists:** Gaps 1–4 add new scripts and references, but SKILL.md
is the entry point Claude reads first. If SKILL.md doesn't document the
new components, Claude won't know they exist or how to use them.

**What to update:**
- Add `mllp_listener.py` to Quick Start section with usage example
- Add `mllp_listener.py` to File Layout section
- Add section `## Listening & ACK Processing` documenting AA/AE/AR behavior
- Add section `## Phase 2 — SoftDonor Migration` documenting the feature flag
- Replace inline LOINC table with reference to `references/product_panels.md`

---

## Commit convention

Use conventional commits, one per gap:
- feat(mllp): add bidirectional MLLP listener with ACK handling
- feat(oru): add Epic/WellSky custom OBX fields and DIN report header
- feat(donor): add SoftDonor feature flag adapter for Phase 2
- docs(panels): add product-specific order panels for BM and CB
- docs(skill): update SKILL.md with listener, panels reference, Phase 2 flag

---

## What NOT to do

- Do not modify existing script interfaces (mllp_sender.py, generate_adt_a04.py etc.)
- Do not add the recipient MRN to any HL7 segment — SHA-256 hash only
- Do not create new dependencies outside the Python standard library unless essential
- Do not change the anonymous donor field rules in PID segments
