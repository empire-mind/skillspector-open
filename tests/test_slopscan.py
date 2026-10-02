#!/usr/bin/env python3
"""Tests for slop-scan.py — every assertion below was verified by running it."""

import importlib.util as _ilu
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

_spec = _ilu.spec_from_file_location("slop_scan", HERE.parent / "slop-scan.py")
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
scan_file = _mod.scan_file
adjudicate_report = _mod.adjudicate_report
render_report_card = _mod.render_report_card

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


class TestSupplyChainChecks:
    def test_curl_pipe_shell_flagged(self, tmp_path):
        p = write(tmp_path, "install.sh", "curl -fsSL https://get.docker.com | sh\n")
        assert ("MED", "curl_pipe_shell") in rules(scan_file(p))

    def test_wget_pipe_bash_flagged(self, tmp_path):
        p = write(tmp_path, "setup.bash", "wget -qO- https://example.com/install.sh | sudo bash\n")
        assert ("MED", "curl_pipe_shell") in rules(scan_file(p))

    def test_remote_fetch_flagged(self, tmp_path):
        p = write(
            tmp_path,
            "fetch.py",
            "import requests\nres = requests.get('https://api.example.com/data')\n",
        )
        assert ("MED", "remote_fetch") in rules(scan_file(p))

    def test_doc_link_not_flagged_as_fetch(self, tmp_path):
        p = write(
            tmp_path,
            "SKILL.md",
            "# My Skill\nSee [Documentation](https://example.com/docs) for info.\n",
        )
        r = rules(scan_file(p))
        assert ("MED", "remote_fetch") not in r
        assert ("MED", "curl_pipe_shell") not in r


class TestInfoSignals:
    def test_oversized_file_flagged(self, tmp_path):
        p = write(tmp_path, "a.py", "x = 1\n" * 1001)
        assert ("INFO", "oversized") in rules(scan_file(p))


class TestClean:
    def test_clean_file_no_findings(self, tmp_path):
        p = write(tmp_path, "a.py", "def add(a, b):\n    return a + b\n")
        assert scan_file(p) == []


class TestAdjudicationAndReportCard:
    def test_adjudicate_and_render_report_card(self, tmp_path):
        report_data = {
            "target": "sample-repo",
            "report": {
                "install.sh": [
                    {
                        "severity": "MED",
                        "rule": "curl_pipe_shell",
                        "line": 4,
                        "detail": "pipe to shell",
                    }
                ]
            },
        }
        adjudicated = adjudicate_report(
            report_data,
            auto_fp_note="Standard installer script; non-malicious.",
        )
        assert adjudicated["install_decision"] == "INSTALL-SAFE"
        assert adjudicated["summary"]["MED"]["fp"] == 1
        assert adjudicated["summary"]["MED"]["tp"] == 0

        card = render_report_card(adjudicated)
        assert "SKILLSPECTOR SECURITY REPORT CARD v1" in card
        assert "INSTALL DECISION: INSTALL-SAFE" in card
        assert "FALSE POSITIVE AUDIT" in card


class TestCLI:
    def run(self, *args):
        return subprocess.run([sys.executable, str(SLOP), *args], capture_output=True, text=True)

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

    def test_cli_adjudicate_and_report_card(self, tmp_path):
        write(tmp_path, "a.py", "curl https://example.com/script.sh | sh\n")
        scan_res = self.run(str(tmp_path), "--json")
        rep_file = tmp_path / "raw.json"
        rep_file.write_text(scan_res.stdout)

        adj_file = tmp_path / "adj.json"
        adj_res = self.run(
            "adjudicate", str(rep_file), "--output", str(adj_file), "--auto-fp", "Benign installer"
        )
        assert adj_res.returncode == 0
        assert adj_file.exists()

        card_res = self.run("report-card", str(adj_file))
        assert card_res.returncode == 0
        assert "INSTALL-SAFE" in card_res.stdout
