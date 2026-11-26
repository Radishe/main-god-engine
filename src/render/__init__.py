"""P5 呈现层包：render_profile 元数据解析（D17 占位）。

对外只暴露纯数据 API。本包只读包命名空间配置并返回呈现元数据副本，
不写入任何状态，也不导入引擎模块。
"""

from .registry import (
    known_profiles,
    is_valid,
    affects_settlement,
    resolve,
    resolve_instance,
    describe,
)

__all__ = [
    "known_profiles",
    "is_valid",
    "affects_settlement",
    "resolve",
    "resolve_instance",
    "describe",
]
