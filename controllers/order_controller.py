from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import List, Dict, Any
from config import EXPORT_DIR
from sqlmodel import select
import re
import os
import csv  # 新增：用于写入/读取 CSV
from config import CONFIG
from db import get_session
from models.order import Order
from utils.douyin import batch_aweme_likes

def query_order_refund_amount():
    """
    遍历导出的 CSV 文件，按每行：
      缺失数量 / 下单数量 * 订单总价
    的公式累加为总收入。订单总价与下单数量以数据库为准，通过订单ID查询。
    """
    total_income = 0.0
    export_dir = EXPORT_DIR
    if not os.path.isdir(export_dir):
        return 0.0

    # 统一复用一个会话
    with get_session() as s:
        for filename in os.listdir(export_dir):
            if not filename.endswith(".csv"):
                continue
            file_path = os.path.join(export_dir, filename)
            try:
                with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # 从 CSV 读取订单ID与缺失数量
                        try:
                            order_id = int((row.get("订单ID") or "0").strip() or 0)
                            deficiency = int((row.get("缺失的数量") or "0").strip() or 0)
                        except ValueError:
                            continue
                        if order_id <= 0 or deficiency <= 0:
                            continue

                        # 查库获取订单总价与下单数量
                        stmt = select(Order).where(Order.id == order_id)
                        found: List[Order] = list(s.exec(stmt))
                        if not found:
                            continue
                        o = found[0]

                        try:
                            order_num = int(o.order_num or 0)
                        except Exception:
                            order_num = 0
                        if order_num <= 0:
                            continue

                        try:
                            order_amount = float(o.order_amount or 0)
                        except Exception:
                            order_amount = 0.0

                        total_income += (deficiency / order_num) * order_amount
            except Exception as e:  # noqa: BLE001
                logging.warning(f"读取导出文件失败: {file_path}, 错误: {e}")
                continue

    return total_income


def _format_ts(ts: int | None) -> str:
    """将时间戳转换为易读格式，空值返回空字符串。"""
    if not ts:
        return ""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(ts)))


def query_finished_orders_for_monitor() -> List[Dict[str, Any]]:
    """
    查询：
      - 配置中的指定商品ID（MONITORED_GOOD_IDS）
      - 已完成的订单（order_status == 4）
      - tb_time 在 [now - EXPORT_TIME_OFFSET - EXPORT_TIME_INTERVAL, now - EXPORT_TIME_OFFSET) 之间
    并将时间戳转为可读字符串返回。
    """
    now = int(time.time())
    export_time_offset = int(CONFIG["EXPORT_TIME_OFFSET"])
    export_time_interval = int(CONFIG["EXPORT_TIME_INTERVAL"])
    monitored_ids = CONFIG["MONITORED_GOOD_IDS"] or []

    start_ts = now - export_time_offset
    end_ts = start_ts + export_time_interval

    if not monitored_ids:
        return []

    stmt = (
        select(Order)
        .where(Order.goods_id.in_(monitored_ids))
        .where(Order.order_status == 4)
        .where(Order.tb_time.is_not(None))
        .where(Order.tb_time >= start_ts)
        .where(Order.tb_time < end_ts)
        .order_by(Order.tb_time.desc())
    )

    with get_session() as s:
        orders: List[Order] = list(s.exec(stmt))

    result: List[Dict[str, Any]] = []
    pattern = re.compile(r'(https?://[^\s]+)"')
    for o in orders:
        link = (
            re.search(pattern, o.params).group(1)
            if re.search(pattern, o.params)
            else ""
        )
        result.append(
            {
                "id": o.id,
                "order_s_n": o.order_s_n,
                "goods_id": o.goods_id,
                "goods_name": o.goods_name,
                "link": link,
                "s_name": o.s_name,
                "order_num": o.order_num,
                "order_amount": str(o.order_amount),
                "order_num": o.order_num,
                "start_num": o.start_num,
                "current_num": o.current_num,
                "order_status": o.order_status,
                "create_at": _format_ts(o.create_at),
                "tb_time": _format_ts(o.tb_time),
                "other_order_s_n": o.other_order_s_n or "",  # 新增：三方订单号
            }
        )
    return result


async def export_deficiency_orders_links():
    """
    导出所有数量缺失的订单，按商品名称分组生成 CSV：
    {EXPORT_DIR}/{current_time_str}_{goods_name}.csv
    列包含：
    商品名称, 商品ID, 链接, 订单号, 订单ID, 三方订单号, 缺失的数量, 订单总价, 下单数量, 初始数量, 当前数量
    """
    def _sanitize_filename(name: str) -> str:
        # 仅保留中英文、数字、下划线和连字符，其余替换为下划线
        return re.sub(r'[^0-9A-Za-z\u4e00-\u9fff_-]+', '_', name).strip('_') or 'unknown'

    orders = query_finished_orders_for_monitor()
    current_real_nums = await batch_aweme_likes(orders)

    # 按商品名称分组行
    rows_by_goods: Dict[str, List[Dict[str, Any]]] = {}
    deficiency_links_by_goods: Dict[str, List[str]] = {}

    for i in range(len(orders)):
        orders[i]["current_num"] = current_real_nums[i]
        produced = orders[i]["current_num"] - orders[i]["start_num"]
        deficiency_num = orders[i]["order_num"] - produced
        if deficiency_num > 0:
            goods_name = orders[i]["goods_name"] or "unknown"
            rows_by_goods.setdefault(goods_name, []).append(
                {
                    "商品名称": goods_name,
                    "商品ID": orders[i]["goods_id"],
                    "链接": orders[i]["link"],
                    "订单号": orders[i]["order_s_n"],
                    "订单ID": orders[i]["id"],
                    "三方订单号": orders[i].get("other_order_s_n", "") or "",
                    "缺失的数量": deficiency_num,
                    "订单总价": orders[i]["order_amount"],
                    "下单数量": orders[i]["order_num"],
                    "初始数量": orders[i]["start_num"],
                    "当前数量": orders[i]["current_num"],
                }
            )
            deficiency_links_by_goods.setdefault(goods_name, []).append(orders[i]["link"])
            logging.info(f"数量缺失：{orders[i]['link']} 缺失 {deficiency_num} 个")

    # 写出 CSV
    os.makedirs(EXPORT_DIR, exist_ok=True)
    current_time_str = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
    headers = [
        "商品名称",
        "商品ID",
        "链接",
        "订单号",
        "订单ID",
        "三方订单号",
        "缺失的数量",
        "订单总价",
        "下单数量",
        "初始数量",
        "当前数量",
    ]

    for goods_name, rows in rows_by_goods.items():
        safe_name = _sanitize_filename(goods_name)
        file_path = f"{EXPORT_DIR}/{current_time_str}_{safe_name}.csv"
        try:
            with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
        except Exception as e:  # noqa: BLE001
            logging.error(f"写入导出文件失败: {file_path}, 错误: {e}")

    # 返回分组的链接（兼容原有调用）
    return deficiency_links_by_goods




