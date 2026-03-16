# LOINC Codes for HSC Products — Complete Reference

> Source: loinc.org verified entries, AABB donor testing guidelines, FACT-JACIE Standards

---

## 1. Cell Characterization Tests

| LOINC | Long Name | Property | Specimen | Units | Method |
|-------|-----------|----------|----------|-------|--------|
| `42808-4` | CD34 cells [#/volume] in Blood | NCnc | Blood | cells/uL | Flow cytometry |
| `8125-7` | CD34 cells/100 cells in Blood | NFr | Blood | % | Flow cytometry |
| `80698-4` | Viable CD34 cells/CD34 cells in HPC product unit | NFr | HPC product | % | Flow + viability dye |
| `26464-8` | Leukocytes [#/volume] in Blood by Automated count | NCnc | Blood | 10*3/uL | Automated |
| `26515-7` | Platelets [#/volume] in Blood by Automated count | NCnc | Blood | 10*3/uL | Automated |
| `718-7` | Hemoglobin [Mass/volume] in Blood | MCnc | Blood | g/dL | Automated |
| `55793-4` | Nucleated cells [#/volume] in Body fluid | NCnc | Body fluid | cells/uL | Manual/Automated |
| `34542-1` | Cell viability [%] in Body fluid | NFr | Body fluid | % | Trypan blue / 7-AAD |

### Key Notes

- **`42808-4` vs `58410-2`**: Code `42808-4` is the correct LOINC for CD34+ cell count. Code `58410-2` is "CBC panel - Blood by Automated count" — a completely different test. Using `58410-2` for CD34 is a data error.
- **TNC count (`55793-4`)**: Total Nucleated Cell count is critical for cord blood and processed products. Specimen type is "Body fluid" (not "Blood") because it applies to the processed product.
- **Cell viability (`34542-1`)**: Minimum acceptable viability is typically >= 70% post-thaw. This is a release criterion.

---

## 2. ABO/Rh Typing

| LOINC | Long Name | Property | Specimen | Result Values |
|-------|-----------|----------|----------|---------------|
| `882-1` | ABO group [Type] in Blood | Type | Blood | A, B, AB, O |
| `10331-7` | Rh [Type] in Blood | Type | Blood | Pos, Neg |
| `34532-2` | Blood type and Indirect antibody screen panel - Blood | — | Blood | Panel result |

### Key Notes

- ABO/Rh typing is **mandatory** for all HSC products per FACT standards
- ABO incompatibility between donor and recipient requires special processing (red cell depletion or plasma reduction) but does NOT make the product ineligible
- The comprehensive panel (`34532-2`) includes antibody screen which detects clinically significant antibodies

---

## 3. Infectious Disease Screening

### 3.1 HIV Testing

| LOINC | Long Name | Method | FDA Requirement |
|-------|-----------|--------|-----------------|
| `62469-2` | HIV 1+2 Ab+Ag [Presence] in Serum or Plasma by Immunoassay | 4th gen combo | Preferred — covers HIV-1/2 Ab + p24 Ag |
| `68961-2` | HIV 1 Ab [Presence] in Serum, Plasma or Blood by Rapid immunoassay | Rapid | Alternative |
| `29893-5` | HIV 1 Ab [Presence] in Serum or Plasma by Immunoassay | Standard | Alternative |
| `30361-0` | HIV 2 Ab [Presence] in Serum or Plasma by Immunoassay | Standard | Required if not using combo |
| `5196-1` | HIV 1 RNA [Presence] in Serum or Plasma by NAT | NAT | Required (nucleic acid test) |

### 3.2 Hepatitis B Testing

| LOINC | Long Name | Method | FDA Requirement |
|-------|-----------|--------|-----------------|
| `5195-3` | HBsAg [Presence] in Serum by Immunoassay | Immunoassay | Required (surface antigen) |
| `16933-4` | Hepatitis B virus core Ab [Presence] in Serum | Immunoassay | Required (core antibody, total) |
| `42595-7` | Hepatitis B virus DNA [Presence] in Serum or Plasma by NAT | NAT | Required (nucleic acid test) |

### 3.3 Hepatitis C Testing

| LOINC | Long Name | Method | FDA Requirement |
|-------|-----------|--------|-----------------|
| `16128-1` | Hepatitis C virus Ab [Presence] in Serum | Immunoassay | Required |
| `7905-3` | Hepatitis C virus RNA [Presence] in Serum or Plasma by NAT | NAT | Required |

### 3.4 Syphilis Testing

| LOINC | Long Name | Method | FDA Requirement |
|-------|-----------|--------|-----------------|
| `22587-0` | Treponema pallidum Ab [Presence] in Serum | Treponemal | Screen option 1 |
| `20507-0` | Reagin Ab [Presence] in Serum by RPR | Non-treponemal | Screen option 2 |

### 3.5 CMV Testing (Viable Leukocyte-Rich Only)

| LOINC | Long Name | Method | FDA Requirement |
|-------|-----------|--------|-----------------|
| `22244-8` | Cytomegalovirus IgG Ab [Mass/volume] in Serum | Immunoassay | Required for HSC |
| `5124-3` | Cytomegalovirus IgM Ab [Presence] in Serum | Immunoassay | Required for HSC |

**Important**: CMV positive does NOT make the donor ineligible. Result must be communicated to the accepting transplant physician.

### 3.6 HTLV Testing (Viable Leukocyte-Rich Only)

| LOINC | Long Name | Method | FDA Requirement |
|-------|-----------|--------|-----------------|
| `7942-6` | HTLV I+II Ab [Presence] in Serum | Immunoassay | Required for HSC |

---

## 4. Sterility / Microbiology

| LOINC | Long Name | Specimen | Culture Type |
|-------|-----------|----------|-------------|
| `630-4` | Bacteria identified in Blood by Culture | Blood culture | Aerobic |
| `635-3` | Bacteria identified in Body fluid by Culture | Product culture | Sterility |
| `580-1` | Fungus identified in Body fluid by Culture | Product culture | Fungal |

### Key Notes

- Sterility testing is required for all processed HSC products per FACT standards
- Culture results may take 7-14 days; product may be released before final culture if clinically urgent
- Positive cultures require immediate notification and escalation

---

## 5. LOINC Code Validation Set

All 31 recognized HSC panel LOINC codes:

```
42808-4  8125-7   80698-4  26464-8  26515-7  718-7    55793-4  34542-1
882-1    10331-7  34532-2
62469-2  68961-2  29893-5  30361-0  5196-1
5195-3   16933-4  42595-7
16128-1  7905-3
22587-0  20507-0
22244-8  5124-3
7942-6
630-4    635-3    580-1
```

Any LOINC code in a clinical config `test_panels` entry should be checked against this set. Codes not in this set may be valid LOINC but are not recognized HSC panel codes and should trigger a warning.
