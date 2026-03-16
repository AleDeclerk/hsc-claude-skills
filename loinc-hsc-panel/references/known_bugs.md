# Known LOINC/Panel Bugs in Current Codebase

> These bugs are confirmed against loinc.org and FDA 21 CFR 1271.85.

---

## Bug 1: Wrong LOINC code for CD34

**File**: `src/agents/orchestration/nodes/order.py` (~line 49)
**Severity**: High — orders wrong lab test

### Current code (wrong)

```python
loinc_codes = [
    {"code": "58410-2", "name": "CD34+ count"},
    {"code": "26515-7", "name": "Platelet count"},
]
```

### Problem

`58410-2` is "CBC panel - Blood by Automated count" per loinc.org. It is NOT a CD34 count.
The correct LOINC for CD34+ absolute count is `42808-4` ("CD34 cells [#/volume] in Blood").

Ordering `58410-2` as "CD34+ count" means Beaker receives a CBC panel order labeled as CD34,
which will either fail or return wrong results.

### Fix

```python
loinc_codes = [
    {"code": "42808-4", "name": "CD34 cells [#/volume] in Blood"},
    {"code": "26515-7", "name": "Platelets [#/volume] in Blood"},
]
```

---

## Bug 2: Default panel has only 2 tests

**File**: `src/agents/orchestration/nodes/order.py` (~line 48-51)
**Severity**: High — FDA non-compliance

### Problem

The default fallback panel has only 2 LOINC codes (CD34 + platelets). An HSC product requires
minimum 10-15 tests per FDA 21 CFR 1271.85 and FACT standards:

- Cell characterization: CD34, WBC, viability (minimum)
- ABO/Rh typing: ABO group, Rh type
- Infectious disease: HIV, HBV, HCV, syphilis, CMV, HTLV (8-11 tests)
- Sterility: aerobic culture (minimum)

A 2-test panel would fail any FDA or FACT audit.

### Fix

Replace the default fallback with the full recommended panel (15 tests):

```python
DEFAULT_HSC_PANEL = [
    {"code": "42808-4", "name": "CD34 cells [#/volume] in Blood"},
    {"code": "8125-7",  "name": "CD34 cells/100 cells in Blood"},
    {"code": "26464-8", "name": "Leukocytes [#/volume] in Blood"},
    {"code": "34542-1", "name": "Cell viability [%] in Body fluid"},
    {"code": "882-1",   "name": "ABO group [Type] in Blood"},
    {"code": "10331-7", "name": "Rh [Type] in Blood"},
    {"code": "62469-2", "name": "HIV 1+2 Ab+Ag [Presence] in Serum or Plasma"},
    {"code": "5195-3",  "name": "HBsAg [Presence] in Serum"},
    {"code": "16933-4", "name": "HBc Ab [Presence] in Serum"},
    {"code": "16128-1", "name": "HCV Ab [Presence] in Serum"},
    {"code": "22587-0", "name": "Treponema pallidum Ab [Presence] in Serum"},
    {"code": "22244-8", "name": "CMV IgG Ab [Mass/volume] in Serum"},
    {"code": "5124-3",  "name": "CMV IgM Ab [Presence] in Serum"},
    {"code": "7942-6",  "name": "HTLV I+II Ab [Presence] in Serum"},
    {"code": "630-4",   "name": "Bacteria identified in Blood by Culture"},
]
```

---

## Bug 3: No LOINC validation in config service

**File**: `src/services/config_service.py`
**Severity**: Medium — allows invalid lab orders

### Problem

The `propose_config()` function accepts `test_panels` as JSON without validating that the
LOINC codes are real. A typo like `"42808-44"` or a completely made-up code like `"99999-9"`
would be accepted and later sent to Beaker, which would reject the order.

### Fix

Add validation in `propose_config()`:

```python
from src.services.loinc_validator import VALID_HSC_LOINC_CODES

def validate_test_panels(panels: list[dict]) -> list[str]:
    """Validate LOINC codes in test panels. Returns list of errors."""
    errors = []
    for panel in panels:
        for code in panel.get("loinc_codes", []):
            if code not in VALID_HSC_LOINC_CODES:
                errors.append(f"Unknown LOINC code: {code}")
    return errors
```

---

## Bug 4: Test data uses wrong LOINC

**Files**:
- `tests/unit/services/test_hl7_builder_orm.py` (line ~12)
- `tests/contract/test_anonymity.py` (multiple lines)

### Problem

Test data uses `58410-2` labeled as "CD34+ count". Tests pass structurally but encode the
wrong lab test. Update test data to use `42808-4`.

### Fix

```python
# In test files, replace:
LOINC_CODES = [
    {"code": "58410-2", "name": "CD34+ count"},
    {"code": "26515-7", "name": "Platelet count"},
]

# With:
LOINC_CODES = [
    {"code": "42808-4", "name": "CD34 cells [#/volume] in Blood"},
    {"code": "26515-7", "name": "Platelets [#/volume] in Blood"},
]
```

Also update any hardcoded HL7 messages in test fixtures that reference `58410-2`.
