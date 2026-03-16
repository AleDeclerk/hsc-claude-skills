# ISO 7064 Mod 37,2 Check Character — Reference

> Source: ICCBBA ST-001 Appendix A.1/A.2, ISO/IEC 7064:2003

---

## Algorithm Overview

The ISBT 128 check character uses the **ISO/IEC 7064 Modulo 37,2** checksum.

- **Character set**: 37 characters — `0-9` (values 0-9), `A-Z` (values 10-35), `*` (value 36)
- **Input**: The 13-character DIN only. Flag characters are NOT included.
- **Output**: A single character from the 37-character set.

The asterisk `*` is a valid check character. Code that rejects `*` as a check character is buggy.

---

## Using python-stdnum

The `python-stdnum` library (version 2.2+) provides the `iso7064.mod_37_2` module:

### Calculate check character

```python
from stdnum.iso7064 import mod_37_2

din_13 = "A999914123458"
check_char = mod_37_2.calc_check_digit(din_13)
print(check_char)  # "J"
```

### Validate DIN + check character

```python
from stdnum.iso7064 import mod_37_2

din_14 = "A999914123458J"
try:
    mod_37_2.validate(din_14)
    print("Valid")
except Exception:
    print("Invalid check character")
```

### Important API notes

| Function | Input | Returns | Raises |
|----------|-------|---------|--------|
| `mod_37_2.calc_check_digit(din_13)` | 13-char DIN | Single check character | `InvalidFormat` if input invalid |
| `mod_37_2.validate(din_14)` | 14-char string (DIN + check) | The validated string | `InvalidChecksum` if check fails |
| `mod_37_2.is_valid(din_14)` | 14-char string | `True` or `False` | Never raises |

---

## Verified Examples

| DIN (13 chars) | Check Character | DIN+Check (14 chars) | Source |
|----------------|----------------|---------------------|--------|
| `A999914123458` | `J` | `A999914123458J` | ICCBBA documentation |

### Verification script

```python
from stdnum.iso7064 import mod_37_2

# ICCBBA verified example
assert mod_37_2.calc_check_digit("A999914123458") == "J"
assert mod_37_2.is_valid("A999914123458J") is True
assert mod_37_2.is_valid("A9999141234580") is False  # wrong check char
```

---

## Common Mistakes

1. **Calling `validate()` on the 13-char DIN** — This will fail because `validate()` expects the string to INCLUDE the check digit. Use `calc_check_digit()` on the 13-char DIN, or `validate()` on the 14-char string.

2. **Excluding `*` from allowed characters** — The Mod 37,2 algorithm can produce `*` (value 36) as a valid check digit. Any regex or validation that uses `[A-Z0-9]` without `*` will reject valid DINs.

3. **Including flag characters in the check calculation** — Flag characters are NOT part of the DIN and must NOT be included when computing or validating the check character.

4. **Treating the check character as part of the DIN** — The check character is for keyboard entry validation only. The DIN is always 13 characters. Store 13 characters in the database.
