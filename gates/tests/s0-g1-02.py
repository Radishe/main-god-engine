"""S0-G1-02: D15 is a ratified decision with both contribution channels (00 §3).

D15 body must describe the declarative channel AND the code channel, each
with its own review flow, and the channel boundary must be single-valued.
This checks a ratIfied decision's structure — not a gameplay number.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S0-G1-02"
DECS = ROOT / "docs" / "设计决议记录.md"
STUB = ROOT / "gates" / "stubs" / "loader.json"


def main():
    if not DECS.is_file():
        return emit(ID, "FAIL", "decision record missing")
    text = DECS.read_text(encoding="utf-8")
    import re
    m = re.search(r"^## D15\b.*?$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return emit(ID, "FAIL", "D15 section not found")
    body = m.group(1)

    # two channels, each with a review-flow cue
    declarative = any(k in body for k in ("声明式 JSON", "声明式"))
    code = any(k in body for k in ("DLL", "代码通道"))
    decl_review = any(k in body for k in ("Schema validation CI", "Schema validation", "可机检"))
    code_review = any(k in body for k in ("独立审核流程", "受限沙盒", "权限受限沙盒"))
    problems = []
    if not declarative:
        problems.append("declarative channel absent")
    if not code:
        problems.append("code channel absent")
    if not decl_review:
        problems.append("declarative review flow absent")
    if not code_review:
        problems.append("code channel review flow absent")

    # single-valued channel boundary from the loader stub
    if STUB.is_file():
        stub = json.loads(STUB.read_text(encoding="utf-8"))
        boundary = stub.get("code_channel", {}).get("boundary")
        if boundary != "json_primary_dll_optin":
            problems.append("loader code_channel.boundary=%r" % boundary)

    if problems:
        return emit(ID, "FAIL", "; ".join(problems))

    ev = ROOT / "evidence" / "s0"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g1-02.md").write_text(
        "D15 ratified: declarative(JSON/Schema CI) + code(DLL/independent review+sandbox); "
        "boundary=json_primary_dll_optin\n", encoding="utf-8")
    return emit(ID, "PASS", "D15 has both channels with distinct review flows, single-valued boundary")


if __name__ == "__main__":
    sys.exit(main())
