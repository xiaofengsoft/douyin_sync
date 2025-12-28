from __future__ import annotations

from typing import List, Dict
import os
import datetime as dt
import csv  # 新增：CSV 读取

from config import EXPORT_DIR


def list_export_files() -> List[Dict]:
    """
    列出导出目录下的 CSV 文件：
    返回 [{name, path, size, mtime}]，按时间倒序。
    """
    os.makedirs(EXPORT_DIR, exist_ok=True)
    files: List[Dict] = []
    for name in os.listdir(EXPORT_DIR):
        path = os.path.join(EXPORT_DIR, name)
        if not os.path.isfile(path):
            continue
        # 仅保留 .csv
        if not name.lower().endswith(".csv"):
            continue
        stat = os.stat(path)
        files.append(
            {
                "name": name,
                "path": path,
                "size": stat.st_size,
                "mtime": dt.datetime.fromtimestamp(stat.st_mtime),
            }
        )
    files.sort(key=lambda x: x["mtime"], reverse=True)
    return files


def read_file_content(path: str) -> str:
    """读取指定文件内容。安全起见，仅允许在 EXPORT_DIR 下的文件。"""
    abs_export = os.path.abspath(EXPORT_DIR)
    abs_path = os.path.abspath(path)
    if not abs_path.startswith(abs_export):
        raise ValueError("非法文件路径")
    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def delete_files_between(start: dt.datetime, end: dt.datetime) -> int:
    """
    删除导出目录中在 [start, end] 间修改的文件，返回删除数量。
    """
    files = list_export_files()
    count = 0
    for f in files:
        if start <= f["mtime"] <= end:
            os.remove(f["path"])
            count += 1
    return count


def delete_all_files() -> int:
    """删除导出目录中所有文件，返回删除数量。"""
    files = list_export_files()
    count = 0
    for f in files:
        os.remove(f["path"])
        count += 1
    return count


def read_csv_table(path: str) -> Dict[str, List]:
    """
    读取 CSV 文件为表格数据：
    返回 {"headers": List[str], "rows": List[Dict[str, str]]}
    """
    abs_export = os.path.abspath(EXPORT_DIR)
    abs_path = os.path.abspath(path)
    if not abs_path.startswith(abs_export):
        raise ValueError("非法文件路径")
    if not abs_path.lower().endswith(".csv"):
        raise ValueError("仅支持 CSV 文件")

    with open(abs_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = [dict(r) for r in reader]
    return {"headers": headers, "rows": rows}
