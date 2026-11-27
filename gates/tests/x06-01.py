"""X06-01: D1 full chain — declaration -> notarization -> CLI -> settle -> ledger.

Content-production proof: a REAL instance (D1, not a fixture) walks the whole
pipeline with real components. Every step is a real call; no doubles.

  load D1 declaration -> notary.admit (3 markers) -> apply declared event
  -> validate.py checks D1's OWN manifest -> Engine.settle recomputes payout
  -> ledger lands, SHA changes only at settle, payout == scoring chain result.

Numbers are NOT invented: score=volume=12 comes from D1's declaration; payout
is recomputed under D20. credit_delta in the manifest stays 0 (D20: engine
recomputes, never copies).
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
from src.core.ledger import Engine, digest
from src.core.scoring import decode_claims, compute_payout
import src.loader as loader
import src.notary as notary
import vocab as vocabulary

ID = "X06-01"
D1_DIR = ROOT / "content" / "instances" / "D1"


class Hooks:
    def __init__(self):
        self.commits = []

    def committed(self, instance_id, delta):
        self.commits.append((instance_id, delta))

    def reject(self, code, detail):
        pass


def sha(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def main():
    decl = D1_DIR / "instance.json"
    manifest = D1_DIR / "settlement.json"
    if not decl.is_file() or not manifest.is_file():
        return emit(ID, "FAIL", "D1 declaration or manifest missing")

    # 1. load the real declaration
    d1 = loader.load(decl)
    declared_volume = d1["settlement_evidence"]["volume"]
    if declared_volume != 12:
        return emit(ID, "FAIL", "D1 declared volume drift: %r" % declared_volume)

    # 2. notarization with real vocabulary registry
    registry = vocabulary.load_all()
    base = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    hooks = Hooks()
    engine = Engine(base, hooks=hooks)
    ok, markers, snap = notary.admit(d1, engine.ledger().as_dict(), asset_library=set(registry))
    if not ok or not notary.steps_complete(markers):
        return emit(ID, "FAIL", "D1 admission markers incomplete: %s" % markers)

    # 3. declared event applied on instance axes, ledger untouched
    h0 = sha(engine.ledger().as_dict())
    axes, touched = loader.apply_event(d1, tick=1)
    if axes["stamina"] != d1["axes"]["stamina"] + d1["events"][0]["delta"]:
        return emit(ID, "FAIL", "D1 sprint event not applied to declared stamina axis")
    if sha(engine.ledger().as_dict()) != h0:
        return emit(ID, "FAIL", "ledger changed during D1 event (not via settle)")

    # 4. real CLI validates D1's own manifest
    proc = subprocess.run([sys.executable, str(ROOT / "tools" / "validate.py"), str(manifest)],
                          cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        return emit(ID, "FAIL", "D1 manifest rejected by CLI: %s" % (proc.stdout or proc.stderr)[:150])

    mf = json.loads(manifest.read_text(encoding="utf-8"))
    if mf["instance_id"] != "D1":
        return emit(ID, "FAIL", "manifest instance_id != D1")
    if mf["credit_delta"] != 0:
        return emit(ID, "FAIL", "credit_delta must stay 0 (D20 recomputes)")
    claims = decode_claims(mf)
    if claims["volume"] != declared_volume or claims["score"] != declared_volume:
        return emit(ID, "FAIL", "claims score/volume must derive from D1 declaration")

    # 5. the single real ledger write
    engine.settle(dict(mf, idempotency_key="X06-D1-001"))
    h1 = sha(engine.ledger().as_dict())
    if len(hooks.commits) != 1 or h1 == h0:
        return emit(ID, "FAIL", "settle did not produce exactly one credited write")
    if sha(engine.ledger().as_dict()) != digest(engine.ledger()):
        return emit(ID, "FAIL", "digest mismatch after settle")

    # 6. ledger lands at the scoring-chain-derived payout
    payout = compute_payout(claims)
    final = engine.ledger().as_dict()
    expected = dict(base)
    expected["credits"] = base["credits"] + payout
    if final != expected:
        return emit(ID, "FAIL", "final ledger mismatch: %r vs %r" % (final, expected))

    ev = ROOT / "evidence" / "content"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "d1-full-chain.json").write_text(json.dumps({
        "instance": "D1", "declared_volume": declared_volume, "payout": payout,
        "commits": hooks.commits, "cli": "valid", "ledger_sha_before": h0,
        "ledger_sha_after": h1,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return emit(ID, "PASS", "D1 full chain: admit -> event -> CLI valid -> settle -> "
                "credits +%d, SHA changed only at settle" % payout)


if __name__ == "__main__":
    sys.exit(main())
