from __future__ import annotations

from typing import List

import os

from config import LOG_PATH


def read_log_lines(limit: int = 500) -> List[str]:
    """
    读取日志文件的最后 limit 行。
    """
    if not os.path.exists(LOG_PATH):
        return []

    with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    if limit <= 0 or len(lines) <= limit:
        return [line.rstrip("\n") for line in lines]
    return [line.rstrip("\n") for line in lines[-limit:]]


def clear_log() -> None:
    """清空日志文件。"""
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("")
