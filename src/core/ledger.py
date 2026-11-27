"""Ledger access layer: the engine owns the ledger; instances only get a frozen view."""

import copy
import hashlib
import json
from collections.abc import Mapping


class Rejected(Exception):
    """A settlement or a direct write was refused. Message carries the error code."""


def digest(ledger):
    """Stable SHA-256 of a ledger, used by isolation tests."""
    blob = json.dumps(dict(ledger), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _deep_freeze(value):
    """Recursively convert mutable containers into immutable views.

    dict -> _FrozenDict, list -> tuple, scalar -> itself. This closes the
    nested-write loophole (view['ability_ids'].append(...)) found in the audit.
    """
    if isinstance(value, dict):
        return _FrozenDict({k: _deep_freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_deep_freeze(v) for v in value)
    return value


class _FrozenDict(Mapping):
    """Immutable mapping; any mutation attempt raises the contract error code."""

    def __init__(self, data):
        self.__data = data  # name-mangled; no public _data to write through

    def __getitem__(self, key):
        return self.__data[key]

    def __iter__(self):
        return iter(self.__data)

    def __len__(self):
        return len(self.__data)

    def __setitem__(self, key, value):
        raise Rejected("rejected_direct_write:" + str(key))

    def __delitem__(self, key):
        raise Rejected("rejected_direct_write:" + str(key))


class _ReadOnlyLedger(Mapping):
    """Deep-frozen ledger view handed to instances. No write path, no public data."""

    def __init__(self, data, hooks=None):
        # Deep-copy then deep-freeze: nested lists/dicts are immutable views.
        self.__data = _FrozenDict(_deep_freeze(copy.deepcopy(data)))
        self.__hooks = hooks if hooks is not None else _NullHooks()

    def __getitem__(self, key):
        return self.__data[key]

    def __iter__(self):
        return iter(self.__data)

    def __len__(self):
        return len(self.__data)

    def as_dict(self):
        """Return a plain mutable dict snapshot with normal Python containers.

        The view itself stays deep-frozen; callers that need to work with the
        data (e.g. downstream instances) use this explicit copy.
        """
        return _thaw(self.__data)

    def __setitem__(self, key, value):
        self.__hooks.reject("rejected_direct_write", str(key))
        raise Rejected("rejected_direct_write:" + str(key))

    def __delitem__(self, key):
        self.__hooks.reject("rejected_direct_write", str(key))
        raise Rejected("rejected_direct_write:" + str(key))


def _thaw(value):
    """Reverse _deep_freeze: immutable views back to plain dict/list."""
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


class Engine:
    """Owns one ledger. The only write entry point is settle()."""

    def __init__(self, ledger, hooks=None):
        self._ledger = copy.deepcopy(ledger)
        self._seen = set()
        self._hooks = hooks if hooks is not None else _NullHooks()
        self.__peak_tier = 0  # C25 memorial: engine-owned, never from a manifest

    @property
    def peak_tier(self):
        """C25 '曾到达 X 阶' — read-only memorial value (no setter)."""
        return self.__peak_tier

    def ledger(self):
        """Return a deep-frozen view. Any write attempt raises Rejected."""
        return _ReadOnlyLedger(self._ledger, self._hooks)

    def snapshot(self):
        """Admission snapshot: a deep copy of the ledger at this instant."""
        return copy.deepcopy(self._ledger)

    def settle(self, manifest, registry=None, task_volume=None, tier=1):
        """Commit one settlement manifest. Returns the new frozen ledger view.

        D18 dual-track:
          * scoring chain DISABLED (values unratified): legacy credit_delta path
            stays authoritative so structural tests remain green. No claims
            payout is honoured.
          * scoring chain ENABLED: credit_delta is no longer an authority; a
            success must carry structured claims and the engine recomputes the
            payout via D12. Double-reporting both is rejected.

        failure/aborted are always engine-computed (C11/D14, D16) regardless.
        """
        from .settlement import check_manifest
        from .penalty import engine_completed_delta
        from .scoring import is_enabled, decode_claims, compute_payout, tier_coefficient

        scoring_on = is_enabled()
        check_manifest(manifest, scoring_enabled=scoring_on)

        if manifest["completion"] == "success":
            if scoring_on:
                claims = decode_claims(manifest)
                if claims is None:
                    raise Rejected("rejected_unratified_scoring:claims_required")
                effective_delta = compute_payout(
                    claims, ledger_credits=self._ledger.get("credits"),
                    tier_coefficient=tier_coefficient(tier))
            else:
                # legacy: credit_delta remains the only source while the
                # scoring chain is unratified; claims never changes credits.
                effective_delta = manifest["credit_delta"]
        else:
            effective_delta = engine_completed_delta(manifest, volume=task_volume)

        key = manifest.get("idempotency_key")
        if key is not None and key in self._seen:
            self._hooks.reject("duplicate_settlement", key)
            raise Rejected("duplicate_settlement:" + key)

        ids = list(manifest.get("ability_ids", [])) + list(manifest.get("item_ids", []))
        if registry is not None:
            unknown = [i for i in ids if i not in registry]
            if unknown:
                self._hooks.reject("rejected_unnotarized", ",".join(unknown))
                raise Rejected("rejected_unnotarized:" + ",".join(unknown))

        if key is not None:
            self._seen.add(key)

        next_ledger = copy.deepcopy(self._ledger)
        next_ledger["credits"] = next_ledger.get("credits", 0) + effective_delta
        self._ledger = next_ledger
        self._hooks.committed(manifest["instance_id"], effective_delta)
        # C25: record the highest tier the engine has settled. Not part of the
        # ledger, not from the manifest, no setter — purely commemorative.
        if tier > self.__peak_tier:
            self.__peak_tier = tier
        return self.ledger()


class _NullHooks:
    def reject(self, code, detail):
        pass

    def committed(self, instance_id, delta):
        pass
