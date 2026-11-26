"""S3-G6-01: timeline basis is a single enum.

SPEC (00 §6 S3-G6-01): config/timeline.json basis is one enum value;
every timeline statement in the docs references that config.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import stage_skeleton

if __name__ == "__main__":
    sys.exit(stage_skeleton("S3-G6-01", "00 §6 S3-G6-01", ("config/timeline.json",)))
