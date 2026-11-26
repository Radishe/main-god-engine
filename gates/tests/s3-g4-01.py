"""S3-G4-01: A/B/C deduction uses one valuation unit.

SPEC (00 §6 S3-G4-01): with A insufficient and B/C needed, all three asset kinds
are compared in the unit declared by config/penalty.json; log carries that unit.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import stage_skeleton

if __name__ == "__main__":
    sys.exit(stage_skeleton("S3-G4-01", "00 §6 S3-G4-01", ("config/penalty.json",)))
