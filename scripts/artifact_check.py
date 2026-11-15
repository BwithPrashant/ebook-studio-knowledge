#!/usr/bin/env python3
"""artifact_check - verify a written file on disk (standard library only).

Never trust a model's "done": run this after every write.
  python3 scripts/artifact_check.py FILE [--min-lines N] [--max-lines N]
      [--numbered N] [--contains TEXT]... [--forbid TEXT]... [--json]
Exit 0 = all checks pass, 1 = a check failed, 2 = usage error.
Always checked: file exists, is a regular file, is not empty, ends with a
newline (a HEURISTIC for mid-line truncation), has no tool-call markup text.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

DEFAULT_FORBID = ("<tool_call>", "</tool_call>")
NUM_RE = re.compile(r"^\s*(\d+)(?=[\s.):,\-]|$)")


def check_numbered(lines, n):
    """Non-blank lines must start with 1..n in order, exactly n of them."""
    nums, expected = [l for l in lines if l.strip()], 1
    for l in nums:
        m = NUM_RE.match(l)
        if not m or int(m.group(1)) != expected:
            got = m.group(1) if m else repr(l[:30])
            return False, f"sequence breaks after {expected - 1}: expected {expected}, got {got}"
        expected += 1
    if expected - 1 != n:
        return False, f"found {expected - 1} numbered lines, expected {n}"
    return True, f"lines 1..{n} present, in order"


def run_checks(path, min_lines=None, max_lines=None, numbered=None, contains=(), forbid=()):
    p, res = Path(path), []

    def add(name, ok, detail):
        res.append({"check": name, "ok": bool(ok), "detail": detail})

    if not p.exists():
        add("exists", False, f"{p} not found")
        return res, {}
    if not p.is_file():
        add("exists", False, f"{p} is not a regular file")
        return res, {}
    data = p.read_bytes()
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    info = {"bytes": len(data), "lines": len(lines), "sha256": hashlib.sha256(data).hexdigest()}
    add("exists", True, str(p))
    add("non_empty", len(data) > 0, f"{len(data)} bytes")
    add("final_newline", text.endswith("\n"), "ends with newline (heuristic for truncation)")
    if min_lines is not None:
        add("min_lines", len(lines) >= min_lines, f"{len(lines)} lines, need >= {min_lines}")
    if max_lines is not None:
        add("max_lines", len(lines) <= max_lines, f"{len(lines)} lines, need <= {max_lines}")
    if numbered is not None:
        ok, d = check_numbered(lines, numbered)
        add("numbered", ok, d)
    for s in contains:
        add("contains", s in text, repr(s))
    for s in tuple(DEFAULT_FORBID) + tuple(forbid):
        add("forbid", s not in text, f"must not contain {s!r}")
    return res, info


def main(argv=None):
    ap = argparse.ArgumentParser(prog="artifact_check", description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--min-lines", type=int)
    ap.add_argument("--max-lines", type=int)
    ap.add_argument("--numbered", type=int, metavar="N")
    ap.add_argument("--contains", action="append", default=[])
    ap.add_argument("--forbid", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    res, info = run_checks(a.file, a.min_lines, a.max_lines, a.numbered, a.contains, a.forbid)
    failed = [r for r in res if not r["ok"]]
    if a.json:
        print(json.dumps({"ok": not failed, "info": info, "results": res}, indent=1))
    else:
        for r in res:
            print(f"{'PASS' if r['ok'] else 'FAIL'} {r['check']}: {r['detail']}")
        if info:
            print(f"INFO bytes={info['bytes']} lines={info['lines']} sha256={info['sha256']}")
        print(f"{'FAIL' if failed else 'OK'}: {len(failed)} failed check(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
