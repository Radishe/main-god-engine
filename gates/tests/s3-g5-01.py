"""S3-G5-01: inflated total volume is rejected.

SPEC (00 §6 S3-G5-01): total_volume above config/volume.json limit yields
non-zero exit, error names total_volume and includes the limit value.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import stage_skeleton

if __name__ == "__main__":
    sys.exit(stage_skeleton("S3-G5-01", "00 §6 S3-G5-01", ("config/volume.json",)))
