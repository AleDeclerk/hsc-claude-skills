# Epic FHIR Error Codes & Troubleshooting

## OperationOutcome Structure

All FHIR errors return an `OperationOutcome` resource:

```json
{
  "resourceType": "OperationOutcome",
  "issue": [
    {
      "severity": "error",
      "code": "processing",
      "details": {
        "coding": [
          {
            "system": "urn:oid:1.2.840.114350.1.13.0.1.7.2.657369",
            "code": "4100",
            "display": "The resource request contained an invalid parameter."
          }
        ],
        "text": "The resource request contained an invalid parameter."
      },
      "diagnostics": "Invalid value for parameter 'patient'."
    }
  ]
}
```

## Epic-Specific Error Codes

| Code | Severity | Meaning | Common Cause |
|------|----------|---------|--------------|
| **4100** | Fatal | Invalid parameter | Wrong patient ID, malformed query param |
| **4101** | Warning | No results found | Search returned empty — not necessarily an error |
| **4102** | Fatal | Invalid resource ID | Malformed FHIR ID in a read operation |
| **4103** | Fatal | Resource was deleted | Trying to read a deleted resource |
| **4111** | Fatal | Missing required search parameter | Search endpoint requires a param you didn't include |
| **4112** | Fatal | Invalid parameter combination | Params that can't be used together |
| **4118** | Fatal | User not authorized | Token lacks permission for this patient's data |
| **4119** | Warning | Additional data may exist | Results may be incomplete (paginated or access-limited) |
| **59102** | Fatal | Invalid parameter value | Value doesn't match expected format/codeset |

## HTTP Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| **200** | OK | Success |
| **201** | Created | Resource created successfully |
| **400** | Bad Request | Check request body and params against the spec |
| **401** | Unauthorized | Token expired or missing → re-authenticate |
| **403** | Forbidden | Insufficient scopes → check app registration |
| **404** | Not Found | Resource ID doesn't exist |
| **409** | Conflict | Resource version conflict on update |
| **422** | Unprocessable | Valid FHIR but fails business rules |
| **429** | Too Many Requests | Rate limited → retry with exponential backoff |
| **500** | Internal Server Error | Epic server issue → retry once, then report |

## Troubleshooting Guide

### OAuth Issues

**Problem: Authorization redirects but fails silently**
- Cause: Missing `aud` parameter in authorize request
- Fix: Add `aud={FHIR_BASE_URL}` — must be the exact FHIR R4 base URL

**Problem: Token exchange returns 400**
- Cause: `redirect_uri` doesn't match exactly (trailing slash, different port)
- Fix: Ensure the redirect_uri in the token request matches the authorize request exactly

**Problem: Token works but some resources return 403**
- Cause: App not registered for required scopes
- Fix: Check app registration at https://fhir.epic.com, add missing scopes. Note that Epic silently drops unregistered scopes during authorization.

**Problem: Token exchange succeeds but `patient` field is missing**
- Cause: `launch/patient` scope not requested or not granted
- Fix: Include `launch/patient` in scope and ensure app is configured as patient-facing

### Search Issues

**Problem: Patient search returns empty**
- Cause: Sandbox has limited test data
- Fix: Use known test patients (e.g., `family=Lin&given=Derrick`). Check https://fhir.epic.com/Documentation?docId=testpatients

**Problem: Slot search returns empty even with valid Schedule ID**
- Cause: No slots exist in the date range, or practitioner has no scheduling data
- Fix: Try a wider date range. Not all sandbox practitioners have scheduling data.

**Problem: Search returns 4111 "missing required parameter"**
- Cause: Endpoint requires a parameter you didn't include
- Fix: Check `references/endpoints.md` for required params per resource type

### Booking Issues

**Problem: $book returns 400 or 422**
- Cause: Appointment sent as raw body instead of inside Parameters resource
- Fix: Wrap the Appointment in a Parameters resource with `name: "appt-resource"` and `resource: {Appointment}`

**Problem: $book succeeds but duplicate appointments created**
- Cause: Missing idempotency — user double-clicked or retry after timeout
- Fix: Generate a client-side transaction ID, check for existing appointment before booking

**Problem: Cancel (PUT) returns 409 Conflict**
- Cause: Resource was modified between your GET and PUT
- Fix: Re-read the appointment, apply your change, and PUT again

### Rate Limiting

Implement exponential backoff for 429 responses:

```python
import asyncio
import random

async def retry_with_backoff(
    func, *args, max_retries: int = 3, **kwargs,
):
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except FHIRRateLimitError:
            if attempt == max_retries - 1:
                raise
            wait = (2 ** attempt) + random.uniform(0, 1)
            await asyncio.sleep(wait)
```
