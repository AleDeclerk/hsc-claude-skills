---
name: loinc-hsc-panel
description: >
  Use correct LOINC codes for HSC (Hematopoietic Stem Cell) product lab orders, result validation,
  and test panel configuration per FDA 21 CFR 1271.85 and FACT-JACIE standards. Trigger whenever
  the user works on lab order generation (ORM^O01), lab result validation, clinical config for test
  panels, LOINC code references in HL7 messages (OBR-4, OBX-3), CD34 counts, infectious disease
  screening, donor testing, ABO/Rh typing, cell viability, sterility cultures, or any code mentioning
  "LOINC", "lab panel", "test codes", "donor eligibility", or "HCT/P testing".
---

# LOINC HSC Panel Skill

Provides verified LOINC codes for HSC product testing per FDA 21 CFR 1271.85 and ICCBBA/FACT standards.

---

## HSC Product Test Panel — Complete LOINC Code Table

### Cell Characterization (Product Quality)

| LOINC | Component | Units | Specimen | Notes |
|-------|-----------|-------|----------|-------|
| `42808-4` | CD34 cells [#/volume] | cells/uL | Blood | CD34+ count by flow cytometry |
| `8125-7` | CD34 cells/100 cells | % | Blood | CD34+ fraction |
| `80698-4` | Viable CD34 cells/CD34 cells | % | HPC product | CD34+ viability post-processing |
| `26464-8` | Leukocytes [#/volume] | 10*3/uL | Blood | WBC count |
| `26515-7` | Platelets [#/volume] | 10*3/uL | Blood | Platelet count |
| `718-7` | Hemoglobin [Mass/volume] | g/dL | Blood | Hemoglobin |
| `55793-4` | Nucleated cells [#/volume] | cells/uL | Body fluid | TNC count |
| `34542-1` | Cell viability [%] | % | Body fluid | Trypan blue / 7-AAD |

### ABO/Rh Typing

| LOINC | Component | Result Type | Notes |
|-------|-----------|-------------|-------|
| `882-1` | ABO group [Type] | Nominal (A/B/AB/O) | ABO blood type |
| `10331-7` | Rh [Type] | Nominal (Pos/Neg) | RhD type |
| `34532-2` | Blood type and Indirect antibody screen panel | Panel | Comprehensive typing |

### Infectious Disease Screening (FDA 21 CFR 1271.85)

| LOINC | Component | Method | Required For | Notes |
|-------|-----------|--------|-------------|-------|
| `62469-2` | HIV 1+2 Ab+Ag | 4th gen combo | ALL HCT/P donors | **Preferred** — replaces separate HIV-1/2 |
| `68961-2` | HIV 1 Ab | Rapid immunoassay | ALL | Alternative to combo |
| `29893-5` | HIV 1 Ab | Standard immunoassay | ALL | Alternative to combo |
| `30361-0` | HIV 2 Ab | Immunoassay | ALL | If not using combo test |
| `5196-1` | HIV 1 RNA [Presence] | NAT | ALL | HIV nucleic acid test |
| `5195-3` | HBsAg [Presence] | Immunoassay | ALL | Hepatitis B surface antigen |
| `16933-4` | HBc Ab [Presence] | Immunoassay | ALL | Hep B core antibody (total) |
| `42595-7` | HBV DNA [Presence] | NAT | ALL | HBV nucleic acid test |
| `16128-1` | HCV Ab [Presence] | Immunoassay | ALL | Hepatitis C antibody |
| `7905-3` | HCV RNA [Presence] | NAT | ALL | HCV nucleic acid test |
| `22587-0` | T. pallidum Ab | Treponemal | ALL | Syphilis treponemal test |
| `20507-0` | Reagin Ab (RPR) | Non-treponemal | ALL | Syphilis screen |
| `22244-8` | CMV IgG Ab | Immunoassay | Viable leukocyte-rich | CMV IgG |
| `5124-3` | CMV IgM Ab | Immunoassay | Viable leukocyte-rich | CMV IgM |
| `7942-6` | HTLV I/II Ab | Immunoassay | Viable leukocyte-rich | HTLV screening |

### Sterility / Microbiology

| LOINC | Component | Specimen | Notes |
|-------|-----------|----------|-------|
| `630-4` | Bacteria identified | Blood culture | Aerobic culture |
| `635-3` | Bacteria identified | Body fluid culture | Product sterility |
| `580-1` | Fungus identified | Body fluid culture | Fungal culture |

---

## All Valid LOINC Codes (Lookup Set)

Use this set to validate that a LOINC code is a recognized HSC panel code:

```python
VALID_HSC_LOINC_CODES = {
    # Cell characterization
    "42808-4", "8125-7", "80698-4", "26464-8", "26515-7", "718-7", "55793-4", "34542-1",
    # ABO/Rh
    "882-1", "10331-7", "34532-2",
    # Infectious disease
    "62469-2", "68961-2", "29893-5", "30361-0", "5196-1",
    "5195-3", "16933-4", "42595-7",
    "16128-1", "7905-3",
    "22587-0", "20507-0",
    "22244-8", "5124-3",
    "7942-6",
    # Sterility
    "630-4", "635-3", "580-1",
}
```

---

## Recommended Minimum Default Panel

For an HSC product, the minimum panel that satisfies FDA 21 CFR 1271.85 + FACT standards:

```python
DEFAULT_HSC_PANEL = [
    # Product characterization
    {"code": "42808-4", "name": "CD34 cells [#/volume] in Blood"},
    {"code": "8125-7",  "name": "CD34 cells/100 cells in Blood"},
    {"code": "26464-8", "name": "Leukocytes [#/volume] in Blood"},
    {"code": "34542-1", "name": "Cell viability [%] in Body fluid"},
    # ABO/Rh
    {"code": "882-1",   "name": "ABO group [Type] in Blood"},
    {"code": "10331-7", "name": "Rh [Type] in Blood"},
    # Infectious disease (FDA-mandated)
    {"code": "62469-2", "name": "HIV 1+2 Ab+Ag [Presence] in Serum or Plasma"},
    {"code": "5195-3",  "name": "HBsAg [Presence] in Serum"},
    {"code": "16933-4", "name": "HBc Ab [Presence] in Serum"},
    {"code": "16128-1", "name": "HCV Ab [Presence] in Serum"},
    {"code": "22587-0", "name": "Treponema pallidum Ab [Presence] in Serum"},
    {"code": "22244-8", "name": "CMV IgG Ab [Mass/volume] in Serum"},
    {"code": "5124-3",  "name": "CMV IgM Ab [Presence] in Serum"},
    {"code": "7942-6",  "name": "HTLV I+II Ab [Presence] in Serum"},
    # Sterility
    {"code": "630-4",   "name": "Bacteria identified in Blood by Culture"},
]
```

This is 15 tests. The absolute minimum for FDA compliance is the 8 infectious disease codes + CD34 + viability = 10.

---

## Reference Ranges

These are typical ranges. Actual ranges MUST be configured per-institution via clinical config with dual sign-off.

| LOINC | Test | Typical Range | Units | Notes |
|-------|------|---------------|-------|-------|
| `42808-4` | CD34+ count | >=2.0 x 10^6/kg | cells/uL (dose-calc) | Minimum for engraftment |
| `26464-8` | WBC | 4.5-11.0 | 10*3/uL | Standard range |
| `26515-7` | Platelets | 150-400 | 10*3/uL | Standard range |
| `34542-1` | Cell viability | >=70% | % | Post-thaw minimum |
| `882-1` | ABO group | A, B, AB, or O | Nominal | Must be compatible with recipient |
| All ID tests | Infectious disease | Negative/Non-reactive | Qualitative | Reactive = escalation |

---

## HL7 Encoding

### OBR-4 (Universal Service Identifier)

```
OBR|1|ORD12345||42808-4^CD34 cells [#/volume] in Blood^LN|||...
```

Format: `LOINC_CODE^LOINC_LONG_NAME^LN`

The third component MUST be `LN` (LOINC coding system identifier per HL7 Table 0396).

### OBX-3 (Observation Identifier)

```
OBX|1|NM|42808-4^CD34 cells^LN||250|cells/uL||N|||F
```

### Multiple Tests in One ORM^O01

Each LOINC code gets its own ORC+OBR group:

```
ORC|NW|ORD001|||...
OBR|1|ORD001||42808-4^CD34 cells^LN|||...
ORC|NW|ORD002|||...
OBR|2|ORD002||882-1^ABO group^LN|||...
```

---

## Critical Bug: `58410-2` is NOT CD34

The code `58410-2` is "CBC panel - Blood by Automated count" — a **complete blood count panel**, not a CD34 count.

| Code | Actual Name | What It Is |
|------|-------------|------------|
| `58410-2` | CBC panel - Blood by Automated count | **Wrong** — this is a CBC, not CD34 |
| `42808-4` | CD34 cells [#/volume] in Blood | **Correct** — CD34+ absolute count |
| `8125-7` | CD34 cells/100 cells in Blood | **Correct** — CD34+ percentage |

If you see `58410-2` labeled as "CD34+ count" anywhere in the codebase, it's a bug.

---

## FDA Regulatory Context

### 21 CFR 1271.85 — Donor Testing Requirements

**ALL HCT/P donors** (including HSC) must be tested for:
- HIV-1 (antibody + NAT)
- HIV-2 (antibody; combo test acceptable)
- HBV (HBsAg + anti-HBc + NAT)
- HCV (antibody + NAT)
- Syphilis (T. pallidum — treponemal or non-treponemal)

**Viable leukocyte-rich HCT/Ps** (HSC products qualify) additionally require:
- CMV (IgG and IgM antibodies)
- HTLV-I/II (antibody)

A positive CMV does NOT make the donor ineligible — it must be communicated to the accepting physician.

### FACT-JACIE Standards

- All products must have ABO/Rh typing
- Cell characterization (CD34, TNC, viability) required for product release
- Sterility testing required for processed products

---

## Known Bugs in Current Project Code

### Bug 1: Wrong LOINC for CD34

**File**: `src/agents/orchestration/nodes/order.py` (line ~49)

```python
# CURRENT (wrong):
loinc_codes = [
    {"code": "58410-2", "name": "CD34+ count"},    # WRONG! This is CBC panel
    {"code": "26515-7", "name": "Platelet count"},
]

# CORRECT:
loinc_codes = [
    {"code": "42808-4", "name": "CD34 cells [#/volume] in Blood"},
    {"code": "26515-7", "name": "Platelets [#/volume] in Blood"},
]
```

### Bug 2: Default panel has only 2 tests

An HSC product requires minimum 10-15 tests (cell characterization + ABO/Rh + infectious disease + sterility). The default fallback should use `DEFAULT_HSC_PANEL` (15 tests) defined above.

### Bug 3: No LOINC validation

**File**: `src/services/config_service.py`

The config service accepts arbitrary strings as LOINC codes without checking if they're valid. Should validate against `VALID_HSC_LOINC_CODES`.

---

## Quick Reference Card

| Question | Answer |
|----------|--------|
| CD34 count LOINC? | `42808-4` (absolute) or `8125-7` (percentage) |
| Is `58410-2` CD34? | **NO** — it's CBC panel. This is a bug. |
| FDA-required ID tests? | HIV, HBV, HCV, syphilis (all donors) + CMV, HTLV (viable leukocyte-rich) |
| Minimum tests for HSC? | ~15 (4 cell char + 2 ABO/Rh + 8 infectious disease + 1 sterility) |
| HL7 coding system? | `LN` (LOINC) in OBR-4 and OBX-3 third component |
| Result for ID tests? | Qualitative: Negative/Non-reactive = pass; Reactive = escalation |
| CMV positive = reject? | **NO** — communicate to accepting physician |
| Where are ranges configured? | Clinical config (dual sign-off required) |
| LOINC validation set? | `VALID_HSC_LOINC_CODES` (31 codes) |

---

## Reference Files

- `references/loinc_codes.md` — Full LOINC code table with all fields
- `references/fda_requirements.md` — FDA 21 CFR 1271.85 donor testing details
- `references/known_bugs.md` — Current codebase bugs with fix patches
