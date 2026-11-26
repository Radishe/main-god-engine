"""P4 兑换解析接口 —— 纯函数，供 C14-01 真断言 import。

语义约定（不可发明的东西）：
- cost 是结构占位（structural placeholder），不是调参后的物品兑换价目。
  D20 的 1:1 是评分汇率，与物品兑换价无关；payout_for 原样返回条目 cost。
- effect 只认词汇表中已登记的字符串；词汇表之外一律拒绝。
- 不依赖 src.core / src.loader / src.render；只读 vocab/ 与 gates/stubs/vocabulary.json。
- 每次调用重新读盘，不缓存可变状态，调用方拿到的是独立 dict 副本。

稳定入口（维护者按此签名接断言）：
- all_entries()            -> list[dict]   全部词汇表来源的条目副本
- exchange_entries()       -> list[dict]   仅 vocab/exchange.json 的条目副本
- lookup(item_id)          -> dict | None  按精确 id 命中全部词汇表来源
- known_effects()          -> set[str]     词汇表中出现过的全部 effect
- is_known_effect(effect)  -> bool         仅当字符串且命中词汇表时为 True
- payout_for(item_id)      -> int | None   条目的结构占位 cost；id 未命中返回 None
- duplicate_ids()          -> list[str]    重复出现的 id（用于全局唯一性断言）
- is_well_formed(entry)    -> bool         按 stub entry_schema 校验字段齐全与 kind 枚举
"""

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_VOCAB_DIR = _ROOT / "vocab"
_STUB_PATH = _ROOT / "gates" / "stubs" / "vocabulary.json"


def _stub():
    return json.loads(_STUB_PATH.read_text(encoding="utf-8"))


def _source_paths():
    """词汇表来源路径，单一真相来自 gates/stubs/vocabulary.json（只读）。"""
    return [_ROOT / rel for rel in _stub()["sources"]]


def _rows(path):
    """读一个词汇表来源；兼容裸数组（exchange.json）与 {"entries": [...]}。"""
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data.get("entries", [])


def all_entries():
    """[dict] 全部词汇表来源的条目副本；每次调用返回新的 dict，不共享可变状态。"""
    rows = []
    for path in _source_paths():
        rows.extend(dict(row) for row in _rows(path))
    return rows


def exchange_entries():
    """[dict] 仅 vocab/exchange.json 的条目副本（C14 的直接契约来源）。"""
    return [dict(row) for row in _rows(_VOCAB_DIR / "exchange.json")]


def lookup(item_id):
    """条目 dict 或 None：按精确 id 命中全部词汇表来源（含 items/abilities/exchange）。"""
    for entry in all_entries():
        if entry.get("id") == item_id:
            return entry
    return None


def known_effects():
    """set[str] 词汇表中登记过的全部 effect 字符串。"""
    return {e["effect"] for e in all_entries() if isinstance(e.get("effect"), str)}


def is_known_effect(effect):
    """bool：仅当 effect 是字符串且命中词汇表时为 True，其余一律 False（拒绝）。"""
    return isinstance(effect, str) and effect in known_effects()


def payout_for(item_id):
    """条目 cost（结构占位兑换点）或 None（id 未命中）。

    cost 不是价目表数值；兑换点的增减方向由结算层决定，这里只给出占位幅度。
    """
    entry = lookup(item_id)
    if entry is None:
        return None
    return entry.get("cost")


def duplicate_ids():
    """[str] 在词汇表中出现多次的 id；空列表即 id 全局唯一。"""
    seen, dup = set(), []
    for entry in all_entries():
        item_id = entry.get("id")
        if item_id in seen and item_id not in dup:
            dup.append(item_id)
        seen.add(item_id)
    return dup


def is_well_formed(entry):
    """bool：按 gates/stubs/vocabulary.json 的 entry_schema 校验字段与 kind 枚举。"""
    schema = _stub()["entry_schema"]
    if not isinstance(entry, dict):
        return False
    if any(key not in entry for key in schema["required"]):
        return False
    if schema.get("id_unique") and not isinstance(entry.get("id"), str):
        return False
    kind_spec = schema.get("kind", "")
    allowed = set(kind_spec[5:-1].split("|")) if kind_spec.startswith("enum<") else set()
    return entry.get("kind") in allowed
