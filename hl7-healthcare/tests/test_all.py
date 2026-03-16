#!/usr/bin/env python3
"""
tests/test_all.py
-----------------
Comprehensive test suite for the hl7-healthcare skill.

Run:
  python3 tests/test_all.py -v
  python3 tests/test_all.py -v TestGenerateAdtA04   # single class
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

# ── helpers ──────────────────────────────────────────────────────────────────

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
EXAMPLES = os.path.join(ROOT, "examples")

PYTHON = sys.executable

DIN    = "W000055508D001"
DONOR  = "DONOR-2026-0042"
MRN    = "MRN123456"


def run(script, args, stdin_text=None):
    """Run a script with args, return (stdout, stderr, returncode)."""
    cmd = [PYTHON, os.path.join(SCRIPTS, script)] + [str(a) for a in args]
    result = subprocess.run(
        cmd,
        input=stdin_text,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    return result.stdout, result.stderr, result.returncode


def parse_hl7(raw):
    """Split raw HL7 into segment dict: {seg_id: [line, ...]}"""
    segs = {}
    for line in raw.replace("\r\n", "\r").replace("\n", "\r").split("\r"):
        line = line.strip()
        if not line:
            continue
        sid = line[:3]
        segs.setdefault(sid, []).append(line)
    return segs


def get_field(segment, idx):
    """Get field at 1-based index from a segment string."""
    parts = segment.split("|")
    return parts[idx] if idx < len(parts) else ""


ORU_RESULTS_FULL = json.dumps([
    {"loinc": "18207-3", "name": "CD34+ count",    "value": "3.2",          "unit": "10*6/kg", "status": "F", "abnormal": False},
    {"loinc": "883-9",   "name": "ABO group",       "value": "O",            "unit": None,       "status": "F", "abnormal": False},
    {"loinc": "10331-7", "name": "Rh type",          "value": "Positive",    "unit": None,       "status": "F", "abnormal": False},
    {"loinc": "6690-2",  "name": "WBC count",        "value": "5.8",         "unit": "10*3/uL", "status": "F", "abnormal": False},
    {"loinc": "600-7",   "name": "Sterility culture","value": "Negative",    "unit": None,       "status": "F", "abnormal": False},
    {"loinc": "7917-8",  "name": "HIV-1/2 Ab",       "value": "Non-reactive","unit": None,       "status": "F", "abnormal": False},
    {"loinc": "5196-1",  "name": "HBsAg",            "value": "Non-reactive","unit": None,       "status": "F", "abnormal": False},
    {"loinc": "16128-1", "name": "HCV Ab",           "value": "Non-reactive","unit": None,       "status": "F", "abnormal": False},
])

PBSC_LOINCS = ["18207-3","883-9","10331-7","6690-2","600-7","13949-3","7917-8","5196-1","16128-1","31201-7","20507-0"]

# ── generate_adt_a04.py ───────────────────────────────────────────────────────

class TestGenerateAdtA04(unittest.TestCase):

    def _run(self, *args):
        return run("generate_adt_a04.py", list(args))

    # --- happy path ---

    def test_valid_stdout(self):
        out, err, rc = self._run("--din", DIN, "--donor-id", DONOR)
        self.assertEqual(rc, 0)
        self.assertTrue(out.startswith("MSH|"), f"stdout: {out[:60]}")

    def test_valid_segments(self):
        out, _, rc = self._run("--din", DIN, "--donor-id", DONOR)
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        for seg in ("MSH", "EVN", "PID", "PV1"):
            self.assertIn(seg, segs, f"Missing segment {seg}")

    def test_anonymous_pid(self):
        out, _, rc = self._run("--din", DIN, "--donor-id", DONOR)
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        pid = segs["PID"][0]
        self.assertIn("ANONYMOUS^DONOR", pid, "PID-5 must be ANONYMOUS^DONOR")
        self.assertIn("00010101", pid, "PID-7 must be 00010101")
        pid_fields = pid.split("|")
        self.assertEqual(pid_fields[8], "U", "PID-8 must be U (Unknown sex)")
        self.assertEqual(pid_fields[19] if len(pid_fields) > 19 else "", "", "PID-19 (SSN) must be empty")

    def test_din_in_pid3(self):
        out, _, rc = self._run("--din", DIN, "--donor-id", DONOR)
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        pid3 = get_field(segs["PID"][0], 3)
        self.assertIn(DIN, pid3)
        self.assertIn("DIN", pid3)

    def test_json_output(self):
        out, _, rc = self._run("--din", DIN, "--donor-id", DONOR, "--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        for key in ("status", "control_id", "message_type", "din", "donor_id", "segments", "raw_message"):
            self.assertIn(key, data, f"Missing key: {key}")
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["message_type"], "ADT^A04")
        self.assertEqual(data["din"], DIN)

    def test_output_file(self):
        with tempfile.NamedTemporaryFile(suffix=".hl7", delete=False) as f:
            path = f.name
        try:
            out, _, rc = self._run("--din", DIN, "--donor-id", DONOR, "--output", path)
            self.assertEqual(rc, 0)
            self.assertIn("written to", out)
            with open(path) as fh:
                content = fh.read()
            self.assertIn("MSH", content)
        finally:
            os.unlink(path)

    def test_test_mode(self):
        out, _, rc = self._run("--din", DIN, "--donor-id", DONOR, "--test")
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        msh = segs["MSH"][0]
        # MSH-11 is processing ID; at split index 11 (MSH-N is at index N-1)
        # MSH-11 (Processing ID) is at split index 10:
        # parts[0]=MSH, parts[1]=MSH-2(encoding), ..., parts[10]=MSH-11
        proc_id = get_field(msh, 10)
        self.assertEqual(proc_id, "T", f"MSH-11 should be T in test mode, got {proc_id!r}")

    def test_custom_facilities(self):
        out, _, rc = self._run("--din", DIN, "--donor-id", DONOR,
                                "--sending-app", "MYAPP",
                                "--sending-facility", "MYFAC")
        self.assertEqual(rc, 0)
        self.assertIn("MYAPP", out)
        self.assertIn("MYFAC", out)

    def test_validate_generated_message(self):
        out, _, rc = self._run("--din", DIN, "--donor-id", DONOR)
        self.assertEqual(rc, 0)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".hl7", delete=False) as f:
            f.write(out)
            path = f.name
        try:
            vout, _, vrc = run("validate_hl7.py", ["--file", path, "--check-anonymous"])
            self.assertEqual(vrc, 0, f"validate_hl7 failed: {vout}")
            self.assertIn("VALID", vout)
        finally:
            os.unlink(path)

    # --- DIN validation ---

    def test_invalid_din_short(self):
        _, _, rc = self._run("--din", "ABC123", "--donor-id", DONOR)
        self.assertEqual(rc, 1)

    def test_invalid_din_nonalpha(self):
        _, _, rc = self._run("--din", "W0000@55508D001", "--donor-id", DONOR)
        self.assertEqual(rc, 1)

    def test_invalid_din_empty(self):
        _, _, rc = self._run("--din", "", "--donor-id", DONOR)
        self.assertEqual(rc, 1)

    # --- HL7 injection ---

    def test_injection_donor_id_pipe(self):
        _, err, rc = self._run("--din", DIN, "--donor-id", "DONOR|X")
        self.assertEqual(rc, 1)
        self.assertIn("delimiter", err)

    def test_injection_donor_id_caret(self):
        _, err, rc = self._run("--din", DIN, "--donor-id", "DONOR^X")
        self.assertEqual(rc, 1)

    def test_injection_sending_app(self):
        _, err, rc = self._run("--din", DIN, "--donor-id", DONOR, "--sending-app", "APP~X")
        self.assertEqual(rc, 1)

    def test_injection_receiving_facility(self):
        _, err, rc = self._run("--din", DIN, "--donor-id", DONOR, "--receiving-facility", "FAC&X")
        self.assertEqual(rc, 1)

    def test_no_deprecation_warning(self):
        _, err, rc = self._run("--din", DIN, "--donor-id", DONOR)
        self.assertNotIn("DeprecationWarning", err)
        self.assertNotIn("utcnow", err)

# ── generate_orm_o01.py ───────────────────────────────────────────────────────

class TestGenerateOrmO01(unittest.TestCase):

    def _run(self, *args):
        return run("generate_orm_o01.py", list(args))

    # --- panel sizes ---

    def test_pbsc_panel(self):
        out, _, rc = self._run("--donor-id", DONOR, "--din", DIN,
                                "--product-type", "PBSC", "--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(len(data["orders_placed"]), 11)
        self.assertEqual(len(data["orders_skipped"]), 0)

    def test_bm_panel(self):
        out, _, rc = self._run("--donor-id", DONOR, "--din", DIN,
                                "--product-type", "BM", "--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(len(data["orders_placed"]), 12)

    def test_cb_panel(self):
        out, _, rc = self._run("--donor-id", DONOR, "--din", DIN,
                                "--product-type", "CB", "--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        # CB = PBSC(11) - WBC + Platelet = 11 tests
        self.assertEqual(len(data["orders_placed"]), 11)
        loincs = [o["loinc"] for o in data["orders_placed"]]
        self.assertNotIn("6690-2", loincs, "CB should not include WBC (6690-2)")
        self.assertIn("26515-7", loincs, "CB should include Platelet (26515-7)")

    # --- skip-tests ---

    def test_skip_tests(self):
        out, _, rc = self._run("--donor-id", DONOR, "--din", DIN,
                                "--product-type", "PBSC",
                                "--skip-tests", "883-9,10331-7", "--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(len(data["orders_placed"]), 9)
        self.assertEqual(len(data["orders_skipped"]), 2)
        skipped_loincs = [o["loinc"] for o in data["orders_skipped"]]
        self.assertIn("883-9", skipped_loincs)
        self.assertIn("10331-7", skipped_loincs)

    def test_skip_all_pbsc(self):
        out, _, rc = self._run("--donor-id", DONOR, "--din", DIN,
                                "--product-type", "PBSC",
                                "--skip-tests", ",".join(PBSC_LOINCS), "--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(len(data["orders_placed"]), 0)
        self.assertEqual(len(data["orders_skipped"]), 11)

    def test_skip_unknown_loinc_ignored(self):
        out, _, rc = self._run("--donor-id", DONOR, "--din", DIN,
                                "--product-type", "PBSC",
                                "--skip-tests", "999-99", "--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(len(data["orders_placed"]), 11, "Unknown LOINC skip should be ignored")

    # --- output modes ---

    def test_json_output(self):
        out, _, rc = self._run("--donor-id", DONOR, "--din", DIN, "--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        for key in ("status", "control_id", "message_type", "product_type", "orders_placed", "orders_skipped", "raw_message"):
            self.assertIn(key, data)
        self.assertEqual(data["message_type"], "ORM^O01")

    def test_output_file(self):
        with tempfile.NamedTemporaryFile(suffix=".hl7", delete=False) as f:
            path = f.name
        try:
            out, _, rc = self._run("--donor-id", DONOR, "--din", DIN, "--output", path)
            self.assertEqual(rc, 0)
            self.assertIn("written to", out)
            with open(path) as fh:
                content = fh.read()
            self.assertIn("ORM", content)
        finally:
            os.unlink(path)

    def test_test_mode(self):
        out, _, rc = self._run("--donor-id", DONOR, "--din", DIN, "--test")
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        msh = segs["MSH"][0]
        self.assertEqual(get_field(msh, 10), "T")

    # --- error cases ---

    def test_invalid_product_type(self):
        # argparse rejects invalid choices with exit code 2
        _, err, rc = self._run("--donor-id", DONOR, "--din", DIN, "--product-type", "INVALID")
        self.assertEqual(rc, 2)
        self.assertIn("invalid choice", err)

    def test_injection_donor_id(self):
        _, err, rc = self._run("--donor-id", "D|X", "--din", DIN)
        self.assertEqual(rc, 1)
        self.assertIn("delimiter", err)

    def test_injection_din(self):
        _, err, rc = self._run("--donor-id", DONOR, "--din", "W000^X")
        self.assertEqual(rc, 1)

    # --- correctness ---

    def test_no_deprecation_warning(self):
        _, err, rc = self._run("--donor-id", DONOR, "--din", DIN)
        self.assertNotIn("DeprecationWarning", err)

    def test_anonymous_pid_in_orm(self):
        out, _, rc = self._run("--donor-id", DONOR, "--din", DIN)
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        pid = segs["PID"][0]
        self.assertIn("ANONYMOUS^DONOR", pid)
        self.assertIn("00010101", pid)

    def test_orc_obr_pairs(self):
        out, _, rc = self._run("--donor-id", DONOR, "--din", DIN,
                                "--product-type", "PBSC")
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        self.assertEqual(len(segs.get("ORC", [])), 11)
        self.assertEqual(len(segs.get("OBR", [])), 11)

    def test_validate_generated_message(self):
        out, _, rc = self._run("--donor-id", DONOR, "--din", DIN)
        self.assertEqual(rc, 0)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".hl7", delete=False) as f:
            f.write(out)
            path = f.name
        try:
            vout, _, vrc = run("validate_hl7.py", ["--file", path])
            self.assertEqual(vrc, 0, f"validate failed: {vout}")
            self.assertIn("VALID", vout)
        finally:
            os.unlink(path)

# ── generate_oru_r01.py ───────────────────────────────────────────────────────

class TestGenerateOruR01(unittest.TestCase):

    def _run(self, *args):
        return run("generate_oru_r01.py", list(args))

    def _base_args(self):
        return ["--donor-id", DONOR, "--recipient-mrn", MRN, "--din", DIN]

    # --- happy path ---

    def test_valid_inline_results(self):
        _, _, rc = self._run(*self._base_args(), "--results", ORU_RESULTS_FULL)
        self.assertEqual(rc, 0)

    def test_valid_results_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(ORU_RESULTS_FULL)
            path = f.name
        try:
            _, _, rc = self._run(*self._base_args(), "--results-file", path)
            self.assertEqual(rc, 0)
        finally:
            os.unlink(path)

    def test_numeric_value_type(self):
        results = json.dumps([{"loinc": "18207-3", "name": "CD34+ count",
                                "value": "3.2", "unit": "10*6/kg", "status": "F"}])
        out, _, rc = self._run(*self._base_args(), "--results", results)
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        # OBX[0] is the DIN identifier OBX; OBX[1] is the first result OBX
        obx = segs["OBX"][1]
        self.assertEqual(get_field(obx, 2), "NM", "Numeric value should produce OBX-2=NM")

    def test_string_value_type(self):
        results = json.dumps([{"loinc": "883-9", "name": "ABO group",
                                "value": "O", "status": "F"}])
        out, _, rc = self._run(*self._base_args(), "--results", results)
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        # OBX[0] is the DIN identifier OBX; OBX[1] is the first result OBX
        obx = segs["OBX"][1]
        self.assertEqual(get_field(obx, 2), "ST", "Non-numeric value should produce OBX-2=ST")

    def test_obx_field_positions(self):
        """Regression test for Bug 2: OBX-11 must be status, OBX-14 must be timestamp."""
        out, _, rc = self._run(*self._base_args(), "--results", ORU_RESULTS_FULL)
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        for obx in segs["OBX"]:
            parts = obx.split("|")
            status = parts[11] if len(parts) > 11 else ""
            ts     = parts[14] if len(parts) > 14 else ""
            self.assertIn(status, ("F", "P", "C", "X", ""), f"OBX-11 should be status, got {status!r}")
            if ts:
                self.assertRegex(ts, r"^\d{14}$", f"OBX-14 should be timestamp, got {ts!r}")
            # Also verify nothing landed at wrong position
            wrong_pos = parts[9] if len(parts) > 9 else ""
            self.assertNotIn(wrong_pos, ("F", "P", "C"),
                             f"Status code should not appear at OBX-9 (got {wrong_pos!r}) — Bug 2 regression")

    def test_abnormal_flag(self):
        results = json.dumps([{"loinc": "18207-3", "name": "CD34+ count",
                                "value": "0.5", "unit": "10*6/kg", "status": "F", "abnormal": True}])
        out, _, rc = self._run(*self._base_args(), "--results", results, "--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertFalse(data["all_clear"])
        self.assertEqual(len(data["anomalies"]), 1)
        segs = parse_hl7(data["raw_message"])
        # OBX[0] is the DIN identifier OBX; OBX[1] is the first result OBX
        obx = segs["OBX"][1]
        self.assertEqual(get_field(obx, 8), "A", "Abnormal flag should be A in OBX-8")

    def test_all_clear(self):
        out, _, rc = self._run(*self._base_args(), "--results", ORU_RESULTS_FULL, "--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["all_clear"])
        self.assertEqual(data["anomalies"], [])

    def test_anomaly_warning_on_stderr(self):
        results = json.dumps([{"loinc": "18207-3", "name": "CD34+ count",
                                "value": "0.5", "unit": "10*6/kg", "status": "F", "abnormal": True}])
        _, err, rc = self._run(*self._base_args(), "--results", results)
        self.assertEqual(rc, 0)
        self.assertIn("WARNING", err)
        self.assertIn("anomalous", err)

    def test_multiple_results_count(self):
        out, _, rc = self._run(*self._base_args(), "--results", ORU_RESULTS_FULL)
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        # 8 result OBXs + 1 DIN identifier OBX = 9 total
        self.assertEqual(len(segs.get("OBX", [])), 9)

    def test_json_output(self):
        out, _, rc = self._run(*self._base_args(), "--results", ORU_RESULTS_FULL, "--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        for key in ("status", "control_id", "message_type", "donor_id", "recipient_mrn",
                    "din", "results_count", "all_clear", "anomalies", "raw_message"):
            self.assertIn(key, data)
        self.assertEqual(data["message_type"], "ORU^R01")
        self.assertEqual(data["results_count"], 8)

    def test_output_file(self):
        with tempfile.NamedTemporaryFile(suffix=".hl7", delete=False) as f:
            path = f.name
        try:
            out, _, rc = self._run(*self._base_args(), "--results", ORU_RESULTS_FULL, "--output", path)
            self.assertEqual(rc, 0)
            self.assertIn("written to", out)
            with open(path) as fh:
                content = fh.read()
            self.assertIn("ORU", content)
        finally:
            os.unlink(path)

    def test_test_mode(self):
        out, _, rc = self._run(*self._base_args(), "--results", ORU_RESULTS_FULL, "--test")
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        self.assertEqual(get_field(segs["MSH"][0], 10), "T")

    def test_mrn_in_pid(self):
        out, _, rc = self._run(*self._base_args(), "--results", ORU_RESULTS_FULL)
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        self.assertIn(MRN, segs["PID"][0])

    # --- error cases ---

    def test_no_results_arg(self):
        _, err, rc = self._run(*self._base_args())
        self.assertEqual(rc, 1)
        self.assertIn("--results", err)

    def test_injection_recipient_mrn(self):
        _, err, rc = self._run("--donor-id", DONOR, "--recipient-mrn", "MRN|X",
                                "--din", DIN, "--results", ORU_RESULTS_FULL)
        self.assertEqual(rc, 1)
        self.assertIn("delimiter", err)

    def test_injection_donor_id(self):
        _, err, rc = self._run("--donor-id", "D^X", "--recipient-mrn", MRN,
                                "--din", DIN, "--results", ORU_RESULTS_FULL)
        self.assertEqual(rc, 1)

    def test_no_deprecation_warning(self):
        _, err, rc = self._run(*self._base_args(), "--results", ORU_RESULTS_FULL)
        self.assertNotIn("DeprecationWarning", err)

    def test_validate_generated_message(self):
        out, _, rc = self._run(*self._base_args(), "--results", ORU_RESULTS_FULL)
        self.assertEqual(rc, 0)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".hl7", delete=False) as f:
            f.write(out)
            path = f.name
        try:
            vout, _, vrc = run("validate_hl7.py", ["--file", path])
            self.assertEqual(vrc, 0, f"validate failed: {vout}")
            self.assertIn("VALID", vout)
            self.assertNotIn("WARNING", vout)
        finally:
            os.unlink(path)

# ── validate_hl7.py ───────────────────────────────────────────────────────────

class TestValidateHl7(unittest.TestCase):

    def _run(self, *args):
        return run("validate_hl7.py", list(args))

    def _write_hl7(self, content):
        """Write an HL7 string to a temp file, return path."""
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".hl7", delete=False)
        f.write(content)
        f.close()
        return f.name

    # --- example files ---

    def test_valid_adt_example(self):
        out, _, rc = self._run("--file", os.path.join(EXAMPLES, "anonymous_donor_registration.hl7"))
        self.assertEqual(rc, 0)
        self.assertIn("VALID", out)

    def test_valid_orm_example(self):
        out, _, rc = self._run("--file", os.path.join(EXAMPLES, "lab_order_panel_pbsc.hl7"))
        self.assertEqual(rc, 0)
        self.assertIn("VALID", out)

    def test_valid_oru_example_no_warnings(self):
        out, _, rc = self._run("--file", os.path.join(EXAMPLES, "results_routing_to_epic.hl7"))
        self.assertEqual(rc, 0)
        self.assertIn("VALID", out)
        self.assertNotIn("WARNING", out)

    def test_check_anonymous_pass(self):
        out, _, rc = self._run("--file", os.path.join(EXAMPLES, "anonymous_donor_registration.hl7"),
                                "--check-anonymous")
        self.assertEqual(rc, 0)

    # --- anonymous donor violations ---

    def test_check_anonymous_wrong_name(self):
        msg = ("MSH|^~\\&|VERITAS|LSU_SCL|SOFTBANK|LSU|20260311120000||ADT^A04|MSG001|P|2.5.1\r"
               "EVN|A04|20260311120000||||20260311120000\r"
               "PID|1||W000055508D001^^^LSU_SCL^DIN||JOHN^DOE^^^^^L||00010101|U\r"
               "PV1|1|O\r")
        path = self._write_hl7(msg)
        try:
            out, _, rc = self._run("--file", path, "--check-anonymous")
            self.assertEqual(rc, 1)
            self.assertIn("VIOLATION", out)
        finally:
            os.unlink(path)

    def test_check_anonymous_real_dob(self):
        msg = ("MSH|^~\\&|VERITAS|LSU_SCL|SOFTBANK|LSU|20260311120000||ADT^A04|MSG002|P|2.5.1\r"
               "EVN|A04|20260311120000||||20260311120000\r"
               "PID|1||W000055508D001^^^LSU_SCL^DIN||ANONYMOUS^DONOR^^^^^L||19900115|U\r"
               "PV1|1|O\r")
        path = self._write_hl7(msg)
        try:
            out, _, rc = self._run("--file", path, "--check-anonymous")
            self.assertEqual(rc, 1)
            self.assertIn("VIOLATION", out)
            self.assertIn("DOB", out)
        finally:
            os.unlink(path)

    def test_check_anonymous_ssn_populated(self):
        pid_fields = ["PID","1","","W000055508D001^^^LSU_SCL^DIN","",
                      "ANONYMOUS^DONOR^^^^^L","","00010101","U","","","","","","","","","","","123-45-6789"]
        pid_line = "|".join(pid_fields)
        msg = ("MSH|^~\\&|VERITAS|LSU_SCL|SOFTBANK|LSU|20260311120000||ADT^A04|MSG003|P|2.5.1\r"
               "EVN|A04|20260311120000||||20260311120000\r"
               f"{pid_line}\r"
               "PV1|1|O\r")
        path = self._write_hl7(msg)
        try:
            out, _, rc = self._run("--file", path, "--check-anonymous")
            self.assertEqual(rc, 1)
            self.assertIn("SSN", out)
        finally:
            os.unlink(path)

    # --- structural errors ---

    def test_missing_msh(self):
        path = self._write_hl7("EVN|A04|20260311120000\rPID|1||W001\r")
        try:
            out, _, rc = self._run("--file", path)
            self.assertEqual(rc, 1)
            self.assertIn("MSH", out)
        finally:
            os.unlink(path)

    def test_empty_message(self):
        path = self._write_hl7("")
        try:
            _, _, rc = self._run("--file", path)
            self.assertEqual(rc, 1)
        finally:
            os.unlink(path)

    def test_missing_required_segment_adt(self):
        msg = ("MSH|^~\\&|VERITAS|LSU_SCL|SOFTBANK|LSU|20260311120000||ADT^A04|MSG004|P|2.5.1\r"
               "EVN|A04|20260311120000\r"
               "PV1|1|O\r")
        path = self._write_hl7(msg)
        try:
            out, _, rc = self._run("--file", path)
            self.assertEqual(rc, 1)
            self.assertIn("PID", out)
        finally:
            os.unlink(path)

    def test_missing_required_segment_oru(self):
        msg = ("MSH|^~\\&|VERITAS|LSU_SCL|EPIC|LSU|20260311120000||ORU^R01|ORU001|P|2.5.1\r"
               "PID|1||MRN123456^^^LSU^MRN\r"
               "OBR|1||RES001|99DONOR^Test^L\r")
        path = self._write_hl7(msg)
        try:
            out, _, rc = self._run("--file", path)
            self.assertEqual(rc, 1)
            self.assertIn("OBX", out)
        finally:
            os.unlink(path)

    def test_pid3_empty(self):
        msg = ("MSH|^~\\&|VERITAS|LSU_SCL|SOFTBANK|LSU|20260311120000||ADT^A04|MSG005|P|2.5.1\r"
               "EVN|A04|20260311120000\r"
               "PID|1||||ANONYMOUS^DONOR^^^^^L||00010101|U\r"
               "PV1|1|O\r")
        path = self._write_hl7(msg)
        try:
            out, _, rc = self._run("--file", path)
            self.assertEqual(rc, 1)
            self.assertIn("PID-3", out)
        finally:
            os.unlink(path)

    def test_control_id_empty(self):
        msg = "MSH|^~\\&|VERITAS|LSU_SCL|SOFTBANK|LSU|20260311120000||ADT^A04||P|2.5.1\r"
        path = self._write_hl7(msg)
        try:
            out, _, rc = self._run("--file", path)
            self.assertEqual(rc, 1)
            self.assertIn("Control ID", out)
        finally:
            os.unlink(path)

    # --- ACK parsing ---

    def test_ack_aa(self):
        msg = ("MSH|^~\\&|SOFTBANK|LSU|VERITAS|LSU_SCL|20260311120001||ACK|ACK001|P|2.5.1\r"
               "MSA|AA|MSG00123456|Message accepted\r")
        path = self._write_hl7(msg)
        try:
            out, _, rc = self._run("--file", path, "--parse-ack")
            self.assertEqual(rc, 0)
            self.assertIn("AA", out)
        finally:
            os.unlink(path)

    def test_ack_ae(self):
        msg = ("MSH|^~\\&|SOFTBANK|LSU|VERITAS|LSU_SCL|20260311120001||ACK|ACK002|P|2.5.1\r"
               "MSA|AE|MSG00123456|Duplicate message\r")
        path = self._write_hl7(msg)
        try:
            out, _, rc = self._run("--file", path, "--parse-ack")
            self.assertEqual(rc, 1)
            self.assertIn("AE", out)
        finally:
            os.unlink(path)

    def test_ack_ar(self):
        msg = ("MSH|^~\\&|SOFTBANK|LSU|VERITAS|LSU_SCL|20260311120001||ACK|ACK003|P|2.5.1\r"
               "MSA|AR|MSG00123456|Rejected\r")
        path = self._write_hl7(msg)
        try:
            out, _, rc = self._run("--file", path, "--parse-ack")
            self.assertEqual(rc, 1)
            self.assertIn("AR", out)
        finally:
            os.unlink(path)

    # --- MLLP framing ---

    def test_mllp_framing_stripped(self):
        raw = ("MSH|^~\\&|VERITAS|LSU_SCL|SOFTBANK|LSU|20260311120000||ADT^A04|MSG006|P|2.5.1\r"
               "EVN|A04|20260311120000||||20260311120000\r"
               "PID|1||W000055508D001^^^LSU_SCL^DIN||ANONYMOUS^DONOR^^^^^L||00010101|U\r"
               "PV1|1|O\r")
        wrapped = "\x0b" + raw + "\x1c\r"
        path = self._write_hl7(wrapped)
        try:
            out, _, rc = self._run("--file", path)
            self.assertEqual(rc, 0)
            self.assertIn("VALID", out)
        finally:
            os.unlink(path)

    # --- JSON output ---

    def test_json_output_valid(self):
        out, _, rc = self._run("--file", os.path.join(EXAMPLES, "anonymous_donor_registration.hl7"),
                                "--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["valid"])
        for key in ("valid", "message_type", "control_id", "segments_found", "errors", "warnings"):
            self.assertIn(key, data)

    def test_json_output_invalid(self):
        path = self._write_hl7("NOT|A|VALID|HL7|MESSAGE\r")
        try:
            out, _, rc = self._run("--file", path, "--json")
            data = json.loads(out)
            self.assertFalse(data["valid"])
            self.assertGreater(len(data["errors"]), 0)
        finally:
            os.unlink(path)

    # --- stdin mode ---

    def test_stdin_mode(self):
        with open(os.path.join(EXAMPLES, "anonymous_donor_registration.hl7")) as f:
            content = f.read()
        out, _, rc = run("validate_hl7.py", ["--stdin"], stdin_text=content)
        self.assertEqual(rc, 0)
        self.assertIn("VALID", out)

    # --- warnings ---

    def test_obx_empty_value_warning(self):
        msg = ("MSH|^~\\&|VERITAS|LSU_SCL|EPIC|LSU|20260311120000||ORU^R01|ORU002|P|2.5.1\r"
               "PID|1||MRN123456^^^LSU^MRN\r"
               "OBR|1||RES001|99DONOR^Test^L\r"
               "OBX|1|ST|18207-3^CD34+ count^LN||||||||F\r")
        path = self._write_hl7(msg)
        try:
            out, _, rc = self._run("--file", path)
            self.assertEqual(rc, 0)
            self.assertIn("WARNING", out)
            self.assertIn("OBX", out)
        finally:
            os.unlink(path)

    def test_unknown_message_type_warning(self):
        msg = ("MSH|^~\\&|VERITAS|LSU_SCL|DEST|LSU|20260311120000||FOO^BAR|MSG007|P|2.5.1\r"
               "PID|1||W000055508D001\r")
        path = self._write_hl7(msg)
        try:
            out, _, rc = self._run("--file", path)
            self.assertEqual(rc, 0)
            self.assertIn("WARNING", out)
        finally:
            os.unlink(path)

    def test_version_warning(self):
        msg = ("MSH|^~\\&|VERITAS|LSU_SCL|DEST|LSU|20260311120000||ADT^A04|MSG008|P|3.0\r"
               "EVN|A04|20260311120000\r"
               "PID|1||W000055508D001^^^LSU_SCL^DIN||ANONYMOUS^DONOR^^^^^L||00010101|U\r"
               "PV1|1|O\r")
        path = self._write_hl7(msg)
        try:
            out, _, rc = self._run("--file", path)
            self.assertIn("WARNING", out)
        finally:
            os.unlink(path)

# ── parse_hl7.py ──────────────────────────────────────────────────────────────

class TestParseHl7(unittest.TestCase):

    def _run(self, *args):
        return run("parse_hl7.py", list(args))

    ADT_PATH = os.path.join(EXAMPLES, "anonymous_donor_registration.hl7")
    ORU_PATH = os.path.join(EXAMPLES, "results_routing_to_epic.hl7")

    # --- all segments ---

    def test_all_segments(self):
        out, _, rc = self._run("--file", self.ADT_PATH, "--all")
        self.assertEqual(rc, 0)
        for seg in ("MSH", "EVN", "PID", "PV1"):
            self.assertIn(seg, out)

    # --- MSH field labels (Bug 3 regression) ---

    def test_msh_field_labels(self):
        out, _, rc = self._run("--file", self.ADT_PATH, "--segment", "MSH")
        self.assertEqual(rc, 0)
        # MSH fields should be labeled starting at 2, not 1
        self.assertIn("Encoding Characters", out, "MSH-2 label missing")
        self.assertIn("Sending Application", out, "MSH-3 label missing")

    def test_msh_field_numbers_start_at_2(self):
        out, _, rc = self._run("--file", self.ADT_PATH, "--segment", "MSH")
        self.assertEqual(rc, 0)
        self.assertIn("[02]", out, "First displayed MSH field should be [02]")
        self.assertNotIn("[01] Field Separator", out, "MSH-1 (|) should not appear — Bug 3 regression")

    def test_msh_field_09_is_message_type(self):
        out, _, rc = self._run("--file", self.ADT_PATH, "--segment", "MSH")
        self.assertEqual(rc, 0)
        self.assertIn("Message Type", out)
        self.assertIn("ADT^A04", out)

    # --- specific segment filters ---

    def test_segment_pid(self):
        out, _, rc = self._run("--file", self.ADT_PATH, "--segment", "PID")
        self.assertEqual(rc, 0)
        self.assertIn("PID", out)
        self.assertIn("ANONYMOUS^DONOR", out)
        self.assertNotIn("MSH", out)

    def test_segment_obx_multiple(self):
        out, _, rc = self._run("--file", self.ORU_PATH, "--segment", "OBX")
        self.assertEqual(rc, 0)
        self.assertEqual(out.count("┌── OBX"), 8, "Should show all 8 OBX segments")

    def test_segment_not_found(self):
        _, err, rc = self._run("--file", self.ADT_PATH, "--segment", "ZZZ")
        self.assertEqual(rc, 1)
        self.assertIn("ZZZ", err)

    # --- JSON output ---

    def test_json_output_valid(self):
        out, _, rc = self._run("--file", self.ADT_PATH, "--all", "--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        self.assertIn("segment", data[0])
        self.assertIn("fields", data[0])

    def test_json_msh_field_keys_start_at_2(self):
        out, _, rc = self._run("--file", self.ADT_PATH, "--segment", "MSH", "--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        msh_data = data[0]
        field_keys = list(msh_data["fields"].keys())
        nums = [int(k.split(":")[0]) for k in field_keys]
        self.assertGreaterEqual(min(nums), 2, "MSH field numbers should start at 2, not 1")
        self.assertNotIn("1:Field Separator", msh_data["fields"], "Bug 3 regression: no Field Separator key")

    # --- stdin mode ---

    def test_stdin_mode(self):
        with open(self.ADT_PATH) as f:
            content = f.read()
        out, _, rc = run("parse_hl7.py", ["--stdin", "--segment", "MSH"], stdin_text=content)
        self.assertEqual(rc, 0)
        self.assertIn("MSH", out)

    # --- error cases ---

    def test_no_mode_flag(self):
        _, err, rc = self._run("--file", self.ADT_PATH)
        self.assertEqual(rc, 1)
        self.assertIn("--segment", err)

    # --- SSN warning flag ---

    def test_ssn_warning_flag(self):
        pid_fields = ["PID","1","","W000055508D001^^^LSU_SCL^DIN","",
                      "ANONYMOUS^DONOR^^^^^L","","00010101","U","","","","","","","","","","","123-45-6789"]
        pid_line = "|".join(pid_fields)
        msg = ("MSH|^~\\&|VERITAS|LSU_SCL|SOFTBANK|LSU|20260311120000||ADT^A04|MSG009|P|2.5.1\r"
               "EVN|A04|20260311120000||||20260311120000\r"
               f"{pid_line}\r"
               "PV1|1|O\r")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".hl7", delete=False) as f:
            f.write(msg)
            path = f.name
        try:
            out, _, rc = self._run("--file", path, "--segment", "PID")
            self.assertEqual(rc, 0)
            self.assertIn("⚠", out, "SSN field should show ⚠ warning symbol")
        finally:
            os.unlink(path)

# ── mllp_sender.py ────────────────────────────────────────────────────────────

class TestMllpSender(unittest.TestCase):

    def _run(self, *args):
        return run("mllp_sender.py", list(args))

    ADT_PATH = os.path.join(EXAMPLES, "anonymous_donor_registration.hl7")

    # --- dry-run (no network needed) ---

    def test_dry_run(self):
        out, _, rc = self._run("--host", "localhost", "--port", "2575",
                                "--file", self.ADT_PATH, "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("DRY RUN", out)

    def test_dry_run_json(self):
        out, _, rc = self._run("--host", "localhost", "--port", "2575",
                                "--file", self.ADT_PATH, "--dry-run", "--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        for key in ("dry_run", "host", "port", "message_length", "framed_length",
                    "mllp_start_byte", "mllp_end_bytes", "first_segment"):
            self.assertIn(key, data)
        self.assertTrue(data["dry_run"])
        self.assertEqual(data["mllp_start_byte"], "0x0B")
        self.assertEqual(data["mllp_end_bytes"], "0x1C 0x0D")

    def test_dry_run_framing_adds_3_bytes(self):
        out, _, rc = self._run("--host", "localhost", "--port", "2575",
                                "--file", self.ADT_PATH, "--dry-run", "--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["framed_length"], data["message_length"] + 3,
                         "MLLP framing should add exactly 3 bytes (0x0B + 0x1C + 0x0D)")

    def test_dry_run_stdin(self):
        with open(self.ADT_PATH) as f:
            content = f.read()
        out, _, rc = run("mllp_sender.py",
                          ["--host", "localhost", "--port", "2575", "--stdin", "--dry-run"],
                          stdin_text=content)
        self.assertEqual(rc, 0)
        self.assertIn("DRY RUN", out)

    # --- network errors ---

    def test_connection_refused(self):
        _, err, rc = self._run("--host", "localhost", "--port", "19999",
                                "--file", self.ADT_PATH)
        self.assertEqual(rc, 2)
        self.assertIn("refused", err.lower() + run("mllp_sender.py",
            ["--host", "localhost", "--port", "19999",
             "--file", self.ADT_PATH, "--json"])[0].lower())

    def test_empty_message_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".hl7", delete=False) as f:
            path = f.name
        try:
            _, err, rc = self._run("--host", "localhost", "--port", "2575", "--file", path)
            self.assertEqual(rc, 1)
            self.assertIn("Empty message", err)
        finally:
            os.unlink(path)

    # --- unit tests for framing functions (imported directly) ---

    def test_wrap_mllp(self):
        sys.path.insert(0, SCRIPTS)
        from mllp_sender import wrap_mllp
        framed = wrap_mllp("MSH|^~\\&|TEST\r")
        self.assertEqual(framed[0:1], b"\x0b")
        self.assertEqual(framed[-2:], b"\x1c\r")
        self.assertIn(b"MSH", framed)

    def test_unwrap_mllp(self):
        sys.path.insert(0, SCRIPTS)
        from mllp_sender import wrap_mllp, unwrap_mllp
        original = "MSH|^~\\&|TEST\r"
        self.assertEqual(unwrap_mllp(wrap_mllp(original)), original)

    def test_parse_ack_aa(self):
        sys.path.insert(0, SCRIPTS)
        from mllp_sender import parse_ack
        ack_raw = "MSH|^~\\&|SB|LSU|VER|LSU|20260311||ACK|ACK001|P|2.5.1\rMSA|AA|MSG001|Accepted\r"
        result = parse_ack(ack_raw)
        self.assertEqual(result["ack_code"], "AA")
        self.assertTrue(result["accepted"])

    def test_parse_ack_ae(self):
        sys.path.insert(0, SCRIPTS)
        from mllp_sender import parse_ack
        ack_raw = "MSH|^~\\&|SB|LSU|VER|LSU|20260311||ACK|ACK002|P|2.5.1\rMSA|AE|MSG001|Error\r"
        result = parse_ack(ack_raw)
        self.assertEqual(result["ack_code"], "AE")
        self.assertFalse(result["accepted"])

    def test_parse_ack_ar(self):
        sys.path.insert(0, SCRIPTS)
        from mllp_sender import parse_ack
        ack_raw = "MSH|^~\\&|SB|LSU|VER|LSU|20260311||ACK|ACK003|P|2.5.1\rMSA|AR|MSG001|Rejected\r"
        result = parse_ack(ack_raw)
        self.assertEqual(result["ack_code"], "AR")
        self.assertFalse(result["accepted"])


# ── mllp_listener.py ─────────────────────────────────────────────────────────

class TestMllpListener(unittest.TestCase):
    """Unit tests for mllp_listener.py (imported functions — no network required)."""

    def setUp(self):
        sys.path.insert(0, SCRIPTS)
        import mllp_listener as _ml
        self._ml = _ml

    def test_wrap_unwrap_roundtrip(self):
        msg = "MSH|^~\\&|VERITAS|LSU_SCL|EPIC|LSU|20260313120000||ORU^R01|ORU001|P|2.5.1\r"
        framed = self._ml.wrap_mllp(msg)
        self.assertEqual(framed[0:1], b"\x0b", "MLLP frame must start with VT (0x0B)")
        self.assertEqual(framed[-2:], b"\x1c\r", "MLLP frame must end with FS+CR (0x1C 0x0D)")
        self.assertEqual(self._ml.unwrap_mllp(framed), msg)

    def test_unwrap_strips_vt_only(self):
        """unwrap_mllp should handle missing FS+CR gracefully."""
        msg = "MSH|^~\\&|TEST\r"
        data = b"\x0b" + msg.encode()
        self.assertEqual(self._ml.unwrap_mllp(data), msg)

    def test_parse_message_extracts_msh_fields(self):
        raw = ("MSH|^~\\&|SOFTBANK|LSU|VERITAS|LSU_SCL|20260313120000||ORU^R01|ORU999|P|2.5.1\r"
               "PID|1||W000055508D001^^^LSU_SCL^DIN\r")
        result = self._ml.parse_message(raw)
        self.assertEqual(result["sending_app"], "SOFTBANK")
        self.assertEqual(result["sending_facility"], "LSU")
        self.assertEqual(result["message_type"], "ORU^R01")
        self.assertEqual(result["control_id"], "ORU999")

    def test_parse_message_empty(self):
        result = self._ml.parse_message("")
        self.assertIsNone(result["control_id"])
        self.assertIsNone(result["message_type"])

    def test_build_ack_aa(self):
        ack = self._ml.build_ack("CTRL123", ack_code="AA", text="Accepted")
        self.assertIn("MSH", ack)
        self.assertIn("MSA", ack)
        self.assertIn("|AA|", ack)
        self.assertIn("CTRL123", ack)

    def test_build_ack_ae(self):
        ack = self._ml.build_ack("CTRL456", ack_code="AE", text="Error")
        self.assertIn("|AE|", ack)

    def test_build_ack_ar(self):
        ack = self._ml.build_ack("CTRL789", ack_code="AR")
        self.assertIn("|AR|", ack)

    def test_build_ack_is_valid_hl7(self):
        """ACK message built by listener should parse cleanly."""
        ack = self._ml.build_ack("MSG001", ack_code="AA", text="OK")
        parts = ack.split("\r")
        # Should have MSH and MSA segments
        self.assertTrue(any(p.startswith("MSH") for p in parts))
        self.assertTrue(any(p.startswith("MSA") for p in parts))

    def test_now_iso_format(self):
        ts = self._ml.now_iso()
        self.assertIn("T", ts, "ISO 8601 timestamp should contain 'T'")
        self.assertIn("+", ts + "Z", "ISO 8601 timestamp should have timezone")

    def test_now_hl7_format(self):
        ts = self._ml.now_hl7()
        self.assertRegex(ts, r"^\d{14}$", "HL7 timestamp must be 14 digits YYYYMMDDHHMMSS")


# ── donor_registration.py ─────────────────────────────────────────────────────

class TestDonorRegistration(unittest.TestCase):

    def _run(self, *args, env_overrides=None):
        cmd = [sys.executable, os.path.join(SCRIPTS, "donor_registration.py")] + [str(a) for a in args]
        env = os.environ.copy()
        if env_overrides:
            env.update(env_overrides)
        # Remove DONOR_BACKEND from env unless explicitly set in overrides
        if env_overrides is None or "DONOR_BACKEND" not in env_overrides:
            env.pop("DONOR_BACKEND", None)
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, env=env)
        return result.stdout, result.stderr, result.returncode

    def _base_args(self, backend="softbank"):
        return ["--backend", backend, "--din", DIN, "--donor-id", DONOR]

    # --- softbank backend ---

    def test_softbank_generates_adt_a04(self):
        out, _, rc = self._run(*self._base_args("softbank"))
        self.assertEqual(rc, 0)
        self.assertIn("ADT^A04", out)
        self.assertIn("MSH", out)

    def test_softbank_contains_din(self):
        out, _, rc = self._run(*self._base_args("softbank"))
        self.assertEqual(rc, 0)
        self.assertIn(DIN, out)

    def test_softbank_anonymous_pid(self):
        out, _, rc = self._run(*self._base_args("softbank"))
        self.assertEqual(rc, 0)
        self.assertIn("ANONYMOUS^DONOR", out)

    def test_softbank_json_output(self):
        out, _, rc = self._run(*self._base_args("softbank"), "--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["backend"], "softbank")
        self.assertIn("control_id", data)
        self.assertIn("raw_message", data)

    def test_backend_from_env_var(self):
        out, _, rc = self._run("--din", DIN, "--donor-id", DONOR,
                                env_overrides={"DONOR_BACKEND": "softbank"})
        self.assertEqual(rc, 0)
        self.assertIn("ADT^A04", out)

    def test_backend_arg_overrides_env(self):
        """--backend argument takes precedence over DONOR_BACKEND env var."""
        out, err, rc = self._run("--backend", "softbank", "--din", DIN, "--donor-id", DONOR,
                                  env_overrides={"DONOR_BACKEND": "softbank"})
        self.assertEqual(rc, 0)
        self.assertIn("ADT^A04", out)

    def test_output_file(self):
        with tempfile.NamedTemporaryFile(suffix=".hl7", delete=False) as f:
            path = f.name
        try:
            out, _, rc = self._run(*self._base_args("softbank"), "--output", path)
            self.assertEqual(rc, 0)
            self.assertIn("softbank", out)
            with open(path) as fh:
                content = fh.read()
            self.assertIn("ADT^A04", content)
        finally:
            os.unlink(path)

    # --- softdonor backend (Phase 2 stub) ---

    def test_softdonor_raises_not_implemented(self):
        _, err, rc = self._run(*self._base_args("softdonor"))
        self.assertEqual(rc, 1)
        self.assertIn("SoftDonor API spec pending", err)

    def test_softdonor_json_error(self):
        out, _, rc = self._run(*self._base_args("softdonor"), "--json")
        self.assertEqual(rc, 1)
        data = json.loads(out)
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["backend"], "softdonor")
        self.assertIn("SoftDonor", data["error"])

    def test_softdonor_exact_error_message(self):
        _, err, rc = self._run(*self._base_args("softdonor"))
        self.assertEqual(rc, 1)
        self.assertIn(
            "Set DONOR_BACKEND=softbank until Phase 2",
            err,
            "Error message must include the exact Phase 2 instruction",
        )

    # --- validation ---

    def test_invalid_din_rejected(self):
        _, err, rc = self._run("--backend", "softbank", "--din", "INVALID!", "--donor-id", DONOR)
        self.assertEqual(rc, 1)
        self.assertIn("DIN", err)

    def test_hl7_delimiter_in_donor_id_rejected(self):
        _, err, rc = self._run("--backend", "softbank", "--din", DIN, "--donor-id", "D^ONOR")
        self.assertEqual(rc, 1)
        self.assertIn("delimiter", err)

    # --- library function tests ---

    def test_register_donor_softbank_returns_backend_key(self):
        sys.path.insert(0, SCRIPTS)
        from donor_registration import register_donor
        result = register_donor(backend="softbank", din=DIN, donor_id=DONOR)
        self.assertEqual(result["backend"], "softbank")
        self.assertIn("message", result)
        self.assertIn("control_id", result)

    def test_register_donor_softdonor_raises(self):
        sys.path.insert(0, SCRIPTS)
        from donor_registration import register_donor, SOFTDONOR_NOT_IMPLEMENTED_MSG
        with self.assertRaises(NotImplementedError) as ctx:
            register_donor(backend="softdonor", din=DIN, donor_id=DONOR)
        self.assertEqual(str(ctx.exception), SOFTDONOR_NOT_IMPLEMENTED_MSG)

    def test_register_donor_invalid_backend_raises_value_error(self):
        sys.path.insert(0, SCRIPTS)
        from donor_registration import register_donor
        with self.assertRaises(ValueError):
            register_donor(backend="unknown_backend", din=DIN, donor_id=DONOR)

    def test_resolve_backend_arg_wins(self):
        sys.path.insert(0, SCRIPTS)
        from donor_registration import resolve_backend
        self.assertEqual(resolve_backend("softdonor"), "softdonor")

    def test_resolve_backend_defaults_to_softbank(self):
        sys.path.insert(0, SCRIPTS)
        from donor_registration import resolve_backend
        # No arg, no env var — ensure DONOR_BACKEND is not set
        old = os.environ.pop("DONOR_BACKEND", None)
        try:
            self.assertEqual(resolve_backend(None), "softbank")
        finally:
            if old is not None:
                os.environ["DONOR_BACKEND"] = old


# ── generate_oru_r01.py — DIN OBX / NTE tests ───────────────────────────────

class TestOruR01DinObx(unittest.TestCase):
    """Tests for the Epic/WellSky custom DIN OBX and NTE fields (GAP 2)."""

    def _run(self, *args):
        return run("generate_oru_r01.py", list(args))

    def _base_args(self):
        return ["--donor-id", DONOR, "--recipient-mrn", MRN, "--din", DIN]

    def _single_result(self):
        return json.dumps([{"loinc": "18207-3", "name": "CD34+ count",
                            "value": "3.2", "unit": "10*6/kg", "status": "F"}])

    def test_first_obx_is_din_identifier(self):
        out, _, rc = self._run(*self._base_args(), "--results", self._single_result())
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        din_obx = segs["OBX"][0]
        self.assertIn("DIN^Donor Product Identifier^L", din_obx,
                      "First OBX must contain DIN^Donor Product Identifier^L in OBX-3")

    def test_din_obx_value_is_din(self):
        out, _, rc = self._run(*self._base_args(), "--results", self._single_result())
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        din_obx = segs["OBX"][0]
        self.assertIn(DIN, din_obx, "OBX-5 of DIN OBX must contain the DIN value")

    def test_din_obx_value_type_is_st(self):
        out, _, rc = self._run(*self._base_args(), "--results", self._single_result())
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        din_obx = segs["OBX"][0]
        self.assertEqual(get_field(din_obx, 2), "ST", "DIN OBX-2 Value Type must be ST")

    def test_din_obx_status_is_final(self):
        out, _, rc = self._run(*self._base_args(), "--results", self._single_result())
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        din_obx = segs["OBX"][0]
        self.assertEqual(get_field(din_obx, 11), "F", "DIN OBX-11 Result Status must be F (Final)")

    def test_nte_segment_present(self):
        out, _, rc = self._run(*self._base_args(), "--results", self._single_result())
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        self.assertIn("NTE", segs, "NTE segment must be present after DIN OBX")

    def test_nte_contains_din(self):
        out, _, rc = self._run(*self._base_args(), "--results", self._single_result())
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        nte = segs["NTE"][0]
        self.assertIn(DIN, nte, "NTE-3 must contain the DIN value")

    def test_nte_report_header_format(self):
        out, _, rc = self._run(*self._base_args(), "--results", self._single_result())
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        nte = segs["NTE"][0]
        self.assertIn("Donor Product", nte, "NTE must include 'Donor Product' in report header")

    def test_result_obx_set_id_starts_at_2(self):
        out, _, rc = self._run(*self._base_args(), "--results", self._single_result())
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        result_obx = segs["OBX"][1]
        self.assertEqual(get_field(result_obx, 1), "2",
                         "First result OBX Set ID must be 2 (1 is DIN OBX)")

    def test_din_obx_always_first(self):
        results = json.dumps([
            {"loinc": "18207-3", "name": "CD34+", "value": "3.2", "unit": "10*6/kg", "status": "F"},
            {"loinc": "883-9",   "name": "ABO",   "value": "O",   "status": "F"},
        ])
        out, _, rc = self._run(*self._base_args(), "--results", results)
        self.assertEqual(rc, 0)
        segs = parse_hl7(out)
        # First OBX is DIN, next two are results
        self.assertEqual(len(segs["OBX"]), 3)
        self.assertIn("DIN^Donor Product Identifier^L", segs["OBX"][0])

    def test_results_count_excludes_din_obx(self):
        results = json.dumps([
            {"loinc": "18207-3", "name": "CD34+", "value": "3.2", "unit": "10*6/kg", "status": "F"},
            {"loinc": "883-9",   "name": "ABO",   "value": "O",   "status": "F"},
        ])
        out, _, rc = self._run(*self._base_args(), "--results", results, "--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["results_count"], 2,
                         "results_count must reflect input results only, not the DIN OBX")


# ── runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
