---
name: isbt-128
description: >
  Validate, parse, and generate ISBT-128 Donation Identification Numbers (DINs) per the ICCBBA
  Technical Specification (ST-001). Use this skill whenever the user works with DIN validation,
  DIN parsing, DIN generation for tests, ISBT-128 barcodes, Facility Identification Numbers (FINs),
  product traceability, or any code that touches donation identifiers. Also trigger when auditing
  existing DIN validation code, fixing DIN-related bugs, or discussing ICCBBA standards, ISO 7064
  Mod 37-2 check characters, or MPHO Unique Identifiers.
---

# ISBT-128 DIN Skill

Validates, parses, and generates ISBT-128 Donation Identification Numbers per ICCBBA specs.
Designed for blood bank, cellular therapy, and HSC product traceability workflows.

---

## DIN Structure (13 Characters)

The DIN is a **13-character** globally unique identifier. Structure: `FYYnnnnnn` expanded as:

```
Position:  1     2-5      6-7    8-13
Content:   α     pppp     yy     nnnnnn
Name:      ───── FIN ─────  Year   Sequence
```

| Position | Chars | Name | Rules |
|----------|-------|------|-------|
| 1 | 1 | Country/region indicator | **MUST be alpha (A-Z)**. First character of FIN. |
| 2-5 | 4 | FIN remainder | Currently numeric (0-9). Alpha MAY be introduced in positions 2-3 in future. Accept `[A-Z0-9]` to be future-proof. |
| 6-7 | 2 | Year code | Digits only (`00-99`). For uniqueness, NOT a collection date. |
| 8-13 | 6 | Sequence number | Digits only (`000000-999999`). Unique within FIN+year for 100 years. |

**Example**: `A999914123458` (FIN=`A9999`, Year=`14`, Seq=`123458`)

---

## Data Structure 001 (16 Characters Total)

The full barcode data structure wraps the DIN with flag characters and a check character:

| Component | Length | Part of DIN? | Description |
|-----------|--------|-------------|-------------|
| DIN (`αppppyynnnnnn`) | 13 | **Yes** | The unique identifier |
| Flag characters | 2 | No | Process control or locally defined. `00` when unused. |
| Check character | 1 | No | ISO 7064 Mod 37,2. For keyboard entry validation. |

Total Data Structure 001 = 16 characters: `[DIN 13][FLAGS 2][CHECK 1]`

---

## Check Character Calculation

- Algorithm: **ISO/IEC 7064 Modulo 37,2**
- Input: the **13-character DIN only** (flags are NOT included)
- Output: single character from charset `0-9, A-Z, *` (37 possible values)
- The asterisk `*` is a valid check character
- `python-stdnum`'s `mod_37_2.validate()` expects the **14-character string** (DIN + check char)
- `mod_37_2.calc_check_digit()` accepts the 13-character DIN and returns the check character

**Verified example**: DIN `A999914123458` has check character `J`

---

## Correct Regex Patterns

### 13-character DIN (no check character)

```python
DIN_PATTERN_13 = re.compile(r"^[A-Z][A-Z0-9]{4}\d{2}\d{6}$")
```

### 14-character DIN + check character

```python
DIN_PATTERN_14 = re.compile(r"^[A-Z][A-Z0-9]{4}\d{2}\d{6}[A-Z0-9*]$")
```

Key rules enforced:
- Position 1: `[A-Z]` — alpha only (NOT alphanumeric)
- Positions 2-5: `[A-Z0-9]` — future-proof for alpha introduction
- Positions 6-7: `\d{2}` — digits only
- Positions 8-13: `\d{6}` — digits only
- Position 14 (check char): `[A-Z0-9*]` — includes asterisk

---

## Validation Algorithm

When validating a DIN input:

```
1. Strip whitespace, normalize to uppercase
2. If empty → error "DIN is empty"
3. If length == 14:
   a. Match against DIN_PATTERN_14
   b. Validate check character: mod_37_2.validate(din_14)
   c. Store the 13-char DIN (strip check char)
4. If length == 13:
   a. Match against DIN_PATTERN_13
   b. No check character to validate
   c. Store as-is
5. If length == 16:
   a. Extract DIN = chars[0:13], flags = chars[13:15], check = chars[15]
   b. Validate DIN per step 4
   c. Validate check: mod_37_2.validate(DIN + check)
   d. Store the 13-char DIN
6. Any other length → error "Invalid format"
7. Check uniqueness against database
```

---

## FIN (Facility Identification Number)

- 5 characters, assigned by ICCBBA to each registered facility
- First character: alphabetic (A-Z) — this is the country/region indicator
- Positions 2-5: currently all numeric, but alpha MAY be introduced
- Over 3,500 FINs assigned across 67+ countries
- NMDP, registries, and national organizations can also hold FINs
- HSC products carry the FIN of the **collection facility or registry** that assigned the DIN

---

## Parsing a DIN

Given a 13-character DIN, extract components:

```python
def parse_din(din: str) -> dict:
    """Parse a validated 13-character DIN into components."""
    return {
        "fin": din[0:5],           # Facility Identification Number
        "country_indicator": din[0], # First char of FIN
        "fin_remainder": din[1:5],   # Remaining 4 chars of FIN
        "year_code": din[5:7],       # 2-digit year (for uniqueness, NOT collection date)
        "sequence": din[7:13],       # 6-digit sequence number
    }
```

---

## Generating Test DINs

When generating DINs for tests, follow these rules:

1. First character MUST be alpha (A-Z)
2. Use recognizable facility prefixes (e.g., `W1234`, `A9999`, `T0001`)
3. Year code: any 2 digits
4. Sequence: any 6 digits
5. To add a check character: `from stdnum.iso7064 import mod_37_2; check = mod_37_2.calc_check_digit(din_13)`

**Valid test DINs**:
- `W123426000123` (FIN=W1234, Year=26, Seq=000123)
- `A999914123458` (FIN=A9999, Year=14, Seq=123458, Check=J → 14-char: `A999914123458J`)
- `T000126999999` (FIN=T0001, Year=26, Seq=999999)

**Invalid test DINs** (for negative tests):
- `0999914123458` — first char is digit, not alpha
- `A99991412345` — only 12 chars (too short)
- `A9999141234580` — check char `0` is wrong (correct is `J`)
- `ABCDE14123458` — positions 6-7 are not digits
- `A999914ABCDEF` — positions 8-13 are not digits
- `` — empty string

---

## Known Bugs in Current Project Code

The following issues exist in `src/services/din_validator.py` and `src/models/case.py`:

### Bug 1: FIN first character not enforced as alpha

```python
# CURRENT (wrong):
DIN_PATTERN = re.compile(r"^[A-Z0-9]{5}\d{2}\d{6}[A-Z0-9]$")
DIN_PATTERN_NO_CHECK = re.compile(r"^[A-Z0-9]{5}\d{2}\d{6}$")

# CORRECT:
DIN_PATTERN_14 = re.compile(r"^[A-Z][A-Z0-9]{4}\d{2}\d{6}[A-Z0-9*]$")
DIN_PATTERN_13 = re.compile(r"^[A-Z][A-Z0-9]{4}\d{2}\d{6}$")
```

The current regex allows `09999...` as a valid DIN — a digit in position 1 is invalid per ICCBBA.

### Bug 2: Check character excludes asterisk

The current 14-char pattern `[A-Z0-9]$` does not accept `*` as the check character.
ISO 7064 Mod 37,2 can produce `*` as a valid check digit.

### Bug 3: DINCase model max_length

```python
# CURRENT:
class DINCase(BaseModel):
    din: str = Field(max_length=13)

# CORRECT:
class DINCase(BaseModel):
    din: str = Field(min_length=13, max_length=13)
```

The model should enforce exactly 13 characters (the DIN only, no check char stored).
The current `max_length=13` allows shorter strings. Add `min_length=13`.

---

## Cellular Therapy Context

- ISBT 128 is endorsed for cellular therapy by FACT, JACIE, NMDP, WMDA, ASTCT, ISCT, EBMT
- All products from the same donation event share the same DIN
- For HSC products, the DIN is assigned by the collection facility or registry
- The MPHO Unique Identifier (29 chars) = Processing FIN (5) + PDC (5) + DIN (13) + Division Code (6)
- Product Code (8 chars) = Product Description Code (5) + collection/division info (3)
- The DIN is NOT the Product Code — they work together for full traceability

---

## Reference Files

- `references/din_spec.md` — Full DIN structure, validation rules, and examples
- `references/check_character.md` — ISO 7064 Mod 37,2 algorithm details and python-stdnum usage
- `references/known_bugs.md` — Current codebase bugs with fix patches

---

## Quick Reference Card

| Question | Answer |
|----------|--------|
| DIN length? | Exactly 13 characters |
| First char? | Alpha (A-Z) only |
| Positions 2-5? | `[A-Z0-9]` (currently numeric, alpha may come) |
| Positions 6-7? | Digits only (year code) |
| Positions 8-13? | Digits only (sequence) |
| Check char algorithm? | ISO 7064 Mod 37,2 |
| Check char charset? | `A-Z`, `0-9`, `*` (37 values) |
| Check char input? | 13-char DIN only (no flags) |
| python-stdnum usage? | `mod_37_2.validate(din_14)` or `mod_37_2.calc_check_digit(din_13)` |
| Storage length? | 13 chars (strip check char before storing) |
| Year code meaning? | Uniqueness support, NOT collection date |
| Flag characters? | 2 chars, NOT part of DIN, `00` when unused |
