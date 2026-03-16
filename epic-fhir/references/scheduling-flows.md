# Scheduling Workflows — Python Implementation

Complete scheduling flows with async Python code examples using httpx.

## Table of Contents

1. [FHIR Client Base](#fhir-client-base)
2. [Search Availability Flow](#search-availability-flow)
3. [Book Appointment Flow](#book-appointment-flow)
4. [Cancel Appointment Flow](#cancel-appointment-flow)
5. [List Patient Appointments](#list-patient-appointments)
6. [OAuth Callback Handler](#oauth-callback-handler)

---

## FHIR Client Base

```python
import httpx
from datetime import datetime, date


class FHIRError(Exception):
    """Base FHIR error with OperationOutcome details."""
    def __init__(self, status_code: int, outcome: dict | None = None):
        self.status_code = status_code
        self.outcome = outcome
        issues = outcome.get("issue", []) if outcome else []
        self.diagnostics = "; ".join(
            i.get("diagnostics", "Unknown error") for i in issues
        )
        super().__init__(f"FHIR {status_code}: {self.diagnostics}")


class FHIRAuthError(FHIRError):
    """401/403 — token expired or insufficient scopes."""
    pass


class FHIRNotFoundError(FHIRError):
    """404 — resource not found."""
    pass


class FHIRRateLimitError(FHIRError):
    """429 — rate limited, retry with backoff."""
    pass


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

    async def close(self):
        await self.client.aclose()

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code < 400:
            return
        try:
            outcome = resp.json()
        except Exception:
            outcome = None

        error_map = {
            401: FHIRAuthError,
            403: FHIRAuthError,
            404: FHIRNotFoundError,
            429: FHIRRateLimitError,
        }
        exc_class = error_map.get(resp.status_code, FHIRError)
        raise exc_class(resp.status_code, outcome)

    async def _get(self, path: str, params: dict | None = None) -> dict:
        resp = await self.client.get(path, params=params)
        self._raise_for_status(resp)
        return resp.json()

    async def _post(self, path: str, json: dict) -> dict:
        resp = await self.client.post(
            path, json=json,
            headers={"Content-Type": "application/fhir+json"},
        )
        self._raise_for_status(resp)
        return resp.json()

    async def _put(self, path: str, json: dict) -> dict:
        resp = await self.client.put(
            path, json=json,
            headers={"Content-Type": "application/fhir+json"},
        )
        self._raise_for_status(resp)
        return resp.json()

    @staticmethod
    def _extract_entries(bundle: dict) -> list[dict]:
        """Extract resources from a FHIR Bundle."""
        return [e["resource"] for e in bundle.get("entry", [])]

    # --- Patient ---

    async def search_patient(
        self, family: str | None = None, given: str | None = None,
        identifier: str | None = None,
    ) -> list[dict]:
        params = {}
        if family:
            params["family"] = family
        if given:
            params["given"] = given
        if identifier:
            params["identifier"] = identifier
        bundle = await self._get("/Patient", params=params)
        return self._extract_entries(bundle)

    async def read_patient(self, patient_id: str) -> dict:
        return await self._get(f"/Patient/{patient_id}")

    # --- Practitioner ---

    async def search_practitioner(self, name: str) -> list[dict]:
        bundle = await self._get("/Practitioner", params={"name": name})
        return self._extract_entries(bundle)

    # --- Schedule ---

    async def search_schedules(self, practitioner_id: str) -> list[dict]:
        bundle = await self._get(
            "/Schedule",
            params={"actor": f"Practitioner/{practitioner_id}"},
        )
        return self._extract_entries(bundle)

    # --- Slot ---

    async def search_slots(
        self, schedule_id: str,
        start_from: str, start_to: str | None = None,
        status: str = "free",
    ) -> list[dict]:
        params = {
            "schedule": f"Schedule/{schedule_id}",
            "start": f"ge{start_from}",
            "status": status,
        }
        if start_to:
            params["start"] = [f"ge{start_from}", f"le{start_to}"]
        bundle = await self._get("/Slot", params=params)
        return self._extract_entries(bundle)

    # --- Appointment ---

    async def search_appointments(
        self, patient_id: str,
        status: str = "booked",
        date_from: str | None = None,
    ) -> list[dict]:
        params = {"patient": patient_id, "status": status}
        if date_from:
            params["date"] = f"ge{date_from}"
        bundle = await self._get("/Appointment", params=params)
        return self._extract_entries(bundle)

    async def read_appointment(self, appointment_id: str) -> dict:
        return await self._get(f"/Appointment/{appointment_id}")

    async def find_availability(
        self, practitioner_id: str,
        start: str, end: str,
    ) -> list[dict]:
        body = {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "start", "valueDateTime": start},
                {"name": "end", "valueDateTime": end},
                {"name": "provider", "valueUri": f"Practitioner/{practitioner_id}"},
            ],
        }
        bundle = await self._post("/Appointment/$find", json=body)
        return self._extract_entries(bundle)

    async def book_appointment(
        self, slot_id: str, patient_id: str, practitioner_id: str,
    ) -> dict:
        body = {
            "resourceType": "Parameters",
            "parameter": [
                {
                    "name": "appt-resource",
                    "resource": {
                        "resourceType": "Appointment",
                        "status": "booked",
                        "slot": [{"reference": f"Slot/{slot_id}"}],
                        "participant": [
                            {
                                "actor": {"reference": f"Patient/{patient_id}"},
                                "status": "accepted",
                            },
                            {
                                "actor": {"reference": f"Practitioner/{practitioner_id}"},
                                "status": "accepted",
                            },
                        ],
                    },
                }
            ],
        }
        result = await self._post("/Appointment/$book", json=body)
        # Response is a Bundle — extract the Appointment resource
        entries = self._extract_entries(result)
        appointments = [e for e in entries if e.get("resourceType") == "Appointment"]
        return appointments[0] if appointments else result

    async def cancel_appointment(self, appointment_id: str) -> dict:
        # Step 1: Read the full appointment
        appt = await self.read_appointment(appointment_id)
        # Step 2: Change status
        appt["status"] = "cancelled"
        # Step 3: PUT the full resource back
        return await self._put(f"/Appointment/{appointment_id}", json=appt)
```

---

## Search Availability Flow

Full flow to find available slots for a practitioner:

```python
async def find_available_slots(
    client: EpicFHIRClient,
    practitioner_name: str,
    date_from: str,
    date_to: str,
) -> list[dict]:
    """
    1. Search practitioner by name
    2. Get their schedules
    3. Find free slots in the date range
    """
    # Step 1: Find the practitioner
    practitioners = await client.search_practitioner(practitioner_name)
    if not practitioners:
        raise ValueError(f"No practitioner found for: {practitioner_name}")
    practitioner = practitioners[0]
    practitioner_id = practitioner["id"]

    # Step 2: Get schedules for this practitioner
    schedules = await client.search_schedules(practitioner_id)
    if not schedules:
        raise ValueError(f"No schedules found for practitioner {practitioner_id}")

    # Step 3: Search free slots across all schedules
    all_slots = []
    for schedule in schedules:
        slots = await client.search_slots(
            schedule_id=schedule["id"],
            start_from=date_from,
            start_to=date_to,
            status="free",
        )
        all_slots.extend(slots)

    return sorted(all_slots, key=lambda s: s.get("start", ""))
```

---

## Book Appointment Flow

```python
import uuid


async def book_slot(
    client: EpicFHIRClient,
    slot_id: str,
    patient_id: str,
    practitioner_id: str,
) -> dict:
    """
    Book a specific slot for a patient.
    Includes idempotency check: verifies slot is still free before booking.
    """
    # Generate a transaction ID for idempotency
    transaction_id = str(uuid.uuid4())

    # Verify slot is still free (race condition guard)
    slot = await client._get(f"/Slot/{slot_id}")
    if slot.get("status") != "free":
        raise ValueError(f"Slot {slot_id} is no longer free (status: {slot.get('status')})")

    # Book the appointment
    appointment = await client.book_appointment(
        slot_id=slot_id,
        patient_id=patient_id,
        practitioner_id=practitioner_id,
    )
    return appointment
```

---

## Cancel Appointment Flow

```python
async def cancel_patient_appointment(
    client: EpicFHIRClient,
    appointment_id: str,
) -> dict:
    """
    Cancel an appointment by ID.
    Reads the full resource, changes status, and PUTs it back.
    """
    return await client.cancel_appointment(appointment_id)
```

---

## List Patient Appointments

```python
async def get_upcoming_appointments(
    client: EpicFHIRClient,
    patient_id: str,
) -> list[dict]:
    """Get all upcoming booked appointments for a patient."""
    today = date.today().isoformat()
    appointments = await client.search_appointments(
        patient_id=patient_id,
        status="booked",
        date_from=today,
    )
    return sorted(appointments, key=lambda a: a.get("start", ""))
```

---

## OAuth Callback Handler

FastAPI route for handling the OAuth callback:

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
import httpx
import secrets

app = FastAPI()

# Store in a secure session/database in production
oauth_states: dict[str, bool] = {}

EPIC_TOKEN_URL = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
EPIC_AUTHORIZE_URL = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize"
FHIR_BASE_URL = "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
CLIENT_ID = "your-non-production-client-id"  # from env var in production
REDIRECT_URI = "http://localhost:8000/callback"

SCOPES = " ".join([
    "patient/Patient.read",
    "patient/Practitioner.read",
    "patient/Appointment.read",
    "patient/Appointment.write",
    "patient/Slot.read",
    "patient/Schedule.read",
    "launch/patient",
    "openid",
    "fhirUser",
])


@app.get("/login")
async def login():
    state = secrets.token_urlsafe(32)
    oauth_states[state] = True
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "aud": FHIR_BASE_URL,  # CRITICAL — omitting this causes silent failure
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"{EPIC_AUTHORIZE_URL}?{query}")


@app.get("/callback")
async def callback(request: Request, code: str, state: str):
    # Validate state to prevent CSRF
    if state not in oauth_states:
        raise HTTPException(400, "Invalid state parameter")
    del oauth_states[state]

    # Exchange authorization code for access token
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            EPIC_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": CLIENT_ID,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if resp.status_code != 200:
        raise HTTPException(502, f"Token exchange failed: {resp.text}")

    token_data = resp.json()
    access_token = token_data["access_token"]
    patient_fhir_id = token_data.get("patient")  # FHIR ID of logged-in patient

    # Store token securely and redirect to app
    # In production: save to encrypted session, NOT cookies or localStorage
    return {
        "message": "Authenticated successfully",
        "patient_id": patient_fhir_id,
        "expires_in": token_data.get("expires_in"),
    }
```
