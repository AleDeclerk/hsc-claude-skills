# ORU^R01 — Observation Result: Field Reference

Used to route donor lab results to the recipient's Epic chart (US-007, INT-07).
Results are attributed to the donor product (DIN), **never** to the recipient
as personal lab results.

## Message Structure

```
MSH — Message Header
PID — Patient Identification  ← Recipient MRN (Epic routing only)
OBR — Observation Request     ← Report header: "Donor Product — DIN {din}"
OBX 1 — DIN identifier        ← Custom field for Epic/WellSky routing
NTE 1 — Report header comment ← "Donor Product — DIN {din}"
OBX 2..N — Individual results ← One OBX per LOINC test
```

## MSH Segment

| Field   | Name                     | Value                  |
|---------|--------------------------|------------------------|
| MSH-3   | Sending Application      | `VERITAS`              |
| MSH-4   | Sending Facility         | `LSU_SCL`              |
| MSH-5   | Receiving Application    | `EPIC`                 |
| MSH-6   | Receiving Facility       | `LSU`                  |
| MSH-9   | Message Type             | `ORU^R01`              |
| MSH-11  | Processing ID            | `P` (production) / `T` (test) |
| MSH-12  | Version ID               | `2.5.1`                |

## PID Segment (Recipient)

The recipient's MRN is placed in PID so Epic routes results to the correct
patient chart. **No donor identity appears in PID.**

| Field   | Name                     | Value                           |
|---------|--------------------------|---------------------------------|
| PID-3   | Patient Identifier List  | `{mrn}^^^{facility}^MRN`       |

## OBR Segment

| Field   | Name                     | Value / Notes                                       |
|---------|--------------------------|-----------------------------------------------------|
| OBR-1   | Set ID                   | `1`                                                 |
| OBR-4   | Universal Service ID     | `99DONOR^Donor Product - DIN {din}^L`               |
| OBR-13  | Relevant Clinical Info   | `DIN={din}` — machine-readable DIN reference        |
| OBR-18  | Placer Field 1           | DIN value                                           |
| OBR-19  | Placer Field 2           | Internal Donor ID                                   |

## Epic/WellSky Custom Fields

These fields are required for WellSky middleware to correctly attribute
results to a donor product rather than the recipient patient.
Without them, results appear as the recipient's own labs — a compliance
and patient safety violation.

### OBX-1 — DIN Identifier

Immediately after the OBR, a special OBX segment identifies the donor product:

| Field   | Name                     | Value                                    |
|---------|--------------------------|------------------------------------------|
| OBX-1   | Set ID                   | `1`                                      |
| OBX-2   | Value Type               | `ST` (String)                            |
| OBX-3   | Observation Identifier   | `DIN^Donor Product Identifier^L`         |
| OBX-5   | Observation Value        | DIN string (e.g. `W000055508D001`)       |
| OBX-11  | Result Status            | `F` (Final)                              |

The coding system `L` in OBX-3.3 means **local** — this is an
institution-specific code, not a standard LOINC or SNOMED code.
WellSky uses this to tag the entire result block for donor routing in Epic.

### NTE-1 — Report Header Comment

Immediately after OBX-1, a NTE segment provides a human-readable label
that appears in the Epic result viewer:

| Field   | Name                     | Value                              |
|---------|--------------------------|------------------------------------|
| NTE-1   | Set ID                   | `1`                                |
| NTE-2   | Source of Comment        | *(empty — defaults to L=Lab)*      |
| NTE-3   | Comment                  | `Donor Product — DIN {din}`        |

This text appears as a header in the Epic chart result display, clearly
identifying the result block as donor product data, not recipient labs.

### WellSky Field Mapping Summary

| WellSky Field | HL7 Source                     | Purpose                         |
|---------------|--------------------------------|---------------------------------|
| ProductType   | OBX-3 (`DIN^...^L`)           | Flag for donor product routing  |
| ProductDIN    | OBX-5                          | Donor product identifier        |
| ReportHeader  | NTE-3                          | Epic display label              |
| DonorRef      | OBR-18                         | Machine-readable DIN            |
| DonorID       | OBR-19                         | Internal donor reference        |

## OBX Segments (Results, set_id 2..N)

Individual test results follow after the DIN OBX and NTE. Set IDs start at 2.

| Field   | Name                     | Value / Notes                              |
|---------|--------------------------|--------------------------------------------|
| OBX-2   | Value Type               | `NM` (numeric) or `ST` (string)           |
| OBX-3   | Observation Identifier   | `{loinc}^{name}^LN`                       |
| OBX-5   | Observation Value        | Result value                               |
| OBX-6   | Units                    | `{unit}^^ISO+`                             |
| OBX-8   | Abnormal Flags           | `A` (abnormal) or empty (normal)           |
| OBX-11  | Result Status            | `F` (Final), `P` (Preliminary), `C` (Corrected) |

## Anomaly Handling

Results with `abnormal: true` are flagged in OBX-8 with `A`.
The generator logs all anomalous results to stderr and returns them
in the `anomalies` list of the result dict.
