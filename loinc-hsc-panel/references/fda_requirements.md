# FDA Donor Testing Requirements for HCT/Ps

> Source: 21 CFR 1271.85, FDA Guidance Documents

---

## Regulatory Framework

The FDA regulates human cells, tissues, and cellular and tissue-based products (HCT/Ps) under 21 CFR Part 1271. Section 1271.85 specifies mandatory donor testing.

HSC products (PBSC, bone marrow, cord blood) are classified as HCT/Ps and fall under these requirements.

---

## 1. Required Tests — ALL HCT/P Donors (21 CFR 1271.85(a))

| Agent | Test Type | LOINC Options | Notes |
|-------|-----------|---------------|-------|
| HIV-1 | Antibody | `62469-2` (combo, preferred), `68961-2` (rapid), `29893-5` (standard) | |
| HIV-2 | Antibody | `62469-2` (combo), `30361-0` (separate) | Combo test covers both |
| HIV-1 | NAT | `5196-1` | Nucleic acid test always required |
| HBV | Surface Antigen | `5195-3` | HBsAg |
| HBV | Core Antibody | `16933-4` | Anti-HBc (total IgG/IgM) |
| HBV | NAT | `42595-7` | HBV DNA |
| HCV | Antibody | `16128-1` | Anti-HCV |
| HCV | NAT | `7905-3` | HCV RNA |
| Syphilis | Treponemal OR non-treponemal | `22587-0` (treponemal) or `20507-0` (RPR) | Either one acceptable |

---

## 2. Additional Tests — Viable Leukocyte-Rich HCT/Ps (21 CFR 1271.85(b))

HSC products are viable leukocyte-rich HCT/Ps, so these are REQUIRED:

| Agent | Test Type | LOINC | Notes |
|-------|-----------|-------|-------|
| CMV | IgG Antibody | `22244-8` | Quantitative or qualitative |
| CMV | IgM Antibody | `5124-3` | Active infection marker |
| HTLV-I/II | Antibody | `7942-6` | Screening test |

### CMV Special Rule

A positive CMV result does NOT make the donor ineligible. Per FDA guidance:
- The CMV status must be communicated to the accepting transplant physician
- The physician decides whether to accept the product based on recipient CMV status
- This is a clinical decision, NOT an automatic disqualification

---

## 3. Minimum LOINC Set for FDA Compliance

The absolute minimum set of LOINC codes to satisfy 21 CFR 1271.85 for an HSC donor:

```python
FDA_MINIMUM_INFECTIOUS_DISEASE = [
    "62469-2",  # HIV 1+2 Ab+Ag (4th gen combo — covers HIV-1 and HIV-2)
    "5196-1",   # HIV 1 RNA (NAT)
    "5195-3",   # HBsAg
    "16933-4",  # HBc Ab (total)
    "42595-7",  # HBV DNA (NAT)
    "16128-1",  # HCV Ab
    "7905-3",   # HCV RNA (NAT)
    "22587-0",  # T. pallidum Ab (syphilis)
    "22244-8",  # CMV IgG (viable leukocyte-rich)
    "5124-3",   # CMV IgM (viable leukocyte-rich)
    "7942-6",   # HTLV I/II Ab (viable leukocyte-rich)
]
```

That's 11 infectious disease tests minimum for HSC donors.

---

## 4. Testing Timing

- **Allogeneic donors**: Test within 30 days before or 7 days after collection
- **Autologous donors**: Testing requirements may differ; consult facility SOP
- **Cord blood**: Mother's blood is tested as surrogate; cord blood segment tested separately

---

## 5. Result Interpretation for Donor Eligibility

| Result | Action |
|--------|--------|
| All Negative/Non-reactive | Donor eligible — proceed with product processing |
| Any Reactive (except CMV) | Donor NOT eligible — escalate per SOP, product cannot be distributed |
| CMV Positive | Donor still eligible — communicate to transplant physician |
| Indeterminate | Repeat testing required; escalate if still indeterminate |

---

## 6. Regulatory References

| Document | Section | Content |
|----------|---------|---------|
| 21 CFR 1271.85(a) | Required testing - all donors | HIV, HBV, HCV, syphilis |
| 21 CFR 1271.85(b) | Required testing - viable leukocyte-rich | CMV, HTLV |
| 21 CFR 1271.80 | Donor eligibility determination | Overall eligibility framework |
| 21 CFR 1271.55 | What testing documentation must show | Records requirements |
