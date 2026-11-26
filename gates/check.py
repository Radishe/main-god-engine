"""Stage gate checker.

Consumes gates/manifest.json. Exit code IS the verdict: 0 = ALLOWED, 1 = DENIED.
No third-party dependencies; the gate toolchain is independent of the game runtime stack.

Usage:
    python gates/check.py
    python gates/check.py --stage s1
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
MANIFEST = ROOT / "manifest.json"
TESTS_DIR = ROOT / "tests"
PACKAGES_DIR = ROOT / "packages"
VALID_LAYERS = {"invariant", "config_driven", "human_in_loop"}
VALID_STATUS = {"active", "pending"}


def shard_hashes():
    """Return (stored, current) SHA-256 maps for all package shards."""
    import hashlib

    hp = ROOT / "package_hashes.json"
    stored = {}
    if hp.is_file():
        try:
            stored = json.loads(hp.read_text(encoding="utf-8")).get("shards", {})
        except (OSError, ValueError):
            stored = {}
    current = {}
    for p in PACKAGES_DIR.glob("*.json"):
        current[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return stored, current


def verify_shards():
    """Return (ok, detail). A changed shard is a protected-path violation."""
    stored, current = shard_hashes()
    if not stored:
        return False, "package_hashes.json missing or empty (run --write-package-hashes)"
    changed = [n for n, h in current.items() if stored.get(n) != h]
    missing = [n for n in stored if n not in current]
    if changed or missing:
        return False, "shard drift: changed=%s missing=%s" % (
            ",".join(changed) or "none", ",".join(missing) or "none")
    return True, "%d shards match recorded hashes" % len(current)


def write_shard_hashes():
    import hashlib

    _, current = shard_hashes()
    hp = ROOT / "package_hashes.json"
    payload = {
        "$comment": "Maintainer-owned. Regenerate with check.py --write-package-hashes after an approved shard change. Agents cannot edit shards; this file detects tampering.",
        "version": 1,
        "date": "2026-11-25",
        "shards": current,
    }
    hp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PACKAGE HASHES written: %s (%d shards)" % (hp.name, len(current)))
    return 0


def load_manifest():
    with MANIFEST.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def check(data, stage):
    stages = data["stages"]
    if stage:
        if stage not in stages:
            return ["unknown stage: %s" % stage], {}
        selected = {stage: stages[stage]}
    else:
        selected = stages

    errors = []
    seen = {}
    total = 0
    pending_tests = 0
    missing = []
    by_layer = {"invariant": 0, "config_driven": 0, "human_in_loop": 0}

    for sname, gates in selected.items():
        for gate in gates:
            gname = gate["gate"]
            layer = gate["layer"]
            status = gate["status"]
            depends = gate.get("depends_on", [])
            tests = gate["tests"]

            if layer not in VALID_LAYERS:
                errors.append("%s/%s: invalid layer %r" % (sname, gname, layer))
            if status not in VALID_STATUS:
                errors.append("%s/%s: invalid status %r" % (sname, gname, status))
            if status == "pending" and not depends:
                errors.append("%s/%s: pending gate must declare depends_on" % (sname, gname))
            if layer == "config_driven" and status != "pending":
                errors.append("%s/%s: config_driven gate must stay pending until config is fixed" % (sname, gname))
            if layer == "invariant" and status != "active":
                errors.append("%s/%s: invariant gate must be active" % (sname, gname))

            for tid in tests:
                total += 1
                if tid in seen:
                    errors.append("duplicate test id %s (%s and %s)" % (tid, seen[tid], sname + "/" + gname))
                seen[tid] = sname + "/" + gname

                if layer in by_layer:
                    by_layer[layer] += 1
                if status == "pending":
                    pending_tests += 1
                else:
                    expected = TESTS_DIR / (tid.lower() + ".py")
                    if not expected.is_file():
                        missing.append(str(expected.relative_to(ROOT)))

    stats = {
        "total": total,
        "pending": pending_tests,
        "missing": len(missing),
        "missing_sample": missing[:5],
        "by_layer": by_layer,
    }
    return errors, stats


def judge_test(path, tid, timeout=30):
    """Run one test and judge it strictly.

    A test is PASS only when ALL hold: exit code == 0, exactly one TEST line,
    that line's id == tid, status == PASS. This closes the forged-output and
    'last line wins' loopholes found in the four-dimension audit.
    """
    import subprocess

    try:
        proc = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True, text=True, encoding="utf-8", timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return "FAIL", "TEST %s FAIL timeout>%ds" % (tid, timeout)

    test_lines = [l for l in (proc.stdout or "").splitlines() if l.startswith("TEST ")]
    if len(test_lines) != 1:
        return "FAIL", ("TEST %s FAIL expected 1 TEST line, got %d; exit=%d" % (
            tid, len(test_lines), proc.returncode))
    line = test_lines[0]
    parts = line.split(" ", 3)
    if len(parts) < 3 or parts[1] != tid:
        return "FAIL", "TEST %s FAIL id mismatch in %r" % (tid, line)
    status = parts[2]
    if status == "PASS" and proc.returncode != 0:
        return "FAIL", "%s -> exit=%d contradicts PASS" % (line, proc.returncode)
    if status not in ("PASS", "FAIL", "PENDING"):
        return "FAIL", "%s has unknown status" % line
    return status, line


def run_tests(data, stage):
    """Execute every existing test file for the selected stage."""
    stages = {stage: data["stages"][stage]} if stage else data["stages"]
    counts = {"PASS": 0, "FAIL": 0, "PENDING": 0, "MISSING": 0}
    lines, detail = [], []
    for gates in stages.values():
        for gate in gates:
            pending_gate = gate["status"] == "pending"
            for tid in gate["tests"]:
                path = TESTS_DIR / (tid.lower() + ".py")
                if not path.is_file():
                    counts["PENDING" if pending_gate else "MISSING"] += 1
                    continue
                status, line = judge_test(path, tid)
                counts[status] += 1
                lines.append(line)
                detail.append((tid, status, line))
    return counts, lines, detail


def _improve_evidence(tid):
    """Return a reason string when a newly-green test lacks required evidence.

    Empty string means no rule applies or evidence is present. Red-team finding:
    FAIL->PASS counted as 'improved' was unguarded, so a fake test could claim
    the golden path. Critical gates now must call the real engine and be covered
    by a mutation recipe before their green is accepted.
    """
    rp = ROOT / "evidence_rules.json"
    if not rp.is_file():
        return "evidence_rules.json missing"
    try:
        rules = json.loads(rp.read_text(encoding="utf-8")).get("require_evidence_on_improve", [])
    except (OSError, ValueError):
        return "evidence_rules.json unreadable"
    rule = next((r for r in rules if r.get("test") == tid), None)
    if not rule:
        return ""

    path = TESTS_DIR / (tid.lower() + ".py")
    if not path.is_file():
        return "test file missing"
    text = path.read_text(encoding="utf-8", errors="ignore")
    for needle in rule.get("must_call", []):
        if needle not in text:
            return "no real call to %r" % needle
    if rule.get("must_have_mutation_guard"):
        mp = ROOT / "mutation_recipes.json"
        try:
            guards = [r.get("guard") for r in json.loads(
                mp.read_text(encoding="utf-8")).get("recipes", [])]
        except (OSError, ValueError):
            return "mutation recipes unreadable"
        if tid.lower() not in guards:
            return "no mutation recipe guards this test"
    return ""


def baseline_report(data, write=False):
    """Ratchet: a test that was PASS must never go red. Red may only shrink.

    Red phase is legitimate, so a plain --run exit=1 cannot block CI. This mode
    runs every test and compares against the recorded baseline: regression from
    PASS is denied, improvement is reported, new red tests are allowed but shown.
    """
    path = ROOT / "baseline.json"
    _, _, detail = run_tests(data, None)
    current = {tid: status for tid, status, _ in detail}

    if write:
        payload = {
            "$comment": "Green-rate ratchet. Auto-generated by check.py --write-baseline. Maintainer-owned.",
            "version": 1,
            "date": "2026-11-25",
            "tests": current,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("BASELINE written: %s (%d tests, PASS=%d)" % (
            path.relative_to(ROOT.parent), len(current),
            sum(1 for s in current.values() if s == "PASS")))
        return 0

    if not path.is_file():
        print("BASELINE missing: %s (run --write-baseline first)" % path.name)
        return 1
    try:
        baseline = json.loads(path.read_text(encoding="utf-8"))["tests"]
    except (OSError, ValueError, KeyError) as exc:
        print("BASELINE unreadable: %s" % exc)
        return 1

    regressions, improved, new_red, missing, unproven = [], [], [], [], []
    for tid, old in baseline.items():
        now = current.get(tid, "MISSING")
        if old == "PASS" and now != "PASS":
            regressions.append("%s %s->%s" % (tid, old, now))
        elif old != "PASS" and now == "PASS":
            improved.append(tid)
            why = _improve_evidence(tid)
            if why:
                unproven.append("%s (%s)" % (tid, why))
        if now == "MISSING":
            missing.append(tid)
    for tid, now in current.items():
        if tid not in baseline and now != "PASS":
            new_red.append("%s(%s)" % (tid, now))

    print("BASELINE ratchet  recorded=%d current=%d" % (len(baseline), len(current)))
    print("  regressions=%d  %s" % (len(regressions), ", ".join(regressions) or "none"))
    print("  improved=%d    %s" % (len(improved), ", ".join(improved) or "none"))
    print("  unproven=%d    %s" % (len(unproven), ", ".join(unproven) or "none"))
    print("  new_red=%d     %s" % (len(new_red), ", ".join(new_red) or "none"))
    print("  missing=%d     %s" % (len(missing), ", ".join(missing) or "none"))

    ok = not regressions and not missing and not unproven
    print("BASELINE_EXIT: %s" % ("ALLOWED" if ok else "DENIED"))
    if improved and not unproven:
        print("note: %d test(s) improved with evidence; run --write-baseline to ratchet forward" % len(improved))
    if not ok:
        print("reason: green regression, missing test, or an improved test without required evidence")
    return 0 if ok else 1


def coverage_report():
    """Answer: can we hand this to parallel agents without drift?"""
    path = ROOT / "coverage.json"
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        print("CONTRACT COVERAGE  matrix=UNREADABLE  %s" % exc)
        print("HANDOFF: NOT_READY")
        return 1

    contracts = data["contracts"]
    effective = [c for c in contracts if not c.get("exempt")]
    exempt = len(contracts) - len(effective)

    def has_code(c):
        for t in c["tests"]:
            p = TESTS_DIR / (t.lower() + ".py")
            if p.is_file() and p.stat().st_size >= 200:
                text = p.read_text(encoding="utf-8", errors="ignore")
                if "SPEC" in text or "assert" in text or "emit(" in text:
                    return True
        return False

    gaps = [c for c in effective if not c["tests"]]
    with_spec = [c for c in effective if c["tests"]]
    with_code = [c for c in with_spec if has_code(c)]
    golden = [c for c in effective if c["kind"] == "golden"]
    golden_code = [c for c in golden if has_code(c)]

    print("CONTRACT COVERAGE  total=%d exempt=%d effective=%d" % (
        len(contracts), exempt, len(effective)))
    print("spec_covered=%d/%d  code_covered=%d/%d  gaps=%d" % (
        len(with_spec), len(effective), len(with_code), len(with_spec), len(gaps)))
    print("golden_with_code=%d/%d" % (len(golden_code), len(golden)))
    xs = [c for c in effective if c["kind"] in ("integration", "cross_stage")]
    xs_code = [c for c in xs if has_code(c)]
    cross = [c for c in xs if c["kind"] == "cross_stage"]
    integ = [c for c in xs if c["kind"] == "integration"]
    print("integration_contracts=%d/%d  cross_stage=%d  integration=%d" % (
        len(xs_code), len(xs), len(cross), len(integ)))
    pkg = {}
    for c in effective:
        row = pkg.setdefault(c["package"], [0, 0, 0])
        row[0] += 1
        if c["tests"]:
            row[1] += 1
        if has_code(c):
            row[2] += 1
    for name in sorted(pkg):
        t, s, k = pkg[name]
        print("  %s total=%d spec=%d code=%d" % (name, t, s, k))
    print("GAPS: %s" % (", ".join(c["id"] for c in gaps) or "none"))
    print("spec_guard=on (size>=200 and SPEC|assert|emit present)")
    try:
        with MANIFEST.open("r", encoding="utf-8") as fh:
            man = json.load(fh)
        mids = set(t for gs in man["stages"].values() for g in gs for t in g["tests"])
        cids = set(t for c in effective for t in c["tests"])
        orphans = sorted(mids - cids)
    except (OSError, ValueError):
        orphans = []
    print("orphan_tests=%d (%s)" % (len(orphans), ", ".join(orphans[:5]) or "none"))
    shards = load_packages()
    disputes = ["%s:%s" % (n, d.get("contract"))
                for n, pkg in shards.items() for d in pkg.get("owner_disputes", [])]
    print("owner_disputes=%d (%s)" % (len(disputes), ", ".join(disputes) or "none"))
    print("registered_packages=%d/%d" % (len(shards), target_package_count()))
    stubs_dir = ROOT / "stubs"
    required_stubs = ["settlement.json", "notary.json", "loader.json", "vocabulary.json"]
    missing_stubs = [n for n in required_stubs if not (stubs_dir / n).is_file()]
    print("contract_stubs=%d/%d" % (len(required_stubs) - len(missing_stubs), len(required_stubs)))
    if missing_stubs:
        print("  missing stubs: %s" % ", ".join(missing_stubs))
    ready = (not gaps and len(with_code) == len(with_spec)
             and len(golden) > 0 and len(golden_code) == len(golden)
             and not missing_stubs
             and len(cross) > 0 and len(integ) > 0 and len(xs_code) == len(xs))
    print("HANDOFF: %s" % ("READY" if ready else "NOT_READY"))
    if not ready:
        print("reason: gaps, spec-only contracts, missing golden path, missing shared stubs, or missing cross-stage/integration coverage")
    return 0 if ready else 1


def load_packages():
    out = {}
    if PACKAGES_DIR.is_dir():
        for p in sorted(PACKAGES_DIR.glob("*.json")):
            try:
                with p.open("r", encoding="utf-8") as fh:
                    d = json.load(fh)
                out[d["package"]] = d
            except (OSError, ValueError, KeyError):
                continue
    return out


def resolve_blockers(pkg):
    """Resolve blockers strictly: an empty title or a 0-byte config cannot unlock.

    Audit P1/mid: `contains:## D14` accepted a one-line empty shell, and
    `file_exists` accepted an empty or unparseable JSON file. Both are now
    content checks so a work order cannot be unblocked without a real decision.
    """
    rows = []
    for b in pkg.get("blocked_by", []):
        target = b.get("unblock_when", "")
        chk = b.get("status_check", "")
        resolved = False
        if chk.startswith("contains:"):
            needle = chk.split(":", 1)[1]
            f = PROJECT_ROOT / target.split("#")[0]
            if f.is_file():
                text = f.read_text(encoding="utf-8")
                if needle in text:
                    # require a substantive section body after the heading
                    section = text.split(needle, 1)[1].split("\n## ", 1)[0]
                    resolved = len(section.strip()) >= 80
        elif chk == "file_exists":
            f = PROJECT_ROOT / target
            if f.is_file() and f.stat().st_size > 0:
                if f.suffix == ".json":
                    try:
                        data = json.loads(f.read_text(encoding="utf-8"))
                        # {} or {"$comment":...} is a placeholder, not a decision.
                        substantive = [k for k in data if not k.startswith("$")]
                        resolved = bool(substantive)
                    except ValueError:
                        resolved = False
                else:
                    resolved = True
        rows.append((b.get("decision", "?"), resolved, target))
    return rows


def write_path_overlaps(pkgs):
    pairs = []
    names = sorted(pkgs)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            pa = pkgs[a].get("writable", [])
            pb = pkgs[b].get("writable", [])
            hits = [x for x in pa for y in pb
                    if x == y or x.startswith(y) or y.startswith(x)]
            if hits:
                pairs.append((a, b, hits))
    return pairs


def _scan_engine_axis_literals(core_dir):
    """I2: engine core must not contain concrete instance axis names."""
    forbidden = ("hp", "atk", "def", "health", "hunger", "stamina")
    hits = []
    for path in core_dir.glob("*.py"):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            code = line.split("#", 1)[0]
            for axis in forbidden:
                if "'%s'" % axis in code or '"%s"' % axis in code:
                    hits.append("%s:%d:%s" % (path.name, lineno, axis))
    return hits


def _scan_instance_engine_imports():
    """I3: instance declarations must not import engine internals."""
    forbidden = ("from src.core", "import src.core", "from core.", "import ledger")
    hits = []
    roots = [PROJECT_ROOT / "content" / "instances", ROOT / "fixtures"]
    for base in roots:
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in (".py", ".json"):
                text = path.read_text(encoding="utf-8")
                for token in forbidden:
                    if token in text:
                        hits.append("%s:%s" % (path.relative_to(PROJECT_ROOT), token))
    return hits


def _scan_render_writes(render_dir):
    """I6: the render layer must never write the ledger.

    Static boundary check: no engine import, no ledger mutation calls. This is
    the machine-checkable half of "render never touches the ledger"; the other
    half is S1-G4-01's runtime SHA check (which P5 already satisfies).
    """
    if not render_dir.is_dir():
        return None  # P5 not landed yet -> PENDING
    forbidden = ("settle(", "commit(", ".credits", "_ledger", "from src.core",
                 "import src.core")
    hits = []
    for path in sorted(render_dir.rglob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            code = line.split("#", 1)[0]
            for token in forbidden:
                if token in code:
                    hits.append("%s:%d:%s" % (path.name, lineno, token))
    return hits


def _runtime_snapshot_equal():
    """I8: admission snapshot deep-equals ledger; run the real engine if landed."""
    ledger_fixture = ROOT / "fixtures" / "f3-ledger.json"
    core = PROJECT_ROOT / "src" / "core" / "ledger.py"
    if not ledger_fixture.is_file() or not core.is_file():
        return None
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.core.ledger import Engine
        import json as _json
        ledger = _json.loads(ledger_fixture.read_text(encoding="utf-8"))
        return dict(Engine(ledger).snapshot()) == ledger
    except Exception:
        return None


def invariants_report():
    """Executable body for I1~I8. Contract-level + runtime checks where landed."""
    def stub(name):
        p = ROOT / "stubs" / name
        if not p.is_file():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            return {}

    settlement = stub("settlement.json")
    vocab = stub("vocabulary.json")
    codes = settlement.get("error_codes", [])
    required = vocab.get("entry_schema", {}).get("required", [])
    core_dir = PROJECT_ROOT / "src" / "core"
    has_impl = core_dir.is_dir() and any(core_dir.glob("*.py"))
    rows = []

    rows.append(("I1", "PASS" if "rejected_direct_write" in codes else "FAIL",
                 "error_codes 含 rejected_direct_write"))
    if not has_impl:
        rows.append(("I2", "PENDING", "引擎核心未落地，无属性名字面量可扫描"))
        rows.append(("I3", "PENDING", "引擎核心未落地，副本 import 扫描待激活"))
    else:
        axis_hits = _scan_engine_axis_literals(core_dir)
        rows.append(("I2", "FAIL" if axis_hits else "PASS",
                     "属性名字面量命中=%s" % (",".join(axis_hits) or "0")))
        import_hits = _scan_instance_engine_imports()
        rows.append(("I3", "FAIL" if import_hits else "PASS",
                     "副本 import 引擎命中=%s" % (",".join(import_hits) or "0")))
    rows.append(("I4", "PASS" if settlement.get("settlement_manifest", {}).get("frozen") is True else "FAIL",
                 "结算清单字段集冻结"))
    rows.append(("I5", "PASS" if "id" in required else "FAIL",
                 "词汇表条目含 id 且引用须命中"))
    render_hits = _scan_render_writes(PROJECT_ROOT / "src" / "render")
    if render_hits is None:
        rows.append(("I6", "PENDING", "渲染层未落地（src/render 不存在）；P5 落地后自动激活"))
    else:
        rows.append(("I6", "FAIL" if render_hits else "PASS",
                     "渲染层账本写入命中=%s" % (",".join(render_hits) or "0")))
    rows.append(("I7", "PASS" if "duplicate_settlement" in codes else "FAIL",
                 "error_codes 含 duplicate_settlement"))
    snap = _runtime_snapshot_equal()
    if snap is None:
        rows.append(("I8", "PENDING", "快照深度相等无法运行（夹具或引擎缺失）"))
    else:
        rows.append(("I8", "PASS" if snap else "FAIL", "运行时快照与账本深度相等=%s" % snap))

    print("INVARIANTS  source=gates/stubs + src/")
    for i, state, why in rows:
        print("  %s %s  %s" % (i, state, why))
    tally = {s: sum(1 for _, x, _ in rows if x == s) for s in ("PASS", "FAIL", "PENDING")}
    print("summary PASS=%d FAIL=%d PENDING=%d" % (tally["PASS"], tally["FAIL"], tally["PENDING"]))
    ok = tally["FAIL"] == 0 and tally["PENDING"] == 0
    print("INVARIANT_EXIT: %s" % ("ALLOWED" if ok else "DENIED"))
    if not ok:
        pend = [i for i, s, _ in rows if s == "PENDING"]
        print("note: 未定项=%s（I6 依赖 P5 渲染层；其余随对应包落地激活）" % (",".join(pend) or "none"))
    return 0 if ok else 1


def target_package_count():
    try:
        with (ROOT / "coverage.json").open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return len([k for k in data.get("packages", {}) if k.startswith("P") and k != "PX"])
    except (OSError, ValueError):
        return 7


def package_report(name, run=False):
    """Step-1 validation: a self-contained work order from a package shard."""
    import subprocess

    pkgs = load_packages()
    hash_ok, hash_detail = verify_shards()
    print("SHARD_INTEGRITY: %s  %s" % ("OK" if hash_ok else "TAMPERED", hash_detail))
    if not hash_ok:
        # A modified shard cannot be trusted as a work order: refuse to hand it out.
        print("STARTABLE: NO")
        return 1
    if name not in pkgs:
        print("PACKAGE %s NOT REGISTERED  registered=%s" % (name, ",".join(sorted(pkgs)) or "none"))
        print("STARTABLE: NO")
        return 1
    pkg = pkgs[name]
    own = [t["id"] for t in pkg.get("tests", [])]
    shared = [t["id"] for t in pkg.get("shared_tests", [])]

    print("PACKAGE %s · %s" % (name, pkg.get("title", "")))
    print("registered_packages=%d/%d (%s)" % (len(pkgs), target_package_count(), ",".join(sorted(pkgs))))
    print("只读: %s" % ", ".join(pkg.get("readonly", [])))
    print("可写: %s" % ", ".join(pkg.get("writable", [])))
    print("验收(本包负责): %s" % ", ".join(own))
    print("参与(PX 终裁，本包不判 PASS): %s" % ", ".join(shared))
    print("全局底线: %s" % ", ".join(pkg.get("global_invariants", [])))
    if pkg.get("shard_owner") != "maintainer" or pkg.get("agent_can_edit_shard") is not False:
        print("WARN: 分片归属未锁定，agent 可能改写自己的验收清单")
    else:
        print("分片归属: maintainer（agent 只读）  config_owner=%s" % pkg.get("config_owner", "UNSET"))
    fakes = [r for r in pkg.get("readonly", []) if "fake_" in r]
    if fakes:
        print("fake_mode=on (%d 个契约替身): 包级 PASS 不等价于 X04 集成通过" % len(fakes))
    for dep in pkg.get("runtime_depends_on", []):
        print("运行时依赖: %s -> %s" % (dep.get("package"), dep.get("needs")))
    for d in pkg.get("owner_disputes", []):
        print("归属争议: %s 分片=%s coverage=%s [%s]" % (
            d.get("contract"), d.get("shard_says"), d.get("coverage_says"), d.get("status")))

    blockers = resolve_blockers(pkg)
    for dec, ok, tgt in blockers:
        print("阻塞: %s [%s]  unblock_when=%s" % (dec, "RESOLVED" if ok else "UNRESOLVED", tgt))
    for dep in pkg.get("downstream_dependents", []):
        print("连带阻塞: %s (%s)" % (dep, "已登记分片" if dep in pkgs else "未登记分片"))

    ids = own + shared
    present = [i for i in ids if (TESTS_DIR / (i.lower() + ".py")).is_file()]
    print("test_files=%d/%d" % (len(present), len(ids)))
    overlaps = write_path_overlaps(pkgs)
    print("write_path_overlap=%d" % len(overlaps))
    for a, b, hits in overlaps:
        print("  OVERLAP %s/%s: %s" % (a, b, ",".join(hits)))

    non_pass = 0
    if run:
        if not own:
            print("WARN: shard declares zero own tests; RUN_EXIT cannot be trusted")
            non_pass += 1
        for tid in own:
            path = TESTS_DIR / (tid.lower() + ".py")
            if not path.is_file():
                print("TEST %s MISSING" % tid)
                non_pass += 1
                continue
            status, line = judge_test(path, tid)
            print(line)
            if status != "PASS":
                non_pass += 1
        print("own_tests: run=%d non_pass=%d" % (len(own), non_pass))
        # shared tests are PX-final, but a package must still surface their state
        if shared:
            shared_bad = 0
            for tid in shared:
                path = TESTS_DIR / (tid.lower() + ".py")
                status, line = judge_test(path, tid) if path.is_file() else ("MISSING", "TEST %s MISSING" % tid)
                if status != "PASS":
                    shared_bad += 1
            print("shared_tests(PX final, informational): run=%d non_pass=%d" % (len(shared), shared_bad))

    unresolved = [d for d, ok, _ in blockers if not ok]
    startable = not unresolved
    print("STARTABLE: %s" % ("YES" if startable else "BLOCKED (%s)" % ",".join(unresolved)))
    if run:
        print("RUN_EXIT: %s" % ("PASS" if non_pass == 0 else "NOT_PASS(%d)" % non_pass))
        print("signals: STARTABLE=阻塞判定, RUN_EXIT=测试判定, 两者独立")
        return 0 if non_pass == 0 else 1
    print("signals: STARTABLE=阻塞判定 (run 模式改为返回测试判定)")
    return 0 if startable else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", help="check a single stage, e.g. s1")
    ap.add_argument("--run", action="store_true", help="execute test files, not just check existence")
    ap.add_argument("--coverage", action="store_true", help="report architecture contract coverage")
    ap.add_argument("--package", help="generate a self-contained work order, e.g. P4")
    ap.add_argument("--invariants", action="store_true", help="run I1~I8 global invariant checks")
    ap.add_argument("--baseline", action="store_true", help="ratchet check: no regression vs baseline.json")
    ap.add_argument("--write-baseline", action="store_true", help="regenerate baseline.json from current results")
    ap.add_argument("--write-package-hashes", action="store_true", help="regenerate package_hashes.json after approved shard changes")
    args = ap.parse_args()

    if args.write_package_hashes:
        return write_shard_hashes()
    if args.coverage:
        return coverage_report()
    if args.invariants:
        return invariants_report()
    if args.package:
        return package_report(args.package, args.run)
    if args.write_baseline or args.baseline:
        try:
            data = load_manifest()
        except (OSError, ValueError) as exc:
            print("BASELINE manifest=UNREADABLE %s" % exc)
            return 1
        return baseline_report(data, write=args.write_baseline)

    if args.stage and args.stage not in ("s0", "s1", "s2", "s3", "s4", "sc", "si"):
        print("unknown stage: %s" % args.stage)
        print("GATE_EXIT: DENIED")
        return 1

    try:
        data = load_manifest()
    except (OSError, ValueError) as exc:
        print("GATE CHECK  manifest=UNREADABLE  %s" % exc)
        print("GATE_EXIT: DENIED")
        return 1

    errors, stats = check(data, args.stage)
    label = args.stage or "all"

    print("GATE CHECK  stage=%s  manifest=gates/manifest.json  run=%s" % (label, args.run))
    if stats:
        print("hard_tests=%d  pending=%d  missing_active_files=%d" % (
            stats["total"], stats["pending"], stats["missing"]))
        b = stats["by_layer"]
        print("by_layer: invariant=%d  config_driven=%d  human_in_loop=%d" % (
            b["invariant"], b["config_driven"], b["human_in_loop"]))
        if stats["missing_sample"]:
            print("missing sample: %s" % ", ".join(stats["missing_sample"]))
    for err in errors:
        print("ERROR: %s" % err)

    counts, detail = None, []
    if args.run:
        counts, lines, detail = run_tests(data, args.stage)
        for line in lines:
            print(line)
        print("runner: PASS=%d FAIL=%d PENDING=%d MISSING=%d" % (
            counts["PASS"], counts["FAIL"], counts["PENDING"], counts["MISSING"]))
        print("judge: strict (exit=0, one TEST line, id match)")

    allowed = not errors and stats.get("pending", 0) == 0 and stats.get("missing", 0) == 0
    if counts is not None:
        allowed = allowed and counts["FAIL"] == 0 and counts["PENDING"] == 0
        allowed = allowed and counts["PASS"] == stats["total"]
    else:
        print("runner_exit=not_run")

    print("GATE_EXIT: %s" % ("ALLOWED" if allowed else "DENIED"))
    if not allowed:
        print("reason: pending gates, missing test files, or red tests; red phase is the expected starting state")
    return 0 if allowed else 1


if __name__ == "__main__":
    sys.exit(main())
