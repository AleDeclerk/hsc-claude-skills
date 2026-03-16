#!/usr/bin/env python3
"""
parse_hl7.py
------------
Parse and inspect HL7 v2 messages. Human-readable segment and field breakdown.

Usage:
  python parse_hl7.py --file message.hl7 --all
  python parse_hl7.py --file message.hl7 --segment PID
  python parse_hl7.py --file message.hl7 --segment OBX --json
  python parse_hl7.py --stdin < message.hl7 --all
"""

import argparse
import json
import sys


FIELD_NAMES = {
    "MSH": {
        1: "Field Separator",
        2: "Encoding Characters",
        3: "Sending Application",
        4: "Sending Facility",
        5: "Receiving Application",
        6: "Receiving Facility",
        7: "Date/Time of Message",
        8: "Security",
        9: "Message Type",
        10: "Message Control ID",
        11: "Processing ID",
        12: "Version ID",
    },
    "EVN": {
        1: "Event Type Code",
        2: "Recorded Date/Time",
        3: "Date/Time Planned Event",
        4: "Event Reason Code",
        5: "Operator ID",
        6: "Event Occurred",
    },
    "PID": {
        1: "Set ID",
        2: "Patient ID (ext, deprecated)",
        3: "Patient Identifier List",
        4: "Alternate Patient ID (deprecated)",
        5: "Patient Name",
        6: "Mother's Maiden Name",
        7: "Date of Birth",
        8: "Administrative Sex",
        9: "Patient Alias",
        10: "Race",
        11: "Patient Address",
        18: "Patient Account Number",
        19: "SSN (⚠ NEVER populate for anon donors)",
    },
    "PV1": {
        1: "Set ID",
        2: "Patient Class",
        3: "Assigned Patient Location",
        44: "Admit Date/Time",
        45: "Discharge Date/Time",
    },
    "ORC": {
        1: "Order Control",
        2: "Placer Order Number",
        3: "Filler Order Number",
        5: "Order Status",
        9: "Date/Time of Transaction",
    },
    "OBR": {
        1: "Set ID",
        2: "Placer Order Number",
        3: "Filler Order Number",
        4: "Universal Service ID (LOINC)",
        5: "Priority",
        6: "Requested Date/Time",
        7: "Observation Date/Time",
        13: "Relevant Clinical Info",
        14: "Specimen Received Date/Time",
        18: "Placer Field 1 (DIN)",
        19: "Placer Field 2 (Donor ID)",
    },
    "OBX": {
        1: "Set ID",
        2: "Value Type",
        3: "Observation Identifier (LOINC)",
        4: "Observation Sub-ID",
        5: "Observation Value",
        6: "Units",
        7: "Reference Range",
        8: "Abnormal Flags",
        11: "Observation Result Status",
        14: "Date/Time of Observation",
    },
    "MSA": {
        1: "Acknowledgment Code (AA/AE/AR)",
        2: "Message Control ID",
        3: "Text Message",
    },
}


def parse_message(raw: str) -> list:
    """Parse raw HL7 into list of (segment_id, fields) tuples."""
    parsed = []
    clean = raw.strip("\x0b\x1c").replace("\r\n", "\r").replace("\n", "\r")
    for line in clean.split("\r"):
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        seg_id = parts[0]
        parsed.append((seg_id, parts))
    return parsed


def format_segment(seg_id: str, fields: list, use_json: bool = False) -> str:
    names = FIELD_NAMES.get(seg_id, {})
    # MSH-1 is the field separator character (|) itself — it does not appear in the
    # split array, so fields[1] corresponds to MSH-2, fields[2] to MSH-3, etc.
    field_offset = 1 if seg_id == "MSH" else 0
    if use_json:
        result = {"segment": seg_id, "fields": {}}
        for i, val in enumerate(fields[1:], start=1):
            if val:
                n = i + field_offset
                label = names.get(n, f"Field {n}")
                result["fields"][f"{n}:{label}"] = val
        return json.dumps(result, indent=2)
    else:
        lines = [f"┌── {seg_id} ─────────────────────────────────────────"]
        for i, val in enumerate(fields[1:], start=1):
            n = i + field_offset
            label = names.get(n, f"Field {n}")
            flag = " ⚠" if "NEVER" in label and val else ""
            if val:
                lines.append(f"│  [{n:02d}] {label}: {val}{flag}")
        lines.append("└────────────────────────────────────────────────")
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Parse and inspect HL7 v2 messages")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to HL7 file")
    group.add_argument("--stdin", action="store_true", help="Read from stdin")
    parser.add_argument("--segment", "-s", help="Show only this segment type (e.g. PID, OBX)")
    parser.add_argument("--all", "-a", action="store_true", help="Show all segments")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    if not args.segment and not args.all:
        print("ERROR: Specify --segment <SEG> or --all", file=sys.stderr)
        sys.exit(1)

    if args.file:
        with open(args.file) as f:
            raw = f.read()
    else:
        raw = sys.stdin.read()

    parsed = parse_message(raw)
    outputs = []

    for seg_id, fields in parsed:
        if args.all or (args.segment and seg_id == args.segment.upper()):
            outputs.append(format_segment(seg_id, fields, use_json=args.json))

    if not outputs:
        print(f"No segments found matching '{args.segment}'", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(f"[{','.join(outputs)}]")
    else:
        print("\n".join(outputs))


if __name__ == "__main__":
    main()
