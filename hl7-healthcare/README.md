# hl7-healthcare

> **Claude Agent Skill** — Generate, validate, parse, and transmit HL7 v2 messages for healthcare interoperability workflows.

Built for clinical lab, stem cell, and hospital integration use cases — including anonymous donor handling compliant with FDA 21 CFR Part 1271 and FACT/JACIE standards.

---

## What this skill does

- **Generates** ADT^A04, ORM^O01, and ORU^R01 messages with correct field mapping
- **Validates** any HL7 v2 message for structural correctness and anonymous donor compliance
- **Parses** messages into human-readable segment/field breakdowns
- **Transmits** messages via MLLP over TCP (SoftBank, Epic Beaker, WellSky, etc.)

## Supported Message Types

| Message     | Use Case                                           |
|-------------|----------------------------------------------------|
| `ADT^A04`   | Register anonymous HSC donor in SoftBank           |
| `ORM^O01`   | Generate lab order panels in Epic Beaker           |
| `ORU^R01`   | Route donor results to recipient's Epic chart      |
| `ACK`       | Parse MLLP acknowledgment responses                |

## Install

```bash
# Claude Code — global install
git clone https://github.com/AleDeclerk/hl7-healthcare ~/.claude/skills/hl7-healthcare

# Claude Code — project install
git clone https://github.com/AleDeclerk/hl7-healthcare .claude/skills/hl7-healthcare
```

Claude will automatically discover and use the skill for HL7-related tasks.

## Requirements

- Python 3.8+
- No external dependencies (stdlib only)

## Quick Start

```bash
# 1. Generate anonymous donor registration message
python scripts/generate_adt_a04.py \
  --din "W000055508D001" \
  --donor-id "DONOR-2026-0042" \
  --output donor_reg.hl7

# 2. Validate it
python scripts/validate_hl7.py --file donor_reg.hl7 --check-anonymous

# 3. Send via MLLP
python scripts/mllp_sender.py \
  --host softbank.lsu.edu \
  --port 2575 \
  --file donor_reg.hl7

# 4. Generate lab order panel (PBSC, skip ABO already done by NMDP)
python scripts/generate_orm_o01.py \
  --donor-id "DONOR-2026-0042" \
  --din "W000055508D001" \
  --product-type PBSC \
  --skip-tests "883-9,10331-7" \
  --output orders.hl7

# 5. Route results to Epic
python scripts/generate_oru_r01.py \
  --donor-id "DONOR-2026-0042" \
  --recipient-mrn "MRN123456" \
  --din "W000055508D001" \
  --results-file results.json \
  --output result_message.hl7
```

## File Layout

```
hl7-healthcare/
├── SKILL.md                        ← Claude skill instructions
├── README.md                       ← This file
├── scripts/
│   ├── generate_adt_a04.py         ← Anonymous donor registration (ADT^A04)
│   ├── generate_orm_o01.py         ← Lab order panel (ORM^O01)
│   ├── generate_oru_r01.py         ← Results routing (ORU^R01)
│   ├── validate_hl7.py             ← Message validator
│   ├── parse_hl7.py                ← Message parser / inspector
│   └── mllp_sender.py              ← MLLP TCP transport
├── references/
│   ├── adt_a04.md                  ← ADT^A04 field reference
│   └── orm_oru_reference.md        ← ORM^O01 + ORU^R01 field reference
└── examples/
    ├── anonymous_donor_registration.hl7
    ├── lab_order_panel_pbsc.hl7
    └── results_routing_to_epic.hl7
```

## Regulatory Context

This skill was built for the **LSU Stem Cell Lab / Veritas Automata** HSC orchestration project. It enforces:

- **FDA 21 CFR Part 1271** — donor anonymity (no real name, DOB, SSN in donor messages)
- **FACT/JACIE** — audit trail, chain of custody
- **ICCBBA ISBT-128** — DIN format validation
- **HL7 v2.5.1** — standard messaging

## Contributing

PRs welcome. For healthcare-specific changes, please include a reference to the relevant regulatory requirement.

## License

MIT
