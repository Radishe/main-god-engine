"""Minimal main-god engine core (P1 slice 1).

Scope of this slice: a single settle() that accepts F4, changes only credits,
hands instances a read-only ledger view, and supports admission snapshots.
No gameplay numbers live here; field definitions come from gates/stubs/settlement.json.
"""
