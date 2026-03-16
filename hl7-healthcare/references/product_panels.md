<<<<<<< HEAD
# Product-Specific Order Panels

Reference for HL7 ORM^O01 lab order generation. Each product type requires
a different test panel. Use the correct table when building OBR/OBX segments
for a given HSC product.

> **NMDP — do not reorder**: Tests already performed and documented by the
> sending registry (NMDP, World Marrow Donor Association, etc.). Results arrive
> pre-populated in the NMDP product documentation. Do not issue a duplicate
> lab order — import the result via ORU^R01 directly.
=======
# HSC Product Order Panels

Test panels for Hematopoietic Stem Cell products ordered via ORM^O01 in Epic Beaker.

> **NMDP — do not reorder**: Tests pre-validated in NMDP donor documentation. Suppress from
> ORM^O01 by passing the LOINC code to `--skip-tests` in `generate_orm_o01.py`.
>>>>>>> 9634376 (feat: skill-creator evals — 100% with-skill, CB panel fix, improved assertions)

---

## PBSC — Peripheral Blood Stem Cells

<<<<<<< HEAD
Mobilized with G-CSF; collected by apheresis.

| Test | LOINC | Notes |
|------|-------|-------|
| CD34+ cell count | 18207-3 | Primary engraftment predictor |
| CD3+ T-cell count | 8122-4 | — |
| ABO blood group | 883-9 | Required for compatibility |
| Rh factor | 10331-7 | Required for compatibility |
| WBC (white blood cell count) | 6690-2 | — |
| Sterility (bacterial/fungal) | 600-7 | Must be negative before release |
| CMV IgG | 13949-3 | NMDP — do not reorder |
| HIV-1/2 antibody | 7917-8 | NMDP — do not reorder |
| HBsAg (Hepatitis B surface antigen) | 5196-1 | NMDP — do not reorder |
| HCV antibody | 16128-1 | NMDP — do not reorder |
| HTLV-I/II antibody | 31201-7 | NMDP — do not reorder |
| Syphilis (RPR/VDRL) | 20507-0 | NMDP — do not reorder |
=======
| LOINC    | Test Name         | Unit       | Normal Range     | Source Notes           |
|----------|-------------------|------------|------------------|------------------------|
| 18207-3  | CD34+ count       | 10⁶/kg     | 2.0 – 5.0        | Required at collection |
| 883-9    | ABO group         | —          | See table        | NMDP — do not reorder  |
| 10331-7  | Rh type           | —          | Pos / Neg        | NMDP — do not reorder  |
| 6690-2   | WBC count         | 10³/µL     | Lab-specific     | Required at collection |
| 600-7    | Sterility culture | —          | Negative         | Required at collection |
| 13949-3  | CMV IgG           | —          | Neg (screen)     | NMDP — do not reorder  |
| 7917-8   | HIV-1/2 Ab        | —          | Non-reactive     | NMDP — do not reorder  |
| 5196-1   | HBsAg             | —          | Non-reactive     | NMDP — do not reorder  |
| 16128-1  | HCV Ab            | —          | Non-reactive     | NMDP — do not reorder  |
| 31201-7  | HTLV-I/II         | —          | Non-reactive     | NMDP — do not reorder  |
| 20507-0  | Syphilis RPR      | —          | Non-reactive     | NMDP — do not reorder  |
>>>>>>> 9634376 (feat: skill-creator evals — 100% with-skill, CB panel fix, improved assertions)

---

## BM — Bone Marrow

<<<<<<< HEAD
Collected by posterior iliac crest harvest under general or regional anesthesia.

| Test | LOINC | Notes |
|------|-------|-------|
| CD34+ cell count | 18207-3 | Primary engraftment predictor |
| ABO blood group | 883-9 | Required for compatibility |
| Rh factor | 10331-7 | Required for compatibility |
| WBC (white blood cell count) | 6690-2 | — |
| Sterility (bacterial/fungal) | 600-7 | Must be negative before release |
| CMV IgG | 13949-3 | NMDP — do not reorder |
| HIV-1/2 antibody | 7917-8 | NMDP — do not reorder |
| HBsAg (Hepatitis B surface antigen) | 5196-1 | NMDP — do not reorder |
| HCV antibody | 16128-1 | NMDP — do not reorder |
| HTLV-I/II antibody | 31201-7 | NMDP — do not reorder |
| Syphilis (RPR/VDRL) | 20507-0 | NMDP — do not reorder |

> **Note:** BM collections do not include CD3+ T-cell counts by default
> unless T-cell depletion is planned. Order separately if required by
> the treatment protocol.
=======
Same panel as PBSC. All infectious disease markers follow the same NMDP suppression rules.

| LOINC    | Test Name         | Unit       | Normal Range     | Source Notes           |
|----------|-------------------|------------|------------------|------------------------|
| 18207-3  | CD34+ count       | 10⁶/kg     | 2.0 – 5.0        | Required at collection |
| 883-9    | ABO group         | —          | See table        | NMDP — do not reorder  |
| 10331-7  | Rh type           | —          | Pos / Neg        | NMDP — do not reorder  |
| 6690-2   | WBC count         | 10³/µL     | Lab-specific     | Required at collection |
| 600-7    | Sterility culture | —          | Negative         | Required at collection |
| 13949-3  | CMV IgG           | —          | Neg (screen)     | NMDP — do not reorder  |
| 7917-8   | HIV-1/2 Ab        | —          | Non-reactive     | NMDP — do not reorder  |
| 5196-1   | HBsAg             | —          | Non-reactive     | NMDP — do not reorder  |
| 16128-1  | HCV Ab            | —          | Non-reactive     | NMDP — do not reorder  |
| 31201-7  | HTLV-I/II         | —          | Non-reactive     | NMDP — do not reorder  |
| 20507-0  | Syphilis RPR      | —          | Non-reactive     | NMDP — do not reorder  |
>>>>>>> 9634376 (feat: skill-creator evals — 100% with-skill, CB panel fix, improved assertions)

---

## CB — Cord Blood

<<<<<<< HEAD
Collected from umbilical cord blood at birth; cryopreserved in public or
private banks.

| Test | LOINC | Notes |
|------|-------|-------|
| CD34+ cell count | 18207-3 | Primary engraftment predictor |
| ABO blood group | 883-9 | Required for compatibility |
| Rh factor | 10331-7 | Required for compatibility |
| WBC (white blood cell count) | 6690-2 | — |
| Sterility (bacterial/fungal) | 600-7 | Must be negative before release |
| HbF (fetal hemoglobin) | 4576-5 | CB-specific; confirms fetal origin |
| TNC (total nucleated cell count) | 26498-6 | CB-specific; determines dose adequacy |
| Unit volume (mL) | 20612-7 | CB-specific; recorded at collection |
| CMV IgG | 13949-3 | NMDP — do not reorder |
| HIV-1/2 antibody | 7917-8 | NMDP — do not reorder |
| HBsAg (Hepatitis B surface antigen) | 5196-1 | NMDP — do not reorder |
| HCV antibody | 16128-1 | NMDP — do not reorder |
| HTLV-I/II antibody | 31201-7 | NMDP — do not reorder |
| Syphilis (RPR/VDRL) | 20507-0 | NMDP — do not reorder |

> **Note:** For CB units, TNC and unit volume are the primary dose adequacy
> metrics used at LSU. Minimum TNC thresholds are defined in the transplant
> protocol. Always verify against the cryopreservation record.

---

## Selecting the Correct Panel

When building an ORM^O01 message, select the panel based on the product
type encoded in the DIN (ISBT-128 product code, positions 6–10):

| ISBT-128 Product Code | Product Type |
|-----------------------|-------------|
| E0178 | PBSC (mobilized, apheresis) |
| E0182 | Bone Marrow |
| E0192 | Cord Blood |

If the product code is unknown or absent, default to the PBSC panel and
flag for manual review.
=======
Same as BM plus cord blood–specific viability and composition tests.

| LOINC    | Test Name              | Unit       | Normal Range     | Source Notes           |
|----------|------------------------|------------|------------------|------------------------|
| 18207-3  | CD34+ count            | 10⁶/kg     | ≥ 1.5            | Required at collection |
| 883-9    | ABO group              | —          | See table        | NMDP — do not reorder  |
| 10331-7  | Rh type                | —          | Pos / Neg        | NMDP — do not reorder  |
| 6690-2   | WBC count              | 10³/µL     | Lab-specific     | Required at collection |
| 600-7    | Sterility culture      | —          | Negative         | Required at collection |
| 13949-3  | CMV IgG                | —          | Neg (screen)     | NMDP — do not reorder  |
| 7917-8   | HIV-1/2 Ab             | —          | Non-reactive     | NMDP — do not reorder  |
| 5196-1   | HBsAg                  | —          | Non-reactive     | NMDP — do not reorder  |
| 16128-1  | HCV Ab                 | —          | Non-reactive     | NMDP — do not reorder  |
| 31201-7  | HTLV-I/II              | —          | Non-reactive     | NMDP — do not reorder  |
| 20507-0  | Syphilis RPR           | —          | Non-reactive     | NMDP — do not reorder  |
| 4576-5   | HbF (fetal hemoglobin) | %          | > 60% in CB unit | Cord blood specific    |
| 26498-6  | TNC (total nucleated cell count) | 10⁷ | > 5.0 | Cord blood specific    |

### CB — Unit Volume

Cord blood units must also record collected volume (mL). This is captured in the collection
record and passed in OBX-5 as a `NM` value type with unit `mL^^ISO+`.

LOINC 19153-8 (Volume of blood collected) may be used for unit volume if required by the
cord blood bank SOP.

---

## NMDP Suppression in Practice

When importing an NMDP Work-Up Summary for a donor, extract validated result LOINCs and
pass them as `--skip-tests` to suppress duplicate orders:

```bash
python scripts/generate_orm_o01.py \
  --donor-id DONOR-2026-0042 \
  --din W000055508D001 \
  --product-type BM \
  --skip-tests "883-9,10331-7,13949-3,7917-8,5196-1,16128-1,31201-7,20507-0" \
  --output orders.hl7
```

This places orders only for CD34+, WBC, and Sterility — the tests not pre-validated by NMDP.

---

## Regulatory Notes

- **PBSC / BM**: Panels satisfy FACT/JACIE and NMDP Standards 12th edition minimum required testing.
- **CB**: HbF and TNC are required by FACT NetCord and AABB CB standards for unit release.
- **Infectious disease**: All infectious disease markers must be completed within 30 days of collection
  per FDA 21 CFR Part 1271.85. NMDP results are accepted if within this window.
>>>>>>> 9634376 (feat: skill-creator evals — 100% with-skill, CB panel fix, improved assertions)
