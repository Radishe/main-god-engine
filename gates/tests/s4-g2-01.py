"""S4-G2-01: checklist items are all closed, no dangling checks.

SPEC (00 §7 S4-G2-01): all 11 items have status defined or removed;
no third value; defined items have an object definition in config/checklist.json.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import stage_skeleton

if __name__ == "__main__":
    sys.exit(stage_skeleton("S4-G2-01", "00 §7 S4-G2-01", ("config/checklist.json",)))
