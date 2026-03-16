# Epic FHIR R4 Endpoint Reference

Complete reference for all FHIR endpoints used in scheduling workflows against Epic's sandbox.

Base URL: `https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4`

All requests require:
```
Authorization: Bearer {access_token}
Accept: application/fhir+json
```

Write operations also require:
```
Content-Type: application/fhir+json
```

---

## Table of Contents

1. [Patient](#patient)
2. [Practitioner](#practitioner)
3. [Schedule](#schedule)
4. [Slot](#slot)
5. [Appointment](#appointment)
6. [Bundle Response Format](#bundle-response-format)

---

## Patient

### Patient.Read

```
GET {base}/Patient/{fhir_id}
```

Returns a single Patient resource.

### Patient.Search by Name

```
GET {base}/Patient?family={last_name}&given={first_name}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `family` | string | Last name (required for name search) |
| `given` | string | First name |
| `birthdate` | date | Filter by date of birth (YYYY-MM-DD) |

### Patient.Search by MRN

```
GET {base}/Patient?identifier={system}|{value}
```

Example for sandbox:
```
GET {base}/Patient?identifier=urn:oid:1.2.840.114350.1.13.0.1.7.5.737384.14|E4007
```

The `|` separates the system OID from the MRN value.

### Patient.Search by FHIR ID

```
GET {base}/Patient?_id={fhir_id}
```

### Example Patient Response

```json
{
  "resourceType": "Patient",
  "id": "eq081-VQEgP8drUUqCWzHfw3",
  "name": [
    {
      "use": "official",
      "family": "Lin",
      "given": ["Derrick"]
    }
  ],
  "gender": "male",
  "birthDate": "1973-06-03",
  "identifier": [
    {
      "use": "usual",
      "system": "urn:oid:1.2.840.114350.1.13.0.1.7.5.737384.14",
      "value": "E4007"
    }
  ],
  "telecom": [
    {
      "system": "phone",
      "value": "608-555-1234",
      "use": "home"
    }
  ],
  "address": [
    {
      "use": "home",
      "line": ["123 Main St"],
      "city": "Madison",
      "state": "WI",
      "postalCode": "53703"
    }
  ]
}
```

---

## Practitioner

### Practitioner.Search

```
GET {base}/Practitioner?name={name}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | Partial or full name |
| `family` | string | Last name only |
| `given` | string | First name only |
| `identifier` | token | NPI or other identifier |

### Practitioner.Read

```
GET {base}/Practitioner/{fhir_id}
```

### Example Practitioner Response

```json
{
  "resourceType": "Practitioner",
  "id": "eM5CWtq15N0WJeuCet5bJlQ3",
  "name": [
    {
      "use": "official",
      "family": "Physician",
      "given": ["Family Medicine"],
      "prefix": ["Dr."]
    }
  ],
  "qualification": [
    {
      "code": {
        "coding": [
          {
            "system": "http://terminology.hl7.org/CodeSystem/v2-0360",
            "code": "MD"
          }
        ],
        "text": "MD"
      }
    }
  ]
}
```

---

## Schedule

### Schedule.Search

```
GET {base}/Schedule?actor=Practitioner/{practitioner_id}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `actor` | reference | Reference to Practitioner (required) |
| `date` | date | Filter by date range |

A Schedule defines when a practitioner is available. It's the template from which Slots are generated.

### Example Schedule Response Entry

```json
{
  "resourceType": "Schedule",
  "id": "eIDmKq.4HlMO6fwMQ5B2eEw3",
  "actor": [
    {
      "reference": "Practitioner/eM5CWtq15N0WJeuCet5bJlQ3",
      "display": "Family Medicine Physician"
    }
  ],
  "planningHorizon": {
    "start": "2026-03-01T08:00:00-05:00",
    "end": "2026-06-30T17:00:00-05:00"
  }
}
```

---

## Slot

### Slot.Search

```
GET {base}/Slot?schedule=Schedule/{schedule_id}&start=ge{date}&status=free
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `schedule` | reference | Reference to Schedule (required) |
| `start` | date | Start date with prefix: `ge`, `le`, `gt`, `lt` |
| `status` | code | `free`, `busy`, `busy-unavailable`, `busy-tentative` |

Date range example:
```
GET {base}/Slot?schedule=Schedule/{id}&start=ge2026-03-20&start=le2026-03-25&status=free
```

### Example Slot Response Entry

```json
{
  "resourceType": "Slot",
  "id": "eJzlw-AnCcC1DdrI2we3Wpg3",
  "schedule": {
    "reference": "Schedule/eIDmKq.4HlMO6fwMQ5B2eEw3"
  },
  "status": "free",
  "start": "2026-03-20T09:00:00-05:00",
  "end": "2026-03-20T09:30:00-05:00"
}
```

---

## Appointment

### Appointment.Search

```
GET {base}/Appointment?patient={patient_id}&status={status}&date=ge{date}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `patient` | reference | Patient FHIR ID (required) |
| `status` | code | `proposed`, `pending`, `booked`, `arrived`, `fulfilled`, `cancelled`, `noshow` |
| `date` | date | Date with prefix (`ge`, `le`, `gt`, `lt`) |
| `identifier` | token | Appointment identifier |
| `service-category` | token | Category of service |

Multiple statuses: `status=booked,arrived`

### Appointment.Read

```
GET {base}/Appointment/{appointment_id}
```

### Appointment.$find (Search Availability)

```
POST {base}/Appointment/$find
Content-Type: application/fhir+json
```

Request body — a Parameters resource:

```json
{
  "resourceType": "Parameters",
  "parameter": [
    {
      "name": "start",
      "valueDateTime": "2026-04-01T08:00:00Z"
    },
    {
      "name": "end",
      "valueDateTime": "2026-04-07T17:00:00Z"
    },
    {
      "name": "provider",
      "valueUri": "Practitioner/{practitioner_id}"
    }
  ]
}
```

Epic may also accept `department`, `visit-type`, `specialty`, and `patient` parameters depending on configuration.

Response: A Bundle of proposed Appointment resources with status `"proposed"`.

### Appointment.$book (Book Appointment)

```
POST {base}/Appointment/$book
Content-Type: application/fhir+json
```

**Argonaut Scheduling IG format** (Epic follows this):

```json
{
  "resourceType": "Parameters",
  "parameter": [
    {
      "name": "appt-resource",
      "resource": {
        "resourceType": "Appointment",
        "status": "booked",
        "slot": [
          {
            "reference": "Slot/{slot_id}"
          }
        ],
        "participant": [
          {
            "actor": {
              "reference": "Patient/{patient_id}"
            },
            "status": "accepted"
          },
          {
            "actor": {
              "reference": "Practitioner/{practitioner_id}"
            },
            "status": "accepted"
          }
        ]
      }
    }
  ]
}
```

The Appointment resource goes INSIDE a Parameters resource as a `parameter[].resource` — never as the raw body.

Response: A Bundle containing the booked Appointment (status `"booked"`) and an OperationOutcome.

### Appointment Cancel (via Update)

There is NO `$cancel` operation. Cancel by updating the full resource:

```
PUT {base}/Appointment/{appointment_id}
Content-Type: application/fhir+json
```

Steps:
1. GET the full Appointment resource
2. Change `"status"` from `"booked"` to `"cancelled"`
3. PUT the complete resource back

You cannot send a partial update — the full resource is required.

### Example Appointment Resource

```json
{
  "resourceType": "Appointment",
  "id": "eWLwjaoTP4VMcO2RNMxszIA3",
  "status": "booked",
  "serviceType": [
    {
      "coding": [
        {
          "system": "urn:oid:1.2.840.114350.1.13.0.1.7.3.808267.11",
          "code": "422",
          "display": "Office Visit"
        }
      ]
    }
  ],
  "start": "2026-03-25T14:00:00-05:00",
  "end": "2026-03-25T14:30:00-05:00",
  "slot": [
    {
      "reference": "Slot/eJzlw-AnCcC1DdrI2we3Wpg3"
    }
  ],
  "participant": [
    {
      "actor": {
        "reference": "Patient/eq081-VQEgP8drUUqCWzHfw3",
        "display": "Derrick Lin"
      },
      "status": "accepted"
    },
    {
      "actor": {
        "reference": "Practitioner/eM5CWtq15N0WJeuCet5bJlQ3",
        "display": "Family Medicine Physician"
      },
      "status": "accepted"
    }
  ]
}
```

---

## Bundle Response Format

All search operations return a Bundle:

```json
{
  "resourceType": "Bundle",
  "type": "searchset",
  "total": 3,
  "link": [
    {
      "relation": "self",
      "url": "https://fhir.epic.com/.../Patient?family=Lin"
    },
    {
      "relation": "next",
      "url": "https://fhir.epic.com/.../Patient?family=Lin&_getpagesoffset=10"
    }
  ],
  "entry": [
    {
      "fullUrl": "https://fhir.epic.com/.../Patient/eq081-VQEgP8drUUqCWzHfw3",
      "resource": {
        "resourceType": "Patient",
        "id": "eq081-VQEgP8drUUqCWzHfw3"
      }
    }
  ]
}
```

**Pagination:** If `link` contains an entry with `relation: "next"`, follow that URL to get the next page. Continue until no `"next"` link exists.

**Empty results:** The Bundle will have `total: 0` and no `entry` array (or an empty one).
