"""S2-G2-01: reproduction material pack is isolated.

human_in_loop test: the machine checks the evidence trail, a human signs it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S2-G2-01"


def main():
    trail = ROOT / "evidence" / "s2" / "g2-01.txt"
    if not trail.is_file():
        return emit(ID, "FAIL", "material manifest not produced; expected red phase")
    text = trail.read_text(encoding="utf-8")
    forbidden = ["_chat_full", "会话记录", "设计讨论过程", "engine_core_src"]
    leaked = [w for w in forbidden if w in text]
    if leaked:
        return emit(ID, "FAIL", "material pack leaked: " + ",".join(leaked))
    if "签字" not in text:
        return emit(ID, "FAIL", "human signature missing")
    return emit(ID, "PASS", "material pack isolated and signed")


if __name__ == "__main__":
    sys.exit(main())
