import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kbcheck  # noqa: E402

REAL = Path(__file__).resolve().parents[2]


def write(root, relpath, text):
    p = Path(root) / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def doc(root, relpath, did, status="draft", body="body\n", extra=""):
    """Write a doc with frontmatter and link it from the INDEX.md beside it."""
    text = f"---\nid: {did}\ntype: note\nstatus: {status}\ntldr: t\n{extra}---\n{body}"
    p = write(root, relpath, text)
    idx = p.parent / "INDEX.md"
    line = f"- [{did}]({p.name})\n"
    cur = idx.read_text(encoding="utf-8") if idx.exists() else "# index\n"
    if line not in cur:
        idx.write_text(cur + line, encoding="utf-8")
    return p


def make_repo(tmp):
    root = Path(tmp)
    shutil.copytree(REAL / "schemas", root / "schemas")
    shutil.copytree(REAL / "knowledge" / "registry", root / "knowledge" / "registry")
    write(root, "AGENTS.md", "# a\n")
    write(root, "scripts/tests/test_kbcheck.py", "# placeholder\n")
    doc(root, "knowledge/09-agent-execution/phases/REGISTRY.md", "PH-REG", "draft")
    doc(root, "knowledge/09-agent-execution/phases/P00a.md", "PH-P00a", "draft")
    doc(root, "knowledge/09-agent-execution/phases/P00b.md", "PH-P00b", "draft")
    return root


def codes(findings):
    return {x.split()[0] for x in findings}


def jload(root, name):
    return json.loads((root / "knowledge/registry" / name).read_text(encoding="utf-8"))


def jsave(root, name, obj):
    (root / "knowledge/registry" / name).write_text(json.dumps(obj, indent=1), encoding="utf-8")


def claim(n, ws="R1", **kw):
    c = {"claim_id": f"{ws}-CLM-{n:03d}", "workstream": ws, "critical": False, "claim": "c",
         "source_url": "https://example.com/x", "source_type": "official_documentation",
         "published_at": None, "accessed_at": "2026-11-15", "snapshot": None,
         "verification": "verified", "validation_method": "read page", "confidence_rationale": "primary",
         "contradictions": [], "implications": [], "reviewer": None}
    c.update(kw)
    return c


def complete_p00b(root):
    """Turn the empty registries into a fully consistent, completed P00b."""
    ws, dl, claims = jload(root, "workstreams.json"), jload(root, "deliverables.json"), []
    for w in ws:
        n = int(w["id"][1:])
        w["status"] = "COMPLETE"
        doc(root, w["outcome_path"].replace("knowledge/", "knowledge/", 1), f"OUT-{w['id']}", "validated")
        for t in w["human_tasks"]:
            t["done"] = True
        if w["requires_claims"]:
            claims.append(claim(1, w["id"], critical=(w["id"] == "R1"),
                                reviewer="human" if w["id"] == "R1" else None, snapshot="snap.html"))
    for d in dl:
        d["maturity"] = d["required_maturity"]
        doc(root, d["path"], "PH-REG" if d["id"] == "D14" else f"DOC-{d['id']}", d["maturity"])
        if any(r in [f"R{i}" for i in range(1, 9)] for r in d["depends_on"]):
            d["evidence"] = [f"{[r for r in d['depends_on'] if int(r[1:]) <= 8][0]}-CLM-001"]
    jsave(root, "workstreams.json", ws)
    jsave(root, "deliverables.json", dl)
    (root / "knowledge/registry/claims.jsonl").write_text("\n".join(json.dumps(c) for c in claims) + "\n", encoding="utf-8")
    kbcheck.main(["--root", str(root), "status", "--write"])


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = make_repo(self.tmp.name)
        kbcheck.main(["--root", str(self.root), "status", "--write"])

    def tearDown(self):
        self.tmp.cleanup()

    def v(self):
        return kbcheck.validate(self.root)


class TestBaseline(Base):
    def test_fresh_fixture_is_clean(self):
        self.assertEqual(self.v(), [])

    def test_real_repo_validates(self):
        if not (REAL / "knowledge").exists():
            self.skipTest("not running inside the knowledge repo")
        self.assertEqual(kbcheck.validate(REAL), [])


class TestMarkdownRules(Base):
    def test_merge_marker(self):
        write(self.root, "README.md", "a\n<<<<<<< HEAD\nb\n")
        self.assertIn("E-MARKER", codes(self.v()))

    def test_missing_frontmatter(self):
        write(self.root, "knowledge/x.md", "no fm\n")
        self.assertIn("E-FM", codes(self.v()))

    def test_bad_status_and_missing_tldr(self):
        write(self.root, "knowledge/x.md", "---\nid: X\ntype: n\nstatus: done\n---\n")
        f = self.v()
        self.assertTrue(any("status" in x for x in f) and any("'tldr'" in x for x in f))

    def test_duplicate_id(self):
        doc(self.root, "knowledge/a.md", "DUP")
        doc(self.root, "knowledge/b.md", "DUP")
        self.assertIn("E-ID", codes(self.v()))

    def test_unindexed_doc(self):
        write(self.root, "knowledge/c.md", "---\nid: C\ntype: n\nstatus: draft\ntldr: t\n---\n")
        self.assertIn("E-INDEX", codes(self.v()))

    def test_double_indexed_doc(self):
        doc(self.root, "knowledge/a.md", "A")
        (self.root / "knowledge/INDEX.md").write_text("- [A](a.md)\n- [A again](a.md)\n")
        self.assertTrue(any("2 times" in x for x in self.v()))

    def test_dead_link(self):
        write(self.root, "knowledge/INDEX.md", "- [x](missing.md)\n")
        self.assertIn("E-LINK", codes(self.v()))

    def test_link_in_code_span_ignored(self):
        write(self.root, "knowledge/INDEX.md", "`- [id](path)` example\n")
        self.assertEqual(self.v(), [])

    def test_oversize_doc(self):
        doc(self.root, "knowledge/big.md", "BIG", body="line\n" * 200)
        self.assertIn("E-SIZE", codes(self.v()))

    def test_agents_too_long(self):
        write(self.root, "AGENTS.md", "x\n" * 30)
        self.assertIn("E-AGENTS", codes(self.v()))

    def test_role_card_missing_labels(self):
        doc(self.root, "knowledge/09-agent-execution/roles/r.md", "ROLE-r", extra="")
        p = self.root / "knowledge/09-agent-execution/roles/r.md"
        p.write_text(p.read_text().replace("type: note", "type: role-card"))
        self.assertIn("E-ROLE", codes(self.v()))

    def test_depends_on_unknown(self):
        doc(self.root, "knowledge/a.md", "A", extra="depends_on: [NOPE]\n")
        self.assertIn("E-DEP", codes(self.v()))

    def test_validated_doc_cannot_depend_on_placeholder(self):
        doc(self.root, "knowledge/p.md", "P", "placeholder")
        doc(self.root, "knowledge/a.md", "A", "validated", extra="depends_on: [P]\n")
        self.assertIn("E-DEP-RANK", codes(self.v()))

    def test_draft_doc_may_depend_on_placeholder(self):
        doc(self.root, "knowledge/p.md", "P", "placeholder")
        doc(self.root, "knowledge/a.md", "A", "draft", extra="depends_on: [P]\n")
        self.assertEqual(self.v(), [])


class TestRegistries(Base):
    def test_schema_violation(self):
        ws = jload(self.root, "workstreams.json")
        ws[0]["id"] = "R11"
        del ws[1]["scope"]
        jsave(self.root, "workstreams.json", ws)
        self.assertIn("E-SCHEMA", codes(self.v()))

    def test_bad_json(self):
        (self.root / "knowledge/registry/phases.json").write_text("{nope")
        self.assertIn("E-REG-JSON", codes(self.v()))

    def test_missing_registry(self):
        (self.root / "knowledge/registry/deliverables.json").unlink()
        self.assertIn("E-REG-MISSING", codes(self.v()))

    def test_deliverable_maturity_without_file(self):
        dl = jload(self.root, "deliverables.json")
        dl[0]["maturity"] = "draft"
        jsave(self.root, "deliverables.json", dl)
        self.assertIn("E-DELIV", codes(self.v()))

    def test_deliverable_maturity_must_match_doc_status(self):
        dl = jload(self.root, "deliverables.json")
        doc(self.root, dl[1]["path"], "D2DOC", "draft")
        dl[1]["maturity"] = "validated"
        jsave(self.root, "deliverables.json", dl)
        self.assertTrue(any("!= doc status" in x for x in self.v()))

    def test_validated_deliverable_needs_evidence(self):
        dl = jload(self.root, "deliverables.json")
        doc(self.root, dl[1]["path"], "D2DOC", "validated")
        dl[1]["maturity"] = "validated"
        jsave(self.root, "deliverables.json", dl)
        self.assertTrue(any("no evidence" in x for x in self.v()))

    def test_unknown_evidence_ref(self):
        dl = jload(self.root, "deliverables.json")
        dl[0]["evidence"] = ["R1-CLM-999"]
        jsave(self.root, "deliverables.json", dl)
        self.assertIn("E-REF", codes(self.v()))


class TestClaims(Base):
    def put(self, *claims):
        (self.root / "knowledge/registry/claims.jsonl").write_text("\n".join(json.dumps(c) for c in claims) + "\n")

    def test_valid_claim_ok(self):
        self.put(claim(1))
        self.assertEqual(self.v(), [])

    def test_vendor_claim_cannot_be_verified(self):
        self.put(claim(1, source_type="vendor_claim"))
        self.assertIn("E-CLAIM", codes(self.v()))

    def test_verified_needs_method_and_url(self):
        self.put(claim(1, validation_method="", source_url=""))
        self.assertGreaterEqual(len([x for x in self.v() if "E-CLAIM" in x]), 2)

    def test_critical_needs_reviewer_and_snapshot(self):
        self.put(claim(1, critical=True))
        f = " ".join(self.v())
        self.assertIn("reviewer", f)
        self.assertIn("snapshot", f)

    def test_disputed_needs_contradictions(self):
        self.put(claim(1, verification="disputed"))
        self.assertIn("E-CLAIM", codes(self.v()))

    def test_duplicate_and_prefix(self):
        self.put(claim(1), claim(1), dict(claim(2), claim_id="R2-CLM-002"))
        f = " ".join(self.v())
        self.assertIn("duplicate", f)
        self.assertIn("id prefix", f)

    def test_bad_date(self):
        self.put(claim(1, accessed_at="15/11/2026"))
        self.assertTrue(codes(self.v()) & {"E-CLAIM", "E-SCHEMA"})

    def test_invalid_json_line(self):
        (self.root / "knowledge/registry/claims.jsonl").write_text("{bad\n")
        self.assertIn("E-CLAIM-JSON", codes(self.v()))


class TestPhasesAndGates(Base):
    def set_phase(self, pid, status):
        ph = jload(self.root, "phases.json")
        next(p for p in ph if p["id"] == pid)["status"] = status
        jsave(self.root, "phases.json", ph)

    def test_cannot_skip_phase_order(self):
        self.set_phase("P01", "IN_PROGRESS")
        self.assertIn("E-PHASE-ORDER", codes(self.v()))

    def test_approved_needs_human_file(self):
        self.set_phase("P00a", "APPROVED")
        kbcheck.main(["--root", str(self.root), "status", "--write"])
        self.assertIn("E-APPROVAL", codes(self.v()))

    def test_approval_file_must_be_complete(self):
        self.set_phase("P00a", "APPROVED")
        write(self.root, "knowledge/00-governance/approvals/P00a.md", "decision: APPROVED\n")
        kbcheck.main(["--root", str(self.root), "status", "--write"])
        self.assertIn("E-APPROVAL", codes(self.v()))

    def test_p00a_approved_with_valid_file(self):
        self.set_phase("P00a", "APPROVED")
        write(self.root, "knowledge/00-governance/approvals/P00a.md",
              "decision: APPROVED\napprover: Owner\ndate: 2026-11-16\n")
        kbcheck.main(["--root", str(self.root), "status", "--write"])
        self.assertEqual(self.v(), [])

    def test_stub_phase_cannot_reach_review(self):
        self.set_phase("P00a", "APPROVED")
        self.set_phase("P00b", "APPROVED")
        self.set_phase("P01", "READY_FOR_REVIEW")
        self.assertIn("E-PHASE-STUB", codes(self.v()))

    def test_gate_p00a_passes_on_clean_repo(self):
        self.assertEqual(kbcheck.gate(self.root, "P00a"), [])

    def test_gate_p00a_detects_stale_status(self):
        (self.root / "knowledge/STATUS.md").write_text("old\n")
        self.assertIn("E-STATUS", codes(kbcheck.gate(self.root, "P00a")))

    def test_ready_for_review_runs_gate(self):
        self.set_phase("P00a", "READY_FOR_REVIEW")
        kbcheck.main(["--root", str(self.root), "status", "--write"])
        self.assertEqual(self.v(), [])
        (self.root / "scripts/tests/test_kbcheck.py").unlink()
        self.assertIn("E-GATE", codes(self.v()))

    def test_stub_gate_returns_none(self):
        self.assertIsNone(kbcheck.gate(self.root, "P03"))

    def test_EMPTY_RESEARCH_CANNOT_PASS_P00b(self):
        f = kbcheck.gate(self.root, "P00b")
        self.assertTrue(any("R1 is NOT_STARTED" in x for x in f))
        self.assertTrue(any("D1 is placeholder" in x for x in f))

    def test_empty_research_cannot_be_marked_ready(self):
        self.set_phase("P00a", "APPROVED")
        write(self.root, "knowledge/00-governance/approvals/P00a.md",
              "decision: APPROVED\napprover: O\ndate: 2026-11-16\n")
        self.set_phase("P00b", "READY_FOR_REVIEW")
        kbcheck.main(["--root", str(self.root), "status", "--write"])
        self.assertIn("E-GATE", codes(self.v()))

    def test_false_completion_one_track_without_evidence(self):
        ws = jload(self.root, "workstreams.json")
        ws[0]["status"] = "COMPLETE"
        jsave(self.root, "workstreams.json", ws)
        f = " ".join(self.v())
        self.assertIn("outcome doc missing", f)
        self.assertIn("no verified claims", f)

    def test_complete_p00b_passes_gate(self):
        complete_p00b(self.root)
        self.assertEqual(kbcheck.gate(self.root, "P00b"), [])

    def test_p00b_fails_if_human_task_not_done(self):
        complete_p00b(self.root)
        ws = jload(self.root, "workstreams.json")
        ws[1]["human_tasks"][0]["done"] = False
        jsave(self.root, "workstreams.json", ws)
        self.assertIn("E-WS-COMPLETE", codes(kbcheck.gate(self.root, "P00b")))

    def test_p00b_fails_if_cited_critical_claim_unverified(self):
        complete_p00b(self.root)
        lines = (self.root / "knowledge/registry/claims.jsonl").read_text().splitlines()
        c = json.loads(lines[0])
        c["verification"] = "hypothesis"
        lines[0] = json.dumps(c)
        (self.root / "knowledge/registry/claims.jsonl").write_text("\n".join(lines) + "\n")
        kbcheck.main(["--root", str(self.root), "status", "--write"])
        f = kbcheck.gate(self.root, "P00b")
        self.assertTrue(any("unverified critical" in x or "critical claim" in x for x in f))

    def test_p00b_fails_if_blocker_open(self):
        complete_p00b(self.root)
        ws = jload(self.root, "workstreams.json")
        ws[2]["blockers"] = ["no interview access"]
        jsave(self.root, "workstreams.json", ws)
        self.assertIn("E-WS-COMPLETE", codes(kbcheck.gate(self.root, "P00b")))


class TestStatusAndTokens(Base):
    def test_status_content_for_empty_research(self):
        text = (self.root / "knowledge/STATUS.md").read_text()
        self.assertIn("R1-R10: NOT_STARTED 10", text)
        self.assertIn("D1-D18 at required maturity: 0/18", text)
        self.assertIn("Application implementation: NOT APPROVED", text)

    def test_status_check_detects_staleness(self):
        self.assertEqual(kbcheck.main(["--root", str(self.root), "status", "--check"]), 0)
        (self.root / "knowledge/STATUS.md").write_text("x\n")
        self.assertEqual(kbcheck.main(["--root", str(self.root), "status", "--check"]), 1)

    def test_validate_record_writes_state(self):
        rc = kbcheck.main(["--root", str(self.root), "validate", "--record"])
        self.assertEqual(rc, 0)
        self.assertEqual(jload(self.root, "state.json")["last_validation"]["result"], "PASS")

    def test_tokens_runs(self):
        doc(self.root, "knowledge/09-agent-execution/roles/x.md", "ROLE-x",
            body="Context budget (TUNABLE): ~8k tokens\n")
        self.assertEqual(kbcheck.main(["--root", str(self.root), "tokens", "--window", "32000"]), 0)


class TestSchemaSubset(unittest.TestCase):
    def test_types_enum_pattern_required(self):
        s = {"type": "object", "required": ["a"], "additionalProperties": False,
             "properties": {"a": {"type": "string", "pattern": "^x"}, "b": {"enum": [1, 2]}}}
        self.assertEqual(kbcheck.schema_errors({"a": "xy", "b": 1}, s), [])
        self.assertEqual(len(kbcheck.schema_errors({"b": 3, "c": 1}, s)), 3)
        self.assertEqual(len(kbcheck.schema_errors({"a": 5}, s)), 1)
        self.assertEqual(len(kbcheck.schema_errors({"a": True}, {"type": "integer"})), 1)


if __name__ == "__main__":
    unittest.main()
