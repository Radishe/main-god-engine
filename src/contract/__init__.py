"""P2 settlement-manifest contract validation.

Public surface (stable for the validation CLI and for maintainer assertions):

    validate_manifest(manifest, ...)  -> None, or raises ContractViolation
    validate_file(path, ...)          -> None, or raises ContractViolation
    ContractViolation                 .field / .path / .line / .code / .render()

The structure half delegates to the maintainer-owned stub via
``src.core.settlement.check_manifest``; the semantic half (F5-3/5/6 context,
S3-G5 volume) reads only shared read-only sources: gates/stubs, vocab/,
content/instances/ and config/volume.json.
"""

from .manifest import (
    ContractViolation,
    loaded_instance_ids,
    notarized_ids,
    validate_file,
    validate_manifest,
    volume_config,
)

__all__ = [
    "ContractViolation",
    "loaded_instance_ids",
    "notarized_ids",
    "validate_file",
    "validate_manifest",
    "volume_config",
]
