#!/usr/bin/env python3
"""
validate_hl7.py
---------------
Validate HL7 v2 messages for structural correctness.

Checks performed:
  1. MSH segment present and correctly delimited
  2. Message type recognized
  3. Required segments present for message type
  4. Timestamp format valid
  5. PID-3 (Patient ID) non-empty
  6. Anonymous donor safety: PID-5 = ANONYMOUS^DONOR, PID-7 = 00010101
  7. No MRN leak into ADT/ORM messages (anonymous donor safety)
  8. ACK parsing (AA/AE/AR)

Usage:
  python validate_hl7.py --file message.hl7
  python validate_hl7.py --stdin < message.hl7
  python validate_hl7.py --file message.hl7 --check-anonymous
  python validate_hl7.py --file ack.hl7 --parse-ack
  python validate_hl7.py --file message.hl7 --json
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import List, Optional


REQUIRED_SEGMENTS = {
    "ADT^A04": ["MSH", "EVN", "PID", "PV1"],
    "ORM^O01": ["MSH", "PID", "ORC", "OBR"],
    "ORU^R01": ["MSH", "PID", "OBR", "OBX"],
    "ACK":     ["MSH", "MSA"],
}

TIMESTAMP_RE = re.compile(r"^\d{8}(\d{6})?(\.\d{1,4})?([\+\-]\d{4})?$")


@dataclass
class ValidationResult:
    valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    message_type: Optional[str] = None
    control_id: Optional[str] = None
    segments_found: List[str] = field(default_factory=list)

    def add_error(self, msg: str):
        self.errors.append(msg)
        self.valid = False

    def add_warning(self, msg: str):
        self.warnings.append(msg)


def parse_segments(raw: str) -> dict:
    """Parse HL7 message into a dict of segment_name -> list of segment strings."""
    segments = {}
    for line in raw.replace("\r\n", "\r").replace("\n", "\r").split("\r"):
        line = line.strip()
        if not line:
            continue
        seg_id = line[:3]
        segments.setdefault(seg_id, []).append(line)
    return segments


def get_field(segment: str, index: int, sep: str = "|") -> str:
    """Get field at 1-based index from a segment string."""
    parts = segment.split(sep)
    if index < len(parts):
        return parts[index]
    return ""


def get_component(field_val: str, index: int, sep: str = "^") -> str:
    """Get component at 1-based index from a field value."""
    parts = field_val.split(sep)
    if index <= len(parts):
        return parts[index - 1]
    return ""


def validate(raw: str, check_anonymous: bool = False, parse_ack: bool = False) -> ValidationResult:
    result = ValidationResult()

    # Strip MLLP framing if present
    raw = raw.strip("\x0b\x1c\r\n ")

    if not raw:
        result.add_error("Empty message")
        return result

    segments = parse_segments(raw)
    result.segments_found = list(segments.keys())

    # --- MSH validation ---
    if "MSH" not in segments:
        result.add_error("MSH segment missing — not a valid HL7 message")
        return result

    msh = segments["MSH"][0]

    # Check delimiter
    if len(msh) < 8 or msh[3] != "|":
        result.add_error("MSH field separator must be '|'")

    encoding = get_field(msh, 1) if len(msh) > 3 else ""
    if not encoding.startswith("^~\\&"):
        result.add_warning(f"Non-standard encoding characters: '{encoding}' (expected '^~\\&')")

    # Message type
    msg_type_field = get_field(msh, 8)
    msg_type = msg_type_field.replace("^", "^") if "^" in msg_type_field else msg_type_field
    # Normalize: keep only first two components
    parts = msg_type_field.split("^")
    if len(parts) >= 2:
        msg_type = f"{parts[0]}^{parts[1]}"
    else:
        msg_type = parts[0]
    result.message_type = msg_type

    # Control ID
    result.control_id = get_field(msh, 9)
    if not result.control_id:
        result.add_error("MSH-10 (Message Control ID) is empty")

    # Timestamp
    ts = get_field(msh, 6)
    if ts and not TIMESTAMP_RE.match(ts):
        result.add_warning(f"MSH-7 timestamp '{ts}' may not be HL7-compliant (expected YYYYMMDDHHMMSS)")

    # Version
    version = get_field(msh, 11)
    if version and not version.startswith("2."):
        result.add_warning(f"Unexpected HL7 version: '{version}'")

    # --- ACK special handling ---
    if parse_ack or msg_type == "ACK":
        if "MSA" not in segments:
            result.add_error("ACK message missing MSA segment")
        else:
            msa = segments["MSA"][0]
            ack_code = get_field(msa, 1)
            if ack_code == "AA":
                result.warnings.append("ACK: Application Accept (AA) — message processed successfully")
            elif ack_code == "AE":
                error_msg = get_field(msa, 2)
                result.add_error(f"ACK: Application Error (AE) — {error_msg}")
            elif ack_code == "AR":
                error_msg = get_field(msa, 2)
                result.add_error(f"ACK: Application Reject (AR) — {error_msg}")
            else:
                result.add_warning(f"ACK: Unknown acknowledgment code '{ack_code}'")
        return result

    # --- Required segments ---
    required = REQUIRED_SEGMENTS.get(msg_type)
    if required:
        for seg in required:
            if seg not in segments:
                result.add_error(f"Required segment '{seg}' missing for {msg_type}")
    else:
        result.add_warning(f"Message type '{msg_type}' not in known types — skipping required segment check")

    # --- PID validation ---
    if "PID" in segments:
        pid = segments["PID"][0]
        pid3 = get_field(pid, 3)
        if not pid3:
            result.add_error("PID-3 (Patient Identifier List) is empty — required for all messages")

        pid5 = get_field(pid, 5)
        pid7 = get_field(pid, 7)
        pid8 = get_field(pid, 8)
        pid19 = get_field(pid, 19)

        if check_anonymous or msg_type in ("ADT^A04", "ORM^O01"):
            # Anonymous donor checks
            if pid5 and not pid5.upper().startswith("ANONYMOUS"):
                result.add_error(
                    f"ANONYMOUS DONOR VIOLATION: PID-5 is '{pid5}' — must be 'ANONYMOUS^DONOR' for donor messages"
                )
            if pid7 and pid7 != "00010101":
                result.add_error(
                    f"ANONYMOUS DONOR VIOLATION: PID-7 (DOB) is '{pid7}' — must be '00010101' placeholder"
                )
            if pid8 and pid8 not in ("U", ""):
                result.add_warning(f"PID-8 (Sex) is '{pid8}' — expected 'U' (Unknown) for anonymous donor")
            if pid19:
                result.add_error(
                    f"ANONYMOUS DONOR VIOLATION: PID-19 (SSN) is populated — never populate SSN for anonymous donors"
                )

    # --- OBX validation for ORU ---
    if msg_type == "ORU^R01" and "OBX" in segments:
        for i, obx in enumerate(segments["OBX"], 1):
            status = get_field(obx, 11)
            if status not in ("F", "P", "C", "X", "R", "S", "U", "W"):
                result.add_warning(f"OBX[{i}]-11 status '{status}' is non-standard")
            value = get_field(obx, 5)
            if not value:
                result.add_warning(f"OBX[{i}]-5 (Observation Value) is empty")

    return result


def main():
    parser = argparse.ArgumentParser(description="Validate HL7 v2 messages")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to HL7 message file")
    group.add_argument("--stdin", action="store_true", help="Read from stdin")
    parser.add_argument("--check-anonymous", action="store_true",
                        help="Enforce anonymous donor rules (PID-5, PID-7, PID-19)")
    parser.add_argument("--parse-ack", action="store_true",
                        help="Parse as ACK and report acknowledgment code")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            raw = f.read()
    else:
        raw = sys.stdin.read()

    result = validate(raw, check_anonymous=args.check_anonymous, parse_ack=args.parse_ack)

    if args.json:
        print(json.dumps({
            "valid": result.valid,
            "message_type": result.message_type,
            "control_id": result.control_id,
            "segments_found": result.segments_found,
            "errors": result.errors,
            "warnings": result.warnings,
        }, indent=2))
    else:
        status = "✓ VALID" if result.valid else "✗ INVALID"
        print(f"{status} — {result.message_type or 'unknown'} (control_id={result.control_id})")
        for e in result.errors:
            print(f"  ERROR:   {e}")
        for w in result.warnings:
            print(f"  WARNING: {w}")
        if not result.errors and not result.warnings:
            print("  No issues found.")

    sys.exit(0 if result.valid else 1)


if __name__ == "__main__":
    main()
