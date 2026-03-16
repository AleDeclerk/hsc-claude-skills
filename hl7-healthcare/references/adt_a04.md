# ADT^A04 — Register a Patient: Field Reference

Used for anonymous donor registration in SoftBank (US-003).

## Message Structure

```
MSH — Message Header
EVN — Event Type
PID — Patient Identification  ← donor identity (anonymous)
PV1 — Patient Visit           ← minimal, patient class O
```

## MSH Segment

| Field | Name                  | Value / Notes                    |
|-------|-----------------------|----------------------------------|
| MSH-1 | Field Separator       | `\|`                             |
| MSH-2 | Encoding Characters   | `^~\&`                           |
| MSH-3 | Sending Application   | `VERITAS`                        |
| MSH-4 | Sending Facility      | `LSU_SCL`                        |
| MSH-5 | Receiving Application | `SOFTBANK`                       |
| MSH-6 | Receiving Facility    | `LSU`                            |
| MSH-7 | Date/Time of Message  | `YYYYMMDDHHMMSS` (UTC)           |
| MSH-8 | Security              | empty                            |
| MSH-9 | Message Type          | `ADT^A04`                        |
| MSH-10| Message Control ID    | unique per message, e.g. `MSG00123456` |
| MSH-11| Processing ID         | `P` (production) or `T` (test)   |
| MSH-12| Version ID            | `2.5.1`                          |

## EVN Segment

| Field | Name                    | Value / Notes      |
|-------|-------------------------|--------------------|
| EVN-1 | Event Type Code         | `A04`              |
| EVN-2 | Recorded Date/Time      | `YYYYMMDDHHMMSS`   |
| EVN-6 | Event Occurred          | same as EVN-2      |

## PID Segment — Anonymous Donor Rules

> **CRITICAL**: These rules are required by FDA 21 CFR Part 1271 and FACT/JACIE.
> Deviation constitutes a regulatory violation.

| Field  | Name                  | Required Value              | Reason                        |
|--------|-----------------------|-----------------------------|-------------------------------|
| PID-1  | Set ID                | `1`                         | —                             |
| PID-2  | Patient ID (ext)      | empty                       | deprecated field              |
| PID-3  | Patient Identifier List | `{DIN}^^^LSU_SCL^DIN~{DonorID}^^^LSU_SCL^DONOR_ID` | ICCBBA DIN + internal ID |
| PID-4  | Alternate Patient ID  | empty                       | deprecated field              |
| PID-5  | Patient Name          | `ANONYMOUS^DONOR^^^^^L`    | **NO real name — regulatory** |
| PID-6  | Mother's Maiden Name  | empty                       | not applicable                |
| PID-7  | Date of Birth         | `00010101`                  | **placeholder — NO real DOB** |
| PID-8  | Administrative Sex    | `U`                         | Unknown — no real sex         |
| PID-9  | Patient Alias         | empty                       | —                             |
| PID-11 | Patient Address       | empty                       | anonymity                     |
| PID-13 | Phone Home            | empty                       | anonymity                     |
| PID-19 | SSN                   | **NEVER POPULATE**          | federal regulation            |

### PID-3 Component Breakdown

```
{DIN}^^^{AssigningAuthority}^DIN~{DonorID}^^^{AssigningAuthority}^DONOR_ID
```

- Component 1: ID value (DIN or Donor ID)
- Component 2: empty
- Component 3: empty  
- Component 4: Assigning Authority (`LSU_SCL`)
- Component 5: ID Type Code (`DIN` or `DONOR_ID`)

Example:
```
W000055508D001^^^LSU_SCL^DIN~DONOR-2026-0042^^^LSU_SCL^DONOR_ID
```

## PV1 Segment

| Field  | Name          | Value | Notes                               |
|--------|---------------|-------|-------------------------------------|
| PV1-1  | Set ID        | `1`   | —                                   |
| PV1-2  | Patient Class | `O`   | Outpatient — donor is not admitted  |

## Full Example Message

```
MSH|^~\&|VERITAS|LSU_SCL|SOFTBANK|LSU|20260311120000||ADT^A04|MSG00123456|P|2.5.1
EVN|A04|20260311120000||||20260311120000
PID|1||W000055508D001^^^LSU_SCL^DIN~DONOR-2026-0042^^^LSU_SCL^DONOR_ID||ANONYMOUS^DONOR^^^^^L||00010101|U
PV1|1|O
```

## ACK Response

SoftBank should respond with an ACK. Expected positive response:

```
MSH|^~\&|SOFTBANK|LSU|VERITAS|LSU_SCL|20260311120001||ACK|ACK00987654|P|2.5.1
MSA|AA|MSG00123456|Message accepted
```

- `AA` = Application Accept → proceed with workflow
- `AE` = Application Error → retry after alert to IT on-call
- `AR` = Application Reject → escalate to Lab Supervisor

## Error Handling

If SoftBank is unavailable:
1. Queue the ADT^A04 message
2. Alert IT on-call
3. Activate downtime protocol (US-010)
4. Retry on reconnection

If ACK returns AE:
1. Log error with raw message and response
2. Alert Lab Supervisor
3. Do not proceed to order generation (US-005) until registration confirmed
