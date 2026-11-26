"""S3-G6-02: entering an instance consumes timeline, not pauses it.

SPEC (00 §6 S3-G6-02): enter -> save -> stay N ticks -> exit; countdown equals
the config model's computed value and differs from the pre-entry value.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import stage_skeleton

if __name__ == "__main__":
    sys.exit(stage_skeleton("S3-G6-02", "00 §6 S3-G6-02", ("config/timeline.json",)))
