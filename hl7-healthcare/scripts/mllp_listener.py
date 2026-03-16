#!/usr/bin/env python3
"""
mllp_listener.py
----------------
Listen for incoming MLLP-framed HL7 v2 messages over TCP.

Used to receive ORU^R01 result messages pushed by SoftBank (INT-05).
Responds with an ACK and logs the result as structured JSON.

MLLP frame structure:
  <VT> [HL7 message bytes] <FS><CR>

  VT = 0x0B (Vertical Tab — Start Block)
  FS = 0x1C (File Separator — End Data)
  CR = 0x0D (Carriage Return)

ACK codes:
  AA = Application Accept (success)
  AE = Application Error
  AR = Application Reject

Exit codes:
  0 = AA (message accepted)
  1 = AE or AR (message rejected/error)
  2 = Network error (timeout, connection refused, etc.)

Usage:
  # Listen for one message on default port 2575
  python mllp_listener.py --host 0.0.0.0 --port 2575

  # Listen with extended timeout and JSON output
  python mllp_listener.py --host 0.0.0.0 --port 2575 --timeout 30 --json

  # Pipe mode — receive one message and exit
  python mllp_listener.py --port 2575 --once
"""

import argparse
import datetime
import json
import socket
import sys
from datetime import timezone

# MLLP framing bytes
MLLP_START = b"\x0b"     # VT — Start Block
MLLP_END   = b"\x1c\r"  # FS + CR — End Data

FIELD_SEP = "|"
SEGMENT_TERMINATOR = "\r"


def now_iso() -> str:
    return datetime.datetime.now(timezone.utc).isoformat()


def now_hl7() -> str:
    return datetime.datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def wrap_mllp(message: str) -> bytes:
    """Wrap an HL7 message string in MLLP framing."""
    return MLLP_START + message.encode("utf-8") + MLLP_END


def unwrap_mllp(data: bytes) -> str:
    """Strip MLLP framing from received bytes."""
    if data.startswith(MLLP_START):
        data = data[1:]
    if data.endswith(b"\x1c\r"):
        data = data[:-2]
    elif data.endswith(b"\x1c"):
        data = data[:-1]
    return data.decode("utf-8", errors="replace")


def parse_message(raw: str) -> dict:
    """Parse key fields from an incoming HL7 message."""
    segments = {}
    for line in raw.replace("\r\n", "\r").replace("\n", "\r").split("\r"):
        line = line.strip()
        if line:
            seg_id = line[:3]
            segments[seg_id] = line.split(FIELD_SEP)

    result = {
        "raw": raw,
        "message_type": None,
        "control_id": None,
        "sending_app": None,
        "sending_facility": None,
    }

    if "MSH" in segments:
        msh = segments["MSH"]
        result["sending_app"]      = msh[2] if len(msh) > 2 else None
        result["sending_facility"] = msh[3] if len(msh) > 3 else None
        result["message_type"]     = msh[8] if len(msh) > 8 else None
        result["control_id"]       = msh[9] if len(msh) > 9 else None

    return result


def build_ack(control_id: str, ack_code: str = "AA", text: str = "") -> str:
    """
    Build a minimal ACK message.

    ack_code: AA (accept), AE (error), AR (reject)
    """
    fields_msh = [
        "MSH",
        "^~\\&",
        "VERITAS",     # Sending Application
        "LSU_SCL",     # Sending Facility
        "",            # Receiving Application (filled by receiver)
        "",            # Receiving Facility
        now_hl7(),     # Date/Time
        "",            # Security
        "ACK",         # Message Type
        f"ACK{control_id}",  # Control ID
        "P",           # Processing ID
        "2.5.1",       # Version
    ]
    msh = FIELD_SEP.join(fields_msh) + SEGMENT_TERMINATOR

    fields_msa = [
        "MSA",
        ack_code,
        control_id,
        text,
    ]
    msa = FIELD_SEP.join(fields_msa) + SEGMENT_TERMINATOR

    return msh + msa


def receive_mllp_message(conn: socket.socket, buffer_size: int = 4096, timeout: float = 10.0) -> bytes:
    """Read a complete MLLP-framed message from a connected socket."""
    conn.settimeout(timeout)
    data = b""
    while True:
        chunk = conn.recv(buffer_size)
        if not chunk:
            break
        data += chunk
        if b"\x1c\r" in data:
            break
    return data


def handle_connection(conn: socket.socket, addr: tuple, timeout: float, use_json: bool) -> dict:
    """
    Handle a single incoming MLLP connection.

    Returns result dict with:
      - received: bool
      - control_id: str or None
      - message_type: str or None
      - ack_code: str
      - sending_app: str or None
      - sending_facility: str or None
      - error: str or None
      - timestamp: str (ISO 8601)
    """
    result = {
        "received": False,
        "control_id": None,
        "message_type": None,
        "ack_code": None,
        "sending_app": None,
        "sending_facility": None,
        "remote_addr": f"{addr[0]}:{addr[1]}",
        "error": None,
        "timestamp": now_iso(),
    }

    try:
        raw_data = receive_mllp_message(conn, timeout=timeout)
        if not raw_data:
            result["error"] = "Empty message received"
            return result

        hl7_raw = unwrap_mllp(raw_data)
        parsed = parse_message(hl7_raw)

        result["received"]          = True
        result["control_id"]        = parsed["control_id"]
        result["message_type"]      = parsed["message_type"]
        result["sending_app"]       = parsed["sending_app"]
        result["sending_facility"]  = parsed["sending_facility"]
        result["ack_code"]          = "AA"

        # Send ACK
        control_id = parsed["control_id"] or "UNKNOWN"
        ack_msg = build_ack(control_id, ack_code="AA", text="Message accepted")
        conn.sendall(wrap_mllp(ack_msg))

        if use_json:
            print(json.dumps(result), flush=True)
        else:
            print(
                f"[{result['timestamp']}] RECEIVED {result['message_type']} "
                f"from {result['sending_app']}@{result['sending_facility']} "
                f"(ctrl={control_id}) → ACK: AA"
            )

    except socket.timeout:
        result["error"] = f"Socket timeout after {timeout}s waiting for message"
        result["ack_code"] = "AE"
        if use_json:
            print(json.dumps(result), flush=True)
        else:
            print(f"[{result['timestamp']}] TIMEOUT from {addr[0]}:{addr[1]}", file=sys.stderr)

    except Exception as e:
        result["error"] = str(e)
        result["ack_code"] = "AE"
        # Try to send AE ack if we can
        try:
            ack_msg = build_ack(result["control_id"] or "UNKNOWN", ack_code="AE", text=str(e))
            conn.sendall(wrap_mllp(ack_msg))
        except Exception:
            pass
        if use_json:
            print(json.dumps(result), flush=True)
        else:
            print(f"[{result['timestamp']}] ERROR from {addr[0]}:{addr[1]}: {e}", file=sys.stderr)

    return result


def listen_once(host: str, port: int, timeout: float, use_json: bool) -> int:
    """
    Open a TCP server, accept exactly one connection, handle it, return exit code.

    Exit codes:
      0 = AA (accepted)
      1 = AE or AR (error/rejected)
      2 = Network error
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((host, port))
            srv.listen(1)
            srv.settimeout(timeout)

            if not use_json:
                print(f"Listening on {host}:{port} (timeout={timeout}s)...", file=sys.stderr)

            try:
                conn, addr = srv.accept()
            except socket.timeout:
                msg = f"Listener timed out after {timeout}s waiting for connection"
                if use_json:
                    print(json.dumps({"error": msg, "timestamp": now_iso()}))
                else:
                    print(f"TIMEOUT: {msg}", file=sys.stderr)
                return 2

            with conn:
                result = handle_connection(conn, addr, timeout=timeout, use_json=use_json)

    except OSError as e:
        msg = f"Network error: {e}"
        if use_json:
            print(json.dumps({"error": msg, "timestamp": now_iso()}))
        else:
            print(f"ERROR: {msg}", file=sys.stderr)
        return 2

    if result.get("error") and result.get("ack_code") != "AA":
        return 2 if not result["received"] else 1
    if result.get("ack_code") in ("AE", "AR"):
        return 1
    return 0


def listen_loop(host: str, port: int, timeout: float, use_json: bool) -> int:
    """
    Open a TCP server and handle connections continuously until interrupted.
    Returns 0 on clean keyboard interrupt.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((host, port))
            srv.listen(5)
            srv.settimeout(1.0)  # Short timeout to allow KeyboardInterrupt polling

            if not use_json:
                print(f"MLLP listener started on {host}:{port} — Ctrl+C to stop", file=sys.stderr)

            while True:
                try:
                    conn, addr = srv.accept()
                    with conn:
                        handle_connection(conn, addr, timeout=timeout, use_json=use_json)
                except socket.timeout:
                    continue  # Poll for KeyboardInterrupt

    except KeyboardInterrupt:
        if not use_json:
            print("\nListener stopped.", file=sys.stderr)
        return 0
    except OSError as e:
        msg = f"Network error: {e}"
        if use_json:
            print(json.dumps({"error": msg, "timestamp": now_iso()}))
        else:
            print(f"ERROR: {msg}", file=sys.stderr)
        return 2


def main():
    parser = argparse.ArgumentParser(
        description="Listen for incoming MLLP-framed HL7 messages over TCP"
    )
    parser.add_argument("--host", default="0.0.0.0",
                        help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=2575,
                        help="TCP port to listen on (default: 2575)")
    parser.add_argument("--timeout", type=float, default=10.0,
                        help="Socket timeout in seconds (default: 10)")
    parser.add_argument("--once", action="store_true",
                        help="Accept exactly one connection then exit")
    parser.add_argument("--json", action="store_true",
                        help="Output result as JSON (one object per message)")
    args = parser.parse_args()

    if args.once:
        sys.exit(listen_once(args.host, args.port, args.timeout, args.json))
    else:
        sys.exit(listen_loop(args.host, args.port, args.timeout, args.json))


if __name__ == "__main__":
    main()
