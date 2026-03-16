# MLLP Protocol — Minimal Lower Layer Protocol

MLLP (Minimal Lower Layer Protocol) is the standard TCP transport for HL7 v2 messages.
It provides lightweight framing so the receiving system knows where a message starts and ends.

---

## Frame Structure

```
<VT> [HL7 message bytes] <FS><CR>
```

| Byte | Hex    | Name               | Purpose                         |
|------|--------|--------------------|---------------------------------|
| VT   | `0x0B` | Vertical Tab       | Start Block — marks message start |
| FS   | `0x1C` | File Separator     | End Data — marks message end    |
| CR   | `0x0D` | Carriage Return    | Required terminator after FS    |

The HL7 message itself uses `\r` (`0x0D`) as the segment terminator.

### Python framing constants

```python
MLLP_START = b"\x0b"     # VT
MLLP_END   = b"\x1c\r"  # FS + CR
```

---

## Connection Flow

```
Sender                           Receiver
  │                                  │
  │──── TCP connect ────────────────►│
  │                                  │
  │──── <VT> [HL7] <FS><CR> ───────►│
  │                                  │ (parse & process)
  │◄─── <VT> [ACK] <FS><CR> ────────│
  │                                  │
  │──── TCP close ──────────────────►│
```

- One TCP connection per message (unless persistent connections are negotiated)
- Sender must wait for ACK before sending the next message
- If no ACK is received within timeout, the sender should retry or alert

---

## ACK Message Types

| MSA-1 | Meaning              | Agent Action                            |
|-------|----------------------|-----------------------------------------|
| `AA`  | Application Accept   | Message processed — proceed             |
| `AE`  | Application Error    | Processing failed — log, alert IT       |
| `AR`  | Application Reject   | Message rejected — escalate, do not retry automatically |

### Minimal ACK structure

```
MSH|^~\&|{RECEIVER}|{FACILITY}|{SENDER}|{SENDER_FACILITY}|{TIMESTAMP}||ACK|{CTRL_ID}|P|2.5.1
MSA|AA|{ORIGINAL_CTRL_ID}|Message accepted
```

---

## Port Conventions (LSU Stem Cell Lab)

| Direction              | Port  | System              |
|------------------------|-------|---------------------|
| Agent → SoftBank       | 2575  | ADT^A04 donor registration |
| Agent → Epic Beaker    | 2576  | ORM^O01 lab orders  |
| SoftBank → Agent       | 2575  | ORU^R01 results (listener) |
| Agent → Epic (WellSky) | 2577  | ORU^R01 results routing |

> Ports are configurable. Confirm with LIS/integration team before deployment.

---

## Timeouts and Retry

| Scenario          | Recommended Action                              |
|-------------------|-------------------------------------------------|
| No ACK in 10s     | Retry up to 3 times with 2s delay              |
| AE received       | Log full exchange, alert IT on-call, queue message |
| AR received       | Log full exchange, escalate to Lab Supervisor  |
| Connection refused| Queue message, activate downtime protocol (US-010) |

Use `mllp_sender.py --retry 3 --retry-delay 2` for production sends.

---

## Scripts

| Script              | Role                                         |
|---------------------|----------------------------------------------|
| `mllp_sender.py`    | Outbound: connect → send → wait for ACK      |
| `mllp_listener.py`  | Inbound: listen → receive → send ACK         |

### Send example

```bash
python scripts/mllp_sender.py \
  --host softbank.lsu.edu \
  --port 2575 \
  --file message.hl7 \
  --timeout 10 \
  --retry 3
```

### Listen example (one message)

```bash
python scripts/mllp_listener.py \
  --host 0.0.0.0 \
  --port 2575 \
  --once \
  --json
```

### Listen continuously

```bash
python scripts/mllp_listener.py \
  --host 0.0.0.0 \
  --port 2575 \
  --timeout 30
# Ctrl+C to stop
```

---

## References

- HL7 v2.5.1 Chapter 1 — Message Format
- ASTM E1238 / HL7 Appendix C — MLLP specification
- RFC for network transport of HL7: HL7 Site Specification document
