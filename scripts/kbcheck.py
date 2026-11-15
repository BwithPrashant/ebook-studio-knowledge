#!/usr/bin/env python3
"""kbcheck - dependency-free validators for the ebook-studio knowledge repo.

Run from the knowledge repo root:
  python3 scripts/kbcheck.py validate [--record]
  python3 scripts/kbcheck.py gate P00a|P00b
  python3 scripts/kbcheck.py status [--write|--check]
  python3 scripts/kbcheck.py tokens [--window N]
Exit codes: 0 ok, 1 findings, 2 usage / gate not implemented.
Token counts are ESTIMATES (characters / 4); measure with your model's tokenizer.
"""
import argparse
import datetime
import json
import math
import re
import sys
from pathlib import Path

VERSION = "0.1"
DOC_RANK = {"placeholder": 0, "draft": 1, "validated": 2, "approved": 3}
EXCLUDED_DIRS = {"sources", "poc", "runs", "templates", "approvals"}
EXEMPT_NAMES = {"INDEX.md", "STATUS.md"}
REQUIRED_FM = ("id", "type", "status", "tldr")
ROLE_LABELS = ("Must load:", "Never load:", "Context budget", "Done when:", "Must not:")
MAX_LINES, MAX_TOKENS, AGENTS_MAX_LINES, TLDR_MAX_CHARS = 150, 2000, 25, 300
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REGISTRIES = (
    ("workstreams", "workstreams.json", "workstream"),
    ("deliverables", "deliverables.json", "deliverable"),
    ("phases", "phases.json", "phase"),
)


# ---------------------------------------------------------------- helpers
def est_tokens(text):
    return math.ceil(len(text) / 4)


def read(path):
    return Path(path).read_text(encoding="utf-8")


def rel(root, path):
    return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()


def valid_date(s):
    if not isinstance(s, str) or not DATE_RE.match(s):
        return False
    try:
        datetime.date.fromisoformat(s)
        return True
    except ValueError:
        return False


def frontmatter(text):
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    fm = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key, val = key.strip(), val.strip()
        if val.startswith("[") and val.endswith("]"):
            val = [x.strip() for x in val[1:-1].split(",") if x.strip()]
        fm[key] = val
    return fm


def doc_status(path):
    p = Path(path)
    if not p.exists():
        return None
    fm = frontmatter(read(p))
    return fm.get("status") if fm else None


def strip_code(text):
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def knowledge_docs(root):
    kd = Path(root) / "knowledge"
    out = []
    for p in sorted(kd.rglob("*.md")):
        parts = p.relative_to(kd).parts[:-1]
        if any(part in EXCLUDED_DIRS for part in parts):
            continue
        out.append(p)
    return out


def is_exempt(p):
    return p.name in EXEMPT_NAMES


# ------------------------------------------------- mini JSON-schema subset
def _type_ok(v, t):
    return {
        "string": isinstance(v, str),
        "integer": isinstance(v, int) and not isinstance(v, bool),
        "boolean": isinstance(v, bool),
        "array": isinstance(v, list),
        "object": isinstance(v, dict),
        "null": v is None,
    }[t]


def schema_errors(inst, sch, path="$"):
    errs = []
    t = sch.get("type")
    if t is not None:
        ts = t if isinstance(t, list) else [t]
        if not any(_type_ok(inst, x) for x in ts):
            return [f"{path}: expected {'|'.join(ts)}, got {type(inst).__name__}"]
    if "enum" in sch and inst not in sch["enum"]:
        errs.append(f"{path}: {inst!r} not in {sch['enum']}")
    if isinstance(inst, str):
        if "pattern" in sch and not re.search(sch["pattern"], inst):
            errs.append(f"{path}: {inst!r} does not match {sch['pattern']}")
        if len(inst) < sch.get("minLength", 0):
            errs.append(f"{path}: shorter than {sch['minLength']}")
    if isinstance(inst, list):
        if len(inst) < sch.get("minItems", 0):
            errs.append(f"{path}: fewer than {sch['minItems']} items")
        if "items" in sch:
            for i, x in enumerate(inst):
                errs += schema_errors(x, sch["items"], f"{path}[{i}]")
    if isinstance(inst, dict):
        for k in sch.get("required", []):
            if k not in inst:
                errs.append(f"{path}: missing '{k}'")
        props = sch.get("properties", {})
        if sch.get("additionalProperties") is False:
            for k in inst:
                if k not in props:
                    errs.append(f"{path}: unknown key '{k}'")
        for k, sub in props.items():
            if k in inst:
                errs += schema_errors(inst[k], sub, f"{path}.{k}")
    return errs


# -------------------------------------------------------------- registries
def load_registries(root):
    root = Path(root)
    reg, sch = root / "knowledge" / "registry", root / "schemas"
    findings, data = [], {}
    for key, fname, sname in REGISTRIES:
        data[key] = []
        path = reg / fname
        if not path.exists():
            findings.append(f"E-REG-MISSING knowledge/registry/{fname}: file not found")
            continue
        schema = _load_schema(sch, sname, findings)
        try:
            items = json.loads(read(path))
        except json.JSONDecodeError as e:
            findings.append(f"E-REG-JSON knowledge/registry/{fname}: {e}")
            continue
        if not isinstance(items, list):
            findings.append(f"E-REG-SHAPE knowledge/registry/{fname}: top level must be a list")
            continue
        for i, it in enumerate(items):
            errs = schema_errors(it, schema, f"[{i}]") if schema else []
            for e in errs:
                findings.append(f"E-SCHEMA knowledge/registry/{fname}: {e}")
            if not errs and isinstance(it, dict):
                data[key].append(it)
    data["claims"] = []
    cpath = reg / "claims.jsonl"
    cschema = _load_schema(sch, "claim", findings)
    if cpath.exists():
        for n, line in enumerate(read(cpath).splitlines(), 1):
            if not line.strip():
                continue
            try:
                it = json.loads(line)
            except json.JSONDecodeError as e:
                findings.append(f"E-CLAIM-JSON knowledge/registry/claims.jsonl:{n}: {e}")
                continue
            errs = schema_errors(it, cschema, f"line {n}") if cschema else []
            for e in errs:
                findings.append(f"E-SCHEMA knowledge/registry/claims.jsonl: {e}")
            if not errs:
                data["claims"].append(it)
    else:
        findings.append("E-REG-MISSING knowledge/registry/claims.jsonl: file not found")
    return data, findings


def _load_schema(sch_dir, name, findings):
    p = sch_dir / f"{name}.schema.json"
    if not p.exists():
        findings.append(f"E-SCHEMA-MISSING schemas/{name}.schema.json: file not found")
        return None
    return json.loads(read(p))


def load_state(root):
    p = Path(root) / "knowledge" / "registry" / "state.json"
    if not p.exists():
        return {}
    try:
        return json.loads(read(p))
    except json.JSONDecodeError:
        return {}


# ------------------------------------------------------------------ checks
def check_markers(root):
    f = []
    for p in sorted(Path(root).rglob("*")):
        if p.suffix not in (".md", ".json", ".jsonl") or ".git" in p.parts or "node_modules" in p.parts:
            continue
        for n, line in enumerate(read(p).splitlines(), 1):
            if line.startswith("<<<<<<<") or line.startswith(">>>>>>>"):
                f.append(f"E-MARKER {rel(root, p)}:{n}: merge-conflict marker")
    return f


def check_agents(root):
    p = Path(root) / "AGENTS.md"
    if not p.exists():
        return ["E-AGENTS AGENTS.md: missing"]
    n = len(read(p).splitlines())
    if n > AGENTS_MAX_LINES:
        return [f"E-AGENTS AGENTS.md: {n} lines, max {AGENTS_MAX_LINES}"]
    return []


def known_ids(root, data, doc_ids):
    ids = set(doc_ids)
    for key in ("workstreams", "deliverables"):
        ids |= {x["id"] for x in data[key]}
    ids |= {c["claim_id"] for c in data["claims"]}
    return ids


def check_docs(root, data):
    f, ids, by_id, deps = [], {}, {}, []
    for p in knowledge_docs(root):
        if is_exempt(p):
            continue
        r, text = rel(root, p), read(p)
        lines, toks = len(text.splitlines()), est_tokens(text)
        if lines > MAX_LINES or toks > MAX_TOKENS:
            f.append(f"E-SIZE {r}: {lines} lines / ~{toks} tokens (max {MAX_LINES} / {MAX_TOKENS})")
        fm = frontmatter(text)
        if fm is None:
            f.append(f"E-FM {r}: missing frontmatter")
            continue
        for k in REQUIRED_FM:
            if not fm.get(k):
                f.append(f"E-FM {r}: missing '{k}'")
        st = fm.get("status")
        if st and st not in DOC_RANK:
            f.append(f"E-FM {r}: status {st!r} not in {list(DOC_RANK)}")
        if len(str(fm.get("tldr", ""))) > TLDR_MAX_CHARS:
            f.append(f"E-FM {r}: tldr longer than {TLDR_MAX_CHARS} chars")
        did = fm.get("id")
        if did:
            if did in ids:
                f.append(f"E-ID {r}: duplicate id {did} (also {ids[did]})")
            else:
                ids[did] = r
                by_id[did] = st
        d = fm.get("depends_on", [])
        deps.append((r, did, st, [d] if isinstance(d, str) and d else d))
        if "roles" in p.parts and fm.get("type") == "role-card":
            for label in ROLE_LABELS:
                if label not in text:
                    f.append(f"E-ROLE {r}: missing '{label}'")
    known = known_ids(root, data, ids)
    for r, did, st, dlist in deps:
        for dep in dlist or []:
            if dep not in known:
                f.append(f"E-DEP {r}: depends_on {dep} not found")
            elif dep in by_id and DOC_RANK.get(st, 0) >= 2 and DOC_RANK.get(by_id[dep], 0) < DOC_RANK[st]:
                f.append(f"E-DEP-RANK {r}: {st} doc depends on {dep} which is {by_id[dep]}")
    return f


def check_links_and_index(root):
    f, counts = [], {}
    root = Path(root).resolve()
    for p in knowledge_docs(root):
        text = strip_code(read(p))
        for m in LINK_RE.finditer(text):
            tgt = m.group(1).split("#")[0]
            if not tgt or "://" in tgt or tgt.startswith("mailto:"):
                continue
            resolved = (p.parent / tgt).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                continue  # points outside this repo (e.g. ../ebook-studio-app)
            if not resolved.exists():
                f.append(f"E-LINK {rel(root, p)}: dead link {tgt}")
            elif p.name == "INDEX.md":
                counts[resolved] = counts.get(resolved, 0) + 1
    for p in knowledge_docs(root):
        if is_exempt(p):
            continue
        n = counts.get(p.resolve(), 0)
        if n == 0:
            f.append(f"E-INDEX {rel(root, p)}: not linked from any INDEX.md")
        elif n > 1:
            f.append(f"E-INDEX {rel(root, p)}: linked from INDEX.md files {n} times (must be 1)")
    return f


def check_claims(data):
    f, seen = [], set()
    wids = {w["id"] for w in data["workstreams"]}
    for c in data["claims"]:
        cid, loc = c["claim_id"], f"claims.jsonl {c['claim_id']}"
        if cid in seen:
            f.append(f"E-CLAIM {loc}: duplicate claim_id")
        seen.add(cid)
        if not cid.startswith(c["workstream"] + "-CLM-"):
            f.append(f"E-CLAIM {loc}: id prefix must be {c['workstream']}-CLM-")
        if c["workstream"] not in wids:
            f.append(f"E-CLAIM {loc}: unknown workstream {c['workstream']}")
        for k in ("accessed_at", "published_at"):
            if c[k] is not None and not valid_date(c[k]):
                f.append(f"E-CLAIM {loc}: {k} must be YYYY-MM-DD or null")
        v, st = c["verification"], c["source_type"]
        if v == "verified":
            if st == "vendor_claim":
                f.append(f"E-CLAIM {loc}: a vendor_claim source cannot be 'verified'")
            if not c["validation_method"].strip():
                f.append(f"E-CLAIM {loc}: verified needs validation_method")
            if not c["confidence_rationale"].strip():
                f.append(f"E-CLAIM {loc}: verified needs confidence_rationale")
            if not valid_date(c["accessed_at"]):
                f.append(f"E-CLAIM {loc}: verified needs accessed_at date")
            if st != "direct_test" and not c["source_url"]:
                f.append(f"E-CLAIM {loc}: verified needs source_url")
            if c["critical"] and not c["reviewer"]:
                f.append(f"E-CLAIM {loc}: critical verified claim needs reviewer")
            if c["critical"] and st != "direct_test" and not c["snapshot"]:
                f.append(f"E-CLAIM {loc}: critical verified claim needs snapshot")
        if v == "disputed" and not c["contradictions"]:
            f.append(f"E-CLAIM {loc}: disputed needs contradictions")
    return f


def check_workstreams(root, data):
    f, seen = [], set()
    dids = {d["id"] for d in data["deliverables"]}
    for w in data["workstreams"]:
        loc = f"registry {w['id']}"
        if w["id"] in seen:
            f.append(f"E-REF {loc}: duplicate id")
        seen.add(w["id"])
        for o in w["outputs"]:
            if o not in dids:
                f.append(f"E-REF {loc}: output {o} is not a deliverable")
        if w["status"] != "COMPLETE":
            continue
        p = w["outcome_path"]
        st = doc_status(Path(root) / p) if p else None
        if st is None:
            f.append(f"E-WS-COMPLETE {loc}: COMPLETE but outcome doc missing or has no status")
        elif DOC_RANK.get(st, 0) < 2:
            f.append(f"E-WS-COMPLETE {loc}: outcome doc is '{st}', needs validated")
        if w["requires_claims"] and not any(
            c["workstream"] == w["id"] and c["verification"] == "verified" for c in data["claims"]
        ):
            f.append(f"E-WS-COMPLETE {loc}: no verified claims recorded")
        if any(not t["done"] for t in w["human_tasks"]):
            f.append(f"E-WS-COMPLETE {loc}: human task(s) not done")
        if w["blockers"]:
            f.append(f"E-WS-COMPLETE {loc}: COMPLETE with open blockers")
    return f


def check_deliverables(root, data):
    f, seen = [], set()
    wmap = {w["id"]: w for w in data["workstreams"]}
    cmap = {c["claim_id"]: c for c in data["claims"]}
    for d in data["deliverables"]:
        loc = f"registry {d['id']}"
        if d["id"] in seen:
            f.append(f"E-REF {loc}: duplicate id")
        seen.add(d["id"])
        for r in d["depends_on"]:
            if r not in wmap:
                f.append(f"E-REF {loc}: depends_on {r} unknown")
        for cid in d["evidence"]:
            if cid not in cmap:
                f.append(f"E-REF {loc}: evidence {cid} unknown")
        actual = doc_status(Path(root) / d["path"])
        exists = (Path(root) / d["path"]).exists()
        if DOC_RANK[d["maturity"]] >= 1 and not exists:
            f.append(f"E-DELIV {loc}: maturity {d['maturity']} but {d['path']} does not exist")
        if exists and actual != d["maturity"]:
            f.append(f"E-DELIV {loc}: registry maturity {d['maturity']} != doc status {actual}")
        if DOC_RANK[d["maturity"]] >= 2:
            needs = any(wmap[r]["requires_claims"] for r in d["depends_on"] if r in wmap)
            if needs and not d["evidence"]:
                f.append(f"E-DELIV {loc}: {d['maturity']} but no evidence claims cited")
            for cid in d["evidence"]:
                c = cmap.get(cid)
                if c and c["critical"] and c["verification"] != "verified":
                    f.append(f"E-DELIV {loc}: cites critical claim {cid} that is {c['verification']}")
    return f


def read_approval(root, phase):
    p = Path(root) / "knowledge" / "00-governance" / "approvals" / f"{phase}.md"
    if not p.exists():
        return None
    out = {}
    for line in read(p).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip().lower()] = v.strip()
    return out


def status_sync(root, data):
    want = render_status(root, data, load_state(root))
    p = Path(root) / "knowledge" / "STATUS.md"
    if not p.exists() or read(p) != want:
        return ["E-STATUS knowledge/STATUS.md: stale; run: python3 scripts/kbcheck.py status --write"]
    return []


def gate_extra(root, phase, data):
    """Objective gate checks for a phase beyond base validation. None = no gate implemented."""
    f = []
    if phase == "P00a":
        if [w["id"] for w in data["workstreams"]] != [f"R{i}" for i in range(1, 11)]:
            f.append("E-GATE P00a: workstream registry must list exactly R1..R10")
        if [d["id"] for d in data["deliverables"]] != [f"D{i}" for i in range(1, 19)]:
            f.append("E-GATE P00a: deliverable registry must list exactly D1..D18")
        if not (Path(root) / "scripts" / "tests" / "test_kbcheck.py").exists():
            f.append("E-GATE P00a: validator tests missing")
        return f + status_sync(root, data)
    if phase == "P00b":
        cmap = {c["claim_id"]: c for c in data["claims"]}
        for w in data["workstreams"]:
            if w["status"] != "COMPLETE":
                f.append(f"E-GATE P00b: {w['id']} is {w['status']}, not COMPLETE")
        for d in data["deliverables"]:
            if DOC_RANK[d["maturity"]] < DOC_RANK[d["required_maturity"]]:
                f.append(f"E-GATE P00b: {d['id']} is {d['maturity']}, needs {d['required_maturity']}")
            for cid in d["evidence"]:
                c = cmap.get(cid)
                if c and c["critical"] and c["verification"] != "verified":
                    f.append(f"E-GATE P00b: {d['id']} cites unverified critical claim {cid}")
        return f + status_sync(root, data)
    return None


def check_phases(root, data):
    f, ph = [], data["phases"]
    ids = [p["id"] for p in ph]
    if len(ids) != len(set(ids)):
        f.append("E-PHASE registry: duplicate phase id")
    for i, p in enumerate(ph):
        s = p["status"]
        if i > 0 and s != "NOT_STARTED" and ph[i - 1]["status"] != "APPROVED":
            f.append(f"E-PHASE-ORDER {p['id']}: {s} but previous phase {ph[i-1]['id']} is not APPROVED")
        if s in ("READY_FOR_REVIEW", "APPROVED"):
            if not p["contract"] or not (Path(root) / p["contract"]).exists():
                f.append(f"E-PHASE-STUB {p['id']}: {s} but no phase contract file exists")
            else:
                extra = gate_extra(root, p["id"], data)
                if extra is None:
                    f.append(f"E-PHASE-STUB {p['id']}: no automated gate implemented")
                else:
                    f += [f"{x} (needed for {s})" for x in extra]
        if s == "APPROVED":
            a = read_approval(root, p["id"])
            if not a or a.get("decision", "").upper() != "APPROVED" or not a.get("approver") or not valid_date(a.get("date")):
                f.append(f"E-APPROVAL {p['id']}: APPROVED needs approvals/{p['id']}.md with decision: APPROVED, approver, date")
    return f


def validate(root):
    data, f = load_registries(root)
    f += check_markers(root) + check_agents(root)
    f += check_docs(root, data) + check_links_and_index(root)
    f += check_claims(data) + check_workstreams(root, data)
    f += check_deliverables(root, data) + check_phases(root, data)
    return sorted(set(f))


def gate(root, phase):
    data, _ = load_registries(root)
    extra = gate_extra(root, phase, data)
    if extra is None:
        return None
    return sorted(set(validate(root) + extra))


# ------------------------------------------------------------------ status
def render_status(root, data, state):
    ph, ws, dl = data["phases"], data["workstreams"], data["deliverables"]
    cur = next((p for p in ph if p["status"] != "APPROVED"), None)
    counts = {}
    for w in ws:
        counts[w["status"]] = counts.get(w["status"], 0) + 1
    d_ok = sum(1 for d in dl if DOC_RANK[d["maturity"]] >= DOC_RANK[d["required_maturity"]])
    blockers = [f"{w['id']}: {b}" for w in ws for b in w["blockers"]]
    blockers += [f"{p['id']} is {p['status']}" for p in ph if p["status"] in ("BLOCKED", "CHANGES_REQUESTED")]
    dates = [c["accessed_at"] for c in data["claims"] if c["verification"] == "verified" and c["accessed_at"]]
    lv = state.get("last_validation")
    lv_txt = f"{lv['date']} {lv['result']}" if isinstance(lv, dict) else "never recorded"
    approved = {p["id"] for p in ph if p["status"] == "APPROVED"}
    impl = "APPROVED" if {"P00b", "P01", "P02"} <= approved else "NOT APPROVED"
    lines = [
        "# Project Status",
        "<!-- GENERATED by scripts/kbcheck.py status --write. Do not edit by hand. -->",
        f"Phase: {cur['id'] + ' - ' + cur['title'] if cur else 'all phases approved'}",
        f"Phase status: {cur['status'] if cur else 'APPROVED'}",
        "R1-R10: " + (", ".join(f"{s} {n}" for s, n in sorted(counts.items())) or "no registry"),
        f"D1-D18 at required maturity: {d_ok}/{len(dl)}",
        f"Claims: {len(data['claims'])} total, {sum(1 for c in data['claims'] if c['verification'] == 'verified')} verified",
        f"Last verified evidence date: {max(dates) if dates else 'none'}",
        f"Last successful validation: {lv_txt}",
        "Blockers: " + ("; ".join(blockers) if blockers else "none"),
        f"Next: {state.get('next_action', 'not set')}",
        f"Application implementation: {impl}",
    ]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ tokens
def cmd_tokens(root, window):
    data, _ = load_registries(root)
    root = Path(root)
    cur = next((p for p in data["phases"] if p["status"] != "APPROVED"), None)
    base_files = [root / "AGENTS.md", root / "knowledge" / "STATUS.md"]
    if cur and cur["contract"]:
        base_files.append(root / cur["contract"])
    base = sum(est_tokens(read(p)) for p in base_files if p.exists())
    print(f"Estimates (chars/4). Shared L0 (AGENTS + STATUS + current phase contract): ~{base} tokens")
    for card in sorted((root / "knowledge" / "09-agent-execution" / "roles").glob("*.md")):
        text = read(card)
        m = re.search(r"Context budget[^:]*:\s*~?(\d+)k", text)
        budget = int(m.group(1)) * 1000 if m else None
        l0 = base + est_tokens(text)
        line = f"  {card.stem:<12} L0 ~{l0:>5}"
        if budget:
            line += f" | budget {budget} | L0 uses {100 * l0 // budget}%"
            if window:
                line += f" | budget is {100 * budget // window}% of window"
        print(line)
    print("Largest docs:")
    sizes = sorted(((est_tokens(read(p)), rel(root, p)) for p in knowledge_docs(root)), reverse=True)[:8]
    for t, r in sizes:
        print(f"  ~{t:>5}  {r}")


# --------------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(prog="kbcheck", description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("--record", action="store_true", help="on success record date in registry/state.json")
    g = sub.add_parser("gate")
    g.add_argument("phase")
    s = sub.add_parser("status")
    s.add_argument("--write", action="store_true")
    s.add_argument("--check", action="store_true")
    t = sub.add_parser("tokens")
    t.add_argument("--window", type=int, default=0)
    a = ap.parse_args(argv)
    root = Path(a.root)

    if a.cmd == "validate":
        f = validate(root)
        for x in f:
            print(x)
        print(f"{'FAIL' if f else 'OK'}: {len(f)} finding(s)")
        if not f and a.record:
            p = root / "knowledge" / "registry" / "state.json"
            st = load_state(root)
            st["last_validation"] = {"date": datetime.date.today().isoformat(), "result": "PASS"}
            p.write_text(json.dumps(st, indent=1) + "\n", encoding="utf-8")
            print("recorded in knowledge/registry/state.json; now run: status --write")
        return 1 if f else 0
    if a.cmd == "gate":
        f = gate(root, a.phase)
        if f is None:
            print(f"Gate for {a.phase} is not implemented (contract is a stub).")
            return 2
        for x in f:
            print(x)
        print(f"GATE {a.phase}: {'FAIL' if f else 'PASS'} ({len(f)} finding(s)). Human approval is still required.")
        return 1 if f else 0
    if a.cmd == "status":
        data, _ = load_registries(root)
        text = render_status(root, data, load_state(root))
        p = root / "knowledge" / "STATUS.md"
        if a.write:
            p.write_text(text, encoding="utf-8")
            print("wrote knowledge/STATUS.md")
            return 0
        if a.check:
            ok = p.exists() and read(p) == text
            print("STATUS.md is current" if ok else "STATUS.md is stale")
            return 0 if ok else 1
        print(text, end="")
        return 0
    cmd_tokens(root, a.window)
    return 0


if __name__ == "__main__":
    sys.exit(main())
