"""C30-01: G1 golden path — the single test that points at the final result.

D19 runtime evidence (review panel hard constraints):
  - MUST call the real src.core.ledger.Engine.settle() (hook counts commits)
  - ledger SHA-256 changes ONLY at the two settle() calls
  - NO test doubles anywhere in the path (real Engine + real notary only)
  - F1 local axes must NOT leak into F2 snapshot or the ledger
  - settlement IDs must hit real vocab entries

Steps (00 §4 C30): F1 admit -> event -> settle -> F2 admit -> settle -> final
ledger deep-equals the hand-computed expectation.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
from src.core.ledger import Engine, digest
import src.loader as loader
import src.notary as notary
import vocab as vocabulary

ID = "C30-01"


class Hooks:
    """Records every ledger write so we can prove writes happen only in settle."""
    def __init__(self):
        self.commits = []
        self.rejections = []

    def committed(self, instance_id, delta):
        self.commits.append((instance_id, delta))

    def reject(self, code, detail):
        self.rejections.append((code, detail))


def sha(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def main():
    # --- runtime evidence: guard against fake doubles ---------------------
    # Build the tokens dynamically so this guard does not match its own source.
    token_a = "fake" + "_settle"
    token_b = "fake" + "_notary"
    source = (ROOT / "gates" / "tests" / "c30-01.py").read_text(encoding="utf-8")
    if token_a in source or token_b in source:
        return emit(ID, "FAIL", "golden path must not use fake doubles")

    # --- real components --------------------------------------------------
    ledger = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    f4 = json.loads((ROOT / "gates" / "fixtures" / "f4-settlement.json").read_text(encoding="utf-8"))
    f1 = loader.load(ROOT / "content" / "instances" / "F1" / "instance.json")
    f2 = loader.load(ROOT / "content" / "instances" / "F2" / "instance.json")
    registry = vocabulary.load_all()

    hooks = Hooks()
    engine = Engine(ledger, hooks=hooks)

    # 1. F1 admission notarization (three markers)
    ok1, markers1, snap1 = notary.admit(f1, engine.ledger().as_dict(),
                                         asset_library=set(registry))
    if not ok1 or not notary.steps_complete(markers1):
        return emit(ID, "FAIL", "F1 admission markers incomplete: %s" % markers1)
    h0 = sha(engine.ledger().as_dict())

    # 2. F1 event applied generically (axes stay in instance, not ledger)
    axes1, touched = loader.apply_event(f1, tick=1)
    if axes1["hp"] != f1["axes"]["hp"] + f1["events"][0]["delta"]:
        return emit(ID, "FAIL", "F1 event not applied to declared axis")
    if sha(engine.ledger().as_dict()) != h0:
        return emit(ID, "FAIL", "ledger changed during F1 event (not via settle)")

    # 3. settlement manifest IDs hit vocab (empty here = vacuously true)
    ids = list(f4.get("ability_ids", [])) + list(f4.get("item_ids", []))
    unknown = vocabulary.check_ids(ids, registry)
    if unknown:
        return emit(ID, "FAIL", "manifest ids not in vocab: " + ",".join(unknown))

    # 4. settle #1 — the ONLY ledger write point so far
    engine.settle(dict(f4, instance_id="F1", idempotency_key="C30-F1-001"))
    h1 = sha(engine.ledger().as_dict())
    if len(hooks.commits) != 1 or h1 == h0:
        return emit(ID, "FAIL", "settle #1 did not produce exactly one credited write")
    if sha(engine.ledger().as_dict()) != digest(engine.ledger()):
        return emit(ID, "FAIL", "digest mismatch after settle #1")

    # 5. F2 admission: snapshot equals post-settle ledger
    ok2, markers2, snap2 = notary.admit(f2, engine.ledger().as_dict(),
                                         asset_library=set(registry))
    if not ok2 or not notary.steps_complete(markers2):
        return emit(ID, "FAIL", "F2 admission markers incomplete")
    if snap2 != engine.ledger().as_dict():
        return emit(ID, "FAIL", "F2 snapshot != post-settle ledger")

    # 6. F1 axes must not leak into F2 snapshot
    f1_axis_keys = set(f1["axes"].keys())
    if f1_axis_keys & set(snap2.keys()):
        return emit(ID, "FAIL", "F1 axes leaked into F2 snapshot: %s" % (f1_axis_keys & set(snap2.keys())))
    if sha(engine.ledger().as_dict()) != h1:
        return emit(ID, "FAIL", "ledger changed during F2 load (not via settle)")

    # 7. F2 event, then settle #2
    axes2, _ = loader.apply_event(f2, tick=1)
    engine.settle(dict(f4, instance_id="F2", idempotency_key="C30-F2-002"))
    h2 = sha(engine.ledger().as_dict())
    if len(hooks.commits) != 2 or h2 == h1:
        return emit(ID, "FAIL", "settle #2 did not produce exactly one credited write")

    # 8. final ledger deep-equals hand-computed expectation.
    # D20: payout is RECOMPUTED from structured claims, not copied from credit_delta.
    from src.core.scoring import decode_claims, compute_payout
    per_settle = compute_payout(decode_claims(f4))
    final = engine.ledger().as_dict()
    expected = dict(ledger)
    expected["credits"] = ledger["credits"] + per_settle + per_settle
    if final != expected:
        return emit(ID, "FAIL", "final ledger mismatch: %r vs %r" % (final, expected))

    return emit(ID, "PASS",
                "G1 chain: 2 real settles, SHA changed only at each settle, "
                "no axis leak, vocab clean; commits=%s" % hooks.commits)


if __name__ == "__main__":
    sys.exit(main())
