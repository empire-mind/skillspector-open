#!/usr/bin/env python3
"""Tests for slop-scan.py — every assertion below was verified by running it."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
import importlib.util as _ilu

_spec = _ilu.spec_from_file_location("slop_scan", HERE.parent / "slop-scan.py")
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
scan_file = _mod.scan_file

SLOP = HERE.parent / "slop-scan.py"


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text)
    return str(p)


def rules(findings):
    return {(f["severity"], f["rule"]) for f in findings}


DUP_BLOCK = """\
def fetch_user(user_id):
    conn = db.connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row
"""


class TestHighSignals:
    def test_duplicate_block_flagged(self, tmp_path):
        p = write(tmp_path, "a.py", DUP_BLOCK * 3)
        assert ("HIGH", "duplicate_block") in rules(scan_file(p))

    def test_two_copies_not_flagged(self, tmp_path):
        p = write(tmp_path, "a.py", DUP_BLOCK * 2)
        assert ("HIGH", "duplicate_block") not in rules(scan_file(p))

    def test_debug_leftover_flagged(self, tmp_path):
        p = write(tmp_path, "a.py", "def f():\n    breakpoint()\n    return 1\n")
        assert ("HIGH", "debug_leftover") in rules(scan_file(p))

    def test_console_log_flagged(self, tmp_path):
        p = write(tmp_path, "a.js", "function f() {\n  console.log('x');\n}\n")
        assert ("HIGH", "debug_leftover") in rules(scan_file(p))

    def test_unimplemented_stub_flagged(self, tmp_path):
        p = write(tmp_path, "a.py", "def f():\n    raise NotImplementedError\n")
        assert ("HIGH", "unimplemented_stub") in rules(scan_file(p))


class TestMediumSignals:
    def test_todo_density_flagged(self, tmp_path):
        body = "\n".join(f"# TODO: thing {i}" for i in range(5))
        p = write(tmp_path, "a.py", body + "\n")
        assert ("MED", "todo_density") in rules(scan_file(p))

    def test_few_todos_not_flagged(self, tmp_path):
        p = write(tmp_path, "a.py", "# TODO: one\n# TODO: two\nx = 1\n")
        assert ("MED", "todo_density") not in rules(scan_file(p))

    def test_ellipsis_placeholder_flagged(self, tmp_path):
        p = write(tmp_path, "a.py", "def f():\n    ...\n")
        assert ("MED", "placeholder") in rules(scan_file(p))


class TestInfoSignals:
    def test_oversized_file_flagged(self, tmp_path):
        p = write(tmp_path, "a.py", "x = 1\n" * 1001)
        assert ("INFO", "oversized") in rules(scan_file(p))


class TestClean:
    def test_clean_file_no_findings(self, tmp_path):
        p = write(tmp_path, "a.py",
                  "def add(a, b):\n    return a + b\n")
        assert scan_file(p) == []


class TestCLI:
    def run(self, *args):
        return subprocess.run([sys.executable, str(SLOP), *args],
                              capture_output=True, text=True)

    def test_exit_1_on_high(self, tmp_path):
        write(tmp_path, "a.py", "def f():\n    breakpoint()\n")
        assert self.run(str(tmp_path)).returncode == 1

    def test_exit_0_when_clean(self, tmp_path):
        write(tmp_path, "a.py", "x = 1\n")
        assert self.run(str(tmp_path)).returncode == 0

    def test_json_shape(self, tmp_path):
        write(tmp_path, "a.py", "def f():\n    breakpoint()\n")
        data = json.loads(self.run(str(tmp_path), "--json").stdout)
        assert data["high_present"] is True
        assert data["files_with_findings"] == 1
