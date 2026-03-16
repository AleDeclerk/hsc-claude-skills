#!/usr/bin/env python3
"""
mllp_sender.py
--------------
Send HL7 v2 messages over TCP using MLLP (Minimal Lower Layer Protocol) framing.

MLLP frame structure:
  <VT> [HL7 message bytes] <FS><CR>

  VT = 0x0B (Vertical Tab — Start Block)
  FS = 0x1C (File Separator — End Data)
  CR = 0x0D (Carriage Return)

Usage:
  python mllp_sender.py \\
    --host softbank.lsu.edu \\
    --port 2575 \\
    --file message.hl7

  python mllp_sender.py \\
    --host beaker.lsu.edu \\
    --port 2576 \\
    --file orders.hl7 \\
    --timeout 10 \\
    --retry 3

  # Pipe mode
  python generate_adt_a04.py --din W000055508D001 --donor-id DONOR-2026-0042 | \\
    python mllp_sender.py --host softbank.lsu.edu --port 2575 --stdin
"""

import argparse
import json
import socket
import sys
import time

# MLLP framing bytes
MLLP_START = b"\x0b"     # VT — Start Block
MLLP_END   = b"\x1c\r"  # FS + CR — End Data


def wrap_mllp(message: str) -> bytes:
    """Wrap an HL7 message string in MLLP framing."""
    msg_bytes = message.encode("utf-8")
    return MLLP_START + msg_bytes + MLLP_END


def unwrap_mllp(data: bytes) -> str:
    """Strip MLLP framing from received bytes and return raw HL7 string."""
    # Remove leading VT and trailing FS+CR if present
    if data.startswith(MLLP_START):
        data = data[1:]
    if data.endswith(b"\x1c\r"):
        data = data[:-2]
    elif data.endswith(b"\x1c"):
        data = data[:-1]
    return data.decode("utf-8", errors="replace")


def parse_ack(ack_raw: str) -> dict:
    """Parse an ACK message and return structured result."""
    segments = {}
    for line in ack_raw.replace("\r\n", "\r").replace("\n", "\r").split("\r"):
        line = line.strip()
        if line:
            seg_id = line[:3]
            segments[seg_id] = line.split("|")

    result = {
        "raw": ack_raw,
        "ack_code": None,
        "control_id": None,
        "text": None,
        "accepted": False,
    }

    if "MSA" in segments:
        msa = segments["MSA"]
        result["ack_code"] = msa[1] if len(msa) > 1 else None
        result["control_id"] = msa[2] if len(msa) > 2 else None
        result["text"] = msa[3] if len(msa) > 3 else None
        result["accepted"] = result["ack_code"] == "AA"

    return result


def send_message(
    host: str,
    port: int,
    message: str,
    timeout: float = 10.0,
    buffer_size: int = 4096,
) -> dict:
    """
    Send a single HL7 message via MLLP and return the ACK.
    
    Returns dict with:
      - sent_bytes: int
      - ack_raw: str
      - ack: dict (parsed ACK)
      - elapsed_ms: float
      - error: str or None
    """
    start = time.time()
    framed = wrap_mllp(message)

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(framed)

            # Receive ACK
            ack_data = b""
            while True:
                chunk = sock.recv(buffer_size)
                if not chunk:
                    break
                ack_data += chunk
                # Check for MLLP end marker
                if b"\x1c\r" in ack_data:
                    break

            elapsed_ms = (time.time() - start) * 1000
            ack_raw = unwrap_mllp(ack_data)
            ack = parse_ack(ack_raw)

            return {
                "sent_bytes": len(framed),
                "ack_raw": ack_raw,
                "ack": ack,
                "elapsed_ms": round(elapsed_ms, 2),
                "error": None,
            }

    except socket.timeout:
        return {
            "sent_bytes": 0,
            "ack_raw": None,
            "ack": None,
            "elapsed_ms": round((time.time() - start) * 1000, 2),
            "error": f"Connection timed out after {timeout}s",
        }
    except ConnectionRefusedError:
        return {
            "sent_bytes": 0,
            "ack_raw": None,
            "ack": None,
            "elapsed_ms": round((time.time() - start) * 1000, 2),
            "error": f"Connection refused to {host}:{port}",
        }
    except Exception as e:
        return {
            "sent_bytes": 0,
            "ack_raw": None,
            "ack": None,
            "elapsed_ms": round((time.time() - start) * 1000, 2),
            "error": str(e),
        }


def main():
    parser = argparse.ArgumentParser(description="Send HL7 message via MLLP over TCP")
    parser.add_argument("--host", required=True, help="Target host (e.g. softbank.lsu.edu)")
    parser.add_argument("--port", required=True, type=int, help="Target port (e.g. 2575)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to HL7 file to send")
    group.add_argument("--stdin", action="store_true", help="Read message from stdin")
    parser.add_argument("--timeout", type=float, default=10.0, help="Socket timeout in seconds (default: 10)")
    parser.add_argument("--retry", type=int, default=1, help="Number of attempts on network error (default: 1)")
    parser.add_argument("--retry-delay", type=float, default=2.0, help="Seconds between retries (default: 2)")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and frame the message without sending — print MLLP frame info")
    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            message = f.read()
    else:
        message = sys.stdin.read()

    message = message.strip()
    if not message:
        print("ERROR: Empty message", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        framed = wrap_mllp(message)
        info = {
            "dry_run": True,
            "host": args.host,
            "port": args.port,
            "message_length": len(message),
            "framed_length": len(framed),
            "mllp_start_byte": "0x0B",
            "mllp_end_bytes": "0x1C 0x0D",
            "first_segment": message.split("|")[0] if "|" in message else message[:20],
        }
        if args.json:
            print(json.dumps(info, indent=2))
        else:
            print(f"DRY RUN — would send {info['framed_length']} bytes to {args.host}:{args.port}")
            print(f"  Message length: {info['message_length']} bytes")
            print(f"  First segment:  {info['first_segment']}")
            print(f"  MLLP framing:   0x0B ... 0x1C 0x0D")
        return

    last_result = None
    for attempt in range(1, args.retry + 1):
        if attempt > 1:
            print(f"Retry {attempt}/{args.retry} after {args.retry_delay}s...", file=sys.stderr)
            time.sleep(args.retry_delay)

        result = send_message(
            host=args.host,
            port=args.port,
            message=message,
            timeout=args.timeout,
        )
        last_result = result

        if result["error"] is None:
            break

    if args.json:
        print(json.dumps({
            "host": args.host,
            "port": args.port,
            **last_result,
        }, indent=2))
    else:
        if last_result["error"]:
            print(f"✗ SEND FAILED: {last_result['error']}", file=sys.stderr)
            sys.exit(2)
        else:
            ack = last_result["ack"]
            code = ack["ack_code"] if ack else "?"
            status = "✓ ACCEPTED (AA)" if ack and ack["accepted"] else f"✗ REJECTED ({code})"
            print(f"{status} — {last_result['elapsed_ms']}ms — {last_result['sent_bytes']} bytes sent")
            if ack and ack["text"]:
                print(f"  ACK message: {ack['text']}")

    if last_result and last_result["ack"] and not last_result["ack"]["accepted"]:
        sys.exit(1)
    elif last_result and last_result["error"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
