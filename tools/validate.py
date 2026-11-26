"""Settlement manifest validation CLI (S4-G1-01 / S3-G5-01 / S4-G1-03).

Usage
-----
    python tools/validate.py                       # canonical F4 fixture (CI wiring)
    python tools/validate.py <manifest.json>       # validate one manifest file
    python tools/validate.py -                     # read one manifest from stdin
    python tools/validate.py <file> --volume-config path/to/volume.json

Exit 0 = valid; non-zero = rejected. A rejection is one clean, single-line
report naming the offending field, its JSON path and its line number — never a
raw traceback. The report is written to stdout (machine-readable verdict) and
mirrored to stderr (conventional error stream).

The path of this script is fixed by config/paths.json -> validation_cli; the CI
wiring calls it with no arguments, so that mode must keep accepting F4.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.contract import ContractViolation, validate_file, validate_manifest  # noqa: E402


def _reject(violation):
    line = "validate: " + violation.render()
    print(line)
    print(line, file=sys.stderr)
    return 1


def _load_stdin():
    text = sys.stdin.read()
    try:
        manifest = json.loads(text)
    except ValueError as exc:
        raise ContractViolation("manifest", "invalid_json", str(exc), "$", 1) from None
    validate_manifest(manifest, text=text, source="<stdin>")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a settlement manifest")
    parser.add_argument("manifest", nargs="?",
                        help="manifest JSON path (default: canonical F4 fixture; '-' reads stdin)")
    parser.add_argument("--volume-config",
                        help="volume.json path for total_volume checks (default: config/volume.json)")
    args = parser.parse_args(argv)

    if args.manifest == "-":
        try:
            _load_stdin()
        except ContractViolation as exc:
            return _reject(exc)
        except Exception as exc:  # never leak a traceback
            return _reject(ContractViolation("manifest", "validation_error",
                                             "%s: %s" % (type(exc).__name__, exc), "$", None))
        print("validate: valid <stdin>")
        return 0

    target = args.manifest or "gates/fixtures/f4-settlement.json"
    try:
        validate_file(target, volume=args.volume_config)
    except ContractViolation as exc:
        return _reject(exc)
    except Exception as exc:  # defensive: CLI must stay traceback-free
        return _reject(ContractViolation("manifest", "validation_error",
                                         "%s: %s" % (type(exc).__name__, exc), "$", None))

    if args.manifest is None:
        print("validate: F4 OK")
    else:
        print("validate: valid %s" % args.manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
