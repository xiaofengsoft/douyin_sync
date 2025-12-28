from __future__ import annotations

import time
from typing import Any, Dict, List

from nicegui import ui

from controllers.order_controller import (
    query_finished_orders_for_monitor,
    export_deficiency_orders_links,
)
from config import CONFIG


def _format_ts(ts: int | None) -> str:
    if not ts:
        return ""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(ts)))


def show_order_page():
    """订单查看页面：实时查看符合配置条件的已完成订单。"""
    ui.page_title("订单查看")

    now = int(time.time())
    export_time_offset = int(CONFIG["EXPORT_TIME_OFFSET"])
    export_time_interval = int(CONFIG["EXPORT_TIME_INTERVAL"])

    start_ts = now - export_time_offset
    end_ts = start_ts + export_time_interval
    time_range_str = f"{_format_ts(start_ts)} ~ {_format_ts(end_ts)}"

    with ui.row().classes("items-center justify-between px-4 py-2"):
        ui.label("订单查看").classes("text-h6")
        ui.label(f"时间窗口：{time_range_str}").classes("text-sm text-grey-7")

        with ui.row().classes("items-center gap-2"):

            def on_refresh():
                ui.navigate.reload()

            ui.button("刷新", on_click=on_refresh)

            def on_export():
                with ui.dialog() as dlg, ui.card():
                    ui.label("正在导出缺失订单链接，请稍候...")
                    ui.spinner(size="lg")
                dlg.open()

                async def do_export():
                    try:
                        await export_deficiency_orders_links()
                        ui.notify("导出完成", type="positive")
                    except Exception as e:  # noqa: BLE001
                        ui.notify(f"导出失败: {e}", type="negative")
                    finally:
                        dlg.close()

                ui.timer(0.1, do_export, once=True)

            ui.button("一键导出缺失订单链接", on_click=on_export).props("color=primary")

    rows: List[Dict[str, Any]] = query_finished_orders_for_monitor()

    columns = [
        {"name": "id", "label": "ID", "field": "id"},
        {"name": "order_s_n", "label": "订单号", "field": "order_s_n"},
        {"name": "goods_id", "label": "商品ID", "field": "goods_id"},
        {"name": "goods_name", "label": "商品名称", "field": "goods_name"},
        {"name": "order_amount", "label": "金额", "field": "order_amount"},
        {"name": "s_name", "label": "对接站点", "field": "s_name"},
        {"name": "create_at", "label": "创建时间", "field": "create_at"},
        {"name": "link", "label": "链接", "field": "link"},
        {"name": "start_num", "label": "初始数量", "field": "start_num"},
        {"name": "current_num", "label": "当前数量", "field": "current_num"},
        {"name": "order_num", "label": "订单数量", "field": "order_num"},
        {"name": "tb_time", "label": "tb_time", "field": "tb_time"},
    ]

    with ui.column().classes("p-4 gap-3 w-full"):
        if not rows:
            ui.label("当前时间窗口内没有符合条件的订单").classes("text-grey-6")
            return

        ui.table(
            columns=columns,
            rows=rows,
            row_key="id",
        ).classes("w-full")
