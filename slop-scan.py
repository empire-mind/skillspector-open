#!/usr/bin/env python3
"""slop-scan.py — heuristic AI-slop detector for generated code.

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
  INFO  - oversized files (>1000 lines) that invite splitting

Usage:
    slop-scan.py file1.py dir/            # human report on stdout
    slop-scan.py --json src/              # machine-readable
Exit code: 1 if any HIGH finding, else 0.
"""

import argparse
import hashlib
import json
import os
import re
import sys

CODE_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx", ".rb", ".go", ".java",
             ".rs", ".php", ".sh", ".bash"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "vendor",
             "dist", "build", ".next", "coverage", "runs"}
WINDOW = 6          # lines per duplication window
DUP_THRESHOLD = 3   # copies before it counts
BIG_FILE = 1000     # lines

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


def _iter_files(paths):
    for p in paths:
        p = os.path.expanduser(p)
        if os.path.isfile(p):
            if os.path.splitext(p)[1] in CODE_EXTS:
                yield p
        elif os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for f in files:
                    if os.path.splitext(f)[1] in CODE_EXTS:
                        yield os.path.join(root, f)


def _norm(line):
    return re.sub(r"\s+", "", line)


def scan_file(path):
    findings = []
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError as e:
        return [{"severity": "INFO", "rule": "unreadable", "line": 0,
                 "detail": f"cannot read: {e}"}]

    n = len(lines)
    if n > BIG_FILE:
        findings.append({"severity": "INFO", "rule": "oversized",
                         "line": 0,
                         "detail": f"{n} lines — consider splitting"})

    # --- near-duplicate windows ---
    seen = {}
    for i in range(n - WINDOW + 1):
        block = tuple(_norm(lines[i + j]) for j in range(WINDOW))
        if any(len(b) < 8 for b in block):  # skip trivial/blank windows
            continue
        h = hashlib.sha1("".join(block).encode()).hexdigest()[:12]
        seen.setdefault(h, []).append(i + 1)
    reported = 0
    for h, locs in seen.items():
        if len(locs) >= DUP_THRESHOLD and reported < 5:
            findings.append({"severity": "HIGH", "rule": "duplicate_block",
                             "line": locs[0],
                             "detail": f"{len(locs)} near-identical {WINDOW}-line "
                                       f"blocks at lines {locs[:6]} — extract a helper"})
            reported += 1

    # --- line-level signals ---
    todos = 0
    for i, line in enumerate(lines, 1):
        for pat, why in _DEBUG_PATTERNS:
            if re.search(pat, line):
                findings.append({"severity": "HIGH", "rule": "debug_leftover",
                                 "line": i, "detail": why})
        if _STUB_RE.search(line):
            findings.append({"severity": "HIGH", "rule": "unimplemented_stub",
                             "line": i,
                             "detail": "NotImplementedError shipped as code"})
        if _ELLIPSIS_RE.match(line):
            findings.append({"severity": "MED", "rule": "placeholder",
                             "line": i,
                             "detail": "ellipsis placeholder — unfinished code"})
        todos += len(_TODO_RE.findall(line))
    if todos > 3:
        findings.append({"severity": "MED", "rule": "todo_density", "line": 0,
                         "detail": f"{todos} TODO/FIXME markers — debt piling up"})

    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(prog="slop-scan",
                                 description="heuristic AI-slop detector")
    ap.add_argument("paths", nargs="+", help="files or directories to scan")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    report = {}
    for path in _iter_files(args.paths):
        f = scan_file(path)
        if f:
            report[path] = f

    high = any(f["severity"] == "HIGH"
               for fl in report.values() for f in fl)
    if args.json:
        print(json.dumps({"files_with_findings": len(report),
                          "high_present": high, "report": report}, indent=2))
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


if __name__ == "__main__":
    sys.exit(main())
