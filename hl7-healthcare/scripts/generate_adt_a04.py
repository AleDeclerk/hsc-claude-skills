#!/usr/bin/env python3
"""
generate_adt_a04.py
-------------------
Generate HL7 v2.5.1 ADT^A04 (Register a Patient) messages for
anonymous HSC donor registration.

Compliant with:
  - FDA 21 CFR Part 1271 (donor anonymity)
  - FACT/JACIE standards
  - ICCBBA ISBT-128 DIN format

Usage:
  python generate_adt_a04.py --din W000055508D001 --donor-id DONOR-2026-0042 \\
    --sending-app VERITAS --sending-facility LSU_SCL \\
    --receiving-app SOFTBANK --receiving-facility LSU

  python generate_adt_a04.py --din W000055508D001 --donor-id DONOR-2026-0042 \\
    --output donor_reg.hl7 --json
"""

import argparse
import datetime
import json
import random
import string
import sys
from datetime import timezone


# HL7 v2 delimiter constants
FIELD_SEP = "|"
COMPONENT_SEP = "^"
REPEAT_SEP = "~"
ESCAPE_CHAR = "\\"
SUBCOMPONENT_SEP = "&"
SEGMENT_TERMINATOR = "\r"


def timestamp(dt: datetime.datetime = None) -> str:
    """Return HL7-formatted timestamp: YYYYMMDDHHMMSS"""
    dt = dt or datetime.datetime.now(timezone.utc)
    return dt.strftime("%Y%m%d%H%M%S")


def message_control_id() -> str:
    """Generate a unique message control ID."""
    rand = "".join(random.choices(string.digits, k=8))
    return f"MSG{rand}"


def build_msh(sending_app: str, sending_facility: str,
              receiving_app: str, receiving_facility: str,
              msg_type: str, control_id: str, version: str = "2.5.1") -> str:
    """Build MSH (Message Header) segment."""
    fields = [
        "MSH",
        f"{COMPONENT_SEP}{REPEAT_SEP}{ESCAPE_CHAR}{SUBCOMPONENT_SEP}",  # MSH-2 encoding chars
        sending_app,           # MSH-3 Sending Application
        sending_facility,      # MSH-4 Sending Facility
        receiving_app,         # MSH-5 Receiving Application
        receiving_facility,    # MSH-6 Receiving Facility
        timestamp(),           # MSH-7 Date/Time of Message
        "",                    # MSH-8 Security (empty)
        msg_type,              # MSH-9 Message Type (e.g. ADT^A04)
        control_id,            # MSH-10 Message Control ID
        "P",                   # MSH-11 Processing ID (P=Production, T=Test)
        version,               # MSH-12 Version ID
    ]
    return FIELD_SEP.join(fields) + SEGMENT_TERMINATOR


def build_evn(event_code: str = "A04") -> str:
    """Build EVN (Event Type) segment."""
    fields = [
        "EVN",
        event_code,    # EVN-1 Event Type Code
        timestamp(),   # EVN-2 Recorded Date/Time
        "",            # EVN-3 Date/Time Planned Event (empty)
        "",            # EVN-4 Event Reason Code (empty)
        "",            # EVN-5 Operator ID (empty)
        timestamp(),   # EVN-6 Event Occurred
    ]
    return FIELD_SEP.join(fields) + SEGMENT_TERMINATOR


def build_pid_anonymous(din: str, donor_id: str, assigning_authority: str = "LSU_SCL") -> str:
    """
    Build PID (Patient Identification) segment for an anonymous donor.

    Per FDA 21 CFR Part 1271 and FACT/JACIE:
      - PID-5 Name: ANONYMOUS^DONOR (never real name)
      - PID-7 DOB:  00010101 (placeholder)
      - PID-8 Sex:  U (Unknown)
      - No SSN, no address, no contact info
    """
    # PID-3: Patient ID List — DIN as primary, Donor ID as secondary
    primary_id = f"{din}^^^{assigning_authority}^DIN"
    secondary_id = f"{donor_id}^^^{assigning_authority}^DONOR_ID"
    patient_id_list = f"{primary_id}{REPEAT_SEP}{secondary_id}"

    fields = [
        "PID",
        "1",               # PID-1 Set ID
        "",                # PID-2 Patient ID (external) — deprecated, empty
        patient_id_list,   # PID-3 Patient Identifier List
        "",                # PID-4 Alternate Patient ID — deprecated, empty
        "ANONYMOUS^DONOR^^^^^L",  # PID-5 Patient Name (LAST^FIRST format, L=Legal)
        "",                # PID-6 Mother's Maiden Name — empty
        "00010101",        # PID-7 Date of Birth — placeholder per regulatory requirement
        "U",               # PID-8 Administrative Sex — Unknown
        "",                # PID-9 Patient Alias — empty
        "",                # PID-10 Race — empty
        "",                # PID-11 Patient Address — empty (anonymity)
        "",                # PID-12 County Code — empty
        "",                # PID-13 Phone Home — empty
        "",                # PID-14 Phone Business — empty
        "",                # PID-15 Primary Language — empty
        "",                # PID-16 Marital Status — empty
        "",                # PID-17 Religion — empty
        "",                # PID-18 Patient Account Number — empty
        "",                # PID-19 SSN — NEVER populate for anonymous donor
        "",                # PID-20 Driver's License — empty
    ]
    return FIELD_SEP.join(fields) + SEGMENT_TERMINATOR


def build_pv1(patient_class: str = "O") -> str:
    """Build PV1 (Patient Visit) segment — minimal for donor registration."""
    fields = [
        "PV1",
        "1",            # PV1-1 Set ID
        patient_class,  # PV1-2 Patient Class (O=Outpatient, used for lab-only visits)
    ]
    return FIELD_SEP.join(fields) + SEGMENT_TERMINATOR


def build_adt_a04(
    din: str,
    donor_id: str,
    sending_app: str = "VERITAS",
    sending_facility: str = "LSU_SCL",
    receiving_app: str = "SOFTBANK",
    receiving_facility: str = "LSU",
    assigning_authority: str = "LSU_SCL",
    test_mode: bool = False,
) -> dict:
    """
    Build a complete ADT^A04 message for anonymous donor registration.

    Returns:
        dict with keys:
          - 'message': full HL7 message string
          - 'control_id': message control ID for tracking
          - 'segments': list of individual segments
    """
    control_id = message_control_id()

    msh = build_msh(
        sending_app=sending_app,
        sending_facility=sending_facility,
        receiving_app=receiving_app,
        receiving_facility=receiving_facility,
        msg_type="ADT^A04",
        control_id=control_id,
    )
    if test_mode:
        # Replace processing ID P with T for test messages
        msh = msh.replace("|P|", "|T|")

    evn = build_evn("A04")
    pid = build_pid_anonymous(din=din, donor_id=donor_id, assigning_authority=assigning_authority)
    pv1 = build_pv1()

    segments = [msh, evn, pid, pv1]
    message = "".join(segments)

    return {
        "message": message,
        "control_id": control_id,
        "segments": {
            "MSH": msh.strip(),
            "EVN": evn.strip(),
            "PID": pid.strip(),
            "PV1": pv1.strip(),
        },
    }


HL7_DELIMITERS = set("|^~\\&")


def contains_hl7_delimiter(value: str) -> bool:
    """Return True if value contains any HL7 delimiter character."""
    return any(c in HL7_DELIMITERS for c in value)


def validate_din(din: str) -> bool:
    """
    Basic ISBT-128 DIN format validation.
    Full format: <facility prefix (5 chars)><product code (5 chars)><sequence (5 chars)>
    Simplified check: non-empty, alphanumeric, reasonable length.
    """
    if not din:
        return False
    clean = din.replace("-", "").upper()
    if not clean.isalnum():
        return False
    if len(clean) < 8 or len(clean) > 20:
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate HL7 ADT^A04 message for anonymous HSC donor registration"
    )
    parser.add_argument("--din", required=True, help="ISBT-128 Donation Identification Number")
    parser.add_argument("--donor-id", required=True, help="Internal Donor ID (e.g. DONOR-2026-0042)")
    parser.add_argument("--sending-app", default="VERITAS", help="MSH-3 Sending Application")
    parser.add_argument("--sending-facility", default="LSU_SCL", help="MSH-4 Sending Facility")
    parser.add_argument("--receiving-app", default="SOFTBANK", help="MSH-5 Receiving Application")
    parser.add_argument("--receiving-facility", default="LSU", help="MSH-6 Receiving Facility")
    parser.add_argument("--assigning-authority", default="LSU_SCL", help="PID-3 Assigning Authority")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument("--test", action="store_true", help="Use test processing ID (T instead of P)")
    parser.add_argument("--json", action="store_true", help="Output structured JSON instead of raw HL7")

    args = parser.parse_args()

    # Validate DIN
    if not validate_din(args.din):
        print(f"ERROR: Invalid DIN format: '{args.din}'", file=sys.stderr)
        print("DIN must be alphanumeric, 8-20 characters (ISBT-128 format)", file=sys.stderr)
        sys.exit(1)

    # Reject HL7 delimiter characters in user-supplied identifiers
    for flag, value in [("--donor-id", args.donor_id), ("--sending-app", args.sending_app),
                        ("--sending-facility", args.sending_facility),
                        ("--receiving-app", args.receiving_app),
                        ("--receiving-facility", args.receiving_facility)]:
        if contains_hl7_delimiter(value):
            print(f"ERROR: {flag} '{value}' contains an HL7 delimiter character (|^~\\&)", file=sys.stderr)
            sys.exit(1)

    result = build_adt_a04(
        din=args.din,
        donor_id=args.donor_id,
        sending_app=args.sending_app,
        sending_facility=args.sending_facility,
        receiving_app=args.receiving_app,
        receiving_facility=args.receiving_facility,
        assigning_authority=args.assigning_authority,
        test_mode=args.test,
    )

    if args.json:
        output = json.dumps({
            "status": "ok",
            "control_id": result["control_id"],
            "message_type": "ADT^A04",
            "din": args.din,
            "donor_id": args.donor_id,
            "segments": result["segments"],
            "raw_message": result["message"],
        }, indent=2)
    else:
        output = result["message"]

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Message written to {args.output} (control_id={result['control_id']})")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
