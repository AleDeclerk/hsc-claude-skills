# ORM^O01 — Lab Order: Field Reference

Used to generate the HSC donor test panel in Epic Beaker (US-005).
Orders are placed under the Donor ID — **never under the recipient's MRN**.

## Message Structure

```
MSH — Message Header
PID — Patient Identification  ← Donor ID (anonymous, same rules as ADT^A04)
[For each test in panel:]
  ORC — Common Order
  OBR — Observation Request
```

## ORC Segment

| Field  | Name                      | Value / Notes              |
|--------|---------------------------|----------------------------|
| ORC-1  | Order Control             | `NW` (New Order)           |
| ORC-2  | Placer Order Number       | unique order ID, e.g. `ORD123456` |
| ORC-5  | Order Status              | `SC` (Scheduled)           |
| ORC-9  | Date/Time of Transaction  | `YYYYMMDDHHMMSS`           |

## OBR Segment

| Field  | Name                      | Value / Notes                         |
|--------|---------------------------|---------------------------------------|
| OBR-1  | Set ID                    | sequence number per test (1, 2, 3...) |
| OBR-2  | Placer Order Number       | same as ORC-2                         |
| OBR-4  | Universal Service ID      | `{LOINC}^{TestName}^LN`               |
| OBR-6  | Requested Date/Time       | `YYYYMMDDHHMMSS`                      |
| OBR-13 | Relevant Clinical Info    | `DIN={DIN}` for traceability          |
| OBR-18 | Placer Field 1            | DIN (ISBT-128)                        |
| OBR-19 | Placer Field 2            | Donor ID                              |

## LOINC Panel by Product Type

### PBSC (Peripheral Blood Stem Cells)
| LOINC    | Test Name          | Unit      |
|----------|--------------------|-----------|
| 18207-3  | CD34+ count        | 10*6/kg   |
| 883-9    | ABO group          | —         |
| 10331-7  | Rh type            | —         |
| 6690-2   | WBC count          | 10*3/uL   |
| 600-7    | Sterility culture  | —         |
| 13949-3  | CMV IgG            | —         |
| 7917-8   | HIV-1/2 Ab         | —         |
| 5196-1   | HBsAg              | —         |
| 16128-1  | HCV Ab             | —         |
| 31201-7  | HTLV-I/II          | —         |
| 20507-0  | Syphilis RPR       | —         |

### BM (Bone Marrow) — same as PBSC plus:
| LOINC    | Test Name          | Unit      |
|----------|--------------------|-----------|
| 26499-4  | Nucleated RBC      | 10*3/uL   |

### CB (Cord Blood) — PBSC minus WBC, plus:
| LOINC    | Test Name          | Unit      |
|----------|--------------------|-----------|
| 26515-7  | Platelet count     | 10*3/uL   |

## Duplicate Order Suppression

If NMDP documentation already contains a validated result for a LOINC code,
that test is excluded from the ORM^O01. Pass `--skip-tests {loinc,loinc}` to
`generate_orm_o01.py`, or set `orders_to_suppress` in the agent config.

---

# ORU^R01 — Observation Result: Field Reference

Used to route validated donor results to the recipient's Epic chart (US-007).
Results appear in Epic under a "Donor Product — DIN XXXX" header — not as the
patient's own labs.

## Message Structure

```
MSH — Message Header
PID — Patient Identification  ← RECIPIENT MRN (for Epic routing)
OBR — Observation Request     ← Report header referencing DIN
OBX (×N) — Observation Result ← One per test result
```

## PID for Recipient (ORU only)

In ORU^R01, PID carries the **recipient's MRN** so Epic routes to the correct chart.
This is the only message type where the MRN appears — and it is resolved from the
encrypted linking table by the agent immediately before send.

| Field | Value                            |
|-------|----------------------------------|
| PID-3 | `{MRN}^^^{Facility}^MRN`         |

## OBR Report Header

| Field  | Value                                            |
|--------|--------------------------------------------------|
| OBR-4  | `99DONOR^Donor Product - DIN {DIN}^L`            |
| OBR-18 | DIN                                              |
| OBR-19 | Donor ID                                         |
| OBR-13 | `DIN={DIN}` — clinical info field for traceability |

## OBX Segment (per result)

| Field   | Name                      | Value / Notes                        |
|---------|---------------------------|--------------------------------------|
| OBX-1   | Set ID                    | sequence (1, 2, 3...)                |
| OBX-2   | Value Type                | `NM` (numeric) or `ST` (string)      |
| OBX-3   | Observation Identifier    | `{LOINC}^{TestName}^LN`              |
| OBX-5   | Observation Value         | result value                         |
| OBX-6   | Units                     | `{unit}^^ISO+`                       |
| OBX-8   | Abnormal Flags            | `H`=High, `L`=Low, `A`=Abnormal, empty=Normal |
| OBX-11  | Result Status             | `F`=Final, `P`=Preliminary, `C`=Corrected |
| OBX-14  | Date/Time of Observation  | `YYYYMMDDHHMMSS`                     |

## Result Status Values

| Code | Meaning       | Agent Action                              |
|------|---------------|-------------------------------------------|
| `F`  | Final         | Proceed to validation logic (US-006)      |
| `P`  | Preliminary   | Wait for final before release             |
| `C`  | Corrected     | Re-run validation, notify physician       |
| `X`  | Cannot Obtain | Escalate to Lab Supervisor                |

## Anomaly Detection (US-006)

After receiving ORU^R01 from SoftBank, agent compares each OBX-5 value against
configured ranges. If OBX-8 is non-empty or value is outside configured thresholds:

1. Create structured anomaly alert (test name, value, expected range, care plan context)
2. Route to attending physician + Medical Director via Epic In-Basket
3. Block PRODUCT_RELEASED event until physician override or result correction

## Example ORU^R01

```
MSH|^~\&|VERITAS|LSU_SCL|EPIC|LSU|20260311140000||ORU^R01|ORU87654321|P|2.5.1
PID|1||MRN123456^^^LSU^MRN
OBR|1||RES654321|99DONOR^Donor Product - DIN W000055508D001^L|||20260311140000|20260311140000|||||DIN=W000055508D001||20260311140000|||W000055508D001|DONOR-2026-0042
OBX|1|NM|18207-3^CD34+ count^LN||3.2|10*6/kg^^ISO+||N|||F|||20260311135000
OBX|2|ST|883-9^ABO group^LN||O||||||F|||20260311135000
OBX|3|ST|10331-7^Rh type^LN||Positive||||||F|||20260311135000
OBX|4|ST|600-7^Sterility culture^LN||Negative||||||F|||20260311135000
OBX|5|ST|7917-8^HIV-1/2 Ab^LN||Non-reactive||||||F|||20260311135000
```
