"""S1-G1-01: engine core has no attribute-name literals (00 §4).

Scan <engine-core>/** for concrete axis names in CODE (comments stripped the
same way as invariant I2). Hit count must be 0. config/, tests/, fixtures/ are
not part of engine core and are not scanned.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S1-G1-01"
# I2's full forbidden set (superset of 00 §4's hp|atk|def|health|hunger)
FORBIDDEN = ("hp", "atk", "def", "health", "hunger", "stamina")


def main():
    paths = json.loads((ROOT / "config" / "paths.json").read_text(encoding="utf-8"))
    core = ROOT / paths["engine_core"]
    if not core.is_dir():
        return emit(ID, "FAIL", "engine core dir missing: %s" % paths["engine_core"])

    hits = []
    files = sorted(core.glob("*.py"))
    for src in files:
        for lineno, line in enumerate(src.read_text(encoding="utf-8").splitlines(), 1):
            code = line.split("#", 1)[0]
            for axis in FORBIDDEN:
                if "'%s'" % axis in code or '"%s"' % axis in code:
                    hits.append("%s:%d:%s" % (src.name, lineno, axis))
    if hits:
        return emit(ID, "FAIL", "axis literals in engine core: " + ",".join(hits))

    ev = ROOT / "evidence" / "s1"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g1-01.txt").write_text(
        "engine_core=%s\nscanned=%d files\nforbidden=%s\nhits=0\n" % (
            paths["engine_core"], len(files), ",".join(FORBIDDEN)),
        encoding="utf-8")
    return emit(ID, "PASS", "0 axis literals across %d engine files" % len(files))


if __name__ == "__main__":
    sys.exit(main())
