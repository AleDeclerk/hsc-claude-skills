# Known DIN Bugs in Current Codebase

> These bugs are confirmed against the ICCBBA ISBT-128 specification.

---

## Bug 1: FIN first character allows digits

**File**: `src/services/din_validator.py`
**Severity**: High — accepts invalid DINs

### Current code (wrong)

```python
DIN_PATTERN = re.compile(r"^[A-Z0-9]{5}\d{2}\d{6}[A-Z0-9]$")
DIN_PATTERN_NO_CHECK = re.compile(r"^[A-Z0-9]{5}\d{2}\d{6}$")
```

### Problem

`[A-Z0-9]{5}` allows the first character to be a digit. Per ICCBBA, the first character of the FIN
(and therefore the DIN) is the country/region indicator and MUST be alphabetic (A-Z).

Example: `09999141234580` would pass validation but is **invalid** — no FIN starts with a digit.

### Fix

```python
DIN_PATTERN_14 = re.compile(r"^[A-Z][A-Z0-9]{4}\d{2}\d{6}[A-Z0-9*]$")
DIN_PATTERN_13 = re.compile(r"^[A-Z][A-Z0-9]{4}\d{2}\d{6}$")
```

---

## Bug 2: Check character excludes asterisk

**File**: `src/services/din_validator.py`
**Severity**: Medium — rejects valid DINs with `*` check character

### Current code (wrong)

```python
DIN_PATTERN = re.compile(r"^[A-Z0-9]{5}\d{2}\d{6}[A-Z0-9]$")
#                                                    ^^^^^^^^
#                                                    Missing *
```

### Problem

ISO 7064 Mod 37,2 uses a 37-value character set: `0-9` (10), `A-Z` (26), `*` (1).
The asterisk is a valid check character. The current regex `[A-Z0-9]` rejects it.

### Fix

```python
# Include * in the check character position
DIN_PATTERN_14 = re.compile(r"^[A-Z][A-Z0-9]{4}\d{2}\d{6}[A-Z0-9*]$")
```

---

## Bug 3: DINCase model allows short DINs

**File**: `src/models/case.py`
**Severity**: Low-Medium — allows storing malformed DINs

### Current code (wrong)

```python
class DINCase(BaseModel):
    din: str = Field(max_length=13)
```

### Problem

`max_length=13` sets an upper bound but no lower bound. A 1-character string would pass
model validation. The DIN must be exactly 13 characters.

### Fix

```python
class DINCase(BaseModel):
    din: str = Field(min_length=13, max_length=13)
```

---

## Test Cases to Add

After fixing the bugs, add these test cases to `tests/unit/services/test_din_validator.py`:

```python
def test_digit_first_char_rejected(self):
    """FIN first character must be alpha — digit is invalid."""
    with pytest.raises(DINValidationError, match="Invalid format"):
        validate_din_format("09999141234580")

def test_asterisk_check_character_accepted(self):
    """ISO 7064 Mod 37,2 can produce * as check character."""
    # Find a DIN whose check char is * using calc_check_digit
    from stdnum.iso7064 import mod_37_2
    # Brute force a DIN with * check char for the test
    for seq in range(100000, 100100):
        din_13 = f"A999926{seq:06d}"
        if mod_37_2.calc_check_digit(din_13) == "*":
            assert validate_din_format(din_13 + "*") is True
            break

def test_13_char_min_length(self):
    """DIN must be at least 13 characters."""
    with pytest.raises(DINValidationError):
        validate_din_format("A999914")
```
