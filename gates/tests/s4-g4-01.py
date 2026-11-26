"""S4-G4-01: submitter is genuinely external.

SPEC (00 §7 S4-G4-01): submitter absent from config/maintainers.json L0/L1 lists
and absent from S0~S3 implementation history.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import stage_skeleton

if __name__ == "__main__":
    sys.exit(stage_skeleton("S4-G4-01", "00 §7 S4-G4-01", ("config/maintainers.json",)))
