"""S4-G3-01: contribution contract documents exist.

SPEC (00 §7 S4-G3-01): CONTRIBUTING.md, SCHEMA.md, REVIEW.md, TAKEDOWN.md
all exist, are non-empty, and contain the section titles registered in config/docs.json.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import stage_skeleton

if __name__ == "__main__":
    sys.exit(stage_skeleton("S4-G3-01", "00 §7 S4-G3-01", ("config/docs.json",)))
