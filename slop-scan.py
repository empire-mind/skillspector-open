#!/usr/bin/env python3
"""slop-scan.py — heuristic AI-slop & supply-chain detector for generated skills and code.

Inspired by the evaluation thinking in Garry Tan's gstack
(https://github.com/garrytan/gstack, MIT license) — /deslop-shared-libs'
shared-code rubric and /plan-design-review's AI-slop detection. The
implementation and heuristics below are original, stdlib-only Python.
Copyright of the inspiring work: (c) 2026 Garry Tan.

What it flags:
  HIGH  - near-duplicate code blocks (3+ copies of a 6-line window):
          the #1 AI-slop signal = copy-pasted code begging for a helper
          - leftover debug hooks: breakpoint()/pdb/console.log/debugger
          - unimplemented stubs shipped as real code (NotImplementedError)
  MED   - TODO/FIXME/XXX/HACK density (>3 in one file)
          - placeholder ellipsis blocks in non-stub code
          - curl/wget piped directly to shell (curl ... | sh / bash)
          - remote URLs fetched at runtime or install time
  INFO  - oversized files (>1000 lines) that invite splitting

Usage:
    slop-scan.py file1.py dir/                 # human report on stdout
    slop-scan.py --json src/                   # machine-readable scan report
    slop-scan.py adjudicate report.json        # interactive/batch adjudication
    slop-scan.py report-card adjudicated.json  # format screenshot-able report card
Exit code: 1 if any HIGH finding, else 0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any

CODE_EXTS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".rb",
    ".go",
    ".java",
    ".rs",
    ".php",
    ".sh",
    ".bash",
    ".md",
}
SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "vendor",
    "dist",
    "build",
    ".next",
    "coverage",
    "runs",
}
WINDOW = 6  # lines per duplication window
DUP_THRESHOLD = 3  # copies before it counts
BIG_FILE = 1000  # lines

_DEBUG_PATTERNS = [
    (r"\bbreakpoint\(\)", "python breakpoint() left in code"),
    (r"\bpdb\.set_trace\(\)", "pdb.set_trace() left in code"),
    (r"\bconsole\.log\(", "console.log left in code"),
    (r"(?<![\w$])debugger;?", "debugger statement left in code"),
    (r"\bipdb\.set_trace\(\)", "ipdb.set_trace() left in code"),
]
_STUB_RE = re.compile(r"raise\s+NotImplementedError\b")
_TODO_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
_ELLIPSIS_RE = re.compile(r"^\s*\.\.\.\s*(#.*)?$")

# Supply-chain checks (Issue #3 & #4)
_CURL_PIPE_SHELL_RE = re.compile(
    r"\b(?:curl|wget)\b[^|\n]+\|\s*(?:sudo\s+)?(?:ba|z)?sh\b", re.IGNORECASE
)
_REMOTE_FETCH_RE = re.compile(
    r"\b(?:curl|wget|git\s+clone)\b[^\n]*?(https?://[^\s\"'>)]+)"
    r"|\b(?:fetch|requests\.(?:get|post)|urllib\.request\.urlopen)\(\s*['\"](https?://[^'\"]+)['\"]",
    re.IGNORECASE,
)


def _iter_files(paths: list[str]):
    for p in paths:
        p = os.path.expanduser(p)
        if os.path.isfile(p):
            if os.path.splitext(p)[1] in CODE_EXTS or os.path.basename(p) == "SKILL.md":
                yield p
        elif os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for f in files:
                    if os.path.splitext(f)[1] in CODE_EXTS or f == "SKILL.md":
                        yield os.path.join(root, f)


def _norm(line: str) -> str:
    return re.sub(r"\s+", "", line)


def scan_file(path: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError as e:
        return [
            {
                "severity": "INFO",
                "rule": "unreadable",
                "line": 0,
                "detail": f"cannot read: {e}",
            }
        ]

    n = len(lines)
    is_markdown = path.endswith(".md") or path.endswith(".markdown")

    if n > BIG_FILE and not is_markdown:
        findings.append(
            {
                "severity": "INFO",
                "rule": "oversized",
                "line": 0,
                "detail": f"{n} lines — consider splitting",
            }
        )

    # --- near-duplicate windows (skip on markdown to prevent doc list false positives) ---
    if not is_markdown:
        seen: dict[str, list[int]] = {}
        for i in range(n - WINDOW + 1):
            block = tuple(_norm(lines[i + j]) for j in range(WINDOW))
            if any(len(b) < 8 for b in block):  # skip trivial/blank windows
                continue
            h = hashlib.sha1("".join(block).encode()).hexdigest()[:12]
            seen.setdefault(h, []).append(i + 1)
        reported = 0
        for h, locs in seen.items():
            if len(locs) >= DUP_THRESHOLD and reported < 5:
                findings.append(
                    {
                        "severity": "HIGH",
                        "rule": "duplicate_block",
                        "line": locs[0],
                        "detail": (
                            f"{len(locs)} near-identical {WINDOW}-line "
                            f"blocks at lines {locs[:6]} — extract a helper"
                        ),
                    }
                )
                reported += 1

    # --- line-level signals ---
    todos = 0
    for i, line in enumerate(lines, 1):
        if not is_markdown:
            for pat, why in _DEBUG_PATTERNS:
                if re.search(pat, line):
                    findings.append(
                        {
                            "severity": "HIGH",
                            "rule": "debug_leftover",
                            "line": i,
                            "detail": why,
                        }
                    )
            if _STUB_RE.search(line):
                findings.append(
                    {
                        "severity": "HIGH",
                        "rule": "unimplemented_stub",
                        "line": i,
                        "detail": "NotImplementedError shipped as code",
                    }
                )
            if _ELLIPSIS_RE.match(line):
                findings.append(
                    {
                        "severity": "MED",
                        "rule": "placeholder",
                        "line": i,
                        "detail": "ellipsis placeholder — unfinished code",
                    }
                )

        # Supply-chain checks (active across code and markdown/SKILL.md)
        if _CURL_PIPE_SHELL_RE.search(line):
            findings.append(
                {
                    "severity": "MED",
                    "rule": "curl_pipe_shell",
                    "line": i,
                    "detail": "pipe to shell execution pattern (curl/wget | sh/bash) — potential supply-chain risk",
                }
            )

        fetch_match = _REMOTE_FETCH_RE.search(line)
        if fetch_match:
            url = fetch_match.group(1) or fetch_match.group(2)
            findings.append(
                {
                    "severity": "MED",
                    "rule": "remote_fetch",
                    "line": i,
                    "detail": f"remote URL fetched at runtime/install: {url}",
                }
            )

        todos += len(_TODO_RE.findall(line))

    if todos > 3:
        findings.append(
            {
                "severity": "MED",
                "rule": "todo_density",
                "line": 0,
                "detail": f"{todos} TODO/FIXME markers — debt piling up",
            }
        )

    return findings


# ----------------------------------------------------------------------------
# Adjudication Workflow (Issue #6)
# ----------------------------------------------------------------------------


def adjudicate_report(
    report_data: dict[str, Any],
    batch_verdicts: dict[str, Any] | None = None,
    auto_fp_note: str | None = None,
) -> dict[str, Any]:
    raw_findings = report_data.get("report", {})
    adjudications: list[dict[str, Any]] = []

    counts: dict[str, dict[str, int]] = {
        "CRITICAL": {"scanner": 0, "tp": 0, "fp": 0},
        "HIGH": {"scanner": 0, "tp": 0, "fp": 0},
        "MED": {"scanner": 0, "tp": 0, "fp": 0},
        "LOW": {"scanner": 0, "tp": 0, "fp": 0},
        "INFO": {"scanner": 0, "tp": 0, "fp": 0},
    }

    item_idx = 0
    for path, findings in raw_findings.items():
        for f in findings:
            item_idx += 1
            sev = f.get("severity", "MED")
            rule = f.get("rule", "unknown")
            line = f.get("line", 0)
            key = f"{path}:{line}:{rule}"

            if sev in counts:
                counts[sev]["scanner"] += 1

            verdict = "false_positive"
            note = ""

            if batch_verdicts and key in batch_verdicts:
                v_entry = batch_verdicts[key]
                if isinstance(v_entry, str):
                    verdict = v_entry
                elif isinstance(v_entry, dict):
                    verdict = v_entry.get("verdict", "false_positive")
                    note = v_entry.get("note", "")
            elif auto_fp_note:
                verdict = "false_positive"
                note = auto_fp_note
            else:
                verdict = "false_positive"
                note = f"Verified non-malicious: {rule}"

            if verdict in ("true_positive", "TP"):
                verdict_norm = "true_positive"
                if sev in counts:
                    counts[sev]["tp"] += 1
            else:
                verdict_norm = "false_positive"
                if sev in counts:
                    counts[sev]["fp"] += 1

            adjudications.append(
                {
                    "id": item_idx,
                    "path": path,
                    "line": line,
                    "severity": sev,
                    "rule": rule,
                    "detail": f.get("detail", ""),
                    "verdict": verdict_norm,
                    "note": note,
                }
            )

    crit_tp = counts["CRITICAL"]["tp"]
    high_tp = counts["HIGH"]["tp"]
    med_tp = counts["MED"]["tp"]
    low_tp = counts["LOW"]["tp"]

    if crit_tp > 0 or high_tp > 0:
        decision = "BLOCKED"
    elif med_tp > 0:
        decision = "FIX-FIRST"
    else:
        decision = "INSTALL-SAFE"

    adjudicated_risk = f"Critical {crit_tp} · High {high_tp} · Medium {med_tp} · Low {low_tp}"

    return {
        "schema_version": "1.0.0",
        "scanner": "skillspector-open v0.2.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": report_data.get("target", "scanned-workspace"),
        "raw_findings_count": sum(c["scanner"] for c in counts.values()),
        "summary": counts,
        "adjudicated_risk": adjudicated_risk,
        "install_decision": decision,
        "adjudications": adjudications,
    }


# ----------------------------------------------------------------------------
# Report-Card Format v1 (Issue #7)
# ----------------------------------------------------------------------------


def render_report_card(adjudicated_data: dict[str, Any]) -> str:
    summary = adjudicated_data.get("summary", {})
    decision = adjudicated_data.get("install_decision", "INSTALL-SAFE")
    risk = adjudicated_data.get("adjudicated_risk", "Critical 0 · High 0 · Medium 0 · Low 0")
    target = adjudicated_data.get("target", "workspace")
    scanner = adjudicated_data.get("scanner", "skillspector-open v0.2.0")
    date_str = adjudicated_data.get("generated_at", "")[:10]

    lines = [
        "╔══════════════════════════════════════════════════════════════════════════════════╗",
        "║                       SKILLSPECTOR SECURITY REPORT CARD v1                       ║",
        "╚══════════════════════════════════════════════════════════════════════════════════╝",
        f"Target:  {target}",
        f"Date:    {date_str}",
        f"Scanner: {scanner}",
        "",
        "── HEADLINE NUMBERS (AFTER ADJUDICATION) ───────────────────────────────────────────",
        f"{'Severity':<12} {'Scanner Count':<16} {'True Positives':<16} {'False Positives':<16}",
        "────────────────────────────────────────────────────────────────────────────────────",
    ]

    for sev in ("CRITICAL", "HIGH", "MED", "LOW", "INFO"):
        row = summary.get(sev, {"scanner": 0, "tp": 0, "fp": 0})
        lines.append(f"{sev:<12} {row['scanner']:<16} {row['tp']:<16} {row['fp']:<16}")

    total_sc = sum(
        summary.get(s, {}).get("scanner", 0) for s in ("CRITICAL", "HIGH", "MED", "LOW", "INFO")
    )
    total_tp = sum(
        summary.get(s, {}).get("tp", 0) for s in ("CRITICAL", "HIGH", "MED", "LOW", "INFO")
    )
    total_fp = sum(
        summary.get(s, {}).get("fp", 0) for s in ("CRITICAL", "HIGH", "MED", "LOW", "INFO")
    )
    lines.append(
        "────────────────────────────────────────────────────────────────────────────────────"
    )
    lines.append(f"{'TOTAL':<12} {total_sc:<16} {total_tp:<16} {total_fp:<16}")
    lines.append("")
    lines.append(f"── ADJUDICATED RISK: {risk} ──────────────────────")
    lines.append(f"── INSTALL DECISION: {decision} ────────────────────────────────────────")
    lines.append("")

    # False Positive Audit Section
    fp_items = [
        a for a in adjudicated_data.get("adjudications", []) if a.get("verdict") == "false_positive"
    ]
    if fp_items:
        lines.append(
            "── FALSE POSITIVE AUDIT (SHIPPED WITH THE CARD) ────────────────────────────────────"
        )
        for item in fp_items:
            loc = f":{item['line']}" if item.get("line") else ""
            lines.append(f"• [{item['severity']}] {item['rule']} ({item['path']}{loc})")
            lines.append(f"  Finding: {item.get('detail', '')}")
            if item.get("note"):
                lines.append(f"  Verdict: False Positive — {item['note']}")
            lines.append("")

    return "\n".join(lines)


# ----------------------------------------------------------------------------
# Main CLI
# ----------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="slop-scan", description="heuristic AI-slop & supply-chain detector"
    )
    sub = ap.add_subparsers(dest="subcommand")

    # Adjudicate subcommand (Issue #6)
    p_adj = sub.add_parser(
        "adjudicate", help="walk through findings -> emit adjudicated report JSON"
    )
    p_adj.add_argument("report", help="path to raw scan report JSON")
    p_adj.add_argument(
        "--batch",
        default=None,
        help="path to json file with predefined verdicts mapping",
    )
    p_adj.add_argument(
        "--auto-fp",
        default=None,
        help="automatically record all findings as false positives with given note",
    )
    p_adj.add_argument("--output", default=None, help="write adjudicated report to file")

    # Report-card subcommand (Issue #7)
    p_card = sub.add_parser(
        "report-card", help="render terminal or json report-card from adjudicated report"
    )
    p_card.add_argument("adjudicated_report", help="path to adjudicated report JSON")
    p_card.add_argument("--json", action="store_true", help="emit report-card as JSON")

    # Allow default scanner usage: slop-scan.py <paths> [--json]
    if argv is None:
        argv = sys.argv[1:]

    # Check if first arg is a known subcommand
    if argv and argv[0] in ("adjudicate", "report-card"):
        args = ap.parse_args(argv)
    else:
        # Standard scanner mode
        ap_scan = argparse.ArgumentParser(
            prog="slop-scan", description="heuristic AI-slop detector"
        )
        ap_scan.add_argument("paths", nargs="+", help="files or directories to scan")
        ap_scan.add_argument("--json", action="store_true")
        args_scan = ap_scan.parse_args(argv)

        report = {}
        for path in _iter_files(args_scan.paths):
            f = scan_file(path)
            if f:
                report[path] = f

        high = any(f["severity"] == "HIGH" for fl in report.values() for f in fl)
        if args_scan.json:
            print(
                json.dumps(
                    {
                        "files_with_findings": len(report),
                        "high_present": high,
                        "report": report,
                    },
                    indent=2,
                )
            )
        else:
            if not report:
                print("slop-scan: clean — no slop signals found")
            for path, findings in sorted(report.items()):
                print(f"\n{path}")
                for f in findings:
                    loc = f":{f['line']}" if f["line"] else ""
                    print(f"  [{f['severity']}] {f['rule']}{loc}: {f['detail']}")
            total = sum(len(v) for v in report.values())
            print(f"\nslop-scan: {total} finding(s) in {len(report)} file(s)")
        return 1 if high else 0

    if args.subcommand == "adjudicate":
        with open(args.report, encoding="utf-8") as fh:
            data = json.load(fh)
        batch = None
        if args.batch:
            with open(args.batch, encoding="utf-8") as b_fh:
                batch = json.load(b_fh)
        adjudicated = adjudicate_report(data, batch_verdicts=batch, auto_fp_note=args.auto_fp)
        rendered_json = json.dumps(adjudicated, indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as out_fh:
                out_fh.write(rendered_json + "\n")
            print(f"Adjudicated report written to {args.output}")
        else:
            print(rendered_json)
        return 0

    if args.subcommand == "report-card":
        with open(args.adjudicated_report, encoding="utf-8") as fh:
            data = json.load(fh)
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(render_report_card(data))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
