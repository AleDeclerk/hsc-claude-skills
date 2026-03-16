#!/usr/bin/env python3
"""
generate_orm_o01.py
-------------------
Generate HL7 v2.5.1 ORM^O01 (Order Message) for HSC donor lab order panels.

Orders are placed under the Donor ID — never under the recipient's MRN.
Supports product types: PBSC (Peripheral Blood Stem Cells), BM (Bone Marrow), CB (Cord Blood).

Usage:
  python generate_orm_o01.py \\
    --donor-id DONOR-2026-0042 \\
    --din W000055508D001 \\
    --product-type PBSC \\
    --output orders.hl7

  # Skip tests already completed by NMDP
  python generate_orm_o01.py \\
    --donor-id DONOR-2026-0042 \\
    --din W000055508D001 \\
    --product-type PBSC \\
    --skip-tests "883-9,10331-7" \\
    --output orders.hl7
"""

import argparse
import datetime
import json
import random
import string
import sys
from datetime import timezone

FIELD_SEP = "|"
COMPONENT_SEP = "^"
REPEAT_SEP = "~"
ESCAPE_CHAR = "\\"
SUBCOMPONENT_SEP = "&"
SEGMENT_TERMINATOR = "\r"

# Standard HSC test panels per product type
# Format: { loinc_code: { name, unit, order_code } }
HL7_DELIMITERS = set("|^~\\&")


def contains_hl7_delimiter(value: str) -> bool:
    """Return True if value contains any HL7 delimiter character."""
    return any(c in HL7_DELIMITERS for c in value)


PANELS = {
    "PBSC": {
        "18207-3": {"name": "CD34+ count", "unit": "10*6/kg", "order_code": "CD34"},
        "883-9":   {"name": "ABO group", "unit": None, "order_code": "ABO"},
        "10331-7": {"name": "Rh type", "unit": None, "order_code": "RH"},
        "6690-2":  {"name": "WBC count", "unit": "10*3/uL", "order_code": "WBC"},
        "600-7":   {"name": "Sterility culture", "unit": None, "order_code": "STERILE"},
        "13949-3": {"name": "CMV IgG", "unit": None, "order_code": "CMV"},
        "7917-8":  {"name": "HIV-1/2 Ab", "unit": None, "order_code": "HIV12"},
        "5196-1":  {"name": "HBsAg", "unit": None, "order_code": "HBSAG"},
        "16128-1": {"name": "HCV Ab", "unit": None, "order_code": "HCVAB"},
        "31201-7": {"name": "HTLV-I/II", "unit": None, "order_code": "HTLV"},
        "20507-0": {"name": "Syphilis RPR", "unit": None, "order_code": "SYPH"},
    },
    "BM": {
        "18207-3": {"name": "CD34+ count", "unit": "10*6/kg", "order_code": "CD34"},
        "883-9":   {"name": "ABO group", "unit": None, "order_code": "ABO"},
        "10331-7": {"name": "Rh type", "unit": None, "order_code": "RH"},
        "6690-2":  {"name": "WBC count", "unit": "10*3/uL", "order_code": "WBC"},
        "26499-4": {"name": "Nucleated RBC", "unit": "10*3/uL", "order_code": "NRBC"},
        "600-7":   {"name": "Sterility culture", "unit": None, "order_code": "STERILE"},
        "13949-3": {"name": "CMV IgG", "unit": None, "order_code": "CMV"},
        "7917-8":  {"name": "HIV-1/2 Ab", "unit": None, "order_code": "HIV12"},
        "5196-1":  {"name": "HBsAg", "unit": None, "order_code": "HBSAG"},
        "16128-1": {"name": "HCV Ab", "unit": None, "order_code": "HCVAB"},
        "31201-7": {"name": "HTLV-I/II", "unit": None, "order_code": "HTLV"},
        "20507-0": {"name": "Syphilis RPR", "unit": None, "order_code": "SYPH"},
    },
    "CB": {
        "18207-3": {"name": "CD34+ count", "unit": "10*6/kg", "order_code": "CD34"},
        "883-9":   {"name": "ABO group", "unit": None, "order_code": "ABO"},
        "10331-7": {"name": "Rh type", "unit": None, "order_code": "RH"},
        "26515-7": {"name": "Platelet count", "unit": "10*3/uL", "order_code": "PLT"},
        "4576-5":  {"name": "Hemoglobin F", "unit": "%", "order_code": "HBF"},
        "26498-6": {"name": "Total nucleated cell count", "unit": "10*6/unit", "order_code": "TNC"},
        "600-7":   {"name": "Sterility culture", "unit": None, "order_code": "STERILE"},
        "13949-3": {"name": "CMV IgG", "unit": None, "order_code": "CMV"},
        "7917-8":  {"name": "HIV-1/2 Ab", "unit": None, "order_code": "HIV12"},
        "5196-1":  {"name": "HBsAg", "unit": None, "order_code": "HBSAG"},
        "16128-1": {"name": "HCV Ab", "unit": None, "order_code": "HCVAB"},
        "31201-7": {"name": "HTLV-I/II", "unit": None, "order_code": "HTLV"},
        "20507-0": {"name": "Syphilis RPR", "unit": None, "order_code": "SYPH"},
    },
}


def timestamp(dt=None):
    dt = dt or datetime.datetime.now(timezone.utc)
    return dt.strftime("%Y%m%d%H%M%S")


def message_control_id():
    rand = "".join(random.choices(string.digits, k=8))
    return f"ORM{rand}"


def order_number():
    rand = "".join(random.choices(string.digits, k=6))
    return f"ORD{rand}"


def build_msh(sending_app, sending_facility, receiving_app, receiving_facility, control_id, test_mode=False):
    proc_id = "T" if test_mode else "P"
    fields = [
        "MSH",
        f"{COMPONENT_SEP}{REPEAT_SEP}{ESCAPE_CHAR}{SUBCOMPONENT_SEP}",
        sending_app, sending_facility,
        receiving_app, receiving_facility,
        timestamp(), "",
        "ORM^O01",
        control_id,
        proc_id,
        "2.5.1",
    ]
    return FIELD_SEP.join(fields) + SEGMENT_TERMINATOR


def build_pid_donor(donor_id, din, assigning_authority="LSU_SCL"):
    """PID for donor — no MRN, no real personal data."""
    primary_id = f"{din}^^^{assigning_authority}^DIN"
    secondary_id = f"{donor_id}^^^{assigning_authority}^DONOR_ID"
    patient_id_list = f"{primary_id}{REPEAT_SEP}{secondary_id}"

    fields = [
        "PID",
        "1", "",
        patient_id_list,
        "",
        "ANONYMOUS^DONOR^^^^^L",
        "", "00010101", "U",
    ]
    return FIELD_SEP.join(fields) + SEGMENT_TERMINATOR


def build_orc(order_num, order_status="NW"):
    """ORC (Common Order) segment."""
    fields = [
        "ORC",
        order_status,   # ORC-1 Order Control (NW=New)
        order_num,      # ORC-2 Placer Order Number
        "",             # ORC-3 Filler Order Number
        "",             # ORC-4 Placer Group Number
        "SC",           # ORC-5 Order Status (SC=Scheduled)
        "",             # ORC-6 Response Flag
        "",             # ORC-7 Quantity/Timing (deprecated)
        "",             # ORC-8 Parent
        timestamp(),    # ORC-9 Date/Time of Transaction
    ]
    return FIELD_SEP.join(fields) + SEGMENT_TERMINATOR


def build_obr(set_id, order_num, loinc_code, test_name, din):
    """OBR (Observation Request) segment for a single test."""
    fields = [
        "OBR",
        str(set_id),    # OBR-1 Set ID
        order_num,      # OBR-2 Placer Order Number
        "",             # OBR-3 Filler Order Number
        f"{loinc_code}^{test_name}^LN",  # OBR-4 Universal Service ID (LOINC)
        "",             # OBR-5 Priority
        timestamp(),    # OBR-6 Requested Date/Time
        "",             # OBR-7 Observation Date/Time
        "",             # OBR-8 Observation End Date/Time
        "",             # OBR-9 Collection Volume
        "",             # OBR-10 Collector Identifier
        "",             # OBR-11 Specimen Action Code
        "",             # OBR-12 Danger Code
        "",             # OBR-13 Relevant Clinical Info
        "",             # OBR-14 Specimen Received Date/Time
        "",             # OBR-15 Specimen Source
        "",             # OBR-16 Ordering Provider
        "",             # OBR-17 Order Callback Phone
        "",             # OBR-18 Placer Field 1 (unused)
        din,            # OBR-19 Placer Field 2 — DIN for traceability
    ]
    return FIELD_SEP.join(fields) + SEGMENT_TERMINATOR


def build_orm_o01(
    donor_id,
    din,
    product_type="PBSC",
    skip_loincs=None,
    sending_app="VERITAS",
    sending_facility="LSU_SCL",
    receiving_app="BEAKER",
    receiving_facility="LSU",
    assigning_authority="LSU_SCL",
    test_mode=False,
):
    skip_loincs = set(skip_loincs or [])
    panel = PANELS.get(product_type.upper())
    if not panel:
        raise ValueError(f"Unknown product type: {product_type}. Supported: {list(PANELS.keys())}")

    control_id = message_control_id()
    active_tests = {loinc: info for loinc, info in panel.items() if loinc not in skip_loincs}
    skipped_tests = {loinc: info for loinc, info in panel.items() if loinc in skip_loincs}

    msh = build_msh(sending_app, sending_facility, receiving_app, receiving_facility, control_id, test_mode)
    pid = build_pid_donor(donor_id, din, assigning_authority)

    order_segments = []
    order_ids = []
    for i, (loinc, info) in enumerate(active_tests.items(), start=1):
        ord_num = order_number()
        order_ids.append(ord_num)
        orc = build_orc(ord_num, "NW")
        obr = build_obr(i, ord_num, loinc, info["name"], din)
        order_segments.extend([orc, obr])

    message = msh + pid + "".join(order_segments)

    return {
        "message": message,
        "control_id": control_id,
        "product_type": product_type,
        "orders_placed": [
            {"order_id": oid, "loinc": loinc, "name": info["name"]}
            for oid, (loinc, info) in zip(order_ids, active_tests.items())
        ],
        "orders_skipped": [
            {"loinc": loinc, "name": info["name"], "reason": "result_available_from_nmdp"}
            for loinc, info in skipped_tests.items()
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Generate HL7 ORM^O01 lab order panel for HSC donor")
    parser.add_argument("--donor-id", required=True)
    parser.add_argument("--din", required=True)
    parser.add_argument("--product-type", default="PBSC", choices=["PBSC", "BM", "CB"])
    parser.add_argument("--skip-tests", default="", help="Comma-separated LOINC codes to skip")
    parser.add_argument("--sending-app", default="VERITAS")
    parser.add_argument("--sending-facility", default="LSU_SCL")
    parser.add_argument("--receiving-app", default="BEAKER")
    parser.add_argument("--receiving-facility", default="LSU")
    parser.add_argument("--output", "-o")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    skip_loincs = [t.strip() for t in args.skip_tests.split(",") if t.strip()]

    # Reject HL7 delimiter characters in user-supplied identifiers
    for flag, value in [("--donor-id", args.donor_id), ("--din", args.din),
                        ("--sending-app", args.sending_app),
                        ("--sending-facility", args.sending_facility),
                        ("--receiving-app", args.receiving_app),
                        ("--receiving-facility", args.receiving_facility)]:
        if contains_hl7_delimiter(value):
            print(f"ERROR: {flag} '{value}' contains an HL7 delimiter character (|^~\\&)", file=sys.stderr)
            sys.exit(1)

    try:
        result = build_orm_o01(
            donor_id=args.donor_id,
            din=args.din,
            product_type=args.product_type,
            skip_loincs=skip_loincs,
            sending_app=args.sending_app,
            sending_facility=args.sending_facility,
            receiving_app=args.receiving_app,
            receiving_facility=args.receiving_facility,
            test_mode=args.test,
        )
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        output = json.dumps({
            "status": "ok",
            "control_id": result["control_id"],
            "message_type": "ORM^O01",
            "donor_id": args.donor_id,
            "din": args.din,
            "product_type": result["product_type"],
            "orders_placed": result["orders_placed"],
            "orders_skipped": result["orders_skipped"],
            "raw_message": result["message"],
        }, indent=2)
    else:
        output = result["message"]

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        n_placed = len(result["orders_placed"])
        n_skipped = len(result["orders_skipped"])
        print(f"ORM^O01 written to {args.output} ({n_placed} orders placed, {n_skipped} skipped)")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
