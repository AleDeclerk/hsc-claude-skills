# epic-fhir

> **Claude Agent Skill** — Integrate with Epic's FHIR R4 API for patient scheduling, OAuth 2.0 / SMART on FHIR authentication, and async Python client patterns.

Built for patient-facing appointment chatbots using FastAPI + httpx against Epic's development sandbox.

---

## What this skill does

- **Authenticates** via OAuth 2.0 Standalone Launch (SMART on FHIR) with Epic's sandbox
- **Searches** patients, practitioners, schedules, and free slots
- **Books** appointments using the Argonaut Scheduling IG `$book` operation
- **Cancels** appointments via full-resource PUT (no `$cancel` in Epic)
- **Debugs** FHIR errors with Epic-specific error codes and troubleshooting

## Supported FHIR Resources

| Resource | Operations |
|----------|-----------|
| `Patient` | Read, Search (name, MRN, FHIR ID) |
| `Practitioner` | Read, Search (name, NPI) |
| `Schedule` | Search (by practitioner) |
| `Slot` | Search (by schedule, date range, status) |
| `Appointment` | Read, Search, `$find`, `$book`, Cancel (PUT) |

## Install

```bash
# Claude Code — global install
cp -r epic-fhir ~/.claude/skills/epic-fhir

# Claude Code — project install
cp -r epic-fhir .claude/skills/epic-fhir
```

Claude will automatically discover and use the skill for Epic FHIR-related tasks.

## Requirements

- Python 3.10+
- httpx (async HTTP client)
- FastAPI (for OAuth callback endpoints)

## Quick Start

```python
import httpx

FHIR_BASE = "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"

async with httpx.AsyncClient(
    base_url=FHIR_BASE,
    headers={
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/fhir+json",
    },
    timeout=30.0,
) as client:
    # Search for a practitioner
    resp = await client.get("/Practitioner", params={"name": "Smith"})
    bundle = resp.json()
    practitioners = [e["resource"] for e in bundle.get("entry", [])]

    # Find free slots
    resp = await client.get("/Slot", params={
        "schedule": f"Schedule/{schedule_id}",
        "start": "ge2026-03-20",
        "status": "free",
    })
    slots = resp.json()
```

## File Layout

```
epic-fhir/
├── SKILL.md                        <- Claude skill instructions
├── README.md                       <- This file
├── evals/
│   └── evals.json                  <- 3 eval cases, 21 assertions
└── references/
    ├── endpoints.md                <- Complete FHIR endpoint reference
    ├── scheduling-flows.md         <- Workflows + async Python client
    └── error-codes.md              <- Epic error codes + troubleshooting
```

## Sandbox Environment

| Endpoint | URL |
|----------|-----|
| FHIR R4 Base | `https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4` |
| OAuth Authorize | `https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize` |
| OAuth Token | `https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token` |

**Test credentials:** `fhirjason` / `epicepic1`

Register your app at [fhir.epic.com](https://fhir.epic.com) and use the Non-Production Client ID.

## Eval Results

3 evals, 21 assertions, **100% pass rate** across 2 rounds:

| Eval | Scenario | Assertions | Result |
|------|----------|------------|--------|
| 1 | OAuth /login + /callback in FastAPI | 8 | 8/8 PASS |
| 2 | Search available slots by doctor name | 7 | 7/7 PASS |
| 3 | Debug $book 400 error (Parameters wrapper) | 6 | 6/6 PASS |

## License

MIT
