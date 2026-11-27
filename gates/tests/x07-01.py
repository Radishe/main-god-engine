"""X07-01: D2 contract-tagged instance — mechanism generality proof.

Companion to X06-01 (D1). D2 differs in every axis that should NOT matter to
the engine: scene_tag=contract, a declared contract, and a disjoint axis set
(trust/standing/obligation, none of D1's hp/hunger/stamina). The same pipeline
must still work — that is what 'generality' means here.

  load -> notary.admit -> apply_event -> validate.py -> Engine.settle -> ledger

SCOPE HONESTY: scene_tag is currently DECLARATIVE METADATA. C15 ratified its
structure (enum/unknown-rejected/declared-by-author) and interaction rules
(PVP/trade protection) in config/scenes.json, but no execution layer reads
scene_tag yet, and tax/notary rates are explicitly UNRATIFIED (D22). This test
verifies the settled structure + that the tag does not leak into the frozen
manifest field set or the engine. It records the execution gap as a finding —
it does NOT pretend contract behaviour is enforced in the engine.
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

ID = "X07-01"
D2_DIR = ROOT / "content" / "instances" / "D2"


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
    decl = D2_DIR / "instance.json"
    manifest = D2_DIR / "settlement.json"
    if not decl.is_file() or not manifest.is_file():
        return emit(ID, "FAIL", "D2 declaration or manifest missing")

    # 1. C15 settled structure: contract is a ratified tag, declared by author
    scenes = json.loads((ROOT / "config" / "scenes.json").read_text(encoding="utf-8"))
    ratified = scenes.get("ratified", {})
    if "contract" not in ratified.get("enum", []):
        return emit(ID, "FAIL", "contract tag not in ratified enum")
    if ratified.get("declared_by") != "instance_author":
        return emit(ID, "FAIL", "scene_tag declaration ownership drift")
    contract_rules = scenes.get("per_tag_rules", {}).get("contract", {})
    if contract_rules.get("enforced_by") != "declared_contract":
        return emit(ID, "FAIL", "contract enforcement declaration drift")
    if scenes.get("tax_or_notary_rate", {}).get("status") != "UNRATIFIED":
        return emit(ID, "FAIL", "tax rate no longer UNRATIFIED (D22)")

    # 2. load D2 — contract tag + disjoint axis set
    d2 = loader.load(decl)
    if d2.get("scene_tag") != "contract":
        return emit(ID, "FAIL", "D2 scene_tag != contract")
    if not isinstance(d2.get("contract"), dict) or not d2["contract"].get("terms"):
        return emit(ID, "FAIL", "D2 declared contract missing terms")
    axis_keys = set(d2["axes"])
    if axis_keys & {"hp", "hunger", "stamina"}:
        return emit(ID, "FAIL", "D2 reuses D1 axes — not a generality probe")
    declared_volume = d2["settlement_evidence"]["volume"]

    # 3. admit with real vocabulary
    registry = vocabulary.load_all()
    base = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    hooks = Hooks()
    engine = Engine(base, hooks=hooks)
    ok, markers, _ = notary.admit(d2, engine.ledger().as_dict(), asset_library=set(registry))
    if not ok or not notary.steps_complete(markers):
        return emit(ID, "FAIL", "D2 admission markers incomplete: %s" % markers)

    # 4. generic event on an axis the engine has never heard of
    h0 = sha(engine.ledger().as_dict())
    axes, touched = loader.apply_event(d2, tick=1)
    ev = d2["events"][0]
    if axes[ev["axis"]] != d2["axes"][ev["axis"]] + ev["delta"]:
        return emit(ID, "FAIL", "D2 event not applied generically to %s" % ev["axis"])
    if sha(engine.ledger().as_dict()) != h0:
        return emit(ID, "FAIL", "ledger changed during D2 event (not via settle)")

    # 5. CLI validates D2's manifest; scene_tag must NOT be in frozen fields
    proc = subprocess.run([sys.executable, str(ROOT / "tools" / "validate.py"), str(manifest)],
                          cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        return emit(ID, "FAIL", "D2 manifest rejected by CLI: %s" % (proc.stdout or proc.stderr)[:150])
    stub = json.loads((ROOT / "gates" / "stubs" / "settlement.json").read_text(encoding="utf-8"))
    sm = stub["settlement_manifest"]
    if "scene_tag" in set(sm["required"]) | set(sm.get("optional", [])):
        return emit(ID, "FAIL", "scene_tag leaked into frozen manifest field set")
    mf = json.loads(manifest.read_text(encoding="utf-8"))
    if "scene_tag" in mf:
        return emit(ID, "FAIL", "D2 manifest smuggled scene_tag into settlement")
    claims = decode_claims(mf)
    if claims["volume"] != declared_volume or claims["score"] != declared_volume:
        return emit(ID, "FAIL", "claims score/volume must derive from D2 declaration")

    # 6. the single real ledger write; payout from scoring chain, not from tag
    engine.settle(dict(mf, idempotency_key="X07-D2-001"))
    h1 = sha(engine.ledger().as_dict())
    if len(hooks.commits) != 1 or h1 == h0:
        return emit(ID, "FAIL", "settle did not produce exactly one credited write")
    if sha(engine.ledger().as_dict()) != digest(engine.ledger()):
        return emit(ID, "FAIL", "digest mismatch after settle")
    payout = compute_payout(claims)
    final = engine.ledger().as_dict()
    expected = dict(base)
    expected["credits"] = base["credits"] + payout
    if final != expected:
        return emit(ID, "FAIL", "final ledger mismatch: %r vs %r" % (final, expected))

    ev = ROOT / "evidence" / "content"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "d2-contract-full-chain.json").write_text(json.dumps({
        "instance": "D2", "scene_tag": "contract", "axes": sorted(axis_keys),
        "declared_volume": declared_volume, "payout": payout,
        "commits": hooks.commits, "cli": "valid",
        "known_gap": "scene_tag is declarative metadata; no execution layer reads it "
                     "(C15 interaction rules settled in config, tax rates UNRATIFIED)",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return emit(ID, "PASS", "D2 contract-tagged chain: disjoint axes + declared contract "
                "settle identically; credits +%d; scene_tag stayed declarative (gap recorded)" % payout)


if __name__ == "__main__":
    sys.exit(main())
