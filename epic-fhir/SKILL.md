---
name: epic-fhir
description: >
  Technical guide for integrating with Epic's FHIR R4 API, including OAuth 2.0 / SMART on FHIR
  authentication, CRUD operations on scheduling resources (Appointment, Slot, Schedule), patient
  and practitioner search, and async Python client patterns (FastAPI + httpx).
  Use this skill whenever the user works with Epic FHIR endpoints, implements SMART on FHIR auth,
  builds scheduling/booking features against Epic, debugs FHIR errors or auth issues with Epic,
  or writes Python code for a FHIR client. Also trigger when the user mentions "Epic", "FHIR",
  "SMART on FHIR", "HL7 FHIR", "appointment booking", "FHIR sandbox", or any FHIR resource name
  (Patient, Practitioner, Appointment, Slot, Schedule) in context of healthcare APIs.
  Do NOT trigger for general Python without FHIR, or for non-Epic healthcare APIs (Cerner, etc.).
---

# Epic FHIR R4 Integration

Guide for building applications against Epic's FHIR R4 API, focused on the development sandbox and scheduling workflows. The primary use case is a medical appointment chatbot with Python (FastAPI + httpx async).

## Sandbox Environment

| Endpoint | URL |
|----------|-----|
| FHIR R4 Base | `https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4` |
| OAuth Authorize | `https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize` |
| OAuth Token | `https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token` |
| SMART Config | `{FHIR_BASE}/.well-known/smart-configuration` |
| Metadata | `{FHIR_BASE}/metadata` |

**Test credentials:** MyChart sandbox login `fhirjason` / `epicepic1`. Alternative: `fhirdaisy` / `epicepic1`.

**MRN system OID (sandbox only):** `urn:oid:1.2.840.114350.1.13.0.1.7.5.737384.14` — each production Epic org has its own OID.

**Test patients:** Listed at https://fhir.epic.com/Documentation?docId=testpatients. Example: Derrick Lin (FHIR ID `eq081-VQEgP8drUUqCWzHfw3`).

To use OAuth in the sandbox, register a "Patient-Facing" app at https://fhir.epic.com and use the **Non-Production Client ID**.

## OAuth 2.0 — Standalone Launch Flow

The standalone launch is the most common flow for patient-facing apps. The `aud` parameter is critical and often missed — without it, authorization fails silently.

### Step 1: Redirect to Authorize

Redirect the user's browser to the authorize endpoint with these query parameters:

```
response_type=code
client_id={NON_PROD_CLIENT_ID}
redirect_uri={your redirect, e.g. http://localhost:8000/callback}
scope=patient/Patient.read patient/Practitioner.read patient/Appointment.read patient/Appointment.write patient/Slot.read patient/Schedule.read launch/patient openid fhirUser
state={random CSRF token}
aud={FHIR_BASE_URL}   ← CRITICAL: must be the exact FHIR base URL
```

### Step 2: User Authorizes

The user logs in to MyChart, selects a patient (if applicable), and authorizes. Epic redirects back to `redirect_uri` with `?code={auth_code}&state={state}`.

Always validate `state` matches to prevent CSRF attacks.

### Step 3: Exchange Code for Token

POST to the token endpoint with `Content-Type: application/x-www-form-urlencoded`:

```
grant_type=authorization_code
code={auth_code}
redirect_uri={same redirect_uri}
client_id={NON_PROD_CLIENT_ID}
```

Response includes:
- `access_token` — use for all FHIR requests
- `token_type` — always "Bearer"
- `expires_in` — typically ~3600 seconds (60 min)
- `scope` — granted scopes (may differ from requested)
- `patient` — **the FHIR ID of the logged-in patient** (important for patient-facing apps)

### Step 4: Make FHIR Requests

Include on every FHIR request:
```
Authorization: Bearer {access_token}
Accept: application/fhir+json
```

For write operations, also set `Content-Type: application/fhir+json`.

### OAuth Pitfalls

- **Missing `aud` parameter** → silent authorization failure, no useful error
- **Non-Production vs Production Client ID** → use Non-Production for sandbox
- **Scope silently dropped** → if the app isn't registered for a scope, Epic drops it without error
- **`redirect_uri` must match exactly** — including trailing slashes
- **Tokens expire in ~60 minutes** — implement refresh or re-auth
- **Epic supports PKCE** for public clients (recommended for SPAs and mobile apps)

## FHIR Resource Model for Scheduling

The scheduling resources form a hierarchy:

```
Schedule (template: who + where + when)
  └─ Slot (specific time window, status: free | busy | busy-unavailable)
       └─ Appointment (booked encounter for a patient)
```

A Schedule defines a practitioner's availability template. Slots are generated from the schedule as individual bookable windows. An Appointment references a Slot and binds it to a Patient.

## Key FHIR Operations

For the complete endpoint reference with all query parameters, examples, and response formats, read `references/endpoints.md`.

### Search Pattern

All searches return a FHIR **Bundle** with `resourceType: "Bundle"`, `type: "searchset"`, `total`, and an `entry[]` array. Each entry has `fullUrl` and `resource`. Always iterate `bundle.entry[].resource`.

Handle pagination by checking `bundle.link` for a relation `"next"` — follow it to get more results.

### Quick Reference

| Operation | Method | Path |
|-----------|--------|------|
| Find patient | GET | `/Patient?family={last}&given={first}` |
| Find patient by MRN | GET | `/Patient?identifier={oid}\|{mrn}` |
| Read patient | GET | `/Patient/{id}` |
| Find practitioner | GET | `/Practitioner?name={name}` |
| Find schedules | GET | `/Schedule?actor=Practitioner/{id}` |
| Find free slots | GET | `/Slot?schedule=Schedule/{id}&start=ge{date}&status=free` |
| Find availability | POST | `/Appointment/$find` (Parameters body) |
| Book appointment | POST | `/Appointment/$book` (Parameters body) |
| List appointments | GET | `/Appointment?patient={id}&status=booked&date=ge{date}` |
| Cancel appointment | PUT | `/Appointment/{id}` (full resource, status→cancelled) |

### Cancellation Warning

There is no `$cancel` operation. To cancel, you must: (1) GET the full Appointment resource, (2) change `status` to `"cancelled"`, (3) PUT the complete resource back. Sending only the status field will fail.

## Scheduling Workflows

For complete step-by-step flows with code examples, read `references/scheduling-flows.md`.

### Search Availability

```
Practitioner.Search(name) → Schedule.Search(actor=practitioner_id)
  → Slot.Search(schedule=schedule_id, start>=date, status=free)
```

### Book an Appointment

Use `Appointment.$book` with a Parameters resource wrapping the Appointment. The Appointment goes inside `parameter[].resource`, not as a raw body. Epic's implementation follows the Argonaut Scheduling IG.

### Cancel an Appointment

```
Appointment.Read(id) → modify status to "cancelled" → Appointment.Update(PUT)
```

### List Patient Appointments

```
Appointment.Search(patient=id, date>=today, status=booked)
```

## Python Client Pattern

Build an async FHIR client using `httpx.AsyncClient` with a 30-second timeout. Structure:

```python
class EpicFHIRClient:
    def __init__(self, base_url: str, access_token: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/fhir+json",
            },
            timeout=30.0,
        )

    async def _get(self, path: str, params: dict | None = None) -> dict: ...
    async def _post(self, path: str, json: dict) -> dict: ...
    async def _put(self, path: str, json: dict) -> dict: ...
```

Implement custom exceptions:
- `FHIRError` — base, includes OperationOutcome details
- `FHIRAuthError` — 401/403, trigger re-auth flow
- `FHIRNotFoundError` — 404
- `FHIRRateLimitError` — 429, implement exponential backoff

Extract resources from Bundles with a helper:

```python
def _extract_entries(self, bundle: dict) -> list[dict]:
    return [e["resource"] for e in bundle.get("entry", [])]
```

For the full client implementation pattern, read `references/scheduling-flows.md`.

## Error Handling

Epic returns `OperationOutcome` resources for errors with `issue[]` containing `severity`, `code`, and `diagnostics`. For the complete error code reference, read `references/error-codes.md`.

Key HTTP status codes:
- **400** — Bad Request (invalid params)
- **401** — Unauthorized (expired/missing token) → re-authenticate
- **403** — Forbidden (insufficient scopes)
- **404** — Not Found
- **429** — Rate limited → exponential backoff retry

## Security Rules

- **Never hardcode** credentials, client IDs, or secrets in code — use environment variables
- **Never log** access tokens or refresh tokens
- **Always validate** the `state` parameter in OAuth callbacks to prevent CSRF
- **Rate limiting:** implement retry with exponential backoff on 429 responses
- **Timeouts:** 30s for FHIR calls, 60s for any LLM API calls

## Sandbox Gotchas

- Test data is curated — not all search combinations return results
- Write operations (`$book`, Create, Update) may behave differently than production
- Test patient/practitioner IDs can change over time
- Not all practitioners have scheduling data in the sandbox
- The MRN OID is sandbox-specific; every production Epic customer has a different one
- Date params use comparison prefixes: `ge` (>=), `le` (<=), `gt` (>), `lt` (<)
- References are relative: `"Patient/abc123"`, not the full URL
- Bundles may be paginated — always check for `link` with `relation: "next"`

## Dates and Timezones

FHIR uses ISO 8601 date strings. Epic stores times in the clinic's local timezone. Normalize to UTC internally and convert at the UI layer. Slot `start`/`end` values include timezone offsets.

## Idempotency

When calling `$book`, generate a client-side transaction ID to detect duplicate bookings from retries (e.g., user double-clicks). Before booking, verify the slot is still `free` to guard against race conditions.

## References

- `references/endpoints.md` — Complete endpoint reference with query params, request/response examples
- `references/scheduling-flows.md` — Full scheduling workflows with Python code examples
- `references/error-codes.md` — Epic-specific error codes and troubleshooting
