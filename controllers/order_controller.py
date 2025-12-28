from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import List, Dict, Any
from config import EXPORT_DIR
from sqlmodel import select
import re
from config import CONFIG
from db import get_session
from models.order import Order
from utils.douyin import batch_aweme_likes


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
            }
        )
    return result


async def export_deficiency_orders_links():
    """
    导出所有数量缺失的订单，按 goods_name 分文件导出：
    {EXPORT_DIR}/{current_time_str}_{goods_name}.txt
    """
    def _sanitize_filename(name: str) -> str:
        # 仅保留中英文、数字、下划线和连字符，其余替换为下划线
        return re.sub(r'[^0-9A-Za-z\u4e00-\u9fff_-]+', '_', name).strip('_') or 'unknown'

    orders = query_finished_orders_for_monitor()
    current_real_nums = await batch_aweme_likes(orders)
    deficiency_links_by_goods: Dict[str, List[str]] = {}

    for i in range(len(orders)):
        orders[i]["current_num"] = current_real_nums[i]
        # 如果数量缺失，按 goods_name 分组记录链接
        if orders[i]["current_num"] - orders[i]["start_num"] < orders[i]["order_num"]:
            goods_name = orders[i]["goods_name"] or "unknown"
            deficiency_link = orders[i]["link"]
            deficiency_num = orders[i]["order_num"] - (
                orders[i]["current_num"] - orders[i]["start_num"]
            )
            deficiency_links_by_goods.setdefault(goods_name, []).append(deficiency_link)
            logging.info(f"数量缺失：{deficiency_link} 缺失 {deficiency_num} 个")

    current_time_str = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
    for goods_name, links in deficiency_links_by_goods.items():
        safe_name = _sanitize_filename(goods_name)
        file_path = f"{EXPORT_DIR}/{current_time_str}_{safe_name}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            for link in links:
                f.write(link + "\n")
    # 把分组记录的链接返回
    return deficiency_links_by_goods




