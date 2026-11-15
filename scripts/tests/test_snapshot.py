import contextlib
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import snapshot as sn  # noqa: E402

PAGE = ("<html><body><h1>Pricing</h1><p>Pro  plan: \u201c$19 per month\u201d,\n"
        "billed annually &amp; cancel anytime.</p><script>var x='secret-js';</script></body></html>")


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def reply(self, code, body=b"", ctype="text/html", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = self.path
        if p == "/robots.txt":
            r = self.server.robots
            return self.reply(404) if r is None else self.reply(200, r.encode(), "text/plain")
        if p in ("/ok.html", "/private/page.html"):
            return self.reply(200, PAGE.encode())
        if p == "/redirect":
            return self.reply(302, b"", extra={"Location": "/ok.html"})
        if p == "/big":
            return self.reply(200, b"x" * 2000, "text/plain")
        if p == "/empty":
            return self.reply(200, b"")
        if p == "/error":
            return self.reply(500, b"boom")
        if p == "/doc.pdf":
            return self.reply(200, b"%PDF-1.4 fake", "application/pdf")
        return self.reply(404, b"nope")


class Base(unittest.TestCase):
    robots = None

    def setUp(self):
        os.environ["no_proxy"] = os.environ["NO_PROXY"] = "127.0.0.1,localhost"
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.srv.robots = self.robots
        threading.Thread(target=lambda: self.srv.serve_forever(poll_interval=0.02), daemon=True).start()
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}"
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()

    def fetch(self, path, **kw):
        kw.setdefault("today", "2026-11-16")
        return sn.fetch(self.base + path, root=self.root, timeout=5, **kw)


class TestFetch(Base):
    def test_saves_file_meta_and_ref(self):
        r = self.fetch("/ok.html")
        saved = self.root / r["path"]
        self.assertTrue(saved.is_file())
        self.assertEqual(sn.sha256_bytes(saved.read_bytes()), r["sha256"])
        self.assertTrue(r["ref"].endswith("#sha256=" + r["sha256"]))
        self.assertTrue(r["path"].startswith("knowledge/01-research/sources/"))
        self.assertIn("20261116", r["path"])
        meta = json.loads(Path(str(saved) + ".meta.json").read_text())
        self.assertEqual(meta["accessed_at"], "2026-11-16")
        self.assertEqual(meta["status"], 200)
        self.assertEqual(meta["content_type"], "text/html")

    def test_same_content_same_name_idempotent(self):
        a, b = self.fetch("/ok.html"), self.fetch("/ok.html")
        self.assertEqual(a["ref"], b["ref"])
        files = [p for p in (self.root / sn.DEFAULT_OUT).iterdir() if not p.name.endswith(".meta.json")]
        self.assertEqual(len(files), 1)

    def test_redirect_followed_and_recorded(self):
        r = self.fetch("/redirect")
        self.assertTrue(r["final_url"].endswith("/ok.html"))

    def test_http_errors_save_nothing(self):
        for path in ("/missing", "/error"):
            with self.assertRaises(sn.SnapshotError):
                self.fetch(path)
        self.assertFalse((self.root / sn.DEFAULT_OUT).exists())

    def test_empty_and_oversize_save_nothing(self):
        with self.assertRaises(sn.SnapshotError):
            self.fetch("/empty")
        with self.assertRaises(sn.SnapshotError):
            self.fetch("/big", max_bytes=1000)
        self.assertFalse((self.root / sn.DEFAULT_OUT).exists())

    def test_non_http_schemes_refused(self):
        for url in ("file:///etc/passwd", "ftp://example.com/x", "javascript:alert(1)", "http://"):
            with self.assertRaises(sn.SnapshotError):
                sn.fetch(url, root=self.root)

    def test_no_leftover_temp_files(self):
        self.fetch("/ok.html")
        left = [p.name for p in (self.root / sn.DEFAULT_OUT).iterdir() if p.name.startswith(".tmp-")]
        self.assertEqual(left, [])

    def test_extension_by_content_type(self):
        self.assertTrue(self.fetch("/big")["path"].endswith(".txt"))
        self.assertTrue(self.fetch("/doc.pdf")["path"].endswith(".pdf"))


class TestRobots(Base):
    robots = "User-agent: *\nDisallow: /private/\n"

    def test_disallowed_path_blocked_with_code_3(self):
        with self.assertRaises(sn.RobotsBlocked):
            self.fetch("/private/page.html")
        self.assertEqual(sn.RobotsBlocked.code, 3)
        self.assertFalse((self.root / sn.DEFAULT_OUT).exists())

    def test_allowed_path_ok_and_override_works(self):
        self.fetch("/ok.html")
        self.assertTrue(self.fetch("/private/page.html", ignore_robots=True)["ref"])


class TestRobotsMissing(Base):
    def test_no_robots_file_means_allowed(self):
        self.assertTrue(self.fetch("/ok.html")["ref"])


class TestVerifyQuoteClaims(Base):
    def test_verify_ok_and_tamper_detected(self):
        r = self.fetch("/ok.html")
        self.assertTrue(sn.verify_ref(r["ref"], self.root)[0])
        (self.root / r["path"]).write_bytes(b"changed")
        ok, d = sn.verify_ref(r["ref"], self.root)
        self.assertFalse(ok)
        self.assertIn("mismatch", d)

    def test_verify_missing_file_and_bad_ref(self):
        ok, _ = sn.verify_ref("knowledge/none.html#sha256=" + "0" * 64, self.root)
        self.assertFalse(ok)
        for bad in ("", "no-hash.html", "x.html#sha256=abc"):
            with self.assertRaises(sn.SnapshotError):
                sn.verify_ref(bad, self.root)

    def test_path_traversal_refused(self):
        with self.assertRaises(sn.SnapshotError):
            sn.verify_ref("../../etc/passwd#sha256=" + "0" * 64, self.root)

    def test_quote_tolerates_whitespace_case_entities_and_curly_quotes(self):
        r = self.fetch("/ok.html")
        for q in ('PRO PLAN: "$19 per month"', "billed annually & cancel anytime", "pricing"):
            self.assertTrue(sn.quote_in_ref(r["ref"], q, self.root)[0], q)

    def test_quote_missing_script_text_and_empty_fail(self):
        r = self.fetch("/ok.html")
        self.assertFalse(sn.quote_in_ref(r["ref"], "$29 per month", self.root)[0])
        self.assertFalse(sn.quote_in_ref(r["ref"], "secret-js", self.root)[0])
        self.assertFalse(sn.quote_in_ref(r["ref"], "   ", self.root)[0])

    def test_quote_refuses_tampered_file(self):
        r = self.fetch("/ok.html")
        (self.root / r["path"]).write_bytes(b"<p>$19 per month</p>")
        self.assertFalse(sn.quote_in_ref(r["ref"], "$19 per month", self.root)[0])

    def test_pdf_quote_unsupported(self):
        r = self.fetch("/doc.pdf")
        with self.assertRaises(sn.SnapshotError):
            sn.quote_in_ref(r["ref"], "anything", self.root)

    def test_claims_check(self):
        r = self.fetch("/ok.html")
        cl = self.root / "claims.jsonl"
        lines = [json.dumps({"claim_id": "R1-CLM-001", "snapshot": r["ref"]}),
                 json.dumps({"claim_id": "R1-CLM-002", "snapshot": None}),
                 json.dumps({"claim_id": "R1-CLM-003", "snapshot": "knowledge/x.html#sha256=" + "1" * 64})]
        cl.write_text("\n".join(lines) + "\n")
        res = sn.check_claims(cl, self.root)
        self.assertEqual([s for s, _ in res], ["PASS", "FAIL"])

    def test_claims_check_missing_file_and_bad_json(self):
        self.assertEqual(sn.check_claims(self.root / "none.jsonl", self.root)[0][0], "FAIL")
        cl = self.root / "c.jsonl"
        cl.write_text("{not json}\n")
        self.assertEqual(sn.check_claims(cl, self.root)[0][0], "FAIL")


class TestCli(Base):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = sn.main(["--root", str(self.root), *args])
        return code, out.getvalue(), err.getvalue()

    def test_fetch_verify_quote_roundtrip(self):
        code, out, _ = self.run_cli("fetch", self.base + "/ok.html")
        self.assertEqual(code, 0)
        ref = [l for l in out.splitlines() if l.startswith("SNAPSHOT: ")][0][len("SNAPSHOT: "):]
        self.assertIn("ACCESSED_AT: ", out)
        self.assertEqual(self.run_cli("verify", ref)[0], 0)
        self.assertEqual(self.run_cli("quote", ref, "$19 per month")[0], 0)
        self.assertEqual(self.run_cli("quote", ref, "$99")[0], 1)

    def test_fetch_failure_exit_1_and_robots_exit_3(self):
        self.assertEqual(self.run_cli("fetch", self.base + "/missing")[0], 1)
        self.srv.robots = "User-agent: *\nDisallow: /\n"
        self.assertEqual(self.run_cli("fetch", self.base + "/ok.html")[0], 3)


if __name__ == "__main__":
    unittest.main()
