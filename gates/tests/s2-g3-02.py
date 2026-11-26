"""S2-G3-02: in-instance death flow is a decision with definite fields.

SPEC (00 §5 S2-G3-02): death classification enum is single-valued;
erasure-count inclusion is boolean; lethal condition is decidable; all non-empty.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import stage_skeleton

if __name__ == "__main__":
    sys.exit(stage_skeleton("S2-G3-02", "00 §5 S2-G3-02", ("config/states.json",)))
