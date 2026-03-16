#!/usr/bin/env python3
"""
donor_registration.py
---------------------
Feature flag adapter for HSC donor registration.

Selects the backend based on the DONOR_BACKEND environment variable
or --backend argument:

  softbank   — Current backend (Phase 1). Delegates to generate_adt_a04.py
               logic. SoftBank receives an ADT^A04 phantom patient record.

  softdonor  — Future backend (Phase 2, post October 2026). Raises
               NotImplementedError until the SCC Soft Computer API spec
               is available.

Usage:
  # Using environment variable
  DONOR_BACKEND=softbank python donor_registration.py \\
    --din W000055508D001 --donor-id DONOR-2026-0042

  # Using --backend argument (takes precedence over env var)
  python donor_registration.py \\
    --backend softbank \\
    --din W000055508D001 --donor-id DONOR-2026-0042 --json

  # SoftDonor (stub — will raise NotImplementedError)
  python donor_registration.py \\
    --backend softdonor \\
    --din W000055508D001 --donor-id DONOR-2026-0042
"""

import argparse
import json
import os
import sys

# Import generate_adt_a04 from the same scripts directory
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from generate_adt_a04 import (  # noqa: E402
    build_adt_a04,
    validate_din,
    contains_hl7_delimiter,
)

VALID_BACKENDS = ("softbank", "softdonor")

SOFTDONOR_NOT_IMPLEMENTED_MSG = (
    "SoftDonor API spec pending discovery call with SCC Soft Computer. "
    "Set DONOR_BACKEND=softbank until Phase 2."
)


def register_donor_softbank(
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
    Register an anonymous HSC donor via SoftBank (Phase 1 backend).

    Delegates to generate_adt_a04.build_adt_a04() and returns the same
    result dict augmented with backend metadata.
    """
    result = build_adt_a04(
        din=din,
        donor_id=donor_id,
        sending_app=sending_app,
        sending_facility=sending_facility,
        receiving_app=receiving_app,
        receiving_facility=receiving_facility,
        assigning_authority=assigning_authority,
        test_mode=test_mode,
    )
    result["backend"] = "softbank"
    return result


def register_donor_softdonor(din: str, donor_id: str, **kwargs) -> dict:
    """
    Register an anonymous HSC donor via SoftDonor (Phase 2 backend).

    NOT YET IMPLEMENTED — raises NotImplementedError until the API spec
    is received from SCC Soft Computer (expected post October 2026).
    """
    raise NotImplementedError(SOFTDONOR_NOT_IMPLEMENTED_MSG)


def register_donor(
    backend: str,
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
    Route donor registration to the appropriate backend.

    Parameters
    ----------
    backend : str
        "softbank" or "softdonor"
    din : str
        ISBT-128 Donation Identification Number
    donor_id : str
        Internal donor ID (e.g. DONOR-2026-0042)

    Returns
    -------
    dict
        Result dict from the selected backend, including 'backend' key
        indicating which backend processed the request.

    Raises
    ------
    ValueError
        If backend is not a recognised value.
    NotImplementedError
        If backend is "softdonor" (Phase 2 — not yet available).
    """
    backend = backend.lower().strip()

    if backend not in VALID_BACKENDS:
        raise ValueError(
            f"Unknown DONOR_BACKEND '{backend}'. Valid values: {', '.join(VALID_BACKENDS)}"
        )

    if backend == "softbank":
        return register_donor_softbank(
            din=din,
            donor_id=donor_id,
            sending_app=sending_app,
            sending_facility=sending_facility,
            receiving_app=receiving_app,
            receiving_facility=receiving_facility,
            assigning_authority=assigning_authority,
            test_mode=test_mode,
        )

    # softdonor
    return register_donor_softdonor(din=din, donor_id=donor_id)


def resolve_backend(args_backend: str | None) -> str:
    """
    Resolve the backend from --backend argument or DONOR_BACKEND env var.
    --backend takes precedence.
    """
    if args_backend:
        return args_backend
    env = os.environ.get("DONOR_BACKEND", "").strip()
    if env:
        return env
    # Default to softbank if nothing set
    return "softbank"


def main():
    parser = argparse.ArgumentParser(
        description="Register an anonymous HSC donor via the configured backend"
    )
    parser.add_argument(
        "--backend",
        choices=VALID_BACKENDS,
        help="Backend to use: softbank (default) or softdonor. "
             "Can also be set via DONOR_BACKEND env var.",
    )
    parser.add_argument("--din", required=True, help="ISBT-128 Donation Identification Number")
    parser.add_argument("--donor-id", required=True, help="Internal Donor ID (e.g. DONOR-2026-0042)")
    parser.add_argument("--sending-app", default="VERITAS")
    parser.add_argument("--sending-facility", default="LSU_SCL")
    parser.add_argument("--receiving-app", default="SOFTBANK")
    parser.add_argument("--receiving-facility", default="LSU")
    parser.add_argument("--assigning-authority", default="LSU_SCL")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument("--test", action="store_true", help="Use test processing ID (T)")
    parser.add_argument("--json", action="store_true", help="Output structured JSON")
    args = parser.parse_args()

    backend = resolve_backend(args.backend)

    # Validate inputs
    if not validate_din(args.din):
        print(f"ERROR: Invalid DIN format: '{args.din}'", file=sys.stderr)
        sys.exit(1)

    for flag, value in [
        ("--donor-id", args.donor_id),
        ("--sending-app", args.sending_app),
        ("--sending-facility", args.sending_facility),
        ("--receiving-app", args.receiving_app),
        ("--receiving-facility", args.receiving_facility),
    ]:
        if contains_hl7_delimiter(value):
            print(
                f"ERROR: {flag} '{value}' contains an HL7 delimiter character (|^~\\&)",
                file=sys.stderr,
            )
            sys.exit(1)

    try:
        result = register_donor(
            backend=backend,
            din=args.din,
            donor_id=args.donor_id,
            sending_app=args.sending_app,
            sending_facility=args.sending_facility,
            receiving_app=args.receiving_app,
            receiving_facility=args.receiving_facility,
            assigning_authority=args.assigning_authority,
            test_mode=args.test,
        )
    except NotImplementedError as e:
        if args.json:
            print(json.dumps({
                "status": "error",
                "backend": backend,
                "error": str(e),
            }, indent=2))
        else:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    log_entry = {
        "status": "ok",
        "backend": result["backend"],
        "din": args.din,
        "donor_id": args.donor_id,
        "control_id": result["control_id"],
        "message_type": "ADT^A04",
    }

    if args.json:
        output = json.dumps({
            **log_entry,
            "segments": result.get("segments", {}),
            "raw_message": result["message"],
        }, indent=2)
    else:
        output = result["message"]

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(
            f"Donor registered via {result['backend']} — "
            f"message written to {args.output} (control_id={result['control_id']})"
        )
    else:
        if not args.json:
            # Log backend used to stderr so raw HL7 goes cleanly to stdout
            import sys as _sys
            print(
                json.dumps(log_entry),
                file=_sys.stderr,
            )
        print(output, end="")


if __name__ == "__main__":
    main()
