"""S2-G1-01: instances are data, never engine code (01/D15).

A new declarative instance must add no line to the engine core, and must live
under content/instances/. This checks the structural boundary, not gameplay.
"""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))

ID = "S2-G1-01"


def _core_digest():
    core = ROOT / "src" / "core"
    h = hashlib.sha256()
    for p in sorted(core.glob("*.py")):
        h.update(p.name.encode("utf-8"))
        h.update(p.read_bytes())
    return h.hexdigest()


def main():
    base = ROOT / "content" / "instances"
    if not base.is_dir():
        return emit(ID, "FAIL", "content/instances missing")
    instances = sorted(p for p in base.glob("*/instance.json"))
    if not instances:
        return emit(ID, "FAIL", "no declarative instances found")
    # no executable code may live inside instance directories
    scripts = [p for p in base.rglob("*.py")]
    if scripts:
        return emit(ID, "FAIL", "instances contain executable code: %s" %
                    ",".join(str(p.relative_to(ROOT)) for p in scripts))
    before = _core_digest()
    # loading an instance must not touch the engine core on disk
    import src.loader as loader
    for inst in instances:
        loader.load(inst)
    if _core_digest() != before:
        return emit(ID, "FAIL", "engine core changed while loading instances")
    return emit(ID, "PASS", "%d declarative instances, 0 scripts, engine core unchanged" % len(instances))


if __name__ == "__main__":
    sys.exit(main())
