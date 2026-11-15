#!/usr/bin/env python3
"""snapshot - save a dated, hashed copy of ONE web page and check it later.

Standard library only. Run from the knowledge repo root.
  python3 scripts/snapshot.py fetch URL [--out-dir DIR] [--timeout S]
          [--max-bytes N] [--ignore-robots] [--json]
  python3 scripts/snapshot.py verify REF
  python3 scripts/snapshot.py quote REF "text"
  python3 scripts/snapshot.py claims [--claims FILE]
REF is what `fetch` prints for a claim's `snapshot` field:
  knowledge/01-research/sources/<file>#sha256=<64 hex>
Rules: one page per call, no crawling, no logins, no paywall bypass. robots.txt
is respected unless a human authorises --ignore-robots. Raw HTML only: pages
drawn by JavaScript may lack the text you need, so always run `quote`.
Exit codes: 0 ok, 1 failed check or fetch, 2 usage, 3 blocked by robots.txt.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser
from pathlib import Path

VERSION = "0.1"
DEFAULT_OUT = "knowledge/01-research/sources"
DEFAULT_CLAIMS = "knowledge/registry/claims.jsonl"
DEFAULT_UA = "ebook-studio-research/0.1 (single-page research snapshot)"
REF_RE = re.compile(r"^(?P<path>[^#\s]+)#sha256=(?P<sha>[0-9a-f]{64})$")
EXT = {"text/html": ".html", "application/xhtml+xml": ".html", "text/plain": ".txt",
       "application/json": ".json", "application/pdf": ".pdf", "text/markdown": ".md"}


class SnapshotError(Exception):
    code = 1


class RobotsBlocked(SnapshotError):
    code = 3


def slugify(text, limit=40):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:limit].strip("-") or "page"


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data):
    """Write to a temp file in the same folder, then rename (never a half file)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _open(url, timeout, ua, max_bytes=None):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read(max_bytes + 1) if max_bytes else r.read()
        return r.status, r.geturl(), r.headers.get_content_type(), body


def robots_allowed(url, ua, timeout):
    u = urllib.parse.urlsplit(url)
    robots = f"{u.scheme}://{u.netloc}/robots.txt"
    try:
        _, _, _, body = _open(robots, timeout, ua, 500_000)
    except urllib.error.HTTPError as e:
        return e.code < 500  # 4xx: no rules; 5xx: treat as disallowed
    except (urllib.error.URLError, OSError):
        return True  # unreachable: the real fetch will report the problem
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(body.decode("utf-8", errors="replace").splitlines())
    return rp.can_fetch(ua, url)


def fetch(url, root=".", out_dir=DEFAULT_OUT, timeout=20, max_bytes=5_000_000,
          ua=DEFAULT_UA, ignore_robots=False, today=None):
    u = urllib.parse.urlsplit(url)
    if u.scheme not in ("http", "https") or not u.netloc:
        raise SnapshotError(f"only http(s) URLs are allowed: {url!r}")
    if not ignore_robots and not robots_allowed(url, ua, timeout):
        raise RobotsBlocked(f"robots.txt disallows {url}; a human must authorise --ignore-robots")
    try:
        status, final_url, ctype, body = _open(url, timeout, ua, max_bytes)
    except urllib.error.HTTPError as e:
        raise SnapshotError(f"HTTP {e.code} for {url}; nothing saved")
    except (urllib.error.URLError, OSError) as e:
        raise SnapshotError(f"fetch failed for {url}: {e}; nothing saved")
    if len(body) > max_bytes:
        raise SnapshotError(f"page larger than --max-bytes {max_bytes}; nothing saved")
    if not body:
        raise SnapshotError("empty response; nothing saved")
    digest = sha256_bytes(body)
    day = today or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    name = "-".join([slugify(u.netloc, 30), slugify(u.path, 30), day.replace("-", ""), digest[:12]])
    name += EXT.get(ctype, ".bin")
    root = Path(root)
    target = root / out_dir / name
    if not (target.exists() and sha256_bytes(target.read_bytes()) == digest):
        atomic_write(target, body)
    if sha256_bytes(target.read_bytes()) != digest:  # verify after write
        target.unlink()
        raise SnapshotError("hash mismatch after write; file removed")
    meta = {"url": url, "final_url": final_url, "status": status, "content_type": ctype,
            "bytes": len(body), "sha256": digest, "accessed_at": day,
            "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "tool": f"snapshot.py {VERSION}"}
    atomic_write(str(target) + ".meta.json", (json.dumps(meta, indent=1) + "\n").encode())
    rel = Path(os.path.relpath(target, root)).as_posix()
    return {**meta, "path": rel, "ref": f"{rel}#sha256={digest}"}


def parse_ref(ref):
    m = REF_RE.match(ref or "")
    if not m:
        raise SnapshotError(f"bad snapshot reference {ref!r}; expected <path>#sha256=<64 hex>")
    return m.group("path"), m.group("sha")


def resolve(root, rel):
    root = Path(root).resolve()
    p = (root / rel).resolve()
    if root != p and root not in p.parents:
        raise SnapshotError(f"snapshot path escapes the repo: {rel}")
    return p


def verify_ref(ref, root="."):
    rel, want = parse_ref(ref)
    p = resolve(root, rel)
    if not p.is_file():
        return False, f"{rel} not found"
    got = sha256_bytes(p.read_bytes())
    if got != want:
        return False, f"hash mismatch for {rel}: file is {got[:12]}..., reference says {want[:12]}..."
    return True, f"{rel} matches sha256 {want[:12]}..."


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


_TRANS = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
                        "\u00a0": " ", "\u2013": "-", "\u2014": "-"})


def normalize(text):
    return re.sub(r"\s+", " ", text.translate(_TRANS)).strip().casefold()


def visible_text(data):
    if data[:5] == b"%PDF-":
        raise SnapshotError("PDF snapshot: text extraction is not supported; check it by hand")
    text = data.decode("utf-8", errors="replace")
    if "<" in text:
        parser = _Text()
        parser.feed(text)
        text = " ".join(parser.parts)
    return normalize(text)


def quote_in_ref(ref, quote, root="."):
    ok, detail = verify_ref(ref, root)
    if not ok:
        return False, detail
    rel, _ = parse_ref(ref)
    q = normalize(quote)
    if not q:
        return False, "empty quote"
    found = q in visible_text(resolve(root, rel).read_bytes())
    return found, ("quote found in visible text" if found else "quote NOT found in visible text")


def check_claims(claims_path, root="."):
    results, p = [], Path(claims_path)
    if not p.exists():
        return [("FAIL", f"{claims_path} not found")]
    for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            c = json.loads(line)
        except json.JSONDecodeError as e:
            results.append(("FAIL", f"line {n}: invalid JSON ({e})"))
            continue
        cid, ref = c.get("claim_id", f"line {n}"), c.get("snapshot")
        if not ref:
            continue
        try:
            ok, detail = verify_ref(ref, root)
        except SnapshotError as e:
            ok, detail = False, str(e)
        results.append(("PASS" if ok else "FAIL", f"{cid}: {detail}"))
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(prog="snapshot", description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("url")
    f.add_argument("--out-dir", default=DEFAULT_OUT)
    f.add_argument("--timeout", type=int, default=20)
    f.add_argument("--max-bytes", type=int, default=5_000_000)
    f.add_argument("--user-agent", default=DEFAULT_UA)
    f.add_argument("--ignore-robots", action="store_true")
    f.add_argument("--json", action="store_true")
    v = sub.add_parser("verify")
    v.add_argument("ref")
    q = sub.add_parser("quote")
    q.add_argument("ref")
    q.add_argument("text")
    c = sub.add_parser("claims")
    c.add_argument("--claims", default=DEFAULT_CLAIMS)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "fetch":
            r = fetch(a.url, a.root, a.out_dir, a.timeout, a.max_bytes, a.user_agent, a.ignore_robots)
            if a.json:
                print(json.dumps(r, indent=1))
            else:
                print(f"SNAPSHOT: {r['ref']}")
                print(f"ACCESSED_AT: {r['accessed_at']}")
                print(f"INFO status={r['status']} type={r['content_type']} bytes={r['bytes']} final_url={r['final_url']}")
            return 0
        if a.cmd == "verify":
            ok, d = verify_ref(a.ref, a.root)
        elif a.cmd == "quote":
            ok, d = quote_in_ref(a.ref, a.text, a.root)
        else:
            res = check_claims(a.claims, a.root)
            for s, d in res:
                print(f"{s} {d}")
            bad = sum(1 for s, _ in res if s == "FAIL")
            print(f"{'FAIL' if bad else 'OK'}: {len(res)} snapshot(s) checked, {bad} failed")
            return 1 if bad else 0
        print(f"{'PASS' if ok else 'FAIL'} {d}")
        return 0 if ok else 1
    except SnapshotError as e:
        print(f"FAIL {e}", file=sys.stderr)
        return e.code


if __name__ == "__main__":
    sys.exit(main())
