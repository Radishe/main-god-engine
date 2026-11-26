"""P5 呈现层：render_profile 元数据注册表与解析器。

纯数据层：只读包自有命名空间 config/p5/profiles.json，按 profile 返回
呈现元数据副本。render_profile 仅是元数据占位（D17），不触发真实渲染、
不参与结算、也不持有任何永久状态；切换只替换呈现描述，不触碰数据层。
"""

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILES_PATH = ROOT / "config" / "p5" / "profiles.json"


def _load_registry():
    """读取注册表原始数据（每次调用即读，保证配置是唯一事实源）。"""
    return json.loads(PROFILES_PATH.read_text(encoding="utf-8"))


def known_profiles():
    """按声明顺序返回注册表中的全部合法 profile 取值。"""
    return tuple(_load_registry()["profiles"].keys())


def is_valid(profile):
    """判断一个 profile 取值是否在注册表中。"""
    return profile in _load_registry()["profiles"]


def affects_settlement():
    """恒为 False：呈现层不影响结算（契约常量，来自包配置）。"""
    return _load_registry()["affects_settlement"]


def resolve(profile):
    """按 profile 返回呈现元数据（深拷贝）；未知取值返回 None。

    返回值只描述呈现：管线名、投影方式、光照模型、资源提示。
    不含任何结算字段，调用方修改返回值不会污染注册表。
    """
    entry = _load_registry()["profiles"].get(profile)
    if entry is None:
        return None
    return copy.deepcopy(entry)


def resolve_instance(instance):
    """从副本声明中读取 render_profile 并解析；无合法取值时返回 None。"""
    if not isinstance(instance, dict):
        return None
    return resolve(instance.get("render_profile"))


def describe(profile):
    """返回可用于加载日志的单行呈现描述；未知取值返回未解析占位串。"""
    meta = resolve(profile)
    if meta is None:
        return "render_profile=%s unresolved" % profile
    view = meta["presentation"]
    return "render_profile=%s pipeline=%s projection=%s lighting=%s" % (
        meta["id"], meta["pipeline"], view["projection"], view["lighting"])
