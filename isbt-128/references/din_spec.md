# DIN Structure — Full Specification Reference

> Source: ICCBBA Technical Specification ST-001, PMC3012209, PMC6916302, ICCBBA FAQ

---

## 1. The 13-Character DIN

The Donation Identification Number (DIN) is a 13-character, globally unique identifier
that remains unique for a minimum of 100 years.

### Structure

```
α p p p p y y n n n n n n
1 2 3 4 5 6 7 8 9 0 1 2 3
├── FIN ──┤├YY┤├─ SEQ ───┤
```

| Position | Width | Name | Character Set | Description |
|----------|-------|------|---------------|-------------|
| 1 | 1 | Country/region indicator | `[A-Z]` | First character of FIN. Always alphabetic. |
| 2-5 | 4 | FIN remainder | `[0-9]` currently, `[A-Z0-9]` future | Facility code. Positions 2-3 may become alpha. |
| 6-7 | 2 | Year code | `[0-9]{2}` | 2-digit year for uniqueness. NOT a collection date. |
| 8-13 | 6 | Sequence number | `[0-9]{6}` | Assigned by facility. Unique within FIN+year for 100 years. |

### Key Points

- The DIN is **exactly 13 characters**. No more, no less.
- The first character MUST be alphabetic (A-Z). A DIN starting with a digit is invalid.
- The year code does NOT represent the collection date. It is solely for supporting 100-year uniqueness.
- The sequence number is assigned by the facility and must be unique within that facility's FIN and year code combination across a 100-year cycle.
- All products derived from a single donation event share the same DIN.

---

## 2. Data Structure 001 (16 Characters)

The DIN is embedded in ISBT 128 "Data Structure 001" which adds flag characters and a check character:

```
[DIN: 13 chars][FLAGS: 2 chars][CHECK: 1 char]
 αppppyynnnnnn    FF              K
```

### Flag Characters (positions 14-15)

Three types exist:

| Type | Purpose | Examples |
|------|---------|---------|
| Type 1 | ICCBBA-defined process control | `01` = Container 1 of a set |
| Type 2 | Locally defined by facility | Meaning varies by facility |
| Type 3 | ISO 7064 Mod 37-2 check on DIN | Secondary check within barcode |

When flags are not used, the value is `00`.

Flag characters are **NOT part of the DIN** and do NOT contribute to unique identification.

### Check Character (position 16)

- Algorithm: ISO/IEC 7064 Modulo 37,2
- Calculated from the **13-character DIN only** (flags excluded)
- Valid characters: `0-9`, `A-Z`, `*` (37 possible values)
- Required by ISBT 128 for keyboard entry validation
- When printed, enclosed in a box for visual distinction

---

## 3. Eye-Readable Presentation

DINs are printed in grouped format with spaces:

```
FIN   YY  NNNNNN  FF  [K]
A9999 14  123458  00  [J]
```

The check character appears boxed. Flag characters may be rotated 90 degrees on labels.

---

## 4. Validation Rules

### Accept as valid DIN:
- 13 characters matching `^[A-Z][A-Z0-9]{4}\d{2}\d{6}$`
- 14 characters matching `^[A-Z][A-Z0-9]{4}\d{2}\d{6}[A-Z0-9*]$` where char 14 passes `mod_37_2.validate()`

### Reject as invalid:
- Empty or whitespace-only
- Length not 13 or 14
- First character is a digit
- Positions 6-7 contain non-digits
- Positions 8-13 contain non-digits
- 14-character input where check character fails `mod_37_2.validate()`

### Normalize before validation:
- Strip leading/trailing whitespace
- Convert to uppercase

### Storage:
- Always store exactly 13 characters (the DIN itself)
- Strip the check character after validation
- Strip flag characters if present (positions 14-15 of a 16-char input)

---

## 5. Examples

### Valid DINs

| DIN (13 chars) | FIN | Year | Sequence | Check Char | Notes |
|----------------|-----|------|----------|------------|-------|
| `A999914123458` | A9999 | 14 | 123458 | J | ICCBBA verified example |
| `W123426000123` | W1234 | 26 | 000123 | (compute) | Typical test DIN |
| `T000126999999` | T0001 | 26 | 999999 | (compute) | Max sequence |
| `Z999900000001` | Z9999 | 00 | 000001 | (compute) | Year code 00 |

### Invalid DINs

| Input | Reason |
|-------|--------|
| `0999914123458` | First char is digit (must be alpha) |
| `A99991412345` | Only 12 chars (too short) |
| `A99991412345800` | 15 chars (too long for DIN, too short for DS001) |
| `ABCDE14123458` | Positions 6-7 not digits |
| `A999914ABCDEF` | Positions 8-13 not digits |
| `A9999141234580` | Check char `0` is wrong for this DIN |
| `` | Empty string |
| `   ` | Whitespace only |
