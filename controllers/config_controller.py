from __future__ import annotations

from typing import Any, Dict

from config import CONFIG


def get_all_config() -> Dict[str, Dict[str, Any]]:
    """
    返回原始配置字典：
    {
        "KEY": {"value": xxx, "desc": "说明"},
        ...
    }
    """
    return CONFIG.to_dict()


def reload_config() -> None:
    """从 config.json 重新加载配置。"""
    CONFIG.reload()


def _cast_value(key: str, raw_value: str) -> Any:
    """
    根据当前 value 的类型对字符串输入做类型转换。
    """
    info = CONFIG.get_info(key)
    if info is None:
        # 不存在该 key，直接返回原字符串
        return raw_value

    current = info.get("value", None)
    t = type(current)

    if t is int:
        return int(raw_value)
    if t is float:
        return float(raw_value)
    if t is bool:
        # 支持常见形式
        v = raw_value.strip().lower()
        return v in ("1", "true", "yes", "y", "on")
    if t in (list, dict):
        # 尝试用 json 解析
        import json

        return json.loads(raw_value)

    # 其他一律当字符串
    return raw_value


def update_config_value(key: str, raw_value: str) -> None:
    """
    更新单个配置项的 value（字符串输入 -> 自动类型转换）。
    """
    new_value = _cast_value(key, raw_value)
    CONFIG[key] = new_value
