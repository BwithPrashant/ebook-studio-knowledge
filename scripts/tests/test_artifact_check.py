import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import artifact_check as ac  # noqa: E402


def numbered(n):
    return "".join(f"{i}. line {i}\n" for i in range(1, n + 1))


class TestArtifactCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def f(self, text, name="a.md"):
        p = self.dir / name
        p.write_text(text, encoding="utf-8")
        return str(p)

    def failed(self, path, **kw):
        res, _ = ac.run_checks(path, **kw)
        return {r["check"] for r in res if not r["ok"]}

    def test_missing_file_fails(self):
        self.assertEqual(self.failed(str(self.dir / "nope.md")), {"exists"})

    def test_directory_fails(self):
        self.assertIn("exists", self.failed(str(self.dir)))

    def test_empty_file_fails(self):
        self.assertIn("non_empty", self.failed(self.f("")))

    def test_truncated_mid_line_fails(self):
        self.assertIn("final_newline", self.failed(self.f("1. a\n2. b\n3. par")))

    def test_good_file_passes(self):
        self.assertEqual(self.failed(self.f("# t\nbody\n")), set())

    def test_full_numbered_passes(self):
        self.assertEqual(self.failed(self.f(numbered(1000)), numbered=1000), set())

    def test_numbered_stopped_early_fails_and_names_the_line(self):
        path = self.f(numbered(627))
        res, _ = ac.run_checks(path, numbered=1000)
        bad = [r for r in res if r["check"] == "numbered"][0]
        self.assertFalse(bad["ok"])
        self.assertIn("627", bad["detail"])

    def test_numbered_gap_fails(self):
        self.assertIn("numbered", self.failed(self.f("1. a\n2. b\n4. d\n"), numbered=3))

    def test_numbered_too_many_fails(self):
        self.assertIn("numbered", self.failed(self.f(numbered(5)), numbered=3))

    def test_line_bounds(self):
        p = self.f(numbered(10))
        self.assertEqual(self.failed(p, min_lines=10, max_lines=10), set())
        self.assertIn("min_lines", self.failed(p, min_lines=11))
        self.assertIn("max_lines", self.failed(p, max_lines=9))

    def test_contains_and_forbid(self):
        p = self.f("hello <!-- unit:U01 -->\n")
        self.assertEqual(self.failed(p, contains=["unit:U01"]), set())
        self.assertIn("contains", self.failed(p, contains=["unit:U02"]))
        self.assertIn("forbid", self.failed(p, forbid=["hello"]))

    def test_tool_call_markup_in_file_fails(self):
        self.assertIn("forbid", self.failed(self.f('<tool_call>{"name":"write"}</tool_call>\n')))

    def test_sha256_reported(self):
        _, info = ac.run_checks(self.f("x\n"))
        self.assertEqual(len(info["sha256"]), 64)

    def test_main_exit_codes(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(ac.main([self.f(numbered(3)), "--numbered", "3"]), 0)
            self.assertEqual(ac.main([self.f(numbered(2), "b.md"), "--numbered", "3"]), 1)
        self.assertIn("FAIL numbered", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
