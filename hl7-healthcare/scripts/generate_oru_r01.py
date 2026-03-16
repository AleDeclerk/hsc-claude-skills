#!/usr/bin/env python3
"""
generate_oru_r01.py
-------------------
Generate HL7 v2.5.1 ORU^R01 (Observation Result) messages to route
donor lab results to the recipient's Epic chart.

Results are attributed to the donor product (DIN), never to the recipient
as personal lab results. The recipient MRN is placed in PID so Epic routes
correctly, but all result headers reference the DIN.

Usage:
  python generate_oru_r01.py \\
    --donor-id DONOR-2026-0042 \\
    --recipient-mrn MRN123456 \\
    --din W000055508D001 \\
    --results '[{"loinc":"18207-3","name":"CD34+ count","value":"3.2","unit":"10*6/kg","status":"F","abnormal":false}]' \\
    --output oru_result.hl7

  # Or pass results from a JSON file
  python generate_oru_r01.py \\
    --donor-id DONOR-2026-0042 \\
    --recipient-mrn MRN123456 \\
    --din W000055508D001 \\
    --results-file results.json \\
    --output oru_result.hl7
"""

import argparse
import datetime
import json
import random
import string
import sys
from datetime import timezone

HL7_DELIMITERS = set("|^~\\&")


def contains_hl7_delimiter(value: str) -> bool:
    """Return True if value contains any HL7 delimiter character."""
    return any(c in HL7_DELIMITERS for c in value)


FIELD_SEP = "|"
COMPONENT_SEP = "^"
REPEAT_SEP = "~"
ESCAPE_CHAR = "\\"
SUBCOMPONENT_SEP = "&"
SEGMENT_TERMINATOR = "\r"


def timestamp(dt=None):
    dt = dt or datetime.datetime.now(timezone.utc)
    return dt.strftime("%Y%m%d%H%M%S")


def message_control_id():
    rand = "".join(random.choices(string.digits, k=8))
    return f"ORU{rand}"


def build_msh(sending_app, sending_facility, receiving_app, receiving_facility, control_id, test_mode=False):
    proc_id = "T" if test_mode else "P"
    fields = [
        "MSH",
        f"{COMPONENT_SEP}{REPEAT_SEP}{ESCAPE_CHAR}{SUBCOMPONENT_SEP}",
        sending_app, sending_facility,
        receiving_app, receiving_facility,
        timestamp(), "",
        "ORU^R01",
        control_id,
        proc_id,
        "2.5.1",
    ]
    return FIELD_SEP.join(fields) + SEGMENT_TERMINATOR


def build_pid_recipient(recipient_mrn, receiving_facility="LSU"):
    """
    PID for the RECIPIENT (Epic chart target).
    The MRN goes here so Epic routes results to the right patient.
    All result content references the DIN, not the patient identity.
    """
    patient_id = f"{recipient_mrn}^^^{receiving_facility}^MRN"
    fields = [
        "PID",
        "1", "",
        patient_id,
        "", "", "", "", "",
    ]
    return FIELD_SEP.join(fields) + SEGMENT_TERMINATOR


def build_obr_result(set_id, din, donor_id, filler_order_num=None):
    """
    OBR header for a result group.
    Report header reads: 'Donor Product — DIN XXXX'
    This labels the result block in Epic as donor-product data.
    """
    filler_order_num = filler_order_num or f"RES{random.randint(100000,999999)}"
    report_header = f"Donor Product - DIN {din}"

    fields = [
        "OBR",
        str(set_id),
        "",                          # OBR-2 Placer Order Number
        filler_order_num,            # OBR-3 Filler Order Number
        f"99DONOR^{report_header}^L",# OBR-4 Universal Service ID (local code, donor report header)
        "",                          # OBR-5 Priority
        timestamp(),                 # OBR-6 Requested Date/Time
        timestamp(),                 # OBR-7 Observation Date/Time
        "",
        "",
        "",
        "",
        "",
        f"DIN={din}",                # OBR-13 Relevant Clinical Info — DIN reference
        timestamp(),                 # OBR-14 Specimen Received Date/Time
        "",
        "",
        "",
        din,                         # OBR-18 Placer Field 1 — DIN
        donor_id,                    # OBR-19 Placer Field 2 — Donor ID
    ]
    return FIELD_SEP.join(fields) + SEGMENT_TERMINATOR


def build_obx_din(set_id, din):
    """
    OBX segment identifying the donor product by DIN.

    Required for Epic/WellSky routing — signals that result observations
    belong to a donor product, not the recipient's own labs.

    OBX-3: DIN^Donor Product Identifier^L  (local code, L = local coding system)
    OBX-5: DIN value string
    OBX-11: F (Final)
    """
    fields = [
        "OBX",
        str(set_id),
        "ST",                               # OBX-2 Value Type — String
        "DIN^Donor Product Identifier^L",   # OBX-3 Observation Identifier (local)
        "",                                  # OBX-4 Observation Sub-ID
        din,                                 # OBX-5 Observation Value — DIN
        "",                                  # OBX-6 Units (not applicable)
        "",                                  # OBX-7 Reference Range
        "",                                  # OBX-8 Abnormal Flags
        "",                                  # OBX-9 Probability
        "",                                  # OBX-10 Nature of Abnormal Test
        "F",                                 # OBX-11 Observation Result Status — Final
        "",                                  # OBX-12 Effective Date of Reference Range
        "",                                  # OBX-13 User Defined Access Checks
        timestamp(),                         # OBX-14 Date/Time of Observation
    ]
    return FIELD_SEP.join(fields) + SEGMENT_TERMINATOR


def build_nte(set_id, din):
    """
    NTE (Notes and Comments) segment following the DIN OBX.

    Adds a human-readable report header in Epic that labels the result
    block as donor product data, satisfying WellSky field mapping
    requirements (see references/oru_r01.md — Epic/WellSky Custom Fields).
    """
    fields = [
        "NTE",
        str(set_id),     # NTE-1 Set ID
        "",               # NTE-2 Source of Comment (empty — default)
        f"Donor Product \u2014 DIN {din}",  # NTE-3 Comment — em dash per spec
    ]
    return FIELD_SEP.join(fields) + SEGMENT_TERMINATOR


def build_obx(set_id, loinc, name, value, unit, status, abnormal_flag=""):
    """
    OBX (Observation/Result) segment for a single test result.
    
    status values:
      F = Final
      P = Preliminary
      C = Corrected
      X = Cannot Obtain
    
    abnormal_flag values:
      H = High, L = Low, A = Abnormal, N = Normal (empty = normal)
    """
    # Determine value type
    value_type = "NM" if _is_numeric(value) else "ST"
    unit_str = f"{unit}^^ISO+" if unit else ""

    fields = [
        "OBX",
        str(set_id),
        value_type,                          # OBX-2 Value Type
        f"{loinc}^{name}^LN",               # OBX-3 Observation Identifier (LOINC)
        "",                                   # OBX-4 Observation Sub-ID
        str(value),                           # OBX-5 Observation Value
        unit_str,                             # OBX-6 Units
        "",                                   # OBX-7 Reference Range
        abnormal_flag,                        # OBX-8 Abnormal Flags
        "",                                   # OBX-9 Probability
        "",                                   # OBX-10 Nature of Abnormal Test
        status,                               # OBX-11 Observation Result Status
        "",                                   # OBX-12 Effective Date of Reference Range
        "",                                   # OBX-13 User Defined Access Checks
        timestamp(),                          # OBX-14 Date/Time of Observation
    ]
    return FIELD_SEP.join(fields) + SEGMENT_TERMINATOR


def _is_numeric(value):
    try:
        float(str(value))
        return True
    except (ValueError, TypeError):
        return False


def build_oru_r01(
    donor_id,
    recipient_mrn,
    din,
    results,
    sending_app="VERITAS",
    sending_facility="LSU_SCL",
    receiving_app="EPIC",
    receiving_facility="LSU",
    test_mode=False,
):
    """
    Build a complete ORU^R01 message.

    results: list of dicts with keys:
      - loinc (str)
      - name (str)
      - value (str or number)
      - unit (str or None)
      - status (str: F/P/C)
      - abnormal (bool)
    """
    control_id = message_control_id()

    msh = build_msh(sending_app, sending_facility, receiving_app, receiving_facility, control_id, test_mode)
    pid = build_pid_recipient(recipient_mrn, receiving_facility)
    obr = build_obr_result(set_id=1, din=din, donor_id=donor_id)

    # OBX-1: DIN identifier (Epic/WellSky custom field for donor product routing)
    din_obx = build_obx_din(set_id=1, din=din)
    # NTE-1: Report header following the DIN OBX
    din_nte = build_nte(set_id=1, din=din)

    obx_segments = []
    anomalies = []
    for i, r in enumerate(results, start=2):  # start=2; set_id=1 is the DIN OBX
        abnormal_flag = "A" if r.get("abnormal") else "N"
        obx = build_obx(
            set_id=i,
            loinc=r["loinc"],
            name=r["name"],
            value=r["value"],
            unit=r.get("unit"),
            status=r.get("status", "F"),
            abnormal_flag=abnormal_flag if r.get("abnormal") else "",
        )
        obx_segments.append(obx)
        if r.get("abnormal"):
            anomalies.append({"loinc": r["loinc"], "name": r["name"], "value": r["value"]})

    message = msh + pid + obr + din_obx + din_nte + "".join(obx_segments)

    return {
        "message": message,
        "control_id": control_id,
        "results_count": len(results),
        "anomalies": anomalies,
        "all_clear": len(anomalies) == 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate HL7 ORU^R01 donor result message for Epic routing")
    parser.add_argument("--donor-id", required=True)
    parser.add_argument("--recipient-mrn", required=True, help="Recipient's Epic MRN (for chart routing)")
    parser.add_argument("--din", required=True)
    parser.add_argument("--results", help="JSON array of result objects (inline)")
    parser.add_argument("--results-file", help="Path to JSON file with result objects")
    parser.add_argument("--sending-app", default="VERITAS")
    parser.add_argument("--sending-facility", default="LSU_SCL")
    parser.add_argument("--receiving-app", default="EPIC")
    parser.add_argument("--receiving-facility", default="LSU")
    parser.add_argument("--output", "-o")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    # Reject HL7 delimiter characters in user-supplied identifiers
    for flag, value in [("--donor-id", args.donor_id), ("--din", args.din),
                        ("--recipient-mrn", args.recipient_mrn),
                        ("--sending-app", args.sending_app),
                        ("--sending-facility", args.sending_facility),
                        ("--receiving-app", args.receiving_app),
                        ("--receiving-facility", args.receiving_facility)]:
        if contains_hl7_delimiter(value):
            print(f"ERROR: {flag} '{value}' contains an HL7 delimiter character (|^~\\&)", file=sys.stderr)
            sys.exit(1)

    # Load results
    if args.results_file:
        with open(args.results_file) as f:
            results = json.load(f)
    elif args.results:
        results = json.loads(args.results)
    else:
        print("ERROR: Provide --results or --results-file", file=sys.stderr)
        sys.exit(1)

    result = build_oru_r01(
        donor_id=args.donor_id,
        recipient_mrn=args.recipient_mrn,
        din=args.din,
        results=results,
        sending_app=args.sending_app,
        sending_facility=args.sending_facility,
        receiving_app=args.receiving_app,
        receiving_facility=args.receiving_facility,
        test_mode=args.test,
    )

    if result["anomalies"]:
        print(f"WARNING: {len(result['anomalies'])} anomalous result(s) detected:", file=sys.stderr)
        for a in result["anomalies"]:
            print(f"  - {a['name']} ({a['loinc']}): {a['value']}", file=sys.stderr)

    if args.json:
        output = json.dumps({
            "status": "ok",
            "control_id": result["control_id"],
            "message_type": "ORU^R01",
            "donor_id": args.donor_id,
            "recipient_mrn": args.recipient_mrn,
            "din": args.din,
            "results_count": result["results_count"],
            "all_clear": result["all_clear"],
            "anomalies": result["anomalies"],
            "raw_message": result["message"],
        }, indent=2)
    else:
        output = result["message"]

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        status = "ALL CLEAR" if result["all_clear"] else f"{len(result['anomalies'])} ANOMALY(IES)"
        print(f"ORU^R01 written to {args.output} — {status}")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
